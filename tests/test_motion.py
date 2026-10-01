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
    def test_captions_have_one_renderer_and_ducking_joins_words(self):
        self.assertEqual(m.render_options({'render': {'engine':'remotion'}})['captions'], 'remotion')
        for engine, captions in [('remotion','ass'), ('ffmpeg','remotion')]:
            with self.assertRaisesRegex(ValueError, 'requiere captions'):
                m.render_options({'render':dict(engine=engine, captions=captions)})
        self.assertEqual(m.merge_speech_windows([[0,1],[1.1,2],[3,4]]), [[0,2],[3,4]])

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

    def test_missing_asset_falls_back_and_commercial_rejects_uncovered_timeline(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);fixture(folder,2)
            spec=dict(schema_version=2,allowed_assets=['missing.png'],events=[dict(type='asset',file='missing.png',
                approved=True,start=0,end=2,reason='faltante')])
            e.write_json(folder/'edicion.json',spec)
            output=e.process_reel(folder,config(),plan_only=True,engine='remotion')
            plan=e.read_json(output/'plan_edicion.json')
            self.assertEqual(plan['events'],[])
            self.assertTrue(any('fallback=camera' in w for w in plan['warnings']))
            spec['render']=dict(engine='remotion',template='comercial',duration_seconds=2)
            e.write_json(folder/'edicion.json',spec)
            with self.assertRaisesRegex(ValueError,'cubran toda la duración'):
                e.process_reel(folder,config(),plan_only=True)

    def test_previous_output_metadata_identifies_stale_hash(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);(folder/'OUTPUT').mkdir()
            file=folder/'OUTPUT/VIDEO_PREVIEW.mp4';file.write_bytes(b'previous')
            e.write_json(folder/'OUTPUT/VIDEO_PREVIEW.json',dict(output_sha256=e.fingerprint(file),resolution=[360,640]))
            self.assertTrue(e.previous_outputs(folder)[0]['metadata_matches_file'])
            file.write_bytes(b'changed')
            self.assertFalse(e.previous_outputs(folder)[0]['metadata_matches_file'])

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
    @unittest.skipUnless(os.name=='nt','BAT de Windows')
    def test_week_remotion_reports_failure_and_preserves_previous_aliases(self):
        import subprocess
        with tempfile.TemporaryDirectory(prefix="Semana motion ñ O'Brien ") as td:
            week=Path(td)
            for i in range(1,6):
                reel=week/f'Reel {i}';fixture(reel,1+i/10)
                e.write_json(reel/'edicion.json',dict(schema_version=2,render=dict(engine='remotion'),events=[
                    dict(type='text',text=f'Pregunta {i}',start=0,end=1,approved=True,reason='Fixture distinto')]))
            command=[str(e.ROOT/'editar_semana.bat'),str(week),'--auto','--preview','--engine','remotion']
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=e.read_json(sorted((week/'OUTPUT').glob('lote_*.json'))[-1])
            self.assertEqual((report['passed'],report['failed']),(5,0))
            old=[e.fingerprint(week/f'Reel {i}/OUTPUT/VIDEO_PREVIEW.mp4') for i in range(1,6)]
            for i in range(1,6):
                path=week/f'Reel {i}/edicion.json';spec=e.read_json(path)
                if i==3:spec['source']='missing.mp4'
                e.write_json(path,spec)
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            report=e.read_json(sorted((week/'OUTPUT').glob('lote_*.json'))[-1])
            self.assertEqual((report['passed'],report['failed']),(4,1))
            failed=next(r for r in report['results'] if r['status']=='failed')
            self.assertTrue(failed['previous_outputs'][0]['metadata_matches_file'])
            self.assertEqual(failed['previous_outputs'][0]['sha256'],old[2])
            self.assertEqual(e.fingerprint(week/'Reel 3/OUTPUT/VIDEO_PREVIEW.mp4'),old[2])

    def test_three_cuts_png_mp4_captions_no_double_subtitles_and_finite_overlay(self):
        with tempfile.TemporaryDirectory(prefix="Motion ñ O'Brien ") as td:
            folder=Path(td);fixture(folder,12,audio=True)
            e.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','color=c=lime:s=320x180','-frames:v','1','-threads','1',folder/'green.png'])
            e.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','color=c=blue:s=320x180:r=30:d=2','-c:v','libx264','-threads','1',folder/'blue.mp4'])
            words=[e.Word(.2,.6,'No'),e.Word(.6,1.3,'16:00.'),e.Word(10.1,10.6,'Próxima'),e.Word(10.6,11.3,'acción.')]
            e.write_json(folder/'transcript.json',e.transcript_document(words,e.fingerprint(folder/'raw.mp4'),12))
            e.write_json(folder/'edicion.json',dict(schema_version=2,keep_segments=[[0,2],[4,8],[10,12]],allowed_assets=['green.png','blue.mp4'],events=[
                dict(type='asset',file='green.png',start=.3,end=1.7,reason='PNG',approved=True,layout='full',animation='none'),
                dict(type='asset',file='blue.mp4',start=4.2,end=5.7,reason='MP4',approved=True,layout='full',animation='none'),
                dict(type='motion',template='QuestionHook',params={'title':'¿Quién sigue?'},start=6,end=7.8,reason='Pregunta',approved=True),
                dict(type='motion',template='SummaryCTA',params={'title':'Un siguiente paso','cta':'Revisá una consulta'},start=10.1,end=11.5,reason='CTA',approved=True)]))
            final=e.process_reel(folder,config(),preview=True,engine='remotion')
            plan=e.read_json(final.parent/'plan_edicion.json');props=e.read_json(final.parent/'remotion_props.json')
            self.assertAlmostEqual(e.ffprobe_duration(final),8,delta=1/30+.001)
            self.assertFalse((final.parent/'subtitulos.ass').exists())
            self.assertEqual([s['start_frame'] for s in props['scenes']],[9,66,120,183])
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
            # El CLI debe funcionar sin conexiones de Node fuera de loopback.
            guard=folder/'offline.cjs'
            guard.write_text("const net=require('node:net'); const dns=require('node:dns');\n"
                "const allowed=h=>!h||['127.0.0.1','localhost','::1','[::1]'].includes(h);\n"
                "const lookup=dns.lookup; dns.lookup=function(h,...a){if(!allowed(h)&&!['::','0.0.0.0'].includes(h))throw Error('RED EXTERNA PROHIBIDA: '+h);return lookup.call(this,h,...a)};\n"
                "const connect=net.Socket.prototype.connect; net.Socket.prototype.connect=function(...a){let o=Array.isArray(a[0])?a[0][0]:a[0];let h=typeof o==='object'?(o.host||o.hostname):(typeof a[1]==='string'?a[1]:null);if(!allowed(h))throw Error('RED EXTERNA PROHIBIDA: '+h);return connect.apply(this,a)};\n",encoding='utf-8')
            with patch.dict(os.environ,NODE_OPTIONS='--require "'+guard.as_posix()+'"'):
                final=e.process_reel(folder,config(),preview=True)
            self.assertFalse((folder/'raw.mp4').exists())
            self.assertFalse(e.read_json(final.parent/'plan_edicion.json')['rendered_audio']['audible'])
            self.assertEqual(e.read_json(final.parent/'metadata.json')['resolution'],[360,640])

    def test_authorized_local_audio_mix_and_preview_preserves_final(self):
        with tempfile.TemporaryDirectory(prefix="Música ñ O'Brien ") as td:
            folder=Path(td);fixture(folder,2,audio=True)
            e.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','sine=frequency=220:sample_rate=48000:duration=3',folder/'tone.wav'])
            e.write_json(folder/'transcript.json',e.transcript_document([e.Word(.3,1.3,'No dieciséis.')],e.fingerprint(folder/'raw.mp4'),2))
            spec=dict(schema_version=2,allowed_assets=['tone.wav'],render=dict(engine='remotion',music=dict(enabled=True,file='tone.wav',rights_declared=True)))
            e.write_json(folder/'edicion.json',spec)
            cfg=config();cfg['video'].update(width=1080,height=1920)
            final=e.process_reel(folder,cfg)
            alias=folder/'OUTPUT/VIDEO_BORRADOR.mp4';digest=e.fingerprint(alias)
            preview=e.process_reel(folder,cfg,preview=True)
            self.assertEqual(e.fingerprint(alias),digest)
            sound=e.read_json(preview.parent/'plan_edicion.json')['rendered_audio']
            self.assertTrue(sound['audible']);self.assertLess(sound['peak_db'],-.1)
            loudness=e.read_json(preview.parent/'plan_edicion.json')['rendered_loudness']
            self.assertIsNotNone(loudness['integrated_lufs'])
            self.assertLess(loudness['true_peak_dbtp'],0)
            props=e.read_json(preview.parent/'remotion_props.json')
            self.assertEqual(props['music']['volume'],.1)
            self.assertEqual(props['speech_windows'],[[.3,1.3]])
            self.assertEqual(e.read_json(final.parent/'metadata.json')['resolution'],[1080,1920])


if __name__=='__main__':unittest.main()
