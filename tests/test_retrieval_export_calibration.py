from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

from fortune_agent.library import load_library,search_library,select_evidence
from fortune_agent.report_export import export_report,report_sections
from fortune_agent.bazi import parse_bazi_pillars,calculate_bazi
from fortune_agent.bazi_judgment import judge_chart,load_judgment_rules
from fortune_agent.bazi_agent import interpret_bazi
from fortune_agent.ziwei import calculate_ziwei
from fortune_agent.chart_agent import interpret_chart
from fortune_agent.web import LocalApp


class RetrievalTests(unittest.TestCase):
    def test_catalog_ids_are_unique_and_sources_remain_actual(self):
        entries=load_library();self.assertEqual(len(entries),665)
        self.assertEqual(len({e['id'] for e in entries}),len(entries))
        self.assertTrue(all(e['source_text'] and e['source_url'] for e in entries))
    def test_relevant_sources_and_single_character_hexagram(self):
        self.assertEqual(search_library('紫微统筹','ziwei',3)['entries'][0]['id'],'ziwei-star-紫微')
        self.assertTrue(search_library('正财格成格救应','bazi',4)['entries'][0]['id'].startswith('ziping-'))
        self.assertEqual(search_library('乾','iching',3)['entries'][0]['name'],'乾')
        self.assertEqual({e['card_name'] for e in search_library('正义','tarot',3)['entries']},{'正义'})
    def test_long_followup_context_remains_supported_in_internal_retrieval(self):
        entries=[e for e in load_library() if e['module']=='bazi']
        result=select_evidence(entries,'近期对话：'+('学习安排。'*600)+'当前追问：通根',['ziping-root-observation'],limit=3)
        self.assertIn('ziping-root-observation',{e['id'] for e in result['entries']})

    def test_missing_book_no_match_and_invalid_inputs_are_explicit(self):
        result=search_library('穷通宝鉴甲木调候','bazi');self.assertEqual(result['entries'],[]);self.assertIn('穷通宝鉴',result['missing_sources'])
        self.assertEqual(search_library('不存在的资料xyz789')['entries'],[])
        with self.assertRaises(ValueError):search_library('','all')
        with self.assertRaises(ValueError):search_library('紫微','wrong')
    def test_mandatory_anchors_never_pruned_even_when_query_does_not_match(self):
        entries=[e for e in load_library() if e['module']=='bazi']
        mandatory=['ziping-yongshen-month-origin','ziping-root-observation']
        result=select_evidence(entries,'学习安排',mandatory,limit=1)
        self.assertTrue(set(mandatory)<={e['id'] for e in result['entries']})
        self.assertTrue(all(e['retrieval']['reason'] for e in result['entries']))
        with self.assertRaises(ValueError):select_evidence(entries,'学习',['invented'])
    def test_bazi_input_retrieval_preserves_master_and_reduces_unrelated_context(self):
        calls=[]
        client=SimpleNamespace(responses=SimpleNamespace(create=lambda **kw:(calls.append(kw) or SimpleNamespace(output_text='学习建议'))))
        chart=parse_bazi_pillars('己卯 丙子 戊午 戊午');interpret_bazi(chart,'通根与旺衰',client,'test')
        payload=json.loads(calls[0]['input'][0]['content']);ids={e['id'] for e in payload['source_evidence']}
        self.assertIn('ditiansui-tiangan-戊',ids);self.assertIn('ziping-root-observation',ids)
        self.assertLessEqual(len(payload['source_evidence']),10)
        self.assertGreater(payload['source_retrieval']['candidate_count'],payload['source_retrieval']['selected_count'])


