from contextlib import closing
from datetime import date,datetime,timedelta
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from fortune_agent.bazi import calculate_bazi,parse_bazi_pillars
from fortune_agent.bazi_analysis import comprehensive_analysis,luck_cycles
from fortune_agent.fortune_store import FortuneStore
from fortune_agent.fortune_daily import make_daily_report
from fortune_agent.web import LocalApp


class CompleteFortuneTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=FortuneStore(Path(self.temp.name)/'fortune.sqlite3')
    def tearDown(self):self.temp.cleanup()

    def test_birth_and_gender_are_required_without_invention(self):
        chart=parse_bazi_pillars('己卯 丙子 戊午 戊午')
        self.assertEqual(luck_cycles(chart,'male')['status'],'needs_input')
        self.assertEqual(luck_cycles(calculate_bazi('2000-01-01T12:00:00+08:00'))['status'],'needs_input')
        with self.assertRaises(ValueError):luck_cycles(chart,'unknown')

    def test_fixed_start_dates_and_opposite_directions(self):
        chart=calculate_bazi('2000-01-01T12:00:00+08:00')
        male=luck_cycles(chart,'male',date(2026,10,5))
        female=luck_cycles(chart,'female',date(2026,10,5))
        self.assertFalse(male['forward']);self.assertTrue(female['forward'])
        self.assertEqual(male['starts_at'],'2008-03-12T14:00:00+08:00')
        self.assertEqual(female['starts_at'],'2001-08-16T12:00:00+08:00')
        self.assertEqual([c['ganzhi'] for c in male['cycles'][:3]],['乙亥','甲戌','癸酉'])
        self.assertEqual([c['ganzhi'] for c in female['cycles'][:3]],['丁丑','戊寅','己卯'])
        self.assertEqual(male['current_cycle']['ganzhi'],'甲戌')

    def test_current_cycle_uses_exact_onset_anniversary_not_calendar_year(self):
        chart=calculate_bazi('2000-01-01T12:00:00+08:00')
        prior=luck_cycles(chart,'male',date(2018,3,11))
        after=luck_cycles(chart,'male',date(2018,3,13))
        self.assertEqual(prior['current_cycle']['ganzhi'],'乙亥')
        self.assertEqual(after['current_cycle']['ganzhi'],'甲戌')
        self.assertEqual(luck_cycles(chart,'male',date(2001,1,1))['current_state'],'before_start')

    def test_strength_evidence_does_not_become_counting_based_final_judgment(self):
        full=comprehensive_analysis(parse_bazi_pillars('庚申 丙寅 甲子 戊辰'))
        self.assertTrue(full['strength']['support_observations'])
        self.assertTrue(full['strength']['drain_control_observations'])
        self.assertEqual(full['strength']['status'],'estimated')
        self.assertEqual(full['strength']['classical_status'],'unresolved')
        self.assertTrue(all(p['formation_status']=='unresolved' for p in full['patterns']))
        self.assertEqual({p['id'] for p in full['useful_god_methods']},{'pattern','balance','climate'})

    def test_profile_validation_and_private_file_mode(self):
        with self.assertRaises(ValueError):self.store.save_profile('one','2000-01-01T12:00:00+08:00',timezone='America/New_York')
        with self.assertRaises(ValueError):self.store.save_profile('one','2000-01-01T12:00:00+08:00','甲子 丙寅 甲子 戊辰')
        self.assertEqual(self.store.path.stat().st_mode&0o777,0o600)

    def test_daily_combines_same_card_chart_context_and_luck_without_api(self):
        self.store.save_profile('one','2000-01-01T12:00:00+08:00',gender='female')
        first=make_daily_report(self.store,'one',date(2026,10,5))
        second=make_daily_report(self.store,'one',date(2026,10,5))
        self.assertTrue(second['cached']);self.assertFalse(first['cached'])
        self.assertEqual(first['reading'],second['reading'])
        self.assertEqual(first['daily_context']['date'],'2026-10-05')
        self.assertEqual(first['natal_chart']['day'],'戊午')
        self.assertEqual(first['natal_facts']['month_branch'],'子')
        self.assertEqual(first['bazi_analysis']['luck']['status'],'calculated')
        self.assertEqual(len(first['reflections']),2)
        ids=[e['id'] for e in first['daily_interactions']['observations']]
        self.assertEqual(len(ids),len(set(ids)))

    def test_profile_change_changes_cache_but_keeps_same_daily_tarot(self):
        self.store.save_profile('one',pillars='己卯 丙子 戊午 戊午')
        first=make_daily_report(self.store,'one',date(2026,10,5))
        self.store.save_profile('one',pillars='甲子 丙寅 甲子 戊辰')
        second=make_daily_report(self.store,'one',date(2026,10,5))
        self.assertNotEqual(first['key'],second['key'])
        self.assertEqual(first['reading'],second['reading'])
        self.assertEqual(len(self.store.history('one')),2)

    def test_review_is_scoped_and_delete_removes_all_owned_history(self):
        self.store.save_profile('one');self.store.save_profile('two')
        report=make_daily_report(self.store,'one',date(2026,10,5))
        with self.assertRaises(ValueError):self.store.review('two',report['key'],'wrong owner')
        self.store.review('one',report['key'],'完成了论文小节')
        export=self.store.export('one')
        self.assertEqual(export['history'][0]['review'],'完成了论文小节')
        self.store.delete('one')
        self.assertEqual(self.store.history('one'),[])
        with self.assertRaises(ValueError):self.store.get_profile('one')
        self.assertEqual(self.store.get_profile('two')['id'],'two')

    def test_taro_only_other_timezone_and_model_is_called_once(self):
        self.store.save_profile('one',timezone='America/New_York')
        calls=[]
        def create(**kw):calls.append(kw);return SimpleNamespace(output_text='今天选择一个小目标。')
        client=SimpleNamespace(responses=SimpleNamespace(create=create))
        first=make_daily_report(self.store,'one',date(2026,10,5),client,'test')
        make_daily_report(self.store,'one',date(2026,10,5),client,'test')
        self.assertEqual(len(calls),1)
        self.assertFalse(calls[0]['store'])
        self.assertIsNone(first['daily_context'])
        self.assertEqual(first['day'],'2026-10-05')
        self.assertNotIn('"id": "one"',calls[0]['input'][0]['content'])

    def test_empty_model_result_is_not_saved(self):
        self.store.save_profile('one')
        client=SimpleNamespace(responses=SimpleNamespace(create=lambda **kw:SimpleNamespace(output_text=' ')))
        with self.assertRaises(RuntimeError):make_daily_report(self.store,'one',date(2026,10,5),client,'test')
        self.assertEqual(self.store.history('one'),[])

    def test_web_actions_end_to_end_without_model(self):
        app=LocalApp(Path(self.temp.name)/'daily.sqlite3')
        app.run({'mode':'profile-save','profile':'one','birth':'2000-01-01T12:00:00+08:00','gender':'male'})
        data=app.run({'mode':'daily-report','profile':'one','date':'2026-10-05'})
        self.assertEqual(data['mode'],'daily-report')
        self.assertEqual(data['bazi_analysis']['luck']['current_cycle']['ganzhi'],'甲戌')
        app.run({'mode':'daily-review','profile':'one','key':data['key'],'review':'完成一项任务'})
        self.assertEqual(app.run({'mode':'profile-export','profile':'one'})['history'][0]['review'],'完成一项任务')
        app.run({'mode':'profile-delete','profile':'one'})
        self.assertEqual(app.run({'mode':'daily-history','profile':'one'})['history'],[])

    def test_cannot_generate_daily_before_birth(self):
        self.store.save_profile('one','2000-01-01T12:00:00+08:00')
        with self.assertRaises(ValueError):make_daily_report(self.store,'one',date(1999,1,1))

    def test_cached_web_report_does_not_require_model_config(self):
        app=LocalApp(Path(self.temp.name)/'daily.sqlite3')
        app.run({'mode':'profile-save','profile':'one'})
        app.run({'mode':'daily-report','profile':'one','date':'2026-10-05'})
        app.model_client=lambda: (_ for _ in ()).throw(AssertionError('cached report must not construct client'))
        result=app.run({'mode':'daily-report','profile':'one','date':'2026-10-05','interpret':True})
        self.assertTrue(result['cached'])

    def test_deleted_profile_cannot_be_recreated_by_inflight_report_save(self):
        self.store.save_profile('one')
        data=make_daily_report(self.store,'one',date(2026,10,5))
        self.store.delete('one')
        with self.assertRaises(ValueError):self.store.save_report(data['key'],'one',data['day'],data)
        self.assertEqual(self.store.history('one'),[])

    def test_unified_daily_uses_saved_profile_and_keeps_card_for_followup(self):
        from fortune_agent.unified_agent import UnifiedAgent
        from threading import Lock
        calls=[]
        def create(**kw):calls.append(kw);return SimpleNamespace(output_text='综合日报：完成一个小目标。')
        client=SimpleNamespace(responses=SimpleNamespace(create=create))
        self.store.save_profile('one',pillars='己卯 丙子 戊午 戊午')
        agent=UnifiedAgent(client,'test',Path(self.temp.name)/'daily.sqlite3',Lock())
        artifact=agent.prepare('daily','今天运势',{},'one','Asia/Shanghai')
        self.assertEqual(artifact.data['mode'],'daily-report')
        self.assertIsNotNone(artifact.data['daily_context'])
        card=artifact.data['reading']
        result=agent.explain(artifact,'如何安排学习','gentle')
        self.assertEqual(result['reading'],card)
        self.assertEqual(len(calls),2)

    def test_conditional_pattern_questions_do_not_declare_cooperation_as_success(self):
        full=comprehensive_analysis(parse_bazi_pillars('己卯 丙子 戊午 戊午'))
        pattern=full['patterns'][0]
        self.assertIn('research_question',pattern)
        self.assertEqual(pattern['formation_status'],'unresolved')
        self.assertEqual({s['id'] for s in full['balance_scenarios']},{'strong','weak','special'})
        self.assertTrue(all(s['status']=='conditional_not_selected' for s in full['balance_scenarios']))

    def test_saved_review_is_not_sent_to_router_or_followup_model(self):
        from fortune_agent.unified_agent import UnifiedAgent,ROUTE_SCHEMA
        from threading import Lock
        captured=[]
        route={key:None for key in ROUTE_SCHEMA['required']}
        route.update(action='followup',method='daily',reply='')
        def create(**kw):
            captured.append(kw)
            if 'tools' in kw:return SimpleNamespace(output=[SimpleNamespace(type='function_call',name='choose_action',arguments=json.dumps(route))])
            return SimpleNamespace(output_text='保留同一日报的行动建议。')
        client=SimpleNamespace(responses=SimpleNamespace(create=create))
        self.store.save_profile('one')
        agent=UnifiedAgent(client,'test',Path(self.temp.name)/'daily.sqlite3',Lock())
        artifact=agent.prepare('daily','今天运势',{},'one','Asia/Shanghai')
        artifact.data['review']='PRIVATE_REVIEW_ONLY_LOCAL'
        session=SimpleNamespace(artifact=artifact,slots={},messages=[])
        agent.decide(session,'怎么安排学习？')
        agent.explain(artifact,'怎么安排学习？','gentle')
        for request in captured:
            self.assertNotIn('PRIVATE_REVIEW_ONLY_LOCAL',json.dumps(request,ensure_ascii=False))
