"""Puente local opcional. El plan Python ya contiene TODOS los tiempos de montaje."""
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from planning import asset_path, bounded

ROOT = Path(__file__).resolve().parents[1] / 'remotion'
TEMPLATES = {'QuestionHook', 'AnimatedMessages', 'CRMHighlight', 'StepDiagram', 'ScreenshotFocus', 'SummaryCTA'}
AUDIO_EXTS = {'.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg'}


def params(value):
    if not isinstance(value, dict) or set(value) - {'title', 'subtitle', 'eyebrow', 'items', 'cta', 'theme'}:
        raise ValueError('params admite title, subtitle, eyebrow, items, cta, theme.')
    result = {}
    for key, limit in [('title', 86), ('subtitle', 130), ('eyebrow', 40), ('cta', 54)]:
        if key in value:
            text = value[key]
            if not isinstance(text, str) or len(text) > limit or any(ord(c) < 32 and c != '\n' for c in text):
                raise ValueError(f'params.{key}: texto de hasta {limit} caracteres.')
            result[key] = text
    result['theme'] = value.get('theme', 'dark')
    if result['theme'] not in ('dark', 'light'):
        raise ValueError('theme debe ser dark o light.')
    items = value.get('items', [])
    if not isinstance(items, list) or len(items) > 4:
        raise ValueError('Máximo cuatro elementos legibles por escena.')
    result['items'] = []
    previous = -1
    for item in items:
        if not isinstance(item, dict) or set(item) - {'label', 'value', 'at_seconds'}:
            raise ValueError('Cada item admite label, value y at_seconds relativo a su escena.')
        label, text = item.get('label', ''), item.get('value', '')
        if not isinstance(label, str) or not isinstance(text, str) or not label.strip() or len(label) > 40 or len(text) > 72:
            raise ValueError('Item requiere label (1–40 caracteres), value hasta 72.')
        at = bounded(item.get('at_seconds', 0), 0, 600, 'at_seconds')
        if at < previous:
            raise ValueError('items deben estar ordenados por at_seconds.')
        previous = at
        result['items'].append(dict(label=label, value=text, at_seconds=at))
    return result


def render_options(spec, override=None):
    value = spec.get('render', {})
    if not isinstance(value, dict) or set(value) - {'engine', 'template', 'music', 'captions', 'duration_seconds'}:
        raise ValueError('render admite engine, template, music, captions y duration_seconds.')
    engine = override or value.get('engine', 'ffmpeg')
    template = value.get('template', 'educativo')
    if engine not in ('ffmpeg', 'remotion') or template not in ('educativo', 'comercial'):
        raise ValueError('engine: ffmpeg|remotion; template: educativo|comercial.')
    if value.get('captions', 'remotion' if engine == 'remotion' else 'ass') not in ('ass', 'remotion'):
        raise ValueError('captions: ass|remotion; el motor elegido dibuja una sola pista.')
    music = value.get('music', {})
    if not isinstance(music, dict) or set(music) - {'enabled', 'file', 'rights_declared', 'volume', 'ducking'}:
        raise ValueError('music admite enabled, file, rights_declared, volume, ducking.')
    if not isinstance(music.get('enabled', False), bool):
        raise ValueError('music.enabled debe ser booleano.')
    music = dict(music, enabled=music.get('enabled', False))
    if music['enabled']:
        if engine != 'remotion':
            raise ValueError('Música opcional requiere --engine remotion; desactívala para FFmpeg.')
        if music.get('rights_declared') is not True or not music.get('file'):
            raise ValueError('Música requiere archivo local y rights_declared:true.')
        music['volume'] = bounded(music.get('volume', .10), 0, .3, 'music.volume')
        music['ducking'] = bounded(music.get('ducking', .35), 0, 1, 'music.ducking')
    return dict(engine=engine, template=template, music=music,
                duration_seconds=value.get('duration_seconds'))


def frame(seconds, fps):
    # Misma regla para ambos extremos, incluso en límites de medio frame.
    return int(math.floor(seconds * fps + .5))


