"""Contrato editorial determinista. No ASR, red ni selección libre de assets."""
import math
import re
import unicodedata
from pathlib import Path


def tokens(text):
    value = unicodedata.normalize('NFKD', text.casefold())
    return re.findall(r'[a-z0-9]+', ''.join(c for c in value if not unicodedata.combining(c)))


def bounded(value, low, high, name):
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f'{name} debe estar entre {low} y {high}.')
    return number


def region(value):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError('focus_region necesita [x,y,ancho,alto] normalizados.')
    x,y,w,h = [bounded(v, 0, 1, 'focus_region') for v in value]
    if w < .02 or h < .02 or x+w > 1.000001 or y+h > 1.000001:
        raise ValueError('focus_region sale del asset o es demasiado pequeña.')
    return [x,y,w,h]


def asset_path(file, folder, roots=()):
    if not isinstance(file, str) or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', file):
        raise ValueError('Asset debe ser una ruta local, nunca una URL.')
    path = (folder / file).resolve()
    safe_roots = [folder.resolve(), (folder.parent / 'Assets').resolve()]
    safe_roots += [(folder / p).resolve() for p in roots]
    if any(p.casefold() in ('research', 'videos_estudiar', 'auditorias_mega-prompts', '.git') for p in path.parts):
        raise ValueError('Los materiales de investigación no se usan como assets.')
    if not any(path.is_relative_to(root) for root in safe_roots):
        raise ValueError('Asset fuera del Reel/Assets de la semana o asset_roots explícitos.')
    if not path.is_file():
        raise ValueError(f'Asset faltante: {path.name}')
    return path


def resolve_beats(spec, words, duration, warnings):
    """Salida exclusivamente source_time. Los events explícitos tienen prioridad."""
    if spec.get('schema_version', 1) not in (1, 2):
        raise ValueError('schema_version soportado: 1 o 2.')
    if spec.get('mode', 'editorial') not in ('auto', 'editorial'):
        raise ValueError('mode debe ser auto o editorial.')
    result = [dict(ev) for ev in spec.get('events', [])]
    flat, owners = [], []
    for i, word in enumerate(words):
        part = tokens(word.text)
        flat += part
        owners += [i] * len(part)
    ids = set()
    for beat in sorted(spec.get('beats', []), key=lambda b: -bounded(b.get('priority', 0), -100, 100, 'priority')):
        identity = beat.get('id')
        if not identity or identity in ids:
            raise ValueError('Cada beat necesita id único.')
        ids.add(identity)
        def skip(reason):
            warnings.append(f'Beat {identity}: {reason}; fallback=camera.')
        if beat.get('fallback', 'camera') != 'camera':
            raise ValueError('Sólo fallback=camera está soportado.')
        if beat.get('approved') is not True:
            skip('pendiente de aprobación')
            continue
        if not beat.get('purpose') or not beat.get('reason'):
            raise ValueError(f'Beat {identity}: requiere purpose y reason.')
        if any(k in beat for k in ('start', 'end', 'output_time')):
            raise ValueError('Beat requiere source_time o match_text; nunca output_time/start/end.')
        if 'source_time' in beat and ('match_text' in beat or 'until_text' in beat):
            raise ValueError('Beat ambiguo: usa source_time o match_text/until_text.')
        if 'source_time' in beat:
            if len(beat['source_time']) != 2:
                raise ValueError('source_time debe ser [inicio,fin].')
            a,b = [bounded(v, 0, duration, 'source_time') for v in beat['source_time']]
            if b <= a:
                raise ValueError('source_time invertido o vacío.')
        else:
            needle = tokens(beat.get('match_text', ''))
            matches = [i for i in range(len(flat)-len(needle)+1) if needle and flat[i:i+len(needle)] == needle]
            if len(needle) < 3 or len(matches) != 1:
                skip('frase ausente, demasiado corta o repetida; indicar source_time')
                continue
            i = matches[0]
            matched = words[owners[i]:owners[i+len(needle)-1]+1]
            if any(y.start-x.end > 1.2 for x,y in zip(matched, matched[1:])):
                skip('frase interrumpida por pausa larga')
                continue
            a = matched[0].start
            b = duration if 'until_text' in beat else a + bounded(beat.get('duration', max(3, matched[-1].end-a)), .1, duration, 'duration')
            if b > duration:
                skip('no queda tiempo suficiente en la fuente')
                continue
        if 'until_text' in beat:
            needle = tokens(beat['until_text'])
            matches = [i for i in range(len(flat)-len(needle)+1)
                       if len(needle) >= 3 and flat[i:i+len(needle)] == needle and words[owners[i]].start > a]
            if len(matches) != 1:
                skip('frase de salida ausente o ambigua')
                continue
            b = words[owners[matches[0]]].start
        min_read = bounded(beat.get('min_read_seconds', 2), .1, duration, 'min_read_seconds')
        if b-a < min_read:
            skip('intervalo insuficiente para leer')
            continue
        if any(a < float(ev['end']) and b > float(ev['start']) for ev in result):
            skip('conflicto con evento explícito o beat de mayor prioridad')
            continue
        animation = beat.get('animation', 'none')
        if animation not in ('none', 'fade', 'DIAGRAM_REVEAL', 'CAMERA_PUNCH_IN_OUT', 'HOOK_TEXT', 'CALLOUT'):
            raise ValueError('Animación no permitida.')
        ev = dict(id=identity, start=a, end=b, time_basis='source', approved=True,
                  purpose=beat['purpose'], reason=beat['reason'], animation=animation)
        if animation == 'CAMERA_PUNCH_IN_OUT':
            ev.update(type='reframe', scale=beat.get('scale', 1.07), x=beat.get('x', .5), y=beat.get('y', .4), animated=True)
        elif animation in ('HOOK_TEXT', 'CALLOUT'):
            ev.update(type='text', text=beat.get('text', ''))
        elif beat.get('asset'):
            ev.update(type='asset', file=beat['asset'], layout=beat.get('layout', 'full'),
                      demo=beat.get('demo', False), offset=beat.get('offset', 0))
            if 'focus_region' in beat:
                ev['focus_region'] = region(beat['focus_region'])
            if animation == 'DIAGRAM_REVEAL':
                steps = beat.get('steps', [])
                if not steps:
                    raise ValueError('DIAGRAM_REVEAL necesita steps con focus_region y duration.')
                cursor = a
                for index, step in enumerate(steps):
                    length = bounded(step['duration'], .5, b-a, 'step.duration')
                    if cursor+length > b+1e-6:
                        raise ValueError('Los pasos exceden la duración del beat.')
                    result.append(dict(ev, id=f'{identity}.{index}', start=cursor, end=cursor+length,
                                       focus_region=region(step['focus_region']), animation='fade'))
                    cursor += length
                if abs(cursor-b) > .05:
                    raise ValueError('Las duraciones de steps deben cubrir exactamente el beat.')
                continue
        else:
            continue  # Beat puramente hablado, cámara.
        result.append(ev)
    return result


