"""Single-concurrency outbound worker. Never listens on a network port."""
import argparse
import hashlib
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import editor as e


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('El worker no sigue redirecciones con credenciales.')


class Client:
    def __init__(self,url,token,bypass=None):
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1')):
            raise ValueError('HTTPS requerido excepto loopback.')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('URL del Studio inválida.')
        if len(token)<32:raise ValueError('WORKER_TOKEN debe tener al menos 32 caracteres.')
        self.url=url.rstrip('/');self.token=token;self.bypass=bypass
        self.opener=urllib.request.build_opener(NoRedirect())

    def request(self,path,body=None,lease=None,method=None,file=None):
        if not path.startswith('/api/worker/'):raise ValueError('Ruta de agente inválida.')
        headers={'Authorization':'Bearer '+self.token}
        if lease:headers['X-Lease-Token']=lease
        if self.bypass:headers['x-vercel-protection-bypass']=self.bypass
        data=None
        if body is not None:data=json.dumps(body).encode();headers['Content-Type']='application/json'
        if file:
            headers.update({'Content-Type':'video/mp4','Content-Length':str(file.stat().st_size)})
            with file.open('rb') as stream:
                req=urllib.request.Request(self.url+path,data=stream,headers=headers,method='PUT')
                with self.opener.open(req,timeout=120) as res:return json.load(res)
        req=urllib.request.Request(self.url+path,data=data,headers=headers,method=method or ('POST' if body is not None else 'GET'))
        with self.opener.open(req,timeout=30) as res:return json.load(res)

    def download(self,job,asset,target,limit):
        headers={'Authorization':'Bearer '+self.token,'X-Lease-Token':job['lease_token']}
        if self.bypass:headers['x-vercel-protection-bypass']=self.bypass
        req=urllib.request.Request(f"{self.url}/api/worker/{job['id']}/assets/{asset['id']}",headers=headers)
        size=0;digest=hashlib.sha256()
        with self.opener.open(req,timeout=60) as res,target.open('xb') as out:
            while True:
                block=res.read(1024*1024)
                if not block:break
                size+=len(block)
                if size>limit:raise ValueError('invalid_media')
                digest.update(block);out.write(block)
        if size!=asset['size'] or (asset.get('sha256') and digest.hexdigest()!=asset['sha256']):raise ValueError('invalid_media')


def stop_tree(process):
    if process.poll() is not None:return
    if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=30)
    else:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name!='nt':os.killpg(process.pid,signal.SIGKILL)
        else:process.kill()
        process.wait()


def capabilities():
    result={'ffmpeg':bool(shutil.which('ffmpeg')),'whisper_offline':False,'remotion':False}
    # Do not load a second model; the full installer diagnosis verifies the model cache.
    try:
        from huggingface_hub import snapshot_download
        from faster_whisper.utils import download_model
        download_model('base',local_files_only=True)
        result['whisper_offline']=True
    except Exception:pass
    try:
        import motion
        motion.runtime();result['remotion']=True
    except Exception:pass
    return result


