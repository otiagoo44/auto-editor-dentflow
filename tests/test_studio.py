import sys
import tempfile
import unittest
import io
import urllib.error
from unittest.mock import patch, Mock
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'worker'))
import editor as e
from editorial import propose
from planning import resolve_beats
from agent import Client,cleanup


class StudioPlannerTests(unittest.TestCase):
    def setUp(self):
        self.content=dict(id='TEST',source_version='fixture',demo_gate='')
        self.scene=dict(id='step',match_text='Una consulta pendiente',purpose='Aclarar el siguiente paso',reason='Frase literal del guion',template='QuestionHook',params={'title':'¿Qué sigue?'},approved=True,duration=2,layout='card',demo=True)
        self.words=[e.Word(6,6.3,'Una'),e.Word(6.3,6.7,'consulta'),e.Word(6.7,7,'pendiente')]

    def test_unique_trigger_and_three_cut_remapping(self):
        plan,decisions,warnings=propose(self.content,[self.scene],self.words,10,{})
        self.assertEqual(decisions[0]['status'],'resolved')
        source=resolve_beats(plan,self.words,10,[])
        with tempfile.TemporaryDirectory() as td:
            events=e.prepare_events(source,[(0,1),(2,3),(4,5),(6,10)],Path(td),10,strict=True)
        self.assertEqual(events[0]['start'],3)
        self.assertEqual(decisions[0]['source_time'],[6,8])
        self.assertEqual(decisions[0]['provenance']['rule'],'unique_spoken_phrase')

    def test_ambiguous_trigger_demo_gate_and_unapproved_assets_stay_camera(self):
        for words,content,scene,assets in [
            (self.words+[e.Word(8,9,'Una consulta pendiente')],self.content,self.scene,{}),
            (self.words,{**self.content,'demo_gate':'D1'},self.scene,{}),
            (self.words,self.content,{**self.scene,'asset_id':'absent'},{}),
            (self.words,self.content,{**self.scene,'approved':False},{})]:
            plan,decisions,_=propose(content,[scene],words,12,assets)
            self.assertEqual(plan['beats'],[])
            self.assertIn(decisions[0]['status'],('suggested','omitted'))

    def test_worker_never_connects_insecure_remote_or_accepts_url_credentials(self):
        for url in ('http://evil.test','https://user:password@example.com','file:///tmp','https://example.com/?token=secret'):
            with self.assertRaises(ValueError):Client(url,'x'*32)
        Client('http://127.0.0.1:3000','x'*32)

    def test_cleanup_does_not_touch_unmarked_or_unfinished_work(self):
        with tempfile.TemporaryDirectory() as td:
            state=Path(td);unfinished=state/'unfinished';unfinished.mkdir();(unfinished/'raw.mp4').write_bytes(b'fixture')
            cleanup(state,days=0)
            self.assertTrue((unfinished/'raw.mp4').exists())

    def test_worker_retries_lost_finish_response_but_never_replays_lease(self):
        client=Client('http://127.0.0.1:3000','x'*32)
        with patch.object(client,'_request',side_effect=[TimeoutError(),{'ok':True}]) as call, patch('agent.time.sleep'):
            self.assertEqual(client.request('/api/worker/test/finish',{}),{'ok':True})
            self.assertEqual(call.call_count,2)
        with patch.object(client,'_request',side_effect=TimeoutError()) as call:
            with self.assertRaises(TimeoutError):client.request('/api/worker/lease',{})
            self.assertEqual(call.call_count,1)

    def test_interrupted_download_never_becomes_a_valid_cached_source(self):
        client=Client('http://127.0.0.1:3000','x'*32)
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'raw.mp4'
            with patch.object(client.opener,'open',return_value=io.BytesIO(b'short')):
                with self.assertRaisesRegex(ValueError,'invalid_media'):
                    client.download({'id':'job','lease_token':'lease'},{'id':'asset','size':100},target,100)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_name('raw.mp4.partial').exists())


if __name__=='__main__':unittest.main()
