import unittest

from fortune_agent.bazi import parse_bazi_pillars
from fortune_agent.bazi_structure import analyze_structure


class InteractionTests(unittest.TestCase):
    def analyze(self, pillars):
        return analyze_structure(parse_bazi_pillars(pillars))

    def test_all_branch_pairings_against_independent_expected_sets(self):
        expected = {'六合': {'子丑','寅亥','卯戌','辰酉','巳申','午未'},
                    '六冲': {'子午','丑未','寅申','卯酉','辰戌','巳亥'},
                    '六害': {'子未','丑午','寅巳','卯辰','申亥','酉戌'},
                    '六破': {'子酉','丑辰','寅亥','卯午','巳申','未戌'}}
        branches='子丑寅卯辰巳午未申酉戌亥'
        for a in branches:
            for b in branches:
                first=('甲' if branches.index(a)%2==0 else '乙')+a
                second=('丙' if branches.index(b)%2==0 else '丁')+b
                result=self.analyze(f'{first} {second} 戊辰 己丑')['interactions']
                for kind, pairs in expected.items():
                    found=any(e['kind']==kind and e['positions']==['年柱','月柱'] for e in result['observations'])
                    self.assertEqual(found,any(set(a+b)==set(p) for p in pairs),(a,b,kind))

    def test_direction_of_punishment_is_independent_of_pillar_order(self):
        events=self.analyze('庚申 丁巳 甲寅 戊辰')['interactions']['observations']
        event=next(e for e in events if e['kind']=='相刑配对' and e['characters']==['寅','巳'])
        self.assertEqual(event['positions'],['日柱','月柱'])
        self.assertTrue(event['adjacent'])
        groups=self.analyze('庚申 丁巳 甲寅 戊辰')['interactions']['complete_punishment_groups']
        self.assertEqual(groups[0]['branches'],list('寅巳申'))

    def test_two_punishment_characters_are_not_complete_three_group(self):
        data=self.analyze('甲寅 丁巳 戊辰 己丑')['interactions']
        self.assertTrue(any(e['kind']=='相刑配对' for e in data['observations']))
        self.assertFalse(data['complete_punishment_groups'])

    def test_repeated_self_punishment_needs_two_different_positions(self):
        single=self.analyze('甲辰 丁卯 戊子 己丑')['interactions']
        self.assertFalse(any(e['kind']=='自刑重复支' for e in single['observations']))
        double=self.analyze('甲辰 丙辰 戊子 己丑')['interactions']
        events=[e for e in double['observations'] if e['kind']=='自刑重复支']
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['positions'],['年柱','月柱'])

    def test_competing_combinations_keep_each_partner_and_do_not_transform(self):
        result=self.analyze('甲子 己丑 甲午 己未')
        data=result['interactions']
        combos=[e for e in data['observations'] if e['kind']=='天干五合']
        self.assertEqual(len(combos),4)
        self.assertTrue(data['overlapping_relations'])
        self.assertTrue(all(e['effect']=='unassessed' for e in data['observations']))
        self.assertEqual(len({e['id'] for e in data['observations']}),len(data['observations']))
        self.assertEqual(result['useful_god_conclusion'],'undetermined')

    def test_root_reviews_do_not_remove_clashed_root(self):
        result=self.analyze('庚申 丙寅 甲子 戊辰')
        root=result['roots'][2]
        self.assertIn('寅',[p['branch'] for p in root['locations']])
        reviews=[r for r in result['interactions']['root_reviews'] if r['stem_position']=='日柱']
        self.assertTrue(reviews)
        lookup={e['id']:e for e in result['interactions']['observations']}
        self.assertTrue(any(lookup[i]['kind']=='六冲' for r in reviews for i in r['interaction_ids']))
        self.assertTrue(all(r['root_effectiveness']=='unassessed' for r in reviews))
        self.assertEqual(root['root_strength'],'unassessed')

    def test_candidate_reviews_link_month_and_transmitted_stem_without_declaring_failure(self):
        result=self.analyze('甲子 己丑 丙午 乙未')
        lookup={e['id'] for e in result['interactions']['observations']}
        reviews=result['interactions']['candidate_reviews']
        self.assertEqual({r['candidate_id'] for r in reviews},{c['id'] for c in result['pattern_candidates']})
        self.assertTrue(all(set(r['interaction_ids'])<=lookup for r in reviews))
        self.assertTrue(all(r['formation_effect']=='unassessed' for r in reviews))
        self.assertEqual(result['pattern_conclusion'],'undetermined')
