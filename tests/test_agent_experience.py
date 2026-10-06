from contextlib import closing
from datetime import date
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fortune_agent.request_jobs import RequestJobs,ProgressClient,RequestCancelled
from fortune_agent.web import LocalApp
from fortune_agent.conversation import ConversationStore
from fortune_agent.fortune_store import FortuneStore,profile_token
from fortune_agent.unified_agent import UnifiedAgent
from fortune_agent.question_focus import question_guidance
from test_unified_agent import FakeResponses,plan


def wait_job(app,identifier):
    job=app.request_jobs.get(identifier)
    if not job.done.wait(5):raise AssertionError('test job did not complete')
    return app.run({'mode':'job-status','job_id':identifier})


class ProfileExperienceTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name);self.store=FortuneStore(self.path/'fortune.sqlite3');self.sessions=ConversationStore()
    def tearDown(self):self.temp.cleanup()
    def agent(self,plans):
        responses=FakeResponses(plans)
        return UnifiedAgent(SimpleNamespace(responses=responses),'test',self.path/'daily.sqlite3',threading.Lock()),responses
    def test_unconfirmed_profile_never_enters_router_or_satisfies_birth_input(self):
        self.store.save_profile('one','2000-01-01T12:00:00+08:00',gender='female')
        agent,responses=self.agent([plan(method='bazi',question='学习安排')])
        result=agent.turn(self.sessions.get(),'用八字分析学习安排','one')
        self.assertEqual(result['status'],'needs_input')
        payload=json.loads(responses.calls[0]['input'][0]['content'])
        self.assertEqual(payload['confirmed_profile'],{})
        self.assertNotIn('2000-01-01',json.dumps(payload))
    def test_confirmed_birth_and_style_and_gender_are_reused_without_reasking(self):
        self.store.save_profile('one','2000-01-01T12:00:00+08:00',gender='female',style='direct')
        agent,_=self.agent([plan(method='bazi',question='论文安排')])
        result=agent.turn(self.sessions.get(),'用八字梳理论文安排','one',use_saved_profile=True)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['result']['chart']['day'],'戊午')
        self.assertEqual(result['result']['complete_analysis']['luck']['gender_parameter'],'female')
    def test_confirmed_four_pillars_are_not_treated_as_model_invention(self):
        self.store.save_profile('one',pillars='己卯 丙子 戊午 戊午')
        agent,_=self.agent([plan(method='bazi',question='沟通安排')])
        result=agent.turn(self.sessions.get(),'八字看沟通安排','one',use_saved_profile=True)
        self.assertEqual(result['status'],'completed');self.assertIsNone(result['result']['chart']['birth_time'])
    def test_changed_profile_binding_recalculates_and_optout_removes_trusted_inputs(self):
        self.store.save_profile('one',pillars='己卯 丙子 戊午 戊午')
        agent,_=self.agent([plan(method='bazi',question='学习'),plan(method='bazi',question='学习'),plan(method='bazi',question='学习')]);session=self.sessions.get()
        first=agent.turn(session,'八字看学习','one',use_saved_profile=True)
        self.store.save_profile('one',pillars='甲子 丙寅 甲子 戊辰')
        second=agent.turn(session,'八字看学习','one',use_saved_profile=True)
        self.assertNotEqual(first['result']['chart']['day'],second['result']['chart']['day'])
        result=agent.turn(session,'八字看学习','one',use_saved_profile=False)
        self.assertEqual(result['status'],'needs_input');self.assertIsNone(session.artifact)
        self.assertEqual(len(session.messages),2)
    def test_web_requires_fresh_confirmation_token_before_profile_reuse(self):
        app=LocalApp(self.path/'daily.sqlite3');self.store.save_profile('one',pillars='己卯 丙子 戊午 戊午')
        preview=app.run({'mode':'profile-preview','profile':'one'});token=preview['confirmation_token']
        responses=FakeResponses([plan(method='bazi',question='学习')])
        app.model_client=lambda:(SimpleNamespace(responses=responses),'test')
        result=app.run({'mode':'chat','message':'八字看学习','profile':'one','profile_confirmation':token})
        self.assertEqual(result['status'],'completed')
        self.store.save_profile('one',pillars='甲子 丙寅 甲子 戊辰')
        with self.assertRaisesRegex(ValueError,'重新确认'):app.run({'mode':'chat','message':'继续','profile':'one','profile_confirmation':token})
    def test_saved_method_preference_only_applies_after_confirmation(self):
        self.store.save_profile('one',pillars='己卯 丙子 戊午 戊午',preferred_method='bazi')
        agent,_=self.agent([plan(method='none',question='学习')])
        result=agent.turn(self.sessions.get(),'梳理学习安排','one',use_saved_profile=True)
        self.assertEqual(result['method'],'bazi')


class RequestExperienceTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.app=LocalApp(Path(self.temp.name)/'daily.sqlite3')
    def tearDown(self):self.temp.cleanup()
    def test_offline_job_reports_completion_and_no_private_error_bodies(self):
        job=self.app.run({'mode':'job-start','request':{'mode':'bazi','pillars':'己卯 丙子 戊午 戊午'}})
        result=wait_job(self.app,job['job_id'])
        self.assertEqual(result['status'],'completed');self.assertIsNotNone(result['preview'])
        self.assertEqual(result['result']['chart']['day'],'戊午')
        with self.assertRaises(ValueError):self.app.run({'mode':'job-start','request':{'mode':'profile-delete','profile':'one'}})
    def test_provider_exception_is_sanitized(self):
        jobs=RequestJobs();identifier=jobs.start({},lambda p,j:(_ for _ in ()).throw(Exception('PRIVATE_KEY_AND_RESPONSE')) )['job_id']
        self.assertTrue(jobs.get(identifier).done.wait(2))
        state=jobs.status(identifier)
        self.assertEqual(state['status'],'failed');self.assertNotIn('PRIVATE',json.dumps(state))
    def test_cancel_checks_stop_next_api_call_and_late_result_is_not_adopted(self):
        started=threading.Event();release=threading.Event();calls=[]
        def create(**kw):calls.append(kw);started.set();release.wait(3);return SimpleNamespace(output_text='late answer')
        jobs=RequestJobs()
        def run(p,job):
            client=ProgressClient(SimpleNamespace(responses=SimpleNamespace(create=create)),job)
            client.responses.create(model='test',input=[])
            client.responses.create(model='test',input=[])
            return {'answer':'should not be adopted'}
        key=jobs.start({},run)['job_id'];self.assertTrue(started.wait(2));jobs.cancel(key)
        with self.assertRaisesRegex(ValueError,'稍后'):jobs.retry(key,run)
        release.set();self.assertTrue(jobs.get(key).done.wait(2))
        state=jobs.status(key);self.assertEqual(state['status'],'cancelled');self.assertIsNone(state['result']);self.assertEqual(len(calls),1)
    def test_cancelled_chat_preserves_session_and_fixed_tarot_for_retry(self):
        entered=threading.Event();release=threading.Event();base=FakeResponses([plan(method='tarot',question='怎样安排学习'),plan(action='followup',method='tarot',question='怎样安排学习')]);count=0
        def create(**kw):
            nonlocal count
            if kw.get('tool_choice')=='none':
                count+=1
                if count==1:entered.set();release.wait(3)
            return base.create(**kw)
        self.app.model_client=lambda:(SimpleNamespace(responses=SimpleNamespace(create=create)),'test')
        start=self.app.run({'mode':'job-start','request':{'mode':'chat','message':'塔罗看学习安排','profile':'one'}})
        key=start['job_id'];self.assertTrue(entered.wait(2));state=self.app.run({'mode':'job-status','job_id':key});sid=state['session_id'];reading=state['preview']['reading']
        self.assertTrue(sid);self.app.run({'mode':'job-cancel','job_id':key});release.set();wait_job(self.app,key)
        self.assertEqual(self.app.conversations.get(sid).messages,[])
        retried=self.app.run({'mode':'job-retry','job_id':key});final=wait_job(self.app,retried['job_id'])
        self.assertEqual(final['result']['result']['reading'],reading)
        self.assertEqual(final['result']['session_id'],sid)
    def test_manual_iching_retry_keeps_cast_after_model_failure(self):
        base=FakeResponses([]);calls=0
        def create(**kw):
            nonlocal calls
            calls+=1
            if calls==1:raise RuntimeError('模拟超时')
            return base.create(**kw)
        self.app.model_client=lambda:(SimpleNamespace(responses=SimpleNamespace(create=create)),'test')
        key=self.app.run({'mode':'job-start','request':{'mode':'iching','question':'学习安排','interpret':True}})['job_id']
        state=wait_job(self.app,key);self.assertEqual(state['status'],'failed');cast=state['preview']['cast']
        with patch('fortune_agent.web.cast_coins',side_effect=AssertionError('Retry must not recast')):
            retry=self.app.run({'mode':'job-retry','job_id':key});final=wait_job(self.app,retry['job_id'])
        self.assertEqual(final['result']['cast'],cast)
    def test_capacity_prevents_unbounded_pending_threads(self):
        jobs=RequestJobs(active_limit=1);started=threading.Event();release=threading.Event()
        def run(p,j):started.set();release.wait(3);return {}
        key=jobs.start({},run)['job_id'];self.assertTrue(started.wait(2))
        with self.assertRaises(ValueError):jobs.start({},run)
        release.set();self.assertTrue(jobs.get(key).done.wait(2))
        with self.assertRaises(ValueError):jobs.retry(key,run)
    def test_question_focus_does_not_invent_user_facts(self):
        study=question_guidance('论文与考试如何安排');relationship=question_guidance('怎样与伴侣沟通')
        self.assertIn('学习与研究',study);self.assertIn('完成标准',study)
        self.assertIn('不读取他人内心',relationship);self.assertIn('避免补出其经历',question_guidance('下一步怎么做'))

    def test_completed_jobs_are_evicted_when_capacity_is_reached(self):
        jobs=RequestJobs(limit=1,active_limit=1)
        first=jobs.start({},lambda p,j:{})['job_id'];self.assertTrue(jobs.get(first).done.wait(2))
        second=jobs.start({},lambda p,j:{})['job_id'];self.assertTrue(jobs.get(second).done.wait(2))
        with self.assertRaises(ValueError):jobs.get(first)
        self.assertEqual(jobs.status(second)['status'],'completed')

    def test_background_clients_are_closed_once_after_request(self):
        calls=[]
        inner=SimpleNamespace(responses=FakeResponses([]),close=lambda:calls.append('closed'))
        self.app.model_client=lambda:(inner,'test')
        key=self.app.run({'mode':'job-start','request':{'mode':'tarot','question':'学习安排','interpret':True}})['job_id']
        state=wait_job(self.app,key)
        self.assertEqual(state['status'],'completed');self.assertEqual(calls,['closed'])
