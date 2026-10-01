"""Explicit production smoke test with synthetic media only.

Usage: python tests/studio_remote_e2e.py --url https://... --sample path/to/synthetic.mp4
Reads private owner credentials from LOCALAPPDATA/DentFlow/studio/vercel.env and
the active Vercel bypass from worker.remote.json. Never prints either secret.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--sample', required=True, type=Path)
    args = parser.parse_args()
    if not args.url.startswith('https://'):
        raise ValueError('La prueba remota requiere HTTPS explícito.')
    source = args.sample.resolve(strict=True)
    private = Path(os.environ['LOCALAPPDATA']) / 'DentFlow' / 'studio'
    env = dict(line.split('=', 1) for line in (private / 'vercel.env').read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.startswith('#'))
    config = json.loads((private / 'worker.remote.json').read_text(encoding='utf-8-sig'))
    assert config['url'].rstrip('/') == args.url.rstrip('/')
    credentials = base64.b64encode(f"{env['OWNER_USER']}:{env['OWNER_PASSWORD']}".encode()).decode()
    headers = {'Authorization': 'Basic ' + credentials, 'x-vercel-protection-bypass': config['bypass']}
    url = args.url.rstrip('/')
    root = private.parent / 'validacion_v3' / ('remote_' + str(uuid.uuid4()))
    root.mkdir(parents=True)

    def api(path, body=None, method=None):
        request = urllib.request.Request(url + '/api/' + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={**headers, 'Content-Type': 'application/json'},
            method=method or ('POST' if body is not None else 'GET'))
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'API {path}: HTTP {error.code}') from error

    def wait(identity):
        start = time.monotonic()
        last = None
        while time.monotonic() - start < 1200:
            job = api('jobs/' + identity)
            marker = (job['status'], job.get('phase'))
            if marker != last:
                print(identity, *marker, flush=True)
                last = marker
            if job['status'] in ('failed', 'canceled'):
                raise RuntimeError(f"Trabajo {identity}: {job['status']} {job.get('error_code')}")
            if job['status'].endswith('_ready'):
                return job
            time.sleep(4)
        raise TimeoutError(identity)

    status = api('status')
    assert status['mode'] == 'REMOTE_STUDIO' and status['worker_online'] and status['seed_loaded'], status
    assert api('content/DEMO-TECNICA')['id'] == 'DEMO-TECNICA'
    print('Estado remoto listo; seed y worker en línea.', flush=True)
    reservation = api('assets', {'name': 'synthetic-check.mp4', 'mime': 'video/mp4', 'size': source.stat().st_size})
    assert reservation['mode'] == 'remote'
    node = shutil.which('node')
    assert node, 'Node necesario para la subida directa a Blob.'
    uploaded = subprocess.run([node, str(ROOT / 'worker' / 'upload.mjs')],
        input=json.dumps({'key': reservation['key'], 'token': reservation['token'], 'file': str(source)}),
        text=True, capture_output=True, timeout=240, cwd=ROOT, shell=False)
    if uploaded.returncode:
        raise RuntimeError('Falló la subida privada de Blob: ' + uploaded.stderr.strip())
    api('assets/' + reservation['id'] + '/complete', {})
    print('Subida privada terminada.', flush=True)

    request = {'content_id': 'DEMO-TECNICA', 'intent_key': str(uuid.uuid4()),
        'settings': {'engine': 'remotion', 'source_mode': 'recording',
                     'asset_id': reservation['id'], 'kind': 'preview'}}
    queued = api('jobs', request)
    duplicate = api('jobs', request)
    assert queued['id'] == duplicate['id'], 'Idempotencia falló.'
    preview = wait(queued['id'])
    assert preview['outputs'][0]['resolution'] == [360, 640]
    words = preview['report']['words']
    assert len(words) >= 2, 'ASR no reconoció la voz sintética.'
    words[0]['text'] = 'Una'
    words[1]['text'] = 'CONSULTA'
    corrected = api('jobs/' + preview['id'] + '/plan',
        {'intent_key': str(uuid.uuid4()), 'settings': {'words': words,
         'source_sha256': preview['report']['source_sha256'], 'kind': 'preview'}}, 'PATCH')
    revised = wait(corrected['id'])
    assert revised['report']['words'][1]['text'] == 'CONSULTA'
    final = api('jobs/' + revised['id'] + '/plan',
        {'intent_key': str(uuid.uuid4()), 'settings': {'kind': 'final'}}, 'PATCH')
    final = wait(final['id'])
    assert final['outputs'][0]['resolution'] == [1080, 1920]

    files = []
    for job in (preview, revised, final):
        output = job['outputs'][0]
        target = root / (job['id'] + '.mp4')
        request = urllib.request.Request(url + output['url'] + '&download=1', headers=headers)
        with urllib.request.urlopen(request, timeout=180) as response, target.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        assert fingerprint(target) == output['sha256']
        subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(target), '-f', 'null', '-'],
            check=True, capture_output=True, timeout=120)
        files.append(str(target))
    assert len({job['outputs'][0]['sha256'] for job in (preview, revised, final)}) == 3
    assert api('jobs/' + preview['id'])['outputs'][0]['sha256'] == preview['outputs'][0]['sha256']
    request = urllib.request.Request(url + final['outputs'][0]['url'], headers={**headers, 'Range': 'bytes=0-1023'})
    with urllib.request.urlopen(request, timeout=90) as response:
        assert response.status == 206 and len(response.read()) == 1024
    evidence = {'asset_id': reservation['id'], 'project_id': queued['project_id'],
        'jobs': [job['id'] for job in (preview, revised, final)], 'files': files,
        'sha256': [job['outputs'][0]['sha256'] for job in (preview, revised, final)],
        'checks': ['private_blob_upload', 'worker_online', 'seed', 'idempotency',
                   'offline_asr', 'word_corrections', 'immutable_versions',
                   'preview_360', 'final_1080', 'download_decode', 'range_206']}
    (root / 'evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('E2E remoto correcto:', root, flush=True)
    api('projects/' + queued['project_id'], method='DELETE')
    api('assets/' + reservation['id'], method='DELETE')
    print('Fixture sintético retirado del Studio.', flush=True)


if __name__ == '__main__':
    main()
