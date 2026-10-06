from datetime import datetime
from pathlib import Path
import tempfile
from threading import Lock
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fortune_agent.astrology import calculate_astrology,validate_birth,coordinates
from fortune_agent.ziwei import calculate_ziwei,node_executable
from fortune_agent.tarot import draw_reading,SPREADS
from fortune_agent.tarot_sessions import TarotSessions
from fortune_agent.fortune_store import FortuneStore
from fortune_agent.web import LocalApp
from fortune_agent.unified_agent import UnifiedAgent
from fortune_agent.conversation import ConversationStore
from test_unified_agent import FakeResponses,plan


class ChartTests(unittest.TestCase):
    def test_j2000_reference_positions_and_whole_sign_house_invariants(self):
        r=calculate_astrology('2000-01-01T12:00:00+00:00','Europe/London',51.4779,0)
        planets={p['id']:p for p in r['planets']}
        self.assertAlmostEqual(planets['Sun']['longitude'],280.3687,places=3)
        self.assertAlmostEqual(planets['Moon']['longitude'],223.3239,places=3)
        self.assertAlmostEqual(r['angles']['ascendant']['longitude'],24.2661,places=3)
        self.assertEqual(r['houses'][0]['sign'],'白羊')
        self.assertEqual(planets['Sun']['house'],10)
        self.assertEqual(len(r['houses']),12)
        self.assertTrue(all(1<=p['house']<=12 for p in r['planets']))
        self.assertTrue(all(a['orb']<=a['orb_limit'] for a in r['aspects']))
        self.assertEqual(len({(a['a'],a['b']) for a in r['aspects']}),len(r['aspects']))

    def test_equal_instants_in_different_civil_zones_keep_planets(self):
        a=calculate_astrology('2000-01-01T12:00:00+00:00','Europe/London',51.4779,0)
        b=calculate_astrology('2000-01-01T20:00:00+08:00','Asia/Shanghai',51.4779,0)
        self.assertEqual(a['planets'],b['planets'])
        self.assertEqual(a['angles'],b['angles'])

    def test_location_changes_angles_but_not_geocentric_planets(self):
        a=calculate_astrology('2000-01-01T12:00:00+00:00','UTC',0,0)
        b=calculate_astrology('2000-01-01T12:00:00+00:00','UTC',31.23,121.47)
        self.assertNotEqual(a['angles'],b['angles'])
        self.assertEqual([p['longitude'] for p in a['planets']],[p['longitude'] for p in b['planets']])

    def test_dst_requires_correct_explicit_offset(self):
        with self.assertRaises(ValueError):validate_birth('2000-07-01T12:00:00-05:00','America/New_York')
        validate_birth('2000-07-01T12:00:00-04:00','America/New_York')
        for lat,lon in [(True,0),(90,0),(0,181),(float('nan'),0),(None,None)]:
            with self.assertRaises(ValueError):coordinates(lat,lon)
        with self.assertRaises(ValueError):validate_birth('2000-01-01T12:00:00','Asia/Shanghai')

    def test_ziwei_snapshot_has_12_palaces_14_major_stars_and_four_mutagens(self):
        r=calculate_ziwei('2000-01-01T12:00:00+08:00','female')['chart']
        self.assertEqual(r['fiveElementsClass'],'土五局')
        self.assertEqual(r['earthlyBranchOfSoulPalace'],'午')
        stars=[s for p in r['palaces'] for s in p['majorStars']]
        self.assertEqual(len(stars),14)
        self.assertEqual(len({s['name'] for s in stars}),14)
        all_stars=[s for p in r['palaces'] for s in p['majorStars']+p['minorStars']]
        self.assertEqual({s['mutagen'] for s in all_stars if s.get('mutagen')},{'禄','权','科','忌'})
        self.assertEqual(sum(p['isBodyPalace'] for p in r['palaces']),1)

    def test_late_zi_day_rule_is_explicit_and_matches_next_early_zi_major_stars(self):
        late=calculate_ziwei('2000-01-01T23:30:00+08:00','female')
        early=calculate_ziwei('2000-01-02T00:30:00+08:00','female')
        positions=lambda c:[[(s['name'],s.get('mutagen','')) for s in p['majorStars']] for p in c['chart']['palaces']]
        self.assertEqual(positions(late),positions(early))
        self.assertTrue(any('23:00' in x for x in late['conventions']))
        with self.assertRaises(ValueError):calculate_ziwei('2000-01-01T12:00:00+00:00','female')
        with self.assertRaises(ValueError):calculate_ziwei('2000-01-01T12:00:00+08:00',None)