def execute(client,job,state,max_duration=600,timeout=3600):
    folder=state/f"{job['id']}_{job['attempt']}"
    folder.mkdir(parents=True,exist_ok=True)
    token=job['lease_token'];prefix=f"/api/worker/{job['id']}"
    canceled=threading.Event();lost=threading.Event();done=threading.Event()
    def heartbeat():
        last=time.monotonic()
        while not done.wait(10):
            try:
                result=client.request(prefix+'/heartbeat',{},token)
                last=time.monotonic()
                if result['cancel']:canceled.set()
            except Exception:
                if time.monotonic()-last>60:lost.set()
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    process=None
    try:
        if shutil.disk_usage(state).free<max(1024**3,sum(a['size'] for a in job['assets'])*5):raise RuntimeError('disk_full')
        if job['settings']['engine']=='remotion':
            import motion
            try:motion.runtime()
            except Exception as exc:raise RuntimeError('engine_unavailable') from exc
        client.request(prefix+'/progress',{'phase':'downloading'},token)
        staged={}
        for asset in job['assets']:
            if canceled.is_set():raise RuntimeError('canceled')
            ext=Path(asset['name']).suffix.lower()
            if ext not in ('.mp4','.mov','.m4v','.webm','.png','.jpg','.jpeg','.webp','.wav','.mp3','.m4a','.ogg'):raise ValueError('invalid_media')
            target=folder/(asset['id']+ext)
            if not target.exists():client.download(job,asset,target,asset['size'])
            if target.stat().st_size!=asset['size'] or (asset.get('sha256') and e.fingerprint(target)!=asset['sha256']):raise ValueError('invalid_media')
            staged[asset['id']]={**asset,'file':target.name}
        payload={k:v for k,v in job.items() if k!='lease_token'}
        payload.update(staged_assets=staged,max_duration=max_duration)
        e.write_json(folder/'job.json',payload)
        result_path=folder/'result.json'
        if not result_path.exists():
            command=[sys.executable,'-u',str(ROOT/'worker/render_job.py'),str(folder)]
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
                                     shell=False,start_new_session=os.name!='nt',env=dict(os.environ,PYTHONUTF8='1'))
            lines=queue.Queue()
            def read_lines():
                for line in process.stdout:lines.put(line)
            reader=threading.Thread(target=read_lines,daemon=True);reader.start();start=time.monotonic()
            with (folder/'engine.log').open('w',encoding='utf-8') as log:
                while process.poll() is None or not lines.empty() or reader.is_alive():
                    if canceled.is_set():raise RuntimeError('canceled')
                    if lost.is_set():raise RuntimeError('lease_lost')
                    if time.monotonic()-start>timeout:raise RuntimeError('timeout')
                    try:line=lines.get(timeout=.2)
                    except queue.Empty:continue
                    log.write(line);log.flush()
                    if line.startswith('DENTFLOW_PROGRESS '):
                        phase=json.loads(line.split(' ',1)[1])['phase']
                        client.request(prefix+'/progress',{'phase':phase},token)
            if process.returncode:raise RuntimeError('render_failed')
        result=e.read_json(result_path);file=Path(result.pop('file')).resolve()
        if not file.is_relative_to(folder.resolve()) or e.fingerprint(file)!=result['sha256']:raise ValueError('invalid_media')
        if canceled.is_set():raise RuntimeError('canceled')
        client.request(prefix+'/progress',{'phase':'uploading'},token)
        upload=client.request(prefix+'/upload-token',{'size':result['size']},token)
        if upload['mode']=='local':client.request(prefix+'/output',lease=token,file=file)
        else:
            # Only a short-lived, path-scoped client token enters the helper's stdin.
            node=shutil.which('node')
            if not node:raise RuntimeError('engine_unavailable')
            payload=json.dumps({**upload,'file':str(file)})
            uploaded=subprocess.run([node,str(ROOT/'worker/upload.mjs')],input=payload,text=True,capture_output=True,timeout=600,shell=False)
            if uploaded.returncode:raise RuntimeError('upload_failed')
        client.request(prefix+'/finish',result,token)
        (folder/'completed').write_text(str(time.time()))
        print(f"Trabajo {job['id']} terminado ({job['settings']['kind']}).",flush=True)
    except Exception as exc:
        if process:stop_tree(process)
        code=str(exc) if str(exc) in ('render_failed','canceled','invalid_media','timeout','disk_full','engine_unavailable') else 'render_failed'
        try:client.request(prefix+'/fail',{'code':code},token)
        except Exception:pass
        print(f"Trabajo {job['id']}: {code}. Diagnóstico conservado localmente.",flush=True)
    finally:
        if process and process.poll() is None:stop_tree(process)
        done.set();thread.join(timeout=1)


def cleanup(state,days=7):
    """Only completed attempt folders created by this worker, after retention expires."""
    for marker in state.glob('*/completed'):
        folder=marker.parent.resolve()
        if folder.is_relative_to(state.resolve()) and (folder/'job.json').exists() and time.time()-marker.stat().st_mtime>days*86400:
            shutil.rmtree(folder)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=Path);ap.add_argument('--once',action='store_true');args=ap.parse_args()
    config=e.read_json(args.config) if args.config else {}
    client=Client(config.get('url') or os.environ.get('STUDIO_URL','http://127.0.0.1:3000'),config.get('token') or os.environ.get('WORKER_TOKEN',''),config.get('bypass') or os.environ.get('VERCEL_AUTOMATION_BYPASS_SECRET'))
    state=Path(config.get('state_dir') or Path(os.environ.get('LOCALAPPDATA',Path.home()))/'DentFlow/studio-worker').resolve();state.mkdir(parents=True,exist_ok=True)
    worker_id=config.get('worker_id','pc-windows');caps=capabilities()
    print('Worker listo. Sondeo saliente; una edición por vez.',flush=True)
    while True:
        try:
            cleanup(state)
            response=client.request('/api/worker/lease',{'worker_id':worker_id,'capabilities':caps})
            if response['job']:execute(client,response['job'],state,int(config.get('max_duration',600)),int(config.get('timeout',3600)))
            elif args.once:return
        except KeyboardInterrupt:return
        except Exception:print('Studio no disponible; reconexión en 10 segundos.',flush=True)
        if args.once:return
        time.sleep(10)


if __name__=='__main__':main()
