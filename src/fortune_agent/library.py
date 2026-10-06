"""Transparent lexical retrieval over supplied sources, with mandatory factual anchors."""
from functools import lru_cache
import hashlib
from importlib.resources import files
import json
import re

RETRIEVAL_VERSION='source-retrieval-v1'
ALIASES={
 'root':('通根','根气','根力','身强','身弱','旺衰'), 'season':('月令','季节','司令','旺衰'),
 'official':('正官','官格','事业','工作'), 'resource':('印格','正印','偏印'), 'food':('食神','食格'),
 'killing':('七杀','七煞','杀格'), 'hurting':('伤官','伤格'), 'wealth':('财格','财星','正财','偏财','财运'),
 'failure':('败格','破格','成败'), 'rescue':('救应','救格'), 'blade':('阳刃','羊刃'), 'lu':('建禄','月劫'),
 'mixed':('杂气','透干','会支')}
MISSING_BOOKS=('渊海子平','三命通会','穷通宝鉴','四书','Tetrabiblos')

def entry_terms(entry):
    terms=[]
    for k in ('star','topic','heading','chapter','name','card_name'):
        if entry.get(k):terms.append(entry[k])
    if entry.get('mutagen'):terms.append('化'+entry['mutagen'])
    identifier=entry.get('id','')
    for key,aliases in ALIASES.items():
        if key in identifier:terms.extend(aliases)
    return terms

def score_entry(entry,question):
    query=re.sub(r'\s+','',question).lower()
    terms=[term for term in entry_terms(entry) if term and term.lower() in query]
    text=' '.join(str(entry.get(k,'')) for k in ('source_text','heading','chapter','topic','star','card_name')).lower()
    tokens=set(re.findall(r'[a-z]{3,}',query))|{query[i:i+2] for i in range(len(query)-1) if re.fullmatch(r'[\u4e00-\u9fff]{2}',query[i:i+2])}
    overlaps=sorted(t for t in tokens if t in text)
    return len(terms)*5+min(len(overlaps),8),sorted(set(terms+overlaps))

def select_evidence(entries,question,mandatory_ids=(),limit=8,context=''):
    if not isinstance(question,str) or len(question)>12000:raise ValueError('内部检索上下文过长')
    if type(limit) is not int or not 1<=limit<=30:raise ValueError('检索数量须为1–30')
    lookup={e['id']:e for e in entries if e.get('id')}
    if not set(mandatory_ids)<=lookup.keys():raise ValueError('必需引用锚点未提供')
    selected=[];seen=set()
    for ident in mandatory_ids:
        e=lookup[ident];selected.append({**e,'retrieval':{'score':None,'reason':'程序事实/方法必需锚点','matched_terms':[]}});seen.add(ident)
    ranked=[]
    for entry in entries:
        if not entry.get('id') or entry['id'] in seen:continue
        score,terms=score_entry(entry,question+' '+context)
        if score>0:ranked.append((score,entry['id'],entry,terms))
    for score,ident,entry,terms in sorted(ranked,key=lambda r:(-r[0],r[1])):
        if len(selected)>=max(limit,len(mandatory_ids)):break
        selected.append({**entry,'retrieval':{'score':score,'reason':'问题/实际命盘关键词匹配','matched_terms':terms}})
    return {'method_version':RETRIEVAL_VERSION,'query':question,'context':context,'entries':selected,
            'candidate_count':len(entries),'selected_count':len(selected),'missing_sources':[b for b in MISSING_BOOKS if b.lower() in question.lower()],
            'limitations':'本地关键词检索，不是语义真值判断；只返回已接入原文。必需锚点不因排序删掉，未匹配或未接入资料明确说明。'}


@lru_cache(maxsize=1)
def load_library():
    root=files('fortune_agent');entries=[]
    for path,kind in [('bazi_sources.json','bazi'),('bazi_context_sources.json','bazi'),('ziping_sources.json','bazi'),('ziwei_sources.json','ziwei')]:
        catalog=json.loads(root.joinpath('data',path).read_text())
        for e in catalog['entries']:
            meta=catalog.get('source',{})
            entries.append({**e,'module':kind,'edition_note':e.get('edition_note') or meta.get('edition_note',''),'source_url':e.get('source_url') or meta.get('url')})
    from .meanings import load_catalog as tarot_catalog
    from .tarot import DECK
    cards={c.id:c.name for c in DECK};catalog=tarot_catalog()
    for ident,e in catalog['cards'].items():
        for orientation in ('upright','reversed'):
            if e.get(orientation):entries.append({'id':f'tarot-{ident}-{orientation}','module':'tarot','card_name':cards[ident],'heading':cards[ident]+' · '+('正位' if orientation=='upright' else '逆位'),'source_text':e[orientation],'source_url':e['source_url'],'locator':'Waite Part III · 扫描页'+str(e['source_page']),'notes':['经典历史牌义，不代表用户事实或事件预言。']})
    from .iching_reading import load_texts,passage
    for e in load_texts()['hexagrams']:
        entries.append({**passage(e['number'],'judgment'),'module':'iching','name':e['name']})
        for line in e['lines']:entries.append({**passage(e['number'],'line',line['position']),'module':'iching','name':e['name']})
        for label in e['special']:entries.append({**passage(e['number'],label),'module':'iching','name':e['name']})
    if len({e['id'] for e in entries})!=len(entries):raise ValueError('资料库ID重复')
    return entries


def search_library(question,module='all',limit=10):
    if not isinstance(question,str) or not question.strip():raise ValueError('请输入检索问题或关键词')
    if module not in ('all','bazi','ziwei','tarot','iching'):raise ValueError('未知资料类别')
    entries=[e for e in load_library() if module=='all' or e['module']==module]
    # A request for a missing book should not masquerade as retrieval from another work.
    missing=[b for b in MISSING_BOOKS if b.lower() in question.lower()]
    if missing and not any(e.get('work') and e['work'] in question for e in entries):
        return {'method_version':RETRIEVAL_VERSION,'query':question,'entries':[],'selected_count':0,'candidate_count':len(entries),'missing_sources':missing,'message':'所问典籍尚未接入原文，未返回其他书目冒充依据。','limitations':'只检索已接入固定资料。'}
    result=select_evidence(entries,question,limit=limit)
    if not result['entries']:result['message']='未找到已接入的匹配原文；不会补造依据。'
    return result
