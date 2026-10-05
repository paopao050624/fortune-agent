"""Position-preserving relationship observations; no effective-strength judgments."""
from functools import lru_cache
from importlib.resources import files
from itertools import combinations
import json

from .bazi_facts import STEMS, HIDDEN_STEMS


@lru_cache(maxsize=1)
def load_interaction_rules():
    rules = json.loads(files('fortune_agent').joinpath('data/bazi_interactions.json').read_text(encoding='utf-8'))
    if len(rules['stem_combinations']) != 5 or any(len(p) != 2 or any(c not in STEMS for c in p) for p in rules['stem_combinations']):
        raise ValueError('天干合表不完整')
    for pairs in rules['branch_pairs'].values():
        if len(pairs) != 6 or len({frozenset(p) for p in pairs}) != 6:
            raise ValueError('支关系配对表不完整或重复')
        if any(len(p) != 2 or any(c not in HIDDEN_STEMS for c in p) for p in pairs):
            raise ValueError('支关系配对含无效字')
    return rules


def analyze_interactions(facts, roots, candidates):
    rules = load_interaction_rules()
    pillars = facts['pillars']
    events = []

    def record(kind, indices, characters, scope):
        event = {
            'id': f'{scope}-{kind}-' + '-'.join(map(str, indices)), 'kind': kind, 'scope': scope,
            'positions': [pillars[i]['position'] for i in indices], 'characters': characters,
            'adjacent': len(indices) == 2 and abs(indices[0] - indices[1]) == 1,
            'status': 'observed_only', 'effect': 'unassessed',
        }
        events.append(event)

    for i, j in combinations(range(len(pillars)), 2):
        stem_pair = pillars[i]['heavenly_stem']['stem'] + pillars[j]['heavenly_stem']['stem']
        if any(set(stem_pair) == set(pair) for pair in rules['stem_combinations']):
            record('天干五合', [i, j], list(stem_pair), 'stem')
        branch_pair = pillars[i]['branch'] + pillars[j]['branch']
        for kind, pairs in rules['branch_pairs'].items():
            if any(set(branch_pair) == set(pair) for pair in pairs):
                record(kind, [i, j], list(branch_pair), 'branch')
        # Direction belongs to the traditional pair, not the chronological order of pillars.
        for pair in rules['punishment_pairs']:
            if set(branch_pair) == set(pair):
                ordered = [i, j] if branch_pair == pair else [j, i]
                record('相刑配对', ordered, list(pair), 'branch')
        if branch_pair[0] == branch_pair[1] and branch_pair[0] in rules['self_punishment']:
            record('自刑重复支', [i, j], list(branch_pair), 'branch')

    complete = []
    present = {p['branch'] for p in pillars}
    for group in rules['punishment_groups']:
        if set(group) <= present:
            complete.append({'branches': list(group), 'positions': [p['position'] for p in pillars if p['branch'] in group],
                             'status': 'branch_set_only', 'effect': 'unassessed'})

    root_reviews = []
    for root in roots:
        for location in root['locations']:
            related = [e['id'] for e in events if e['scope'] == 'branch' and location['position'] in e['positions']]
            if related:
                root_reviews.append({'stem_position': root['position'], 'stem': root['stem'],
                                     'root_location': location, 'interaction_ids': related,
                                     'root_effectiveness': 'unassessed'})
    candidate_reviews = []
    for candidate in candidates:
        related = [e['id'] for e in events if
                   (e['scope'] == 'branch' and '月柱' in e['positions']) or
                   (e['scope'] == 'stem' and any(p in candidate['visible_positions'] for p in e['positions']))]
        candidate_reviews.append({'candidate_id': candidate['id'], 'interaction_ids': related,
                                  'formation_effect': 'unassessed'})
    competition = []
    for pillar in pillars:
        hits = [e for e in events if pillar['position'] in e['positions']]
        for scope in ('stem', 'branch'):
            scoped = [e for e in hits if e['scope'] == scope]
            if len(scoped) > 1:
                competition.append({'position': pillar['position'], 'scope': scope,
                                    'interaction_ids': [e['id'] for e in scoped],
                                    'resolution': 'unassessed'})
    return {'method_version': rules['version'], 'attribution': rules['attribution'],
            'observations': events, 'complete_punishment_groups': complete,
            'root_reviews': root_reviews, 'candidate_reviews': candidate_reviews,
            'overlapping_relations': competition, 'punishment_note': rules['punishment_note'],
            'limitations': rules['limitations']}
