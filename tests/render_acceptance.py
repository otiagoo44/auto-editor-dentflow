"""Aceptación reproducible, explícitamente sintética y fuera de los Reels propios.

Windows: python tests/render_acceptance.py [--final]
Produce dos Reels distintos usando el mismo editor/BAT, voz SAPI local y assets propios.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import editor as e

SCRIPT = ('¿Cuántas consultas siguen abiertas y quién las debe contactar? '
          'Si la respuesta está repartida en conversaciones, cuesta saber qué sigue. '
          'Mirá estos cuatro datos. Estado: en qué etapa está. Responsable: quién sigue esto. '
          'Fecha: cuándo revisar. Próxima acción: qué hacer ahora. '
          'En este ejemplo ficticio, el seguimiento está pendiente y lo tiene Recepción. '
          'La próxima acción es llamar hoy a las dieciséis. Esto es una ilustración del seguimiento. '
          'La idea es simple. Que cada consulta abierta tenga alguien a cargo y un siguiente paso. '
          'Revisá una consulta de tu clínica: ¿están claros esos datos?')


def correct_fixture_transcript(data):
    """Correcciones revisadas contra SCRIPT, sólo para esta locución sintética.

    No es un corrector general ni se incorpora al motor. ASR original queda en cache.
    """
    corrections = {'Mira':'Mirá', 'que':'qué', '¿Estado?':'Estado:', '¿En':'En',
                   'ésta?':'está.', '¿Responsable?':'Responsable:', '¿Quién':'Quién',
                   'esto?':'esto.', 'Fecha,':'Fecha:', 'cuando':'cuándo', 'Proxima':'Próxima',
                   'acción,':'acción:', 'recepción.':'Recepción.', '16.':'dieciséis.',
                   'Revisar':'Revisá', 'clínica,':'clínica:', 'están':'¿están'}
    for i,word in enumerate(data['words']):
        word['text'] = corrections.get(word['text'],word['text'])
        if word['text']=='datos.' and i and data['words'][i-1]['text']=='esos':
            word['text']='datos?'
    data['correction_note']='Correcciones explícitas revisadas contra guion de voz sintética; no generalizar a grabaciones reales.'
    return data


def make_reel(folder, text):
    folder.mkdir(parents=True)
    speech = folder/'speech.wav'
    # El texto viaja como datos en JSON; no se concatena como código PowerShell.
    e.write_json(folder/'speech.json', dict(text=text, output=str(speech)))
    env = dict(os.environ, DENTFLOW_SPEECH_INPUT=str(folder/'speech.json'))
    command = ("Add-Type -AssemblyName System.Speech; "
               "$job = Get-Content -LiteralPath $env:DENTFLOW_SPEECH_INPUT -Raw -Encoding UTF8 | ConvertFrom-Json; "
               "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
               "$speaker.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet, "
               "[System.Speech.Synthesis.VoiceAge]::NotSet, 0, [System.Globalization.CultureInfo]'es-MX'); "
               "$speaker.Rate = -1; $speaker.SetOutputToWaveFile($job.output); "
               "$speaker.Speak($job.text); $speaker.Dispose()")
    subprocess.run(['powershell','-NoProfile','-Command',command],env=env,check=True)
    length = e.ffprobe_duration(speech)
    cfg = e.yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))
    e.write_ass([],folder/'fixture.ass',cfg,[dict(type='text',start=0,end=length,
        text='PRUEBA SINTÉTICA\nVoz local, sin cámara real')])
    fixture_ass = folder/'fixture.ass'
    fixture_ass.write_text(fixture_ass.read_text(encoding='utf-8').replace(r'\pos(540.0,230.4)', r'\pos(540.0,672.0)'), encoding='utf-8')
    e.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c=0x1f2937:s=1080x1920:r=30:d={length}',
           '-i',speech,'-vf','ass=fixture.ass','-c:v','libx264','-threads','2','-preset','ultrafast',
           '-pix_fmt','yuv420p','-c:a','aac','-shortest',folder/'raw.mp4'],cwd=folder)
    return cfg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--final', action='store_true')
    args = parser.parse_args()
    week = Path(os.environ['LOCALAPPDATA'])/'DentFlow/validacion_v2'/datetime.now().strftime('editorial_%Y%m%d_%H%M%S')
    one, two = week/'Reel 1', week/'Reel 2'
    assets = week/'Assets'
    assets.mkdir(parents=True)
    for name in ('C','E','B'):
        shutil.copyfile(ROOT/f'contenido-dentflow/semana-1/Assets/Asset {name}.png',assets/f'Asset {name}.png')
    cfg = make_reel(one,SCRIPT)
    shutil.copyfile(ROOT/'contenido-dentflow/semana-1/Reel 1/edicion.json',one/'edicion.json')
    # Primero ASR verdadera; guarda output auditable para revisar triggers.
    plan_dir=e.process_reel(one,cfg,plan_only=True,auto=True)
    e.write_json(one/'transcript.json',correct_fixture_transcript(e.read_json(plan_dir/'transcript.json')))
    make_reel(two, 'Conversar y controlar son tareas distintas. Conversar permite responder y coordinar. '
              'Para ordenar el seguimiento, mirá el estado, la persona responsable, la fecha y la próxima acción. '
              'Esto es un esquema explicativo. Revisá una consulta abierta y comprobá quién la sigue.')
    e.write_json(two/'edicion.json', dict(schema_version=2,source='raw.mp4',mode='editorial',
        allowed_assets=['../Assets/Asset B.png'],cut_policy=dict(mode='preserve'),beats=[
            dict(id='control',purpose='Separar los campos de control',match_text='para ordenar el seguimiento',
                 until_text='esto es un esquema',asset='../Assets/Asset B.png',layout='full',focus_region=[.545,.3,.415,.62],
                 animation='fade',approved=True,reason='Mostrar sólo el panel control de B',fallback='camera')]))
    command = [str(ROOT/'editar_semana.bat'),str(week),'--auto']
    if not args.final:
        command += ['--preview']
    subprocess.run(command,check=True)
    for reel in (one,two):
        output = reel/'OUTPUT'
        plans = sorted(output.glob('*/plan_edicion.json'))
        plan = e.read_json(plans[-1])
        final = Path(plan['file'])
        review = final.parent/'revision'
        review.mkdir(exist_ok=True)
        cues = {0.5, max(.1,plan['output_duration']-.5)}
        for event in plan['events']:
            cues.update([max(0,event['start']-.1),(event['start']+event['end'])/2,
                         min(plan['output_duration']-.05,event['end']+.1)])
        for i,t in enumerate(sorted(cues)):
            e.run(['ffmpeg','-v','error','-ss',str(t),'-i',final,'-frames:v','1','-vf','scale=360:640',
                   '-threads','1',review/f'{i:02d}_{t:.2f}s.jpg'])
        print(json.dumps(dict(reel=reel.name,path=str(final),events=len(plan['events']),warnings=plan['warnings']),ensure_ascii=False))
    print('ACEPTACIÓN SINTÉTICA:',week)


if __name__ == '__main__':
    main()
