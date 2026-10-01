"""Isolated child process: stages are emitted by the existing editor, never guessed."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import editor as e
from editorial import propose
from planning import resolve_beats
import motion


def clean_event(event):
    return {k:v for k,v in event.items() if k not in ('file','source','asset_roots')}


def run(folder):
    e.PROGRESS_JSON = True
    payload=e.read_json(folder/'job.json')
    settings=payload['settings']
    cfg=e.yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))
    assets=payload['staged_assets']
    spec=dict(schema_version=2,mode='auto',source_mode=settings['source_mode'],allowed_assets=[],
              cut_policy={'mode':'preserve' if settings['preserve_pauses'] else 'conservative'},
              render=dict(engine=settings['engine'],template='educativo',music={'enabled':False}))
    words=[]
    if settings['source_mode']=='recording':
        source=folder/assets[settings['asset_id']]['file']
        probe=e.probe(source)
        if not any(s['codec_type']=='video' for s in probe['streams']):
            raise ValueError('invalid_media')
        duration=float(probe['format']['duration'])
        if not .5 <= duration <= payload.get('max_duration',600):
            raise ValueError('invalid_media')
        digest=e.fingerprint(source)
        if settings.get('source_sha256') and settings['source_sha256']!=digest:
            raise ValueError('invalid_media')
        spec['source']=source.name
        if 'words' in settings:
            words=e.validate_words(settings['words'],duration)
            e.write_json(folder/'transcript.json',e.transcript_document(words,digest,duration))
        e.write_json(folder/'edicion.json',spec)
        first=e.process_reel(folder,cfg,plan_only=True,auto=True,engine=settings['engine'])
        transcript=e.read_json(first/'transcript.json')
        words=e.validate_words(transcript['words'],duration)
        # Reuse only an identified transcript from this exact source.
        e.write_json(folder/'transcript.json',transcript)
    else:
        duration=settings['duration']
        spec['render'].update(template='comercial',duration_seconds=duration)
    plan,decisions,warnings=propose(payload['content'],settings['scenes'],words,duration,assets)
    spec['beats']=plan['beats']
    used={s['asset_id'] for s in settings['scenes'] if s.get('asset_id')}
    if settings.get('music_asset_id'):
        music=assets[settings['music_asset_id']]
        if not music['approved'] or not music['rights']:
            raise ValueError('Música sin derechos declarados.')
        spec['render']['music']=dict(enabled=True,file=music['file'],rights_declared=True,volume=settings['music_volume'],ducking=.35)
        used.add(settings['music_asset_id'])
    spec['allowed_assets']=[assets[a]['file'] for a in sorted(used)]
    # Validate actual source-time events before rendering and remap through existing engine.
    for event in resolve_beats(spec,words,duration,[]):
        if event.get('template'):motion.validate_scene(event)
    e.write_json(folder/'edicion.json',spec)
    preflight=e.process_reel(folder,cfg,plan_only=True,auto=True,engine=settings['engine'])
    pre=e.read_json(preflight/'plan_edicion.json')
    for decision in decisions:
        rendered=next((v for v in pre['events'] if v.get('id')==decision['id']),None)
        if rendered:decision['output_time']=[rendered['start'],rendered['end']]
        elif decision['status']=='resolved':decision.update(status='omitted',warning='El motor omitió el evento en preflight; revisar tiempos/cortes.')
    if settings['engine']=='remotion':
        motion.runtime()
        props=motion.build_props(pre,motion.render_options(spec),'job_preflight','jobs/job_preflight/aroll.mp4',
            {i:{'path':f'jobs/job_preflight/asset_{i}.png','video':False} for i,v in enumerate(pre['events']) if v['type']=='asset'})
        e.write_json(folder/'preflight_props.json',props)
        node,_,_=motion.runtime()
        # Schema preflight before expensive composition; executable is repository-owned only.
        e.run([node,str(ROOT/'remotion/scripts/validate-props.cjs'),str(folder/'preflight_props.json')])
    final=e.process_reel(folder,cfg,preview=settings['kind']=='preview',auto=True,engine=settings['engine'])
    rendered=e.read_json(final.parent/'plan_edicion.json')
    metadata=e.read_json(final.parent/'metadata.json')
    transcript=e.read_json(final.parent/'transcript.json')
    report=dict(words=transcript['words'],captions=rendered['captions'],events=[clean_event(v) for v in rendered['events']],
                time_map=rendered['time_map'],decisions=decisions,source_sha256=metadata['source_sha256'],
                source_duration=rendered['source_duration'],warnings=(warnings+rendered['warnings'])[:500])
    # Public warnings cannot include absolute machine paths or child-process logs.
    report['warnings']=[w if not any(t in w for t in ('\\',str(folder),'Traceback','ffmpeg falló')) else 'El motor informó una incidencia. Revisá el diagnóstico local.' for w in report['warnings']]
    result=dict(file=str(final),sha256=metadata['output_sha256'],size=final.stat().st_size,duration=metadata['duration'],
                resolution=metadata['resolution'],source_sha256=metadata['source_sha256'],validation=metadata['validation'],report=report)
    e.write_json(folder/'result.json',result)


if __name__=='__main__':
    run(Path(sys.argv[1]).resolve())
