"""Deterministic Studio planner. Every intervention has explicit provenance."""
import copy
from planning import resolve_beats
from motion import validate_scene


def propose(content, scenes, words, duration, assets):
    """Input assets are an owner-authorized id -> staged filename mapping."""
    beats, decisions, warnings = [], [], []
    for scene in scenes:
        decision = dict(id=scene['id'], purpose=scene['purpose'], reason=scene['reason'],
                        provenance=dict(content_id=content['id'], source_version=content['source_version'],
                                        rule='explicit_owner_timing' if scene.get('source_time') else 'unique_spoken_phrase'),
                        match_text=scene.get('match_text', ''), status='suggested')
        if content.get('demo_gate') and not content.get('demo_approved'):
            decision.update(status='omitted', warning='Demo de producto pendiente de aprobación D1–D4.')
            decisions.append(decision)
            continue
        beat = {k: copy.deepcopy(scene[k]) for k in ('id','purpose','reason','template','params','approved','demo','duration','layout','focus_region') if k in scene}
        beat.update(fallback='camera', min_read_seconds=min(2, scene.get('duration',4)), animation='fade')
        if scene.get('source_time'):
            beat['source_time'] = scene['source_time']
        else:
            beat['match_text'] = scene.get('match_text', '')
        if scene.get('asset_id'):
            resource = assets.get(scene['asset_id'])
            if not resource or not resource['approved'] or not resource['rights']:
                decision.update(status='omitted', warning='Recurso sin aprobación o procedencia.')
                decisions.append(decision)
                continue
            beat['asset'] = resource['file']
            beat['demo'] = bool(resource.get('demo',False) or scene.get('demo',False))
        local_warnings = []
        try:
            resolved = resolve_beats({'schema_version':2,'beats':beats+[beat]}, words, duration, local_warnings)
            own = next((e for e in resolved if e.get('id') == scene['id']), None)
            if own:
                validate_scene(own) if own.get('template') else None
                decision.update(status='resolved',source_time=[own['start'],own['end']],confidence=1.0,
                                confidence_basis='manual_timing' if scene.get('source_time') else 'unique_literal_match')
                beats.append(beat)
            else:
                decision.update(status='suggested' if not scene.get('approved') else 'omitted',
                                warning=next((w for w in local_warnings if f"Beat {scene['id']}:" in w),'Conservar cámara; falta intervención aprobada.'))
        except (ValueError,KeyError,TypeError) as exc:
            decision.update(status='omitted',warning=str(exc))
        decisions.append(decision)
        if decision.get('warning'):
            warnings.append(decision['warning'])
    return dict(schema_version=2,beats=beats), decisions, warnings
