from copy import deepcopy
import math
import unittest

from fortune_agent.bazi import parse_bazi_pillars
from fortune_agent.bazi_structure import analyze_structure
from fortune_agent.bazi_judgment import judge_chart,load_judgment_rules,weighted_evidence,strength_estimate
from fortune_agent.bazi_facts import STEMS,HIDDEN_STEMS
from fortune_agent.bazi_sources import load_ziping_catalog


class JudgmentTests(unittest.TestCase):
    def chart(self,value):return parse_bazi_pillars(value)

    def test_contrasting_structural_cases_produce_distinct_model_estimates(self):
        cases={'甲寅 丙寅 甲寅 甲子':'strong','庚申 辛酉 甲子 戊辰':'weak','己卯 丙子 戊午 戊午':'balanced'}
        for value,expected in cases.items():
            result=judge_chart(self.chart(value))
            self.assertEqual(result['strength']['classification'],expected)
            self.assertIn('模型',result['strength']['label'])
            self.assertEqual(result['strength']['status'],'estimated')

    def test_mass_conservation_and_no_day_stem_double_count(self):
        chart=self.chart('己卯 丙子 戊午 戊午');rules=load_judgment_rules()
        evidence=weighted_evidence(chart,analyze_structure(chart),rules)
        self.assertAlmostEqual(sum(evidence['element_shares'].values()),1)
        self.assertAlmostEqual(sum(evidence['ten_god_shares'].values()),1)
        self.assertFalse(any(row['position']=='日柱' and row['location']=='显干' for row in evidence['rows']))
        self.assertTrue(all(row['weight']>0 for row in evidence['rows']))
        # Explicitly defined stem keyed weights do not change when fact-table order changes.
        self.assertEqual(rules['hidden_weights']['巳']['戊'],0.3)
        self.assertEqual(rules['hidden_weights']['巳']['庚'],0.1)

    def test_sensitivity_reports_changes_without_deleting_clashed_roots(self):
        result=judge_chart(self.chart('己卯 丙子 戊午 戊午'))
        strength=result['strength']
        self.assertEqual(len(strength['sensitivity_cases']),6)
        ratios={c['support_ratio'] for c in strength['sensitivity_cases']}
        self.assertGreater(len(ratios),1)
        self.assertEqual(strength['parameter_stability'],'sensitive' if len({c['classification'] for c in strength['sensitivity_cases']})>1 else 'stable')
        facts=analyze_structure(self.chart('己卯 丙子 戊午 戊午'))
        self.assertEqual(len(facts['roots'][2]['locations']),2)

    def test_month_weight_can_be_changed_and_explained(self):
        chart=self.chart('己卯 丙子 戊午 戊午');structure=analyze_structure(chart);rules=load_judgment_rules()
        low=weighted_evidence(chart,structure,rules,1.3)
        high=weighted_evidence(chart,structure,rules,2.3)
        self.assertGreater(low['support_ratio'],high['support_ratio'])

    def test_special_following_and_transformation_do_not_force_ordinary_useful_god(self):
        chart=self.chart('辛酉 辛酉 甲申 辛酉')
        result=judge_chart(chart)
        self.assertTrue(result['strength']['special_reviews'])
        self.assertEqual(result['useful_gods']['balance']['status'],'manual_review')
        self.assertEqual(result['useful_gods']['balance']['preferred'],[])
        transformed=judge_chart(self.chart('己丑 戊辰 甲戌 戊辰'))
        reviews=[r for r in transformed['strength']['special_reviews'] if r['type']=='possible_transformation']
        self.assertTrue(reviews)
        self.assertTrue(all(r['status']=='manual_review' for r in reviews))
        self.assertTrue(all('screening' in r for r in reviews))

    def test_all_ten_masters_and_sixty_months_have_valid_traceable_outputs(self):
        branches='子丑寅卯辰巳午未申酉戌亥'
        sources={e['id'] for e in load_ziping_catalog()['entries']}
        for n,master in enumerate(STEMS):
            day=master+branches[n]
            for i in range(60):
                month=STEMS[i%10]+branches[i%12]
                result=judge_chart(self.chart(f'甲子 {month} {day} 丙寅'))
                with self.subTest(day=day,month=month):
                    self.assertTrue(math.isfinite(result['strength']['support_ratio']))
                    self.assertTrue(0<=result['strength']['support_ratio']<=1)
                    self.assertTrue(set(result['source_ids'])<=sources)
                    self.assertTrue(all(c['stem'] in HIDDEN_STEMS[month[1]] for c in result['patterns']['candidates']))
                    for c in result['patterns']['candidates']:
                        for path in c['paths']+c['risks']+c['rescues']:
                            self.assertIn(path['source_id'],sources)
                            self.assertEqual(path['model_satisfied'],all(x['model_satisfied'] for x in path['conditions']))

    def test_pattern_conditions_keep_supported_risk_and_rescue_separate(self):
        chart=self.chart('戊辰 己酉 甲午 丁卯')
        result=judge_chart(chart)
        official=next(c for c in result['patterns']['candidates'] if c['ten_god']=='正官')
        self.assertTrue(any(p['model_satisfied'] for p in official['risks']))
        self.assertEqual(official['judgment_status'],'risk_conditions')
        self.assertFalse(official['rescued_condition_observed'])

    def test_balance_and_climate_disagreement_is_exposed(self):
        result=judge_chart(self.chart('丙午 丙午 丙午 甲午'))
        balance=result['useful_gods']['balance']
        climate=result['useful_gods']['climate']
        self.assertEqual(climate['preferred'][0]['element'],'水')
        self.assertIn('工程',climate['attribution'])
        self.assertNotIn('final',result['useful_gods'])

    def test_scanned_pattern_sources_preserve_locations_and_quotes(self):
        catalog={e['id']:e for e in load_ziping_catalog()['entries']}
        self.assertEqual(catalog['ziping-official-success']['printed_pages'],[19])
        self.assertEqual(catalog['ziping-pattern-failure']['scan_pages'],[29])
        self.assertIn('官逢傷',catalog['ziping-official-rescue']['source_text'])

    def test_lu_and_blade_paths_have_scanned_sources_and_execute_conditions(self):
        lu=judge_chart(self.chart('庚申 丙寅 甲子 戊辰'))['patterns']
        self.assertEqual(lu['main']['status'],'special_month_route')
        killing=next(p for p in lu['special_paths'] if p['label']=='禄劫透杀遇制')
        self.assertTrue(killing['model_satisfied'])
        self.assertEqual(killing['source_id'],'ziping-lu-success')
        blade=judge_chart(self.chart('庚申 癸卯 甲子 戊辰'))['patterns']
        self.assertTrue(blade['special_paths'][0]['model_satisfied'])
        self.assertEqual(blade['special_paths'][0]['source_id'],'ziping-blade-success')
        blocked=judge_chart(self.chart('庚申 丁卯 甲子 戊辰'))['patterns']
        self.assertFalse(blocked['special_paths'][0]['model_satisfied'])

    def test_finance_risk_does_not_call_substantial_finance_light_only_because_peer_is_larger(self):
        result=judge_chart(self.chart('戊辰 丙子 戊午 戊午'))
        shares=result['strength']['evidence']['ten_god_shares']
        finance=shares.get('正财',0)+shares.get('偏财',0)
        self.assertGreaterEqual(finance,load_judgment_rules()['thresholds']['star_substantial'])
        candidate=next(c for c in result['patterns']['candidates'] if c['ten_god']=='正财')
        self.assertFalse(candidate['risks'][0]['model_satisfied'])
