import json
from importlib.resources import files
import unittest
import xml.etree.ElementTree as ET

from fortune_agent.ziwei import calculate_ziwei
from fortune_agent.ziwei_sources import load_catalog,evidence_for,catalog_sha256
from fortune_agent.chart_agent import render_ziwei_analysis,interpret_chart,offline_chart_reading
from fortune_agent.tarot import DECK
from types import SimpleNamespace


class ZiweiEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result=calculate_ziwei('2000-01-01T12:00:00+08:00','female')
    def test_actual_stars_and_four_mutagens_resolve_to_fixed_revision_sources(self):
        c=load_catalog();self.assertEqual(len(c['entries']),27)
        self.assertEqual(c['source']['revision_id'],7913704)
        for entry in c['entries']:
            self.assertIn('oldid=7913704',entry['source_url'])
            self.assertTrue(entry['source_text']);self.assertTrue(entry['notes'])
        chart=self.result['chart'];lookup={p['name']:p for p in chart['palaces']}
        for e in self.result['evidence']:
            for m in e.get('matched_positions',[]):
                stars=lookup[m['palace']]['majorStars']+lookup[m['palace']]['minorStars']
                self.assertTrue(any(s['name']==m['star'] and (not e['mutagen'] or s.get('mutagen')==e['mutagen']) for s in stars))
        self.assertEqual(self.result['source_catalog_sha256'],catalog_sha256())
    def test_absent_supported_stars_are_not_retrieved_and_principles_are_always_present(self):
        chart={'palaces':[{'name':'命宫','earthlyBranch':'子','isBodyPalace':True,'majorStars':[{'name':'紫微','brightness':'庙','mutagen':'科'}],'minorStars':[]}]}
        entries=evidence_for(chart);ids={e['id'] for e in entries}
        self.assertIn('ziwei-star-紫微',ids);self.assertNotIn('ziwei-star-天机',ids)
        self.assertIn('ziwei-mutagen-科',ids);self.assertNotIn('ziwei-mutagen-忌',ids)
        self.assertIn('ziwei-principle-not-absolute',ids)
    def test_context_contains_real_soul_body_and_four_palaces(self):
        context=self.result['explanation_context'];self.assertEqual(len(context['related_palaces']),4)
        self.assertTrue(context['soul_palace'].startswith('命宫'))
        ids={e['id'] for e in self.result['evidence'] if e.get('id')}
        self.assertTrue(set(context['source_ids'])<=ids)
    def test_program_renders_exact_quote_and_rejects_model_invented_reference(self):
        e=next(e for e in self.result['evidence'] if e.get('star')=='紫微')
        a={'summary':'概览','explanations':[{'source_id':e['id'],'meaning':'传统主题','application':'现代行动'}],'advice':['做一件小事'],'limitations':['并非预测']}
        text=render_ziwei_analysis(a,self.result)
        self.assertIn(e['source_text'],text);self.assertIn(e['source_url'],text)
        a['explanations'][0]['source_id']='invented-classic-passage'
        with self.assertRaises(RuntimeError):render_ziwei_analysis(a,self.result)
    def test_model_input_includes_sources_and_requests_validated_structure(self):
        e=next(e for e in self.result['evidence'] if e.get('id'))
        a={'summary':'概览','explanations':[{'source_id':e['id'],'meaning':'概念','application':'行动'}],'advice':['核对资料'],'limitations':['版本限制']}
        calls=[]
        def create(**kwargs):calls.append(kwargs);return SimpleNamespace(output_text=json.dumps(a,ensure_ascii=False))
        answer=interpret_chart('ziwei',self.result,'学习安排',SimpleNamespace(responses=SimpleNamespace(create=create)),'test')
        self.assertIn(e['source_text'],answer)
        self.assertEqual(calls[0]['text']['format']['name'],'ziwei_interpretation')
        self.assertFalse(calls[0]['store'])
        self.assertTrue(json.loads(calls[0]['input'][0]['content'])['result']['evidence'])
    def test_offline_reading_is_grounded_and_discloses_source_limits(self):
        text=offline_chart_reading('ziwei',self.result)
        self.assertIn('oldid=7913704',text);self.assertIn('现代反思',text);self.assertIn('尚未与纸本',text)


class SymbolicArtTests(unittest.TestCase):
    def test_all_78_cards_have_distinct_safe_packaged_svg_and_explicit_attribution(self):
        root=files('fortune_agent');manifest=json.loads(root.joinpath('data/tarot_art.json').read_text())
        self.assertEqual(set(manifest['cards']),{c.id for c in DECK})
        assets=[]
        for card in DECK:
            raw=root.joinpath('static',manifest['cards'][card.id]['path']).read_text()
            svg=ET.fromstring(raw);self.assertEqual(svg.tag,'{http://www.w3.org/2000/svg}svg')
            self.assertIn(card.name,raw);self.assertNotIn('<script',raw);self.assertNotIn('http://',raw.replace('http://www.w3.org/2000/svg',''))
            assets.append(raw)
        self.assertEqual(len(set(assets)),78)
        self.assertIn('不是Waite',manifest['description'])
