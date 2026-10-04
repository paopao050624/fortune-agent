import unittest

from fortune_agent.bazi import parse_bazi_pillars
from fortune_agent.bazi_structure import analyze_structure
from fortune_agent.bazi_sources import load_ziping_catalog


class ResearchSelectionTests(unittest.TestCase):
    def result(self, pillars):
        return analyze_structure(parse_bazi_pillars(pillars))

    def test_ten_lu_positions_and_only_five_yang_blades(self):
        expected = [('甲子','丙寅','jian_lu'),('乙丑','丁卯','jian_lu'),
                    ('丙子','己巳','jian_lu'),('丁丑','庚午','jian_lu'),
                    ('戊子','己巳','jian_lu'),('己丑','庚午','jian_lu'),
                    ('庚子','壬申','jian_lu'),('辛丑','癸酉','jian_lu'),
                    ('壬子','乙亥','jian_lu'),('癸丑','丙子','jian_lu'),
                    ('甲子','丁卯','yang_blade'),('丙子','庚午','yang_blade'),
                    ('戊子','庚午','yang_blade'),('庚子','癸酉','yang_blade'),
                    ('壬子','丙子','yang_blade')]
        for day, month, route in expected:
            with self.subTest(day=day, month=month):
                result=self.result(f'甲子 {month} {day} 丙寅')
                self.assertEqual(result['research_selection']['route'],route)
                self.assertEqual(result['pattern_conclusion'],'undetermined')

    def test_yin_month_jie_and_no_project_yin_blade_assignment(self):
        for day, month in [('乙丑','丙寅'),('丁丑','己巳'),('己丑','己巳'),
                           ('辛丑','壬申'),('癸丑','乙亥')]:
            selection=self.result(f'甲子 {month} {day} 丙寅')['research_selection']
            self.assertEqual(selection['route'],'month_jie')
        for day, month in [('乙丑','戊辰'),('丁丑','辛未'),('己丑','辛未'),
                           ('辛丑','甲戌'),('癸丑','丁丑')]:
            self.assertEqual(self.result(f'甲子 {month} {day} 丙寅')['research_selection']['route'],'mixed_qi')

    def test_containing_peer_in_storage_is_not_lu_or_month_jie(self):
        result=self.result('庚申 戊辰 甲子 乙丑')
        self.assertTrue(result['special_case_flags'])
        self.assertEqual(result['research_selection']['route'],'mixed_qi')

    def test_mixed_qi_tracks_transmission_and_complete_triad_separately(self):
        result=self.result('庚申 戊辰 甲子 乙丑')
        s=result['research_selection']
        items={i['candidate_id']:i for i in s['candidate_selection']}
        self.assertEqual(items['month-hidden-戊']['support'],['exact_transmission'])
        self.assertEqual(items['month-hidden-癸']['support'],['complete_three_branch_set'])
        self.assertEqual(s['month_combinations'][0]['transformation'],'unassessed')
        self.assertTrue(all(i['status']=='supported_for_review' for i in items.values()))
        self.assertEqual(result['useful_god_conclusion'],'undetermined')

    def test_duplicate_branches_do_not_complete_triad(self):
        s=self.result('庚申 壬辰 甲申 丙寅')['research_selection']
        self.assertEqual(s['month_combinations'],[])
        self.assertTrue(all(i['status']=='deferred_without_selection_evidence' for i in s['candidate_selection']))

    def test_triad_elsewhere_does_not_select_this_month_hidden_qi(self):
        s=self.result('庚申 丁未 甲子 戊辰')['research_selection']
        self.assertEqual(s['month_combinations'],[])
        supported={i['candidate_id'] for i in s['candidate_selection'] if i['status']=='supported_for_review'}
        self.assertEqual(supported,{'month-hidden-丁'})

    def test_special_route_keeps_other_visible_finance_official_food_as_observations(self):
        s=self.result('庚申 丙寅 甲子 戊辰')['research_selection']
        self.assertEqual(s['route'],'jian_lu')
        self.assertTrue(all(i['status']=='special_route_review' for i in s['candidate_selection']))
        self.assertEqual([i['ten_god'] for i in s['visible_coordination']],['七杀','食神','偏财'])

    def test_source_variant_and_all_selection_sources_resolve(self):
        entries={e['id']:e for e in load_ziping_catalog()['entries']}
        self.assertIn('惟六陽有之',entries['ziping-yang-blade']['source_text'])
        self.assertEqual(entries['ziping-yang-blade']['scan_pages'],[86])
        self.assertEqual(entries['ziping-lu-jie-method']['printed_pages'],[80])
        for pillars in ['甲子 丙寅 甲子 戊辰','甲子 丁卯 甲子 戊辰','庚申 戊辰 甲子 乙丑']:
            result=self.result(pillars)
            self.assertTrue(set(result['research_selection']['source_ids'])<=entries.keys())
            self.assertTrue(all(set(t['source_ids'])<=entries.keys() for t in result['trace']))


if __name__=='__main__': unittest.main()
