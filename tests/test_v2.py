import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import editor as e
from planning import asset_path, resolve_beats


def config():
    cfg = yaml.safe_load((ROOT / 'config.yaml').read_text(encoding='utf-8'))
    cfg['video'].update(width=180, height=320, preset='ultrafast')
    return cfg


def fixture(folder, duration=12, audio=False):
    folder.mkdir(parents=True, exist_ok=True)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
           f'testsrc2=s=180x320:r=30:d={duration}']
    if audio:
        cmd += ['-f', 'lavfi', '-i', f'sine=frequency=330:sample_rate=48000:duration={duration}', '-c:a', 'aac']
    e.run(cmd + ['-c:v', 'libx264', '-threads', '1', '-pix_fmt', 'yuv420p', folder/'raw.mp4'])


class AutoTests(unittest.TestCase):
    def test_empty_audio_with_asr_on(self):
        with tempfile.TemporaryDirectory(prefix='DentFlow ñ sin audio ') as td:
            folder = Path(td)
            fixture(folder, 2)
            with patch.object(e, 'get_words', side_effect=AssertionError('ASR no debe ejecutarse')):
                final = e.process_reel(folder, config(), auto=True)
            plan = e.read_json(final.parent/'plan_edicion.json')
            self.assertEqual(plan['captions'], [])
            self.assertEqual(plan['events'], [])
            self.assertIn('Sin audio', plan['transcript_source'])
            self.assertTrue((folder/'OUTPUT/VIDEO_BORRADOR.mp4').exists())

    def test_auto_baseline(self):
        # Persistir un artefacto visible sólo cuando se solicita explícitamente.
        with tempfile.TemporaryDirectory(prefix="DentFlow prueba ñ O'Brien ") as td:
            folder = Path(os.environ.get('DENTFLOW_VALIDATION', td))/'Reel 1'
            fixture(folder)
            final = e.process_reel(folder, config(), auto=True, preview=True)
            plan = e.read_json(final.parent/'plan_edicion.json')
            self.assertEqual(plan['keep_segments'], [[0, 12]])
            self.assertEqual(plan['events'], [])
            self.assertAlmostEqual(e.ffprobe_duration(final), 12, delta=.1)
            # Fallar un render posterior nunca reemplaza la última salida válida.
            digest = e.fingerprint(folder/'OUTPUT/VIDEO_BORRADOR.mp4')
            with patch.object(e, 'render_final', side_effect=RuntimeError('fallo simulado')):
                with self.assertRaises(RuntimeError):
                    e.process_reel(folder, config(), auto=True)
            self.assertEqual(digest, e.fingerprint(folder/'OUTPUT/VIDEO_BORRADOR.mp4'))

    def test_asr_failure_is_camera_only(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            fixture(folder, 2, audio=True)
            with patch.object(e, 'get_words', side_effect=RuntimeError('modelo ausente')):
                final = e.process_reel(folder, config(), auto=True)
            plan = e.read_json(final.parent/'plan_edicion.json')
            self.assertEqual(plan['captions'], [])
            self.assertEqual(plan['keep_segments'], [[0, 2]])
            self.assertIn('ASR local falló', plan['transcript_source'])

    def test_auto_cut_requires_sentence_silence_and_no_demo(self):
        words = [e.Word(.2, 1, 'No.'), e.Word(3.1, 3.5, '12'), e.Word(3.6, 4, 'consultas.')]
        audio = dict(audible=True, silences=[[1, 3.1]])
        keep = e.auto_keep_segments(words, 12, config(), audio)
        self.assertEqual(keep, [(0, 1.35), (2.85, 12)])
        self.assertEqual(e.auto_keep_segments(words, 12, config(), dict(audible=True, silences=[])), [(0, 12)])
        self.assertEqual(e.auto_keep_segments(words, 12, config(), audio, [(1, 4)]), [(0, 12)])
        words[0].text = 'No'
        self.assertEqual(e.auto_keep_segments(words, 12, config(), audio), [(0, 12)])


class EditorialTests(unittest.TestCase):
    def beat(self, **changes):
        base = dict(id='demo', purpose='Mostrar acción', match_text='la próxima acción', duration=3,
                    asset='../Assets/demo.png', animation='fade', approved=True, reason='Explicar seguimiento')
        base.update(changes)
        return base

    def test_trigger_unique_and_conflicts(self):
        words = [e.Word(i,i+.5,t) for i,t in enumerate(['Mirá','la','próxima','acción.'])]
        warnings = []
        events = resolve_beats(dict(beats=[self.beat()]),words,10,warnings)
        self.assertEqual((events[0]['start'],events[0]['end']),(1,4))
        self.assertEqual(resolve_beats(dict(beats=[self.beat()]),words+words,10,warnings),[])
        self.assertTrue(warnings)
        self.assertEqual(resolve_beats(dict(beats=[self.beat(approved=False)]),words,10,[]),[])
        with self.assertRaisesRegex(ValueError,'ambiguo'):
            resolve_beats(dict(beats=[self.beat(source_time=[0,2])]),words,10,[])
        explicit = dict(type='reframe',start=0,end=3,reason='Mayor prioridad')
        self.assertEqual(len(resolve_beats(dict(events=[explicit],beats=[self.beat()]), words,10,[])),1)
        ending = words + [e.Word(6,6.3,'Vuelve'),e.Word(6.4,6.7,'a'),e.Word(6.8,7,'cámara.')]
        events = resolve_beats(dict(beats=[self.beat(until_text='vuelve a cámara')]),ending,10,[])
        self.assertEqual(events[0]['end'],6)

    def test_diagram_reveal_steps_and_bad_regions(self):
        beat = self.beat(animation='DIAGRAM_REVEAL',duration=4,steps=[
            dict(duration=2,focus_region=[0,0,.5,1]),dict(duration=2,focus_region=[.5,0,.5,1])])
        words = [e.Word(i,i+.5,t) for i,t in enumerate(['la','próxima','acción'])]
        events = resolve_beats(dict(beats=[beat]),words,6,[])
        self.assertEqual([(x['start'],x['end']) for x in events],[(0,2),(2,4)])
        beat['steps'][1]['focus_region'] = [.8,0,.5,1]
        with self.assertRaisesRegex(ValueError,'sale del asset'):
            resolve_beats(dict(beats=[beat]),words,6,[])

    def test_assets_allowlist_week_and_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reel = root/'semana 1'/'Reel 1'
            assets = reel.parent/'Assets'
            assets.mkdir(parents=True)
            reel.mkdir()
            (assets/'propio.png').write_bytes(b'fixture')
            event = dict(type='asset',file='../Assets/propio.png',approved=True,start=0,end=2,reason='demo')
            self.assertEqual(len(e.prepare_events([event],[(0,4)],reel,4,[event['file']],strict=True)),1)
            with self.assertRaisesRegex(ValueError,'allowed_assets'):
                e.prepare_events([event],[(0,4)],reel,4,[],strict=True)
            for forbidden in ['../../semana 2/Assets/propio.png','../../secreto.png','research/demo.png','../Assets/falta.png']:
                with self.assertRaises(ValueError):
                    asset_path(forbidden,reel)
            with self.assertRaisesRegex(ValueError,'approved'):
                e.prepare_events([dict(event,approved=False)],[(0,4)],reel,4,[event['file']],strict=True)

    def test_timeline_multiple_cuts_negation_and_figures(self):
        keep = [(0,2),(4,6),(8,12)]
        words = [e.Word(.1,.3,'No'),e.Word(.4,.8,'12.'),e.Word(4.1,4.5,'Sí.'),e.Word(8.1,8.7,'Consultas.')]
        caps = e.make_captions(words,keep,config())
        self.assertEqual(caps[0][2],'No 12.')
        self.assertAlmostEqual(caps[-1][0],4.1)
        events = e.prepare_events([dict(type='reframe',start=8.2,end=9,reason='Conclusión',approved=True)],keep,ROOT,12)
        self.assertAlmostEqual(events[0]['start'],4.2)
        self.assertEqual(events[0]['source_start'],8.2)
        self.assertEqual(events[0]['time_basis'],'output')
        for start,end in [(1,5),(5,9)]:
            with self.assertRaisesRegex(ValueError,'cruza un corte'):
                e.prepare_events([dict(type='reframe',start=start,end=end,reason='cruza')],keep,ROOT,12)
        with self.assertRaisesRegex(ValueError,'tiempo fuente'):
            e.prepare_events([dict(type='reframe',start=1,end=2,time_basis='output')],keep,ROOT,12)

    def test_subtitle_safe_band_and_text_injection(self):
        cfg = config()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'sub.ass'
            e.write_ass([(0,1,'Ñandú: próxima acción.\r\\{pos(0,0)}')],path,cfg,
                        [dict(type='text',start=0,end=2,text='¿Quién sigue?',reason='Pregunta')])
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('\\{pos',text)
            self.assertIn('Ñandú',text)
            self.assertIn('\\fad(150,150)',text)
            cfg['subtitles']['margin_v'] = 590
            with self.assertRaisesRegex(ValueError,'invaden'):
                e.write_ass([],path,cfg)

    def test_render_editorial_focus_and_animated_camera(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            fixture(folder,8,audio=True)
            # Asset propio compartido del repo, permitido explícitamente por raíz.
            asset = ROOT/'contenido-dentflow/semana-1/Assets/Asset C.png'
            e.write_json(folder/'edicion.json',dict(schema_version=2,allowed_assets=[str(asset)],asset_roots=[str(asset.parent)],
                events=[dict(type='asset',file=str(asset),start=1,end=4,approved=True,demo=True,layout='full',
                             focus_region=[.445,.572,.252,.2],reason='Mostrar estado y responsable'),
                        dict(type='reframe',start=4.5,end=7.5,scale=1.07,animated=True,approved=True,reason='Énfasis')]))
            e.write_json(folder/'transcript.json',dict(words=[dict(start=1,end=3,text='Ejemplo ficticio.')]))
            final = e.process_reel(folder,config(),preview=True)
            self.assertAlmostEqual(e.ffprobe_duration(final),8,delta=.1)
            self.assertIn('EJEMPLO FICTICIO',(final.parent/'subtitulos.ass').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
