import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import editor as e


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

    def test_brief_words_and_end_pause_are_preserved(self):
        words = [e.Word(.5, .6, "Sí."), e.Word(3, 3.1, "No.")]
        keep = e.build_keep_segments(words, 5, self.cfg)
        self.assertTrue(any(a <= .5 and b >= .6 for a,b in keep))
        self.assertEqual(keep[-1][1], 5)
        self.assertEqual(keep[0][0], 0)

    def test_captions_do_not_bridge_cut_or_punctuation(self):
        words = [e.Word(.1,.4,"Agenda."), e.Word(3.1,3.5,"Confirmada.")]
        caps = e.make_captions(words, [(0,1),(3,4)], self.cfg)
        self.assertEqual([c[2] for c in caps], ["Agenda.", "Confirmada."])
        self.assertAlmostEqual(caps[1][0], 1.1)

    def test_no_clamping_removed_time_or_half_words(self):
        with self.assertRaises(ValueError):
            e.remap_time(2, [(0,1),(3,4)])
        with self.assertRaises(ValueError):
            e.validate_cut_boundaries([e.Word(.9,1.1,"turno")], [(0,1)])

    def test_invalid_ranges_and_event_crossing_cut(self):
        for pairs in ([], [(2,1)], [(0,2),(1,3)], [(0,float("nan"))]):
            with self.assertRaises(ValueError):
                e.validate_ranges(pairs, 5, 30)
        with self.assertRaises(ValueError):
            e.prepare_events([dict(type="reframe",start=.5,end=3.5,reason="énfasis")],
                             [(0,1),(3,4)], ROOT, 5)

    def test_two_line_limit(self):
        words = [e.Word(n*.2,n*.2+.18,"confirmación") for n in range(12)]
        caps = e.make_captions(words, [(0,3)], self.cfg)
        self.assertEqual(sum(len(c[2].split()) for c in caps),12)
        self.assertTrue(all(len(c[2].splitlines()) <= 2 for c in caps))
        self.assertTrue(all(len(line) <= 26 for c in caps for line in c[2].splitlines()))

    def test_ass_rounding_and_injection(self):
        self.assertEqual(e.ass_time(59.999), "0:01:00.00")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"c.ass"
            e.write_ass([(0,1,r"{\\pos(0,0)}texto")],path,self.cfg)
            self.assertNotIn(r"{\\pos", path.read_text(encoding="utf-8"))


class RenderTests(unittest.TestCase):
    def test_actual_ffmpeg_overlays_cuts_and_finite_duration(self):
        cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        cfg["video"].update(width=180,height=320,preset="ultrafast")
        cfg["transcription"]["enabled"] = False
        cfg["subtitles"]["enabled"] = False
        with tempfile.TemporaryDirectory(prefix="dentflow_test_") as td:
            folder = Path(td)
            # Original synthetic fixtures: red A-roll and blue demonstration.
            e.run(["ffmpeg","-loglevel","error","-y","-f","lavfi","-i",
                   "color=c=red:s=180x320:r=30:d=6","-f","lavfi","-i",
                   "sine=frequency=440:sample_rate=48000:duration=6",
                   "-c:v","libx264","-threads","1","-pix_fmt","yuv420p","-c:a","aac",folder/"raw.mp4"])
            e.run(["ffmpeg","-loglevel","error","-y","-f","lavfi","-i",
                   "color=c=blue:s=180x320:r=30:d=2","-c:v","libx264","-threads","1",folder/"demo.mp4"])
            e.run(["ffmpeg","-loglevel","error","-y","-f","lavfi","-i",
                   "color=c=lime:s=100x100","-frames:v","1","-threads","1",folder/"card.png"])
            e.write_json(folder/"edicion.json",dict(source="raw.mp4",allowed_assets=['card.png','demo.mp4'],keep_segments=[[0,2],[3,6]],events=[
                dict(type="asset",file="card.png",approved=True,start=.5,end=1.5,reason="tarjeta",layout="full"),
                dict(type="asset",file="demo.mp4",approved=True,start=4,end=5.5,reason="demostración",layout="full")]))
            final = e.process_reel(folder,cfg)
            self.assertAlmostEqual(e.ffprobe_duration(final),5,delta=.1)
            def pixel(t):
                data = subprocess.check_output(["ffmpeg","-loglevel","error","-ss",str(t),"-i",str(final),
                          "-vf","scale=1:1","-frames:v","1","-f","rawvideo","-pix_fmt","rgb24","-threads","1","-"])
                return tuple(data[:3])
            # PNG during .5–1.5; MP4 source4 becomes output3.
            before, card, gap, demo, after = [pixel(t) for t in (.2,1,2.5,3.5,4.8)]
            self.assertGreater(before[0],200)
            self.assertGreater(card[1],card[0]+50)
            self.assertGreater(gap[0],200)
            self.assertGreater(demo[2],200)
            self.assertGreater(after[0],200)
            # No filter effects and no voice/subtitles must also export.
            e.write_json(folder/"edicion.json",dict(source="raw.mp4",keep_segments=[[0,1]]))
            final2=e.process_reel(folder,cfg)
            self.assertTrue(final2.exists())
            self.assertNotEqual(final,final2)
            # Reencuadre explícito + ASS; el corte no debe suprimir una palabra breve.
            cfg["subtitles"]["enabled"] = True
            e.write_json(folder/"transcript.json", e.transcript_document([e.Word(.1,.5,'Sí.'),
                         e.Word(.6,.95,'Agenda.')],e.fingerprint(folder/'raw.mp4'),6))
            e.write_json(folder/"edicion.json", dict(source="raw.mp4",keep_segments=[[0,1]],events=[
                dict(type="reframe",start=.55,end=.98,scale=1.1,reason="énfasis")]))
            final3=e.process_reel(folder,cfg)
            self.assertTrue(final3.exists())
            # Fuente sin pista de audio: añade silencio, no falla el mapeo 0:a.
            e.write_json(folder/"edicion.json", dict(source="demo.mp4",keep_segments=[[0,1]]))
            (folder/'transcript.json').unlink()  # Sólo fixture; otra fuente exige otro transcript.
            final4=e.process_reel(folder,cfg)
            self.assertTrue(any(s["codec_type"] == "audio" for s in e.probe(final4)["streams"]))


if __name__ == "__main__":
    unittest.main()
