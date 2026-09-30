"""Demos persistentes V2.1 fuera del contenido real. Nunca reutiliza raw propios."""
import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import editor as e


def correct_second_fixture(data):
    """Sólo el guion SAPI de Reel 2, cotejado palabra a palabra; nunca en runtime."""
    corrections={'una':'Una','cargo':'cargo.','no':'No','mensaje':'mensaje.',
                 'revisar':'Revisá','quien':'quién','sigue':'sigue.'}
    for word in data['words']:
        word['text']=corrections.get(word['text'],word['text'])
    data['correction_note']='Correcciones contra guion SAPI de este fixture; no generalizar a grabaciones propias.'
    return data


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--quick',action='store_true')
    ap.add_argument('--final',action='store_true')
    ap.add_argument('--educativo',action='store_true')
    args=ap.parse_args()
    base=Path(os.environ['LOCALAPPDATA'])/'DentFlow/validacion_v21'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    base.mkdir(parents=True,exist_ok=False)
    (base/'.dentflow-synthetic-fixtures').write_text('Sólo fixtures sintéticos, nunca grabaciones del fundador.',encoding='utf-8')
    reel=base/'Comercial';reel.mkdir()
    spec=e.read_json(ROOT/'ejemplos/Comercial/edicion.json')
    asset=ROOT/'contenido-dentflow/semana-1/Assets/Asset E.png'
    assets=base/'Assets';assets.mkdir();shutil.copyfile(asset,assets/'Asset E.png')
    spec['allowed_assets']=['../Assets/Asset E.png'];spec.pop('asset_roots')
    for ev in spec['events']:
        if 'file' in ev:ev['file']='../Assets/Asset E.png'
    if args.quick:
        spec['render']['duration_seconds']=2;spec['events']=spec['events'][:1];spec['events'][0]['end']=2
    e.write_json(reel/'edicion.json',spec)
    cfg=e.yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))
    print('ACEPTACIÓN V2.1:',base,flush=True)
    final=e.process_reel(reel,cfg,preview=not args.final)
    outputs=[final]
    if args.educativo:
        from render_acceptance import make_reel,correct_fixture_transcript,SCRIPT
        one=base/'Reel 1';two=base/'Reel 2'
        for name in ('C','B'):shutil.copyfile(ROOT/f'contenido-dentflow/semana-1/Assets/Asset {name}.png',assets/f'Asset {name}.png')
        make_reel(one,SCRIPT)
        shutil.copyfile(ROOT/'contenido-dentflow/semana-1/Reel 1/edicion.json',one/'edicion.json')
        plan=e.process_reel(one,cfg,plan_only=True)
        e.write_json(one/'transcript.json',correct_fixture_transcript(e.read_json(plan/'transcript.json')))
        outputs.append(e.process_reel(one,cfg,preview=not args.final,engine='remotion'))
        make_reel(two,'Una consulta necesita alguien a cargo. No alcanza con responder un mensaje. Revisá el siguiente paso y quién lo sigue.')
        plan=e.process_reel(two,cfg,plan_only=True)
        e.write_json(two/'transcript.json',correct_second_fixture(e.read_json(plan/'transcript.json')))
        outputs.append(e.process_reel(two,cfg,preview=not args.final,engine='remotion'))
    summary=[]
    for path in outputs:
        plan=e.read_json(path.parent/'plan_edicion.json')
        review=path.parent/'revision';review.mkdir()
        cues={0.,max(0,plan['output_duration']-.2)}
        for ev in plan['events']:
            cues.update([max(0,ev['start']-1/30),min(plan['output_duration']-.04,ev['start']+.3),
                         (ev['start']+ev['end'])/2,min(plan['output_duration']-.04,ev['end']+1/30)])
        for i,t in enumerate(sorted(cues)):
            e.run(['ffmpeg','-v','error','-ss',str(t),'-i',path,'-frames:v','1','-vf','scale=360:640','-threads','1',review/f'{i:03d}_{t:.3f}s.jpg'])
        summary.append(dict(file=str(path),seconds=plan['elapsed_seconds'],remotion_seconds=plan.get('remotion_seconds'),metadata=e.read_json(path.parent/'metadata.json')))
    e.write_json(base/'resultados.json',summary)
    print('DEMOS:',base,flush=True)

if __name__=='__main__':main()
