"""HTTP integration against a running LOCAL_STUDIO; creates only synthetic media."""
import argparse
import json
import os
import sys
import time
import urllib.request
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import editor as e


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:3000');ap.add_argument('--sample',type=Path);args=ap.parse_args()
    if not args.url.startswith(('http://127.0.0.1:','http://localhost:')):raise ValueError('Solo E2E local; no cargas remotas automáticas.')
    def api(path,body=None,method=None):
        req=urllib.request.Request(args.url+'/api/'+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json'},method=method or ('POST' if body is not None else 'GET'))
        try:
            with urllib.request.urlopen(req,timeout=60) as res:return json.load(res)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'API {path}: {exc.code}: {exc.read().decode()}') from exc
    def wait(identity):
        start=time.monotonic();last=None
        while time.monotonic()-start<900:
            job=api('jobs/'+identity)
            if job['status']!=last:print(identity,job['status'],flush=True);last=job['status']
            if job['status'] in ('failed','canceled'):raise RuntimeError(json.dumps(job,ensure_ascii=False))
            if job['status'].endswith('_ready'):return job
            time.sleep(3)
        raise TimeoutError(identity)
    root=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'DentFlow/validacion_v3'/('e2e_'+str(uuid.uuid4()))
    root.mkdir(parents=True)
    if args.sample:
        source=args.sample.resolve()
    else:
        from render_acceptance import make_reel
        make_reel(root/'fixture','Una consulta necesita alguien a cargo. No alcanza con responder un mensaje. Revisá el siguiente paso y quién lo sigue.')
        source=root/'fixture/raw.mp4'
    content=api('content',dict(title='E2E sintético · grabación y correcciones',script='Fixture SAPI técnico, independiente del seed V3.'))
    media=api('assets',dict(name='fixture.mp4',mime='video/mp4',size=source.stat().st_size))
    with source.open('rb') as f:
        req=urllib.request.Request(args.url+'/api/assets/'+media['id']+'/file',data=f,headers={'Content-Type':'video/mp4','Content-Length':str(source.stat().st_size)},method='PUT')
        with urllib.request.urlopen(req,timeout=120) as res:uploaded=json.load(res)
    assert uploaded['sha256']==e.fingerprint(source)
    body=dict(content_id=content['id'],intent_key=str(uuid.uuid4()),settings=dict(engine='remotion',source_mode='recording',asset_id=media['id'],kind='preview'))
    queued=api('jobs',body);duplicate=api('jobs',body);assert queued['id']==duplicate['id']
    preview=wait(queued['id']);assert preview['outputs'][0]['resolution']==[360,640]
    words=preview['report']['words'];assert len(words)>=2,'ASR sin palabras; inspeccionar fuente sintética'
    words[0]['text']='Una';words[1]['text']='CONSULTA'
    corrected=api('jobs/'+preview['id']+'/plan',dict(intent_key=str(uuid.uuid4()),settings=dict(words=words,source_sha256=preview['report']['source_sha256'],kind='preview')),'PATCH')
    revised=wait(corrected['id']);assert revised['report']['words'][1]['text']=='CONSULTA'
    final=api('jobs/'+revised['id']+'/plan',dict(intent_key=str(uuid.uuid4()),settings={'kind':'final'}),'PATCH')
    final=wait(final['id']);assert final['outputs'][0]['resolution']==[1080,1920]
    files=[]
    for j in (preview,revised,final):
        out=j['outputs'][0];path=root/(j['id']+'.mp4')
        with urllib.request.urlopen(args.url+out['url']+'&download=1',timeout=120) as src,path.open('wb') as dst:
            import shutil
            shutil.copyfileobj(src,dst)
        assert e.fingerprint(path)==out['sha256'];e.run(['ffmpeg','-v','error','-xerror','-i',path,'-f','null','-'])
        files.append(str(path))
    assert len(set(j['outputs'][0]['sha256'] for j in (preview,revised,final)))==3
    assert (api('jobs/'+preview['id']))['outputs'][0]['sha256']==preview['outputs'][0]['sha256']
    request=urllib.request.Request(args.url+final['outputs'][0]['url'],headers={'Range':'bytes=0-1023'})
    with urllib.request.urlopen(request) as res:assert res.status==206 and len(res.read())==1024
    e.write_json(root/'evidence.json',dict(content_id=content['id'],asset_id=media['id'],jobs=[preview,revised,final],files=files,
        checks=['upload_SHA','idempotency','real_progress','ASR_offline','two_word_corrections','immutable_versions','preview_360','final_1080','distinct_SHA','download_decode','range_206']))
    print('E2E HTTP PASSED:',root,flush=True)


if __name__=='__main__':main()