def policies(spec, cfg):
    """Configuración por Reel, sin aceptar filtros/expresiones externos."""
    camera = spec.get('camera_policy', {})
    if camera.get('fit', cfg['video']['fit']) not in ('contain', 'cover'):
        raise ValueError('camera_policy.fit: contain o cover.')
    cfg['video']['fit'] = camera.get('fit', cfg['video']['fit'])
    for axis in ('x', 'y'):
        cfg['video'][axis] = bounded(camera.get(axis, .5), 0, 1, 'camera_policy.'+axis)
    subs = spec.get('subtitle_policy', {})
    for key,lo,hi in [('font_size',32,72), ('margin_v',180,600), ('max_chars_per_line',12,32)]:
        if key in subs:
            cfg['subtitles'][key] = int(bounded(subs[key],lo,hi,key))
    if 'enabled' in subs:
        if not isinstance(subs['enabled'], bool):
            raise ValueError('subtitle_policy.enabled debe ser booleano.')
        cfg['subtitles']['enabled'] = subs['enabled']
    cuts = spec.get('cut_policy', {})
    if cuts.get('mode', 'conservative') not in ('conservative', 'preserve'):
        raise ValueError('cut_policy.mode: conservative o preserve.')
    if cuts.get('mode') == 'preserve':
        cfg['cuts']['auto_enabled'] = False
    for key,lo,hi in [('auto_min_gap_seconds',1.2,10), ('auto_max_gap_seconds',1.2,20), ('max_removed_fraction',0,.4)]:
        if key in cuts:
            cfg['cuts'][key] = bounded(cuts[key],lo,hi,key)
    if cfg['cuts'].get('auto_min_gap_seconds', 1.8) > cfg['cuts'].get('auto_max_gap_seconds', 6):
        raise ValueError('auto_min_gap_seconds debe ser <= auto_max_gap_seconds.')
