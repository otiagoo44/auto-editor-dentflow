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


if __name__ == '__main__':
    unittest.main()