class ReportExportTests(unittest.TestCase):
    def sample(self):
        return {'mode':'bazi','chart':{'birth_time':'2000-01-01T12:00:00+08:00','year':'己卯','month':'丙子','day':'戊午','hour':'戊午'},'profile':'private-profile-id','interpretation':'## 结论\n**核对** 2000-01-01T12:00:00+08:00，纬度31.23 <script>alert(1)</script>','evidence':[{'heading':'固定资料','source_url':'https://example.com/source','locator':'章节'}]}
    def test_default_export_redacts_known_private_values_and_escapes_model_html(self):
        d=export_report(self.sample());self.assertNotIn('2000-01-01',d['content']);self.assertNotIn('private-profile-id',d['content']);self.assertNotIn('纬度31.23',d['content'])
        self.assertNotIn('<script>',d['content']);self.assertIn('&lt;script&gt;',d['content']);self.assertIn('己卯',d['content'])
    def test_private_optin_and_source_options_are_applied(self):
        d=export_report(self.sample(),include_private=True,include_sources=False)
        self.assertIn('2000-01-01',d['content']);self.assertNotIn('example.com/source',d['content'])
    def test_svg_is_valid_and_keeps_unicode_without_scripts(self):
        d=export_report(self.sample(),'svg');svg=ET.fromstring(d['content']);self.assertEqual(svg.tag,'{http://www.w3.org/2000/svg}svg');self.assertIn('八字报告',d['content']);self.assertNotIn('<script>',d['content'])
    def test_all_modes_can_export_and_unsupported_structures_are_rejected(self):
        for mode in ('tarot','daily','daily-report','bazi','ziwei','astrology','iching'):
            d=export_report({'mode':mode,'interpretation':'合成结果'});self.assertIn('合成结果',d['content'])
        with self.assertRaises(ValueError):export_report({'mode':'unknown'})
        with self.assertRaises(ValueError):export_report(self.sample(),include_private='false')
    def test_web_export_and_search_do_not_call_model(self):
        with tempfile.TemporaryDirectory() as temp:
            app=LocalApp(Path(temp)/'daily.sqlite3');app.model_client=lambda:(_ for _ in ()).throw(AssertionError('no API'))
            self.assertIn('content',app.run({'mode':'report-document','result':self.sample()}))
            self.assertTrue(app.run({'mode':'library-search','question':'紫微','module':'ziwei'})['entries'])


class CalibrationPolicyTests(unittest.TestCase):
    def test_parameter_conflict_no_longer_selects_balance_candidates(self):
        result=judge_chart(parse_bazi_pillars('己卯 丙子 戊午 戊午'))
        self.assertEqual(result['strength']['parameter_stability'],'sensitive')
        self.assertEqual(result['strength']['decision_status'],'abstain_final')
        self.assertEqual(result['useful_gods']['balance']['preferred'],[])
        self.assertFalse(load_judgment_rules()['calibration_policy']['expert_calibrated'])
    def test_clear_structural_anchors_remain_provisional_and_specials_guarded(self):
        strong=judge_chart(parse_bazi_pillars('甲寅 丙寅 甲寅 甲子'))
        weak=judge_chart(parse_bazi_pillars('庚申 辛酉 甲子 戊辰'))
        self.assertEqual(strong['strength']['classification'],'strong');self.assertEqual(weak['strength']['classification'],'weak')
        self.assertEqual(strong['strength']['decision_status'],'provisional')
        special=judge_chart(parse_bazi_pillars('辛酉 辛酉 甲申 辛酉'))
        self.assertEqual(special['strength']['decision_status'],'abstain_final')
    def test_audit_is_reproducible_and_does_not_claim_expert_ground_truth(self):
        path=Path(__file__).resolve().parents[1]/'evals/results/bazi-calibration-2026-10-06.json'
        report=json.loads(path.read_text());self.assertEqual(report['expert_label_count'],0)
        self.assertTrue(all(a['passed'] for a in report['policy_audits']))
        self.assertEqual(len(report['candidates']),4)


class FullPassageSchemaTests(unittest.TestCase):
    def test_iching_schema_and_instruction_cover_all_selected_passages(self):
        from fortune_agent.iching import build_cast
        from fortune_agent.iching_agent import interpret_cast
        calls=[]
        def create(**kwargs):
            calls.append(kwargs)
            content=json.loads(kwargs['input'][0]['content'])
            response={'summary':'概览','explanations':[{'passage_id':p['id'],'meaning':'语义','application':'应用'} for p in content['selection']['passages']],'advice':['核实信息'],'limitations':['非预测']}
            return SimpleNamespace(output_text=json.dumps(response,ensure_ascii=False))
        result=interpret_cast(build_cast([9]*6),'项目任务分工',SimpleNamespace(responses=SimpleNamespace(create=create)),'test',policy='all-moving-v1')
        length=len(result['selection']['passages'])
        schema=calls[0]['text']['format']['schema']['properties']['explanations']
        self.assertEqual(schema['minItems'],length);self.assertEqual(schema['maxItems'],length)
        self.assertIn('全部',calls[0]['instructions'])