def runtime():
    node = shutil.which('node')
    cli = ROOT / 'node_modules/@remotion/cli/remotion-cli.js'
    if not node or not cli.is_file():
        raise RuntimeError('Remotion no instalado. Ejecuta instalar_remotion.bat o usa --engine ffmpeg.')
    browsers = list((ROOT / 'node_modules/.remotion').glob('**/chrome-headless-shell.exe')) if os.name == 'nt' else list((ROOT / 'node_modules/.remotion').glob('**/chrome-headless-shell'))
    if not browsers:
        raise RuntimeError('Falta Chromium local. Ejecuta instalar_remotion.bat con conexión; luego render offline.')
    return node, cli, browsers[0]


def build_props(plan, options, job_id, base_video, assets, music=None):
    fps = plan['config']['video']['fps']
    count = frame(plan.get('mezzanine_duration', plan['output_duration']), fps)
    if abs(count / fps - plan['output_duration']) > max(.10, 2/fps):
        raise ValueError('El A-roll cortado no coincide con el timeline validado.')
    scenes = []
    for index, ev in enumerate(plan['events']):
        a, b = frame(ev['start'], fps), frame(ev['end'], fps)
        if a < 0 or b > count or b <= a:
            raise ValueError('Escena fuera de duración medida o menor que un fotograma.')
        template = ev.get('template') or ('ScreenshotFocus' if ev['type'] == 'asset' else 'QuestionHook')
        p = params(ev.get('params', {}))
        if ev.get('text'):
            p['title'] = ev['text']
        scene = dict(id=str(ev.get('id', index)), template=template, kind=ev['type'], start_frame=a,
                     duration_frames=b-a, params=p, layout=ev.get('layout', 'card'),
                     demo=ev.get('demo', False), animation=ev.get('animation', 'fade'))
        if ev['type'] == 'asset':
            scene['asset'] = assets[index]
        if ev['type'] == 'reframe':
            scene['camera'] = {k: ev[k] for k in ('scale', 'x', 'y')}
            scene['camera']['animated'] = bool(ev.get('animated'))
        for item in p['items']:
            if item['at_seconds'] >= (b-a)/fps:
                raise ValueError('Un item aparece después de terminar su escena.')
        scenes.append(scene)
    subs = plan['config']['subtitles']
    return dict(format_version=1, job_id=job_id, template=options['template'], fps=fps,
                width=plan['config']['video']['width'], height=plan['config']['video']['height'],
                duration_frames=count, base_video=base_video, scenes=scenes,
                captions=[dict(text=c['text'], startMs=c['start']*1000, endMs=c['end']*1000,
                               timestampMs=None, confidence=None) for c in plan['captions']],
                subtitle_style=dict(font_size=subs['font_size'], margin_v=subs['margin_v']),
                speech_windows=plan.get('speech_windows', []), music=music,
                metadata=dict(source_sha256=plan['sha256'], source_type=plan.get('source_type', 'recording')))


