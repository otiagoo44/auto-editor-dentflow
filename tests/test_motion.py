import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import editor as e
import motion as m
from planning import resolve_beats,asset_path
from test_v2 import config,fixture,center_pixel


class MotionContractTests(unittest.TestCase):
    def test_render_options_and_music_rights(self):
        self.assertEqual(m.render_options({})['engine'],'ffmpeg')
        self.assertEqual(m.render_options({'render':{'engine':'remotion'}},'ffmpeg')['engine'],'ffmpeg')
        for render in ({'engine':'cloud'},{'template':'code.js'},{'music':{'enabled':True,'file':'x.wav'}},
                       {'engine':'remotion','music':{'enabled':True,'rights_declared':True,'file':'x.wav','volume':float('nan')}}):
            with self.assertRaises(ValueError):m.render_options({'render':render})

    def test_motion_beats_are_approved_and_use_output_frames(self):
        beat=dict(id='ui',purpose='mostrar',reason='explicar',source_time=[8.1,9.6],min_read_seconds=1,
                  template='CRMHighlight',params={'title':'No 16:00','items':[{'label':'Estado','value':'Pendiente'}]},demo=True,approved=True)
        resolved=resolve_beats({'schema_version':2,'beats':[beat]},[],12,[])
        with tempfile.TemporaryDirectory() as td:
            events=e.prepare_events(resolved,[(0,2),(4,6),(8,12)],Path(td),12,strict=True)
        plan=dict(config=config(),output_duration=8,events=events,captions=[dict(start=4.1,end=5.6,text='No 16:00.')],sha256='0'*64)
        props=m.build_props(plan,m.render_options({'render':{'engine':'remotion'}}),'job_test','jobs/job_test/aroll.mp4',{})
        self.assertEqual(props['scenes'][0]['start_frame'],123)
        self.assertEqual(props['scenes'][0]['duration_frames'],45)
        self.assertEqual(props['captions'][0]['startMs'],4100)
        self.assertEqual(props['duration_frames'],240)
        self.assertEqual(m.frame(1.05,30),32)
        self.assertEqual(resolve_beats({'beats':[dict(beat,approved=False)]},[],12,[]),[])
        for template in ('../../evil','eval','<script>'):
            with self.assertRaises(ValueError):resolve_beats({'beats':[dict(beat,template=template)]},[],12,[])

    def test_research_urls_and_escaped_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td); research=folder/'auditorias_mega-prompts';research.mkdir()
            (research/'asset.png').write_bytes(b'x')
            for path in ('auditorias_mega-prompts/asset.png','https://example.com/x.png'):
                with self.assertRaises(ValueError):asset_path(path,folder)

    def test_params_reject_code_and_unreadable_sizes(self):
        for p in ({'html':'<script>'},{'title':'x'*90},{'items':[{'label':'a'}]*5},{'theme':'url(https://x)'},
                  {'items':[{'label':'A','at_seconds':2},{'label':'B','at_seconds':1}]}):
            with self.assertRaises(ValueError):m.params(p)

    def test_missing_unselected_allowed_asset_does_not_suppress_valid_asset(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);(folder/'ok.png').write_bytes(b'x')
            event=dict(type='asset',file='ok.png',approved=True,start=0,end=1,reason='visible')
            self.assertEqual(len(e.prepare_events([event],[(0,2)],folder,2,['ok.png','missing.png'],strict=True)),1)

    def test_ffmpeg_does_not_require_node_and_remotion_failure_preserves_output(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);fixture(folder,1)
            with patch.object(m,'runtime',side_effect=RuntimeError('Node ausente')):
                final=e.process_reel(folder,config(),preview=True,engine='ffmpeg')
                alias=folder/'OUTPUT/VIDEO_PREVIEW.mp4';digest=e.fingerprint(alias)
                with self.assertRaisesRegex(RuntimeError,'Node ausente'):e.process_reel(folder,config(),preview=True,engine='remotion')
                self.assertEqual(e.fingerprint(alias),digest)
                self.assertTrue(final.exists())


@unittest.skipUnless(os.environ.get('DENTFLOW_REMOTION_TESTS')=='1','Remotion render opt-in: DENTFLOW_REMOTION_TESTS=1')
class MotionRenderTests(unittest.TestCase):
    def test_three_cuts_png_mp4_captions_no_double_subtitles_and_finite_overlay(self):
        with tempfile.TemporaryDirectory(prefix="Motion ñ O'Brien ") as td:
            folder=Path(td);fixture(folder,10,audio=True)
            e.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','color=c=lime:s=320x180','-frames:v','1','-threads','1',folder/'green.png'])
            e.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','color=c=blue:s=320x180:r=30:d=2','-c:v','libx264','-threads','1',folder/'blue.mp4'])
            words=[e.Word(.2,.6,'No'),e.Word(.6,1.3,'16:00.'),e.Word(8.1,8.6,'Próxima'),e.Word(8.6,9.3,'acción.')]
            e.write_json(folder/'transcript.json',e.transcript_document(words,e.fingerprint(folder/'raw.mp4'),10))
            e.write_json(folder/'edicion.json',dict(schema_version=2,keep_segments=[[0,2],[4,6],[8,10]],allowed_assets=['green.png','blue.mp4'],events=[
                dict(type='asset',file='green.png',start=.3,end=1.7,reason='PNG',approved=True,layout='full',animation='none'),
                dict(type='asset',file='blue.mp4',start=4.2,end=5.7,reason='MP4',approved=True,layout='full',animation='none'),
                dict(type='motion',template='SummaryCTA',params={'title':'Un siguiente paso','cta':'Revisá una consulta'},start=8.1,end=9.5,reason='CTA',approved=True)]))
            final=e.process_reel(folder,config(),preview=True,engine='remotion')
            plan=e.read_json(final.parent/'plan_edicion.json');props=e.read_json(final.parent/'remotion_props.json')
            self.assertAlmostEqual(e.ffprobe_duration(final),6,delta=.10)
            self.assertFalse((final.parent/'subtitulos.ass').exists())
            self.assertEqual([s['start_frame'] for s in props['scenes']],[9,66,123])
            self.assertEqual(plan['engine'],'remotion')
            self.assertGreater(center_pixel(final,1)[1],180)
            self.assertGreater(center_pixel(final,3)[2],180)
            self.assertNotEqual(center_pixel(final,3),center_pixel(final,3.9))
            self.assertFalse((m.ROOT/'public/jobs'/props['job_id']).exists())

    def test_commercial_no_camera_and_silence(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            e.write_json(folder/'edicion.json',dict(schema_version=2,render=dict(engine='remotion',template='comercial',duration_seconds=2),
                events=[dict(type='motion',template='QuestionHook',params={'title':'¿Quién sigue esta consulta?'},layout='full',start=0,end=2,approved=True,reason='Pregunta')]))
            final=e.process_reel(folder,config(),preview=True)
            self.assertFalse((folder/'raw.mp4').exists())
            self.assertFalse(e.read_json(final.parent/'plan_edicion.json')['rendered_audio']['audible'])
            self.assertEqual(e.read_json(final.parent/'metadata.json')['resolution'],[360,640])


if __name__=='__main__':unittest.main()