class TarotExperienceTests(unittest.TestCase):
    def test_all_spreads_have_correct_unique_cards(self):
        for name,positions in SPREADS.items():
            r=draw_reading('合成问题',name)
            self.assertEqual(len(r.cards),len(positions))
            self.assertEqual(len({c.card.id for c in r.cards}),len(positions))
    def test_server_shuffle_is_hidden_stable_and_cannot_change_picks_after_reveal(self):
        store=TarotSessions();session=store.create('学习','five')
        self.assertNotIn('deck',session)
        r=store.reveal(session['draw_id'],[1,2,3,4,78])
        self.assertEqual(r,store.reveal(session['draw_id'],[1,2,3,4,78]))
        self.assertEqual(r,store.reading(session['draw_id']))
        with self.assertRaises(ValueError):store.reveal(session['draw_id'],[1,2,3,4,77])
    def test_expiry_duplicate_and_boolean_positions_are_rejected(self):
        store=TarotSessions(ttl=0.01);session=store.create('学习','three')
        for picks in [[1,1,3],[True,2,3],[1,2,79]]:
            with self.assertRaises(ValueError):store.reveal(session['draw_id'],picks)
        with patch('fortune_agent.tarot_sessions.time.monotonic',return_value=10**12):
            with self.assertRaises(ValueError):store.reading(session['draw_id'])


class ProfileCompletionTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=FortuneStore(Path(self.temp.name)/'fortune.sqlite3')
    def tearDown(self):self.temp.cleanup()
    def test_advanced_profile_and_reading_export_restore(self):
        self.store.save_profile('one',chart_birth='2000-01-01T12:00:00+00:00',chart_timezone='Europe/London',latitude=51.4779,longitude=0,preferred_method='astrology',display_name='示例',style='direct')
        key=self.store.save_reading('one','astrology',{'mode':'astrology','synthetic':True})
        data=self.store.export('one');self.assertEqual(data['readings'][0]['key'],key)
        self.store.delete('one');self.store.import_archive(data)
        self.assertEqual(self.store.get_profile('one')['longitude'],0)
        self.assertEqual(len(self.store.readings('one')),1)
        with self.assertRaises(ValueError):self.store.import_archive(data)
    def test_import_cannot_overwrite_existing_id_by_whitespace(self):
        self.store.save_profile('one',display_name='原档案')
        with self.assertRaises(ValueError):self.store.import_archive({'profile':{'id':' one ','display_name':'覆盖'}})
        self.assertEqual(self.store.get_profile('one')['display_name'],'原档案')

    def test_minute_birth_input_is_canonical_and_invalid_text_is_rejected(self):
        p=self.store.save_profile('one',chart_birth='2000-01-01T12:00+00:00',chart_timezone='Europe/London')
        self.assertEqual(p['chart_birth'],'2000-01-01T12:00:00+00:00')
        with self.assertRaises(ValueError):self.store.save_profile('bad',birth=None)

    def test_import_database_failure_rolls_back_profile_and_all_history(self):
        from contextlib import closing
        import sqlite3
        archive={'profile':{'id':'rollback'},'readings':[
            {'key':'one','kind':'tarot','created':'2026-10-05T12:00:00+00:00','result':{}},
            {'key':'two','kind':'tarot','created':'2026-10-05T12:00:00+00:00','result':{}}]}
        with closing(self.store.connect()) as con,con:
            con.execute("CREATE TRIGGER reject_second BEFORE INSERT ON readings WHEN NEW.key='two' BEGIN SELECT RAISE(ABORT,'simulated storage error'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.store.import_archive(archive)
        with self.assertRaises(ValueError):self.store.get_profile('rollback')
        self.assertEqual(self.store.readings('rollback'),[])

    def test_duplicate_import_keys_are_rejected_instead_of_silent_record_loss(self):
        row={'key':'same','kind':'tarot','created':'2026-10-05T12:00:00+00:00','result':{}}
        with self.assertRaises(ValueError):self.store.import_archive({'profile':{'id':'duplicates'},'readings':[row,row]})
        with self.assertRaises(ValueError):self.store.get_profile('duplicates')

    def test_invalid_import_does_not_save_partial_profile(self):
        with self.assertRaises(ValueError):self.store.import_archive({'profile':{'id':'broken'},'history':[{'key':'bad'}]})
        with self.assertRaises(ValueError):self.store.get_profile('broken')
    def test_import_under_new_id_preserves_colliding_history_instead_of_dropping_it(self):
        from fortune_agent.fortune_daily import make_daily_report
        from datetime import date
        self.store.save_profile('one');r=make_daily_report(self.store,'one',date(2026,10,5))
        data=self.store.export('one');data['profile']['id']='two';self.store.import_archive(data)
        restored=self.store.history('two')[0]
        self.assertNotEqual(restored['key'],r['key'])
        self.assertEqual(restored['key'],restored['report']['key'])
        self.store.review('two',restored['key'],'恢复后可回顾')
    def test_web_profile_drives_star_chart_and_optional_history(self):
        app=LocalApp(Path(self.temp.name)/'daily.sqlite3')
        app.run({'mode':'profile-save','profile':'one','chart_birth':'2000-01-01T12:00:00+00:00','chart_timezone':'Europe/London','latitude':51.4779,'longitude':0})
        result=app.run({'mode':'astrology','profile':'one','use_profile':True,'save_history':True})
        self.assertEqual(result['chart_result']['longitude'],0)
        self.assertEqual(len(app.run({'mode':'reading-history','profile':'one'})['readings']),1)
        app.run({'mode':'profile-delete','profile':'one'})
        self.assertFalse(self.store.readings('one'))


class UnifiedChartTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.sessions=ConversationStore();self.session=self.sessions.get()
    def tearDown(self):self.temp.cleanup()
    def agent(self,plans):return UnifiedAgent(SimpleNamespace(responses=FakeResponses(plans)),'test',Path(self.temp.name)/'daily.sqlite3',Lock())
    def test_missing_location_clarifies_and_does_not_guess(self):
        agent=self.agent([plan(method='astrology',birth='2000-01-01T12:00:00+08:00',chart_timezone='Asia/Shanghai')])
        result=agent.turn(self.session,'占星，2000-01-01 12:00 +08:00 Asia/Shanghai出生')
        self.assertEqual(result['status'],'needs_input')
        self.assertIn('经纬度',result['reply'])
    def test_saved_astrology_profile_and_followup_keep_exact_chart(self):
        store=FortuneStore(Path(self.temp.name)/'fortune.sqlite3')
        store.save_profile('one',chart_birth='2000-01-01T12:00:00+00:00',chart_timezone='Europe/London',latitude=51.4779,longitude=0)
        agent=self.agent([plan(method='astrology',question='学习安排'),plan(action='followup',method='astrology',question='沟通建议')])
        first=agent.turn(self.session,'用占星梳理学习安排','one',use_saved_profile=True)
        second=agent.turn(self.session,'继续给沟通建议','one',use_saved_profile=True)
        self.assertEqual(first['result']['chart_result'],second['result']['chart_result'])
        self.assertTrue(second['trace'][-1]['reused'])
    def test_model_cannot_invent_gender_for_ziwei(self):
        agent=self.agent([plan(method='ziwei',birth='2000-01-01T12:00:00+08:00',gender='female')])
        result=agent.turn(self.session,'紫微，2000-01-01 12:00 +08:00出生')
        self.assertEqual(result['status'],'needs_input')
        self.assertIsNone(self.session.artifact)
