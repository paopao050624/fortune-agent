"""Retrieve fixed-revision historical excerpts against actual chart stars and positions."""
from functools import lru_cache
from importlib.resources import files
import hashlib
import json

MAJOR_STARS={'紫微','天机','太阳','武曲','天同','廉贞','天府','太阴','贪狼','巨门','天相','天梁','七杀','破军'}


@lru_cache(maxsize=1)
def load_catalog():
    catalog=json.loads(files('fortune_agent').joinpath('data/ziwei_sources.json').read_text(encoding='utf-8'))
    entries=catalog['entries']
    if len({e['id'] for e in entries})!=len(entries):raise ValueError('紫微资料ID重复')
    if not MAJOR_STARS<={e['star'] for e in entries if e['star']}:raise ValueError('紫微十四主星资料不完整')
    if {e['mutagen'] for e in entries if e['mutagen']}!={'禄','权','科','忌'}:raise ValueError('紫微四化资料不完整')
    if any(not e['source_text'] or e['revision_id']!=catalog['source']['revision_id'] or f"oldid={e['revision_id']}" not in e['source_url'] for e in entries):raise ValueError('紫微引用缺少固定版本')
    return catalog


def catalog_sha256():
    return hashlib.sha256(json.dumps(load_catalog(),ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def evidence_for(chart):
    matched=[]
    for entry in load_catalog()['entries']:
        positions=[]
        for palace in chart['palaces']:
            for star in palace['majorStars']+palace['minorStars']:
                if (entry['star'] and entry['star']==star['name']) or (entry['mutagen'] and entry['mutagen']==star.get('mutagen')):
                    positions.append({'palace':palace['name'],'branch':palace['earthlyBranch'],'star':star['name'],
                                      'brightness':star.get('brightness',''),'mutagen':star.get('mutagen',''),'is_body_palace':palace['isBodyPalace']})
        if positions or (not entry['star'] and not entry['mutagen']):
            matched.append({**entry,'matched_positions':positions,'retrieval_basis':'按实际本命星曜/四化匹配；综合方法段共用。不据单颗星直接判断人物或事件。'})
    return matched


def explanation_context(chart,evidence):
    soul=next(p for p in chart['palaces'] if p['name']=='命宫')
    body=next(p for p in chart['palaces'] if p['isBodyPalace'])
    # Palace-array indexing comes from iztro; define triad/opposition explicitly.
    indices={(soul['index']+offset)%12 for offset in (0,4,6,8)}
    relevant=[p for p in chart['palaces'] if p['index'] in indices]
    references=[]
    for entry in evidence:
        if entry.get('id') and (not entry['matched_positions'] or any(m['palace'] in {p['name'] for p in relevant} or m['palace']==body['name'] for m in entry['matched_positions'])):
            references.append(entry['id'])
    return {'soul_palace':soul['name']+' '+soul['earthlyBranch'],'body_palace':body['name']+' '+body['earthlyBranch'],
            'related_palaces':[{'name':p['name'],'branch':p['earthlyBranch'],'major_stars':[s['name'] for s in p['majorStars']]} for p in relevant],
            'source_ids':references,'method':'命宫、对宫与三方按库宫位索引偏移0/4/6/8定位；属于程序组织依据，非全书自动格局判定。',
            'limitations':'亮度及四化采用iztro版本；电子书字词或传统分类有异文时不静默重写，不把现代反思冒充原文结论。'}
