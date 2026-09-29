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
    if (folder/'raw.mp4').exists():
        raise ValueError('Fixture no puede sobrescribir raw.mp4 existente.')
    cmd = ['ffmpeg', '-v', 'error', '-n', '-f', 'lavfi', '-i',
           f'testsrc2=s=180x320:r=30:d={duration}']
    if audio:
        cmd += ['-f', 'lavfi', '-i', f'sine=frequency=330:sample_rate=48000:duration={duration}', '-c:a', 'aac']
    e.run(cmd + ['-c:v', 'libx264', '-threads', '1', '-pix_fmt', 'yuv420p', folder/'raw.mp4'])


class AutoTests(unittest.TestCase):
    def test_invalid_cut_policy_rejected(self):
        from planning import policies
        with self.assertRaisesRegex(ValueError, 'auto_min_gap_seconds'):
            policies({'cut_policy': {'auto_min_gap_seconds': 7, 'auto_max_gap_seconds': 3}}, config())

    def test_final_preview_and_failed_render_preserve_aliases(self):
        with tempfile.TemporaryDirectory(prefix="Alias ñ O'Brien ") as td:
            folder=Path(td)
            fixture(folder,1)
            cfg=config()
            cfg['video'].update(width=1080,height=1920)
            e.process_reel(folder,cfg,auto=True)
            final=folder/'OUTPUT/VIDEO_BORRADOR.mp4'
            digest=e.fingerprint(final)
            e.process_reel(folder,cfg,auto=True,preview=True)
            preview=folder/'OUTPUT/VIDEO_PREVIEW.mp4'
            prev_digest=e.fingerprint(preview)
            self.assertEqual(e.fingerprint(final),digest)
            for name,size in [('VIDEO_BORRADOR',[1080,1920]),('VIDEO_PREVIEW',[360,640])]:
                meta=e.read_json(folder/f'OUTPUT/{name}.json')
                self.assertEqual(meta['resolution'],size)
                self.assertEqual(meta['source_sha256'],e.fingerprint(folder/'raw.mp4'))
                self.assertEqual(meta['output_sha256'],e.fingerprint(folder/f'OUTPUT/{name}.mp4'))
                self.assertEqual(meta['validation'],'probe+full_decode_passed')
            for is_preview in (False,True):
                with patch.object(e,'render_final',side_effect=RuntimeError('fallo simulado')):
                    with self.assertRaises(RuntimeError):
                        e.process_reel(folder,cfg,preview=is_preview)
                self.assertEqual(e.fingerprint(final),digest)
                self.assertEqual(e.fingerprint(preview),prev_digest)

    def test_transcript_identity_migration_and_word_overlap(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            fixture(folder,2,audio=True)
            path=folder/'transcript.json'
            legacy=dict(words=[dict(start=.1,end=.8,text='No 16:00.')])
            e.write_json(path,legacy)
            digest=e.fingerprint(folder/'raw.mp4')
            with self.assertRaisesRegex(ValueError,'sin identidad'):
                e.process_reel(folder,config(),plan_only=True)
            with self.assertRaises(ValueError):
                e.migrate_transcript(folder,'0'*64)
            e.migrate_transcript(folder,digest)
            result=e.process_reel(folder,config(),plan_only=True)
            exported=e.read_json(result/'transcript.json')
            self.assertEqual(exported['source_sha256'],digest)
            self.assertEqual(e.read_json(folder/'transcript.legacy.json'),legacy)
            with self.assertRaisesRegex(ValueError,'otra fuente'):
                e.validate_transcript_identity(exported,'0'*64,2)
            with self.assertRaisesRegex(ValueError,'otra fuente'):
                e.validate_transcript_identity(exported,digest,3)
            with self.assertRaisesRegex(ValueError,'otra fuente'):
                e.validate_transcript_identity(dict(exported,source_duration=float('nan')),digest,2)
            # Incluso sin voz: no reutilizar un transcript de otra fuente.
            changed=dict(exported,source_sha256='0'*64)
            e.write_json(path,changed)
            with patch.object(e,'audio_analysis',return_value=dict(audible=False)):
                with self.assertRaisesRegex(ValueError,'otra fuente'):
                    e.process_reel(folder,config(),plan_only=True)
        for bad in ([dict(start=1,end=2,text='No'),dict(start=.9,end=1.5,text='12')],
                    [dict(start=0,end=1,text='No'),dict(start=.9,end=2,text='12')]):
            with self.assertRaises(ValueError):
                e.validate_words(bad,3)
        warnings=[]
        words=e.validate_words([dict(start=0,end=1,text='No'),dict(start=.99,end=2,text='12.')],3,warnings)
        self.assertEqual(words[1].start,1)
        self.assertEqual(words[1].text,'12.')
        self.assertTrue(warnings)
        self.assertEqual(e.lines_for('electroencefalografista1234567890',26),['electroencefalografista1234567890'])

    def test_fixture_collision_and_environment_cannot_select_production(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            source=folder/'raw.mp4'
            source.write_bytes(b'VIDEO PERSONAL NO TOCAR')
            with patch.dict(os.environ,DENTFLOW_VALIDATION=str(folder)):
                with self.assertRaisesRegex(ValueError,'sobrescribir'):
                    fixture(folder)
            self.assertEqual(source.read_bytes(),b'VIDEO PERSONAL NO TOCAR')

    def test_diagnose_fails_missing_required_capability(self):
        with patch.object(e.shutil,'which',return_value=None):
            self.assertFalse(e.diagnose(config()))
        with patch.object(e,'run',return_value=' ass '):
            self.assertFalse(e.diagnose(config()))

    def test_invalid_editorial_interventions_fall_back_to_camera(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            fixture(folder,3)
            for event in [dict(type='asset',file='../../secret.png',approved=True,start=0,end=1,reason='fuera'),
                          dict(type='asset',file='missing.png',approved=True,reason='sin tiempos'),
                          dict(type='reframe',approved=False,start=0,end=1,reason='no aprobado'),
                          dict(type='reframe',approved=True,start=.5,end=2.5,reason='cruza corte')]:
                e.write_json(folder/'edicion.json',dict(schema_version=2,allowed_assets=[],
                    keep_segments=[[0,1],[2,3]],events=[event]))
                output=e.process_reel(folder,config(),plan_only=True)
                plan=e.read_json(output/'plan_edicion.json')
                self.assertEqual(plan['events'],[])
                self.assertTrue(any('fallback=camera' in w for w in plan['warnings']))
                self.assertEqual(plan['cut_joins'][0]['output_time'],1)

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
            self.assertTrue(final.exists())

    def test_auto_baseline(self):
        # Nunca tomar una raíz de fixtures desde variables de entorno.
        with tempfile.TemporaryDirectory(prefix="DentFlow prueba ñ O'Brien ") as td:
            folder = Path(td)/'Reel 1'
            fixture(folder)
            final = e.process_reel(folder, config(), auto=True, preview=True)
            plan = e.read_json(final.parent/'plan_edicion.json')
            self.assertEqual(plan['keep_segments'], [[0, 12]])
            self.assertEqual(plan['events'], [])
            self.assertAlmostEqual(e.ffprobe_duration(final), 12, delta=.1)
            # Fallar un render posterior nunca reemplaza la última salida válida.
            digest = e.fingerprint(folder/'OUTPUT/VIDEO_PREVIEW.mp4')
            with patch.object(e, 'render_final', side_effect=RuntimeError('fallo simulado')):
                with self.assertRaises(RuntimeError):
                    e.process_reel(folder, config(), auto=True)
            self.assertEqual(digest, e.fingerprint(folder/'OUTPUT/VIDEO_PREVIEW.mp4'))
            repeat = e.process_reel(folder, config(), auto=True, preview=True)
            self.assertEqual(e.fingerprint(final), e.fingerprint(repeat))

    def test_asr_failure_is_camera_only(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            fixture(folder, 2, audio=True)
            e.write_json(folder/'edicion.json',dict(schema_version=2,keep_segments=[[0,1]],events=[
                dict(type='text',text='No debe aparecer',start=0,end=1,approved=True,reason='No hay ASR fiable')]))
            with patch.object(e, 'get_words', side_effect=RuntimeError('modelo ausente')):
                final = e.process_reel(folder, config(), auto=True)
            plan = e.read_json(final.parent/'plan_edicion.json')
            self.assertEqual(plan['captions'], [])
            self.assertEqual(plan['events'], [])
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
            with self.assertRaisesRegex(ValueError,'allowed_assets'):
                e.prepare_events([event],[(0,4)],reel,4)  # V1 no evade allowlist.
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
            e.write_json(folder/'transcript.json',e.transcript_document([e.Word(1,3,'Ejemplo ficticio.')],e.fingerprint(folder/'raw.mp4'),8))
            final = e.process_reel(folder,config(),preview=True)
            self.assertAlmostEqual(e.ffprobe_duration(final),8,delta=.1)
            self.assertIn('EJEMPLO FICTICIO',(final.parent/'subtitulos.ass').read_text(encoding='utf-8'))


def center_pixel(path, t):
    raw = subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(path),
        '-vf','crop=2:2:(iw-2)/2:(ih-2)/2,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'])
    return tuple(raw[:3])


class AcceptanceTests(unittest.TestCase):
    def test_adjacent_graphics_no_blank_frame_at_fractional_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            e.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','color=c=red:s=180x320:r=30:d=3',
                   '-c:v','libx264','-threads','1',folder/'raw.mp4'])
            for color in ('lime','blue'):
                e.run(['ffmpeg','-v','error','-n','-f','lavfi','-i',f'color=c={color}:s=180x320',
                       '-frames:v','1','-threads','1',folder/(color+'.png')])
            e.write_json(folder/'edicion.json',dict(schema_version=2,allowed_assets=['lime.png','blue.png'],events=[
                dict(type='asset',file='lime.png',start=.2,end=1.28,approved=True,layout='full',animation='none',reason='Primero'),
                dict(type='asset',file='blue.png',start=1.28,end=2.5,approved=True,layout='full',animation='none',reason='Segundo')]))
            cfg=config();cfg['subtitles']['enabled']=False
            final=e.process_reel(folder,cfg)
            for t in (1.20,1.233334,1.266667):
                self.assertGreater(center_pixel(final,t)[1],200,f'PNG termina antes del evento: {t}')
            for t in (1.30,2.40,2.466667):
                self.assertGreater(center_pixel(final,t)[2],200,f'PNG termina antes del evento: {t}')
            self.assertLess(center_pixel(final,2.6)[2],200)

    def test_hdr_pq_hlg_hevc_to_sdr_and_no_sdr_tonemap(self):
        with tempfile.TemporaryDirectory(prefix="HDR ñ O'Brien ") as td:
            folder=Path(td)
            for transfer in ('arib-std-b67','smpte2084'):
                # Fixture generado en espacio SDR y convertido a HDR, no sólo retagged.
                raw=folder/(transfer+'.mp4')
                vf=('format=yuv420p,zscale=pin=bt709:tin=bt709:min=bt709:rin=limited:'
                    f'p=bt2020:t={transfer}:m=bt2020nc:r=limited,format=yuv420p10le')
                e.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','testsrc2=s=180x320:r=30:d=1',
                       '-vf',vf,'-c:v','libx265','-threads','1','-x265-params','pools=1:frame-threads=1',
                       '-color_primaries','bt2020','-color_trc',transfer,'-colorspace','bt2020nc',raw])
                e.write_json(folder/'edicion.json',dict(source=raw.name))
                final=e.process_reel(folder,config())
                stream=next(s for s in e.probe(final)['streams'] if s['codec_type']=='video')
                self.assertEqual((stream['color_transfer'],stream['color_primaries'],stream['pix_fmt']),('bt709','bt709','yuv420p'))
                self.assertIn('tonemap=',e.read_json(final.parent/'plan_edicion.json')['color_conversion'])
                self.assertGreater(sum(center_pixel(final,.5)),30)
            self.assertNotIn('tonemap',e.color_filter(dict(color_transfer='bt709',color_space='bt709',color_primaries='bt709')))
            with self.assertRaisesRegex(ValueError,'HDR sin'):
                e.color_filter(dict(color_transfer='smpte2084'))

    def test_animated_punch_really_moves_and_returns(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            e.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=180x320',
                   '-frames:v','1','-threads','1',folder/'still.png'])
            e.run(['ffmpeg','-v','error','-y','-loop','1','-framerate','30','-i',folder/'still.png',
                   '-t','4','-c:v','libx264','-threads','1','-pix_fmt','yuv420p',folder/'raw.mp4'])
            e.write_json(folder/'edicion.json',dict(schema_version=2,events=[dict(type='reframe',
                start=.5,end=3.5,approved=True,animated=True,scale=1.1,reason='Prueba movimiento real')]))
            final=e.process_reel(folder,config())
            def pixels(t):
                return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(final),
                    '-vf','scale=60:100','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'])
            frames=[pixels(t) for t in (.2,1,2,3.8)]
            def diff(a,b):
                return sum(abs(x-y) for x,y in zip(a,b))/len(a)
            self.assertGreater(diff(frames[0],frames[2]),3)
            self.assertGreater(diff(frames[1],frames[2]),1)
            self.assertLess(diff(frames[0],frames[3]),2)

    def test_content_root_and_subtitle_clipping_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            folder=root/'Reel 1'
            fixture(folder,2,audio=True)
            e.write_json(folder/'transcript.json',e.transcript_document([e.Word(.2,1.8,'W'*26)],e.fingerprint(folder/'raw.mp4'),2))
            cfg=config()
            cfg['content_root']=str(root)
            path=root/'config.yaml'
            path.write_text(yaml.safe_dump(cfg),encoding='utf-8')
            result=subprocess.run([sys.executable,str(ROOT/'src/editor.py'),'Reel 1','--config',str(path),'--plan-only'],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            plan=e.read_json(next((folder/'OUTPUT').glob('*/plan_edicion.json')))
            self.assertTrue(plan['caption_diagnostics'][0]['possible_horizontal_clipping'])
            self.assertTrue(any('desborde' in w for w in plan['warnings']))

    @unittest.skipUnless(os.environ.get('DENTFLOW_ASR_SAMPLE'), 'ASR real opt-in: DENTFLOW_ASR_SAMPLE=clip local')
    def test_offline_asr_with_socket_connections_denied(self):
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/'words.json'
            command = ("import socket,sys; from pathlib import Path; from unittest.mock import patch; "
                       "sys.path.insert(0,sys.argv[1]); import editor; "
                       "guard=patch.object(socket.socket,'connect',side_effect=AssertionError('RED PROHIBIDA')); "
                       "guard.start(); editor.transcribe_worker(Path(sys.argv[2]),Path(sys.argv[3]),"
                       "{'model':'base','offline':True,'language':'es','threads':2}); guard.stop()")
            result=subprocess.run([sys.executable,'-c',command,str(ROOT/'src'),os.environ['DENTFLOW_ASR_SAMPLE'],str(output)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8','replace'))
            self.assertGreater(len(e.read_json(output)['words']),10)

    def test_overlay_window_16_9_and_alpha_after_second_cut(self):
        with tempfile.TemporaryDirectory(prefix="Overlay ñ O'Brien ") as td:
            folder=Path(td)
            cfg=config()
            cfg['subtitles']['enabled']=False
            e.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=red:s=180x320:r=30:d=6',
                   '-c:v','libx264','-threads','1',folder/'raw.mp4'])
            e.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=lime:s=320x180',
                   '-frames:v','1','-threads','1',folder/'wide.png'])
            e.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=320x180:r=30:d=2',
                   '-c:v','libx264','-threads','1',folder/'wide.mp4'])
            e.write_json(folder/'edicion.json',dict(schema_version=2,allowed_assets=['wide.png','wide.mp4'],
                keep_segments=[[0,1.5],[2,3.5],[4,6]],events=[
                    dict(type='asset',file='wide.png',start=.2,end=1.2,approved=True,layout='full',reason='PNG'),
                    dict(type='asset',file='wide.mp4',offset=.5,start=4.2,end=5.5,approved=True,layout='full',reason='MP4')]))
            final=e.process_reel(folder,cfg)
            self.assertAlmostEqual(e.ffprobe_duration(final),5,delta=.07)
            before,fade,mid,after,clip,done=[center_pixel(final,t) for t in (.1,.2667,.7,1.4,3.8,4.8)]
            self.assertGreater(before[0],200)
            self.assertTrue(30 < fade[0] < 220 and 30 < fade[1] < 220,fade)
            self.assertGreater(mid[1],200)
            self.assertGreater(after[0],200)
            self.assertGreater(clip[2],200)
            self.assertGreater(done[0],200)

    def test_digital_silence_with_asr_on(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            e.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=gray:s=180x320:r=30:d=2',
                   '-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','2','-c:v','libx264',
                   '-threads','1','-c:a','aac',folder/'raw.mp4'])
            with patch.object(e,'get_words',side_effect=AssertionError('No transcribir silencio')):
                final=e.process_reel(folder,config(),auto=True)
            plan=e.read_json(final.parent/'plan_edicion.json')
            self.assertFalse(plan['audio_analysis']['audible'])
            self.assertFalse(plan['rendered_audio']['audible'])

    def test_vfr_rotated_input_and_audio_joins(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            # Cadencia variable real: 30 fps primeros 2 s, luego uno de cada dos cuadros.
            e.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=30:d=10',
                   '-f','lavfi','-i',r"aevalsrc=if(between(t\,1\,3.2)\,0\,0.1*sin(2*PI*330*t)):s=48000:d=10",
                   '-vf',r"select=if(lt(t\,2)\,1\,not(mod(n\,2)))",'-fps_mode','vfr',
                   '-c:v','libx264','-threads','1','-c:a','aac',folder/'source.mp4'])
            e.run(['ffmpeg','-v','error','-y','-i',folder/'source.mp4','-c','copy',
                   '-metadata:s:v:0','rotate=90',folder/'raw.mp4'])
            e.write_json(folder/'transcript.json',e.transcript_document([e.Word(.2,.9,'No.'),
                e.Word(3.3,3.7,'12.'),e.Word(4,4.5,'Consultas.')],e.fingerprint(folder/'raw.mp4'),e.ffprobe_duration(folder/'raw.mp4')))
            final=e.process_reel(folder,config(),auto=True)
            plan=e.read_json(final.parent/'plan_edicion.json')
            self.assertEqual(len(plan['keep_segments']),2)
            self.assertEqual(plan['fps'],'30/1')
            self.assertLess(plan['output_duration'],10)
            self.assertLess(plan['rendered_audio']['peak_db'],0)
            video=next(s for s in e.probe(final)['streams'] if s['codec_type']=='video')
            self.assertEqual((video['width'],video['height']),(180,320))
            # La unión cae dentro del silencio conservado; no hay sílabas/tone solapados.
            boundary=plan['time_map'][0]['output_end']
            raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(boundary-.05),'-i',str(final),
                '-t','0.1','-f','f32le','-ac','1','-ar','48000','-'])
            import array
            samples=array.array('f',raw)
            self.assertLess(max(map(abs,samples)),.001)

    @unittest.skipUnless(sys.platform=='win32','BAT Windows')
    def test_week_and_windows_paths_with_partial_failure(self):
        with tempfile.TemporaryDirectory(prefix="Semana ñ O'Brien ") as td:
            week=Path(td)
            assets=week/'Assets'
            assets.mkdir()
            for i,color in [(1,'blue'),(2,'lime')]:
                folder=week/f'Reel {i}'
                fixture(folder,2)
                name=f'demo {i}.png'
                e.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c={color}:s=180x320',
                       '-frames:v','1','-threads','1',assets/name])
                e.write_json(folder/'edicion.json',dict(schema_version=2,allowed_assets=[f'../Assets/{name}'],events=[
                    dict(type='asset',file=f'../Assets/{name}',start=.2,end=1.7,approved=True,layout='full',reason='Test propio')]))
            cmd=[str(ROOT/'editar_semana.bat'),str(week),'--auto','--preview']
            good=subprocess.run(cmd,capture_output=True)
            self.assertEqual(good.returncode,0,good.stderr)
            one=week/'Reel 1/OUTPUT/VIDEO_PREVIEW.mp4'
            two=week/'Reel 2/OUTPUT/VIDEO_PREVIEW.mp4'
            self.assertGreater(center_pixel(one,1)[2],200)
            self.assertGreater(center_pixel(two,1)[1],200)
            # Ampliación a cinco: tres correctos adicionales; uno se hace fallar después.
            for i in (3,4,5):
                fixture(week/f'Reel {i}',1)
            five=subprocess.run(cmd,capture_output=True)
            self.assertEqual(five.returncode,0,five.stderr)
            e.write_json(week/'Reel 2/edicion.json',dict(source='falta.mp4'))
            previous=e.fingerprint(two)
            failed=subprocess.run(cmd,capture_output=True)
            self.assertEqual(failed.returncode,1)
            self.assertIn(b'4 correctos; 1 fallidos',failed.stdout)
            self.assertEqual(previous,e.fingerprint(two))
            self.assertTrue((week/'Reel 5/OUTPUT/VIDEO_PREVIEW.mp4').exists())
            report=e.read_json(sorted((week/'OUTPUT').glob('lote_*.json'))[-1])
            self.assertEqual((report['passed'],report['failed']),(4,1))
            self.assertEqual(report['results'][0]['metadata']['resolution'],[360,640])
            plan_only=subprocess.run([str(ROOT/'editar_reel.bat'),str(week/'Reel 1'),'--plan-only'],capture_output=True)
            self.assertEqual(plan_only.returncode,0,plan_only.stderr)


if __name__ == '__main__':
    unittest.main()