def render(cut, out, plan, spec, options, folder, run_dir, api):
    """Stages sólo material validado; subprocess sin shell ni npx/descargas runtime."""
    node, cli, browser = runtime()
    jobs = ROOT / 'public/jobs'
    jobs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='job_', dir=jobs) as directory:
        stage = Path(directory)
        prefix = 'jobs/' + stage.name + '/'
        ar = stage/'aroll.mp4'
        cfg = plan['config']
        # Ya CFR/Rec.709. Sólo convertir PCM -> AAC; nunca quemar ASS/overlays.
        api.run(api.ffmpeg_base(cfg) + ['-i', cut, '-map', '0:v:0', '-map', '0:a:0',
                '-c:v', 'copy', '-c:a', 'aac', '-ar', '48000', '-b:a', '160k', '-movflags', '+faststart', ar])
        ar_probe = api.probe(ar)
        plan['mezzanine_duration'] = float(next(s for s in ar_probe['streams'] if s['codec_type']=='video')['duration'])
        assets = {}
        for index, ev in enumerate(plan['events']):
            if ev['type'] != 'asset':
                continue
            source = asset_path(ev['file'], folder, spec.get('asset_roots', []))
            allowed = {(folder / name).resolve() for name in spec.get('allowed_assets', [])}
            if source not in allowed:
                raise ValueError('Asset de staging fuera de allowed_assets.')
            is_video = source.suffix.lower() in api.VIDEO_EXTS
            target = stage / (f'asset_{index:03d}' + ('.mp4' if is_video else '.png'))
            filters = []
            if is_video:
                stream = next(s for s in api.probe(source)['streams'] if s['codec_type']=='video')
                colors = api.color_filter(stream).rstrip(',')
                if colors:
                    filters.append(colors)
            if 'focus_region' in ev:
                x,y,w,h = ev['focus_region']
                filters.append(f'crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}')
            filters.append('scale=1080:1200:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1')
            cmd = api.ffmpeg_base(cfg)
            if is_video:
                cmd += ['-ss', str(ev['offset'])]
            cmd += ['-i', source, '-an', '-vf', ','.join(filters)]
            if is_video:
                cmd += ['-t', str(ev['end']-ev['start']), '-r', str(cfg['video']['fps']), '-c:v', 'libx264',
                        '-threads', '2', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
            else:
                cmd += ['-frames:v', '1', '-threads', '1']
            api.run(cmd+[target])
            assets[index] = dict(path=prefix+target.name, video=is_video)
        music = None
        if options['music']['enabled']:
            entry = options['music']
            path = asset_path(entry['file'], folder, spec.get('asset_roots', []))
            if path not in {(folder/name).resolve() for name in spec.get('allowed_assets', [])} or path.suffix.lower() not in AUDIO_EXTS:
                raise ValueError('Música debe estar en allowed_assets y ser audio local.')
            if api.ffprobe_duration(path) < plan['output_duration']:
                raise ValueError('Música demasiado corta: prepara una pista que cubra el montaje.')
            target = stage/('music'+path.suffix.lower())
            shutil.copyfile(path, target)
            music = dict(path=prefix+target.name, volume=entry['volume'], ducking=entry['ducking'])
        props = build_props(plan, options, stage.name, prefix+'aroll.mp4', assets, music)
        props_path = run_dir/'remotion_props.json'
        api.write_json(props_path, props)
        composition = 'DentFlowEducativo' if options['template']=='educativo' else 'DentFlowComercial'
        rendered = stage/'render.mp4'
        command = [node, str(cli), 'render', 'src/index.ts', composition, str(rendered),
                   '--props', str(props_path), '--concurrency', '1', '--codec', 'h264', '--pixel-format', 'yuv420p',
                   '--crf', str(cfg['video']['crf']), '--audio-codec', 'aac', '--audio-sample-rate', '48000',
                   '--browser-executable', str(browser), '--log', 'error']
        started = time.monotonic()
        with (run_dir/'remotion_log.txt').open('w', encoding='utf-8') as log:
            try:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                        shell=False, timeout=3600, env=dict(os.environ, REMOTION_DISABLE_TELEMETRY='1'))
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError('Remotion superó 60 minutos. Revisa remotion_log.txt; reduce duración o usa FFmpeg.') from exc
        if result.returncode:
            raise RuntimeError('Remotion falló. Revisa remotion_log.txt; instala el motor o vuelve a --engine ffmpeg.')
        plan['remotion_seconds'] = round(time.monotonic()-started,2)
        # Normalización final de la mezcla (una vez); también asegura +faststart/AAC 48k.
        audible = api.audio_analysis(rendered, plan['output_duration'])['audible']
        af = f"loudnorm=I={cfg['audio']['target_lufs']}:LRA=11:TP=-1.5" if cfg['audio']['normalize'] and audible else 'anull'
        api.run(api.ffmpeg_base(cfg)+['-i',rendered,'-map','0:v:0','-map','0:a:0','-c:v','copy',
                '-af',af,'-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart',out])
        plan['staging'] = 'temporales eliminados; props preservadas como evidencia, regenerar desde edicion.json'


def validate_scene(ev):
    if ev.get('template') not in TEMPLATES:
        raise ValueError('template no pertenece al catálogo Remotion permitido.')
    ev['params'] = params(ev.get('params', {}))
    if ev['type']=='motion' and not ev['params'].get('title'):
        raise ValueError('Escena motion requiere params.title.')
    if ev['type']=='motion' and ev['template']=='ScreenshotFocus':
        raise ValueError('ScreenshotFocus requiere asset autorizado.')
    for item in ev['params']['items']:
        if item['at_seconds'] >= ev['end']-ev['start']:
            raise ValueError('at_seconds debe estar dentro de la escena.')
    if not isinstance(ev.get('demo', False), bool):
        raise ValueError('demo debe ser booleano.')
    if ev['type']=='motion' and ev['template'] in ('CRMHighlight','AnimatedMessages') and ev.get('demo') is not True:
        raise ValueError('UI ilustrativa requiere demo:true.')
