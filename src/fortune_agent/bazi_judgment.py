"""Versioned approximate judgments; engineering parameters are fully disclosed."""
from functools import lru_cache
from importlib.resources import files
import json
import math

from .bazi_facts import ELEMENTS,HIDDEN_STEMS,stem_facts,chart_facts
from .bazi_structure import analyze_structure


@lru_cache(maxsize=1)
def load_judgment_rules():
    rules=json.loads(files('fortune_agent').joinpath('data/bazi_judgment_rules.json').read_text(encoding='utf-8'))
    if set(rules['hidden_weights'])!=set(HIDDEN_STEMS):raise ValueError('藏干权重表不完整')
    for branch,weights in rules['hidden_weights'].items():
        if set(weights)!=set(HIDDEN_STEMS[branch]) or not math.isclose(sum(weights.values()),1.0):raise ValueError('藏干权重无效')
        if any(type(v) not in (int,float) or v<=0 for v in weights.values()):raise ValueError('藏干权重必须为正数')
    for weights in rules['season_multipliers'].values():
        if set(weights)!=set(ELEMENTS) or any(v<=0 for v in weights.values()):raise ValueError('季节倍率不完整')
    source=json.loads(files('fortune_agent').joinpath('data/ziping_sources.json').read_text(encoding='utf-8'))
    if not set(rules['source_ids'])<={e['id'] for e in source['entries']}:raise ValueError('判断规则来源不完整')
    if not 0<rules['thresholds']['weak']<rules['thresholds']['strong']<1:raise ValueError('旺衰阈值无效')
    return rules


def weighted_evidence(chart,structure,rules,month_weight=None,clash_retention=1.0):
    master=stem_facts(chart.day_master,chart.day_master)['element']
    support_elements={master,ELEMENTS[(ELEMENTS.index(master)-1)%5]}
    multipliers=rules['season_multipliers'][structure['season']['label']]
    clashed={p for e in structure['interactions']['observations'] if e['kind']=='六冲' for p in e['positions']}
    rows=[]
    for p in chart_facts(chart)['pillars']:
        if p['position']!='日柱':
            stem=p['heavenly_stem'];value=rules['stem_weight']*multipliers[stem['element']]
            rows.append({'position':p['position'],'location':'显干',**stem,'weight':value,'supports_master':stem['element'] in support_elements})
        pillar_weight=(month_weight or rules['month_weight']) if p['position']=='月柱' else rules['branch_weight']
        for stem in p['hidden_stems']:
            value=pillar_weight*rules['hidden_weights'][p['branch']][stem['stem']]*multipliers[stem['element']]
            if p['position'] in clashed:value*=clash_retention
            rows.append({'position':p['position'],'branch':p['branch'],'location':'藏干',**stem,'weight':value,
                         'supports_master':stem['element'] in support_elements})
    total=sum(row['weight'] for row in rows)
    support=sum(row['weight'] for row in rows if row['supports_master'])
    gods={god:sum(row['weight'] for row in rows if row['ten_god']==god)/total for god in {r['ten_god'] for r in rows}}
    elements={e:sum(row['weight'] for row in rows if row['element']==e)/total for e in ELEMENTS}
    return {'support_ratio':support/total,'support_weight':support,'other_weight':total-support,
            'ten_god_shares':gods,'element_shares':elements,'rows':rows}


def strength_estimate(chart,structure,rules):
    evidence=weighted_evidence(chart,structure,rules)
    def classify(ratio):
        if ratio<rules['thresholds']['weak']:return 'weak'
        if ratio>rules['thresholds']['strong']:return 'strong'
        return 'balanced'
    cases=[]
    for month in rules['sensitivity']['month_weights']:
        for retention in rules['sensitivity']['clashed_branch_retention']:
            ratio=weighted_evidence(chart,structure,rules,month,retention)['support_ratio']
            cases.append({'month_weight':month,'clashed_branch_retention':retention,'support_ratio':round(ratio,5),'classification':classify(ratio)})
    category=classify(evidence['support_ratio'])
    stable=len({case['classification'] for case in cases})==1
    labels={'strong':'偏强','weak':'偏弱','balanced':'相对均衡'}
    # Ratios below/above extremes are alerts, not automatic following/transforming charts.
    specials=[]
    ratio=evidence['support_ratio']
    if ratio<rules['thresholds']['extreme_weak']:
        specials.append({'type':'possible_following','label':'极低生助比例，须核查从弱类特殊格','status':'manual_review'})
    if ratio>rules['thresholds']['extreme_strong']:
        specials.append({'type':'possible_dominance','label':'极高生助比例，须核查专旺／从强类特殊格','status':'manual_review'})
    for event in structure['interactions']['observations']:
        if event['kind']=='天干五合' and '日柱' in event['positions']:
            specials.append({'type':'possible_transformation','label':'日干参与五合，须核查化气格条件','interaction_id':event['id'],'status':'manual_review'})
    special_conditions=[]
    if specials:
        no_roots=not structure['roots'][2]['locations']
        resource_share=sum(evidence['ten_god_shares'].get(g,0) for g in ('正印','偏印'))
        for item in specials:
            if item['type']=='possible_following':
                conditions=[('模型极低生助',ratio<rules['thresholds']['extreme_weak']),('四支未见日主同类根',no_roots),('模型无印生助',resource_share==0)]
            elif item['type']=='possible_dominance':
                conditions=[('模型极高生助',ratio>rules['thresholds']['extreme_strong']),('日主有同类根',not no_roots)]
            else:
                event=next(e for e in structure['interactions']['observations'] if e['id']==item['interaction_id'])
                key=next(pair for pair in rules['stem_transform_elements'] if set(pair)==set(event['characters']))
                target=rules['stem_transform_elements'][key]
                conditions=[('日干五合相邻',event['adjacent']),('四支未见日主同类根',no_roots),
                            ('模型化神占比达到约定阈值',evidence['element_shares'][target]>=rules['thresholds']['transform_dominance'])]
                item['target_element']=target
            special_conditions.append({**item,'conditions':[{'condition':name,'model_satisfied':value} for name,value in conditions],
                                       'screening':'candidate_conditions' if all(value for name,value in conditions) else 'conditions_not_met',
                                       'reason':'仅项目特殊格筛选代理；从格化格实际条件和司令效力未统一裁定，不自动按特殊格取用。'})
    return {'status':'estimated','classification':category,'label':labels[category]+'（项目模型估计）',
            'support_ratio':round(ratio,5),'evidence':evidence,'parameter_stability':'stable' if stable else 'sensitive',
            'sensitivity_cases':cases,'special_reviews':special_conditions,
            'limitations':'此数值是模型内部生助占比，不是好运评分或古籍旺衰标准。权重不是司令分日，冲的效力只作敏感性情景，不自动合化或删根。'}


def pattern_estimates(chart,structure,strength,rules):
    rows=strength['evidence']['rows']
    shares=strength['evidence']['ten_god_shares']
    visible={r['ten_god'] for r in rows if r['location']=='显干'}
    present={r['ten_god'] for r in rows}
    has=lambda gods:bool(present&set(gods))
    shows=lambda gods:bool(visible&set(gods))
    share=lambda gods:sum(shares.get(g,0) for g in gods)
    roots=lambda gods:any(r['ten_god'] in gods and r['location']=='藏干' for r in rows)
    finance=('正财','偏财'); resource=('正印','偏印'); peer=('比肩','劫财'); output=('食神','伤官')
    substantial=rules['thresholds']['star_substantial']
    strong=strength['classification']=='strong';weak=strength['classification']=='weak'
    season_events=[e for e in structure['interactions']['observations'] if '月柱' in e['positions'] and e['kind'] in ('六冲','六害','六破','相刑配对','自刑重复支')]
    def clause(label,source,conditions):
        return {'label':label,'source_id':source,'conditions':[{'condition':name,'model_satisfied':bool(value)} for name,value in conditions],
                'model_satisfied':all(value for name,value in conditions)}
    candidates=[]
    for c in structure['pattern_candidates']:
        god=c['ten_god'];paths=[];risks=[];rescues=[]
        if god=='正官':
            paths=[clause('财印配合且月支无刑冲害破观察','ziping-official-success', [('有财',has(finance)),('有印',has(resource)),('月支无所列关系',not season_events)])]
            risks=[clause('官遇伤官或月支刑冲观察','ziping-pattern-failure',[('见伤官或月支相关关系','伤官' in present or any(e['kind'] in ('六冲','相刑配对','自刑重复支') for e in season_events))])]
            rescues=[clause('伤官见官，印星透出解的研究条件','ziping-official-rescue',[('见伤官','伤官' in present),('印透',shows(resource))])]
        elif god in finance:
            paths=[clause('财旺生官','ziping-wealth-success-conditions',[('模型财占比不低于15%',share(finance)>=substantial),('见正官','正官' in present)]),
                   clause('食生财且身强带比','ziping-wealth-success-conditions',[('见食神','食神' in present),('模型偏强',strong),('比劫显干',shows(peer))]),
                   clause('财印双透，位置另审','ziping-wealth-success-conditions',[('财透',shows(finance)),('印透',shows(resource))])]
            risks=[clause('模型财轻比重或财透杀','ziping-pattern-failure',[('模型财占比低于15%且比劫大于财，或七杀透',(share(finance)<substantial and share(peer)>share(finance)) or '七杀' in visible)])]
        elif god in resource:
            paths=[clause('印轻逢杀','ziping-resource-success',[('模型印占比低于15%',share(resource)<substantial),('见七杀','七杀' in present)]),
                   clause('官印双全','ziping-resource-success',[('见正官','正官' in present),('见印',has(resource))]),
                   clause('身印旺而食伤泄','ziping-resource-success',[('模型偏强',strong),('模型印占比不低于15%',share(resource)>=substantial),('见食伤',has(output))])]
            risks=[clause('印轻遇财或身强印重透杀','ziping-pattern-failure',[('模型印轻见财或偏强印重杀透',(share(resource)<substantial and has(finance)) or (strong and share(resource)>=substantial and '七杀' in visible))])]
        elif god=='食神':
            paths=[clause('食神生财','ziping-food-success',[('见财',has(finance))]),clause('食神制杀而无财','ziping-food-success',[('见七杀','七杀' in present),('无财观察',not has(finance))])]
            risks=[clause('食遇偏印或财杀同见','ziping-pattern-failure',[('偏印存在或财杀同见','偏印' in present or (has(finance) and '七杀' in visible))])]
        elif god=='七杀':
            paths=[clause('身强七杀逢制','ziping-killing-success',[('模型偏强',strong),('见食伤制的观察',has(output))])]
            risks=[clause('杀见财而无食伤制观察','ziping-pattern-failure',[('见财',has(finance)),('无食伤观察',not has(output))])]
        elif god=='伤官':
            paths=[clause('伤官生财','ziping-hurting-success',[('见财',has(finance))]),
                   clause('伤官佩印','ziping-hurting-success',[('伤官模型占比不低于15%',shares.get('伤官',0)>=substantial),('印有藏根观察',roots(resource))]),
                   clause('身弱透杀印','ziping-hurting-success',[('模型偏弱',weak),('七杀透','七杀' in visible),('印透',shows(resource))]),
                   clause('伤官带杀无财','ziping-hurting-success',[('见七杀','七杀' in present),('无财观察',not has(finance))])]
            # This is an observation warning, not a source-backed universal failure claim.
            risks=[clause('伤官与正官配合需审','ziping-yongshen-pillar-coordination',[('见正官','正官' in present)])]
        if god in finance:
            rescues=[clause('财见比劫，食神或正官观察','ziping-rescue-other',[('见比劫',has(peer)),('食神或正官可见',shows(('食神','正官')))])]
        elif god in resource:
            rescues=[clause('财印相见，另见比劫代理','ziping-rescue-other',[('见财',has(finance)),('见比劫',has(peer))])]
        elif god=='食神':
            rescues=[clause('食遇偏印另见财护食代理','ziping-rescue-other',[('见偏印','偏印' in present),('见财',has(finance))])]
        elif god=='七杀':
            rescues=[clause('杀食印同现另见财代理','ziping-rescue-other',[('见食神','食神' in present),('见印',has(resource)),('见财',has(finance))])]
        supported=any(p['model_satisfied'] for p in paths)
        risk=any(p['model_satisfied'] for p in risks)
        rescued=any(p['model_satisfied'] for p in rescues)
        status='mixed_conditions' if supported and risk else 'supported_conditions' if supported else 'risk_conditions' if risk else 'conditions_not_met'
        weight=rules['hidden_weights'][chart.month[1]][c['stem']]
        candidates.append({**c,'month_qi_weight':weight,'paths':paths,'risks':risks,'rescues':rescues,
                           'rescued_condition_observed':rescued,'judgment_status':status,
                           'limitations':'满足的是项目条件代理，不等于经典最终成格；见星不证明生制有效。财印位置、合冲效力及候选取舍仍需复核。'})
    route=structure['research_selection']['route']
    special_paths=[]
    if route=='yang_blade':
        special_paths=[clause('阳刃透官杀，财印配合且无伤官','ziping-blade-success',
                      [('官杀透',shows(('正官','七杀'))),('财或印透',shows(finance+resource)),('无伤官观察','伤官' not in present)])]
    elif route in ('jian_lu','month_jie'):
        special_paths=[clause('禄劫透官逢财印','ziping-lu-success',[('正官透','正官' in visible),('见财与印',has(finance) and has(resource))]),
                       clause('禄劫透财逢食伤','ziping-lu-success',[('财透',shows(finance)),('见食伤',has(output))]),
                       clause('禄劫透杀遇制','ziping-lu-success',[('七杀透','七杀' in visible),('见食伤制代理',has(output))])]
    if route in ('jian_lu','month_jie','yang_blade'):
        main={'label':structure['research_selection']['label'],'status':'special_month_route',
              'source_ids':structure['research_selection']['source_ids'],'reason':'采用明确月支映射，另查财官杀食配合，不套普通八格取法。'}
    elif candidates:
        transmitted=[c for c in candidates if c['transmitted']]
        pool=transmitted or candidates
        top=max(pool,key=lambda c:c['month_qi_weight'])
        tied=len(pool)>1
        main={'label':top['label'],'candidate_id':top['id'],'status':'provisional_selection',
              'reason':'项目依次取月藏干同干透出、模型本气权重；多候选保留全部，不替代杂气会合取舍。',
              'multiple_candidates':tied,'source_ids':top['source_ids']}
    else:main={'label':'月令同类特殊条件复核','status':'manual_review','source_ids':[]}
    return {'main':main,'special_paths':special_paths,'candidates':candidates,'month_interactions':season_events,
            'attribution':'成敗原文已核对；15%旺轻条件、星的同现代理与藏干权重取舍是项目约定，均非原文数值。'}


def useful_god_estimates(chart,structure,strength,patterns,rules):
    master=stem_facts(chart.day_master,chart.day_master)['element'];i=ELEMENTS.index(master)
    def element_roles(elements):return [{'element':e,'share':round(strength['evidence']['element_shares'][e],5),
                                        'present':strength['evidence']['element_shares'][e]>0} for e in elements]
    if strength['special_reviews']:
        balance={'status':'manual_review','preferred':[],'avoid_increasing':[],'reason':'特殊从化方向待核实，暂停常规格扶抑取用。'}
    elif strength['classification']=='strong':
        balance={'status':'estimated','preferred':element_roles([ELEMENTS[(i+1)%5],ELEMENTS[(i+2)%5],ELEMENTS[(i+3)%5]]),
                 'avoid_increasing':element_roles([master,ELEMENTS[(i-1)%5]]),'reason':'模型偏强，列出泄、耗、制候选；需结合格局和调候择用，不把全部同时定喜。'}
    elif strength['classification']=='weak':
        balance={'status':'estimated','preferred':element_roles([ELEMENTS[(i-1)%5],master]),
                 'avoid_increasing':element_roles([ELEMENTS[(i+1)%5],ELEMENTS[(i+2)%5],ELEMENTS[(i+3)%5]]),'reason':'模型偏弱，列出生、扶候选；需核对财印、食印和特殊格条件。'}
    else:balance={'status':'balanced_review','preferred':[],'avoid_increasing':[],'reason':'模型相对均衡，不强行指定扶抑用神，优先复核格局和寒暖。'}
    climate=rules['climate_months'].get(chart.month[1])
    climate={'status':'estimated','preferred':element_roles([climate['need']]),'secondary':element_roles([climate['secondary']]),'reason':climate['reason']} if climate else {'status':'no_generic_priority','preferred':[],'secondary':[],'reason':'本项目无通用月支调候优先项，不强行指定。'}
    climate['attribution']=rules['climate_attribution']
    conflict=sorted({r['element'] for r in balance['avoid_increasing']} & {r['element'] for r in climate['preferred']})
    return {'balance':balance,'climate':climate,'pattern':{'status':'method_separate','main':patterns['main'],
            'reason':'格局用神为月令研究类别，扶抑用神为平衡候选，调候为寒暖方向；不可混称一种用神。'},
            'conflicts':conflict,'resolution':'有冲突时并列方法，不自动选择单一最终用神；不以缺五行补五行。'}


def judge_chart(chart):
    rules=load_judgment_rules();structure=analyze_structure(chart)
    strength=strength_estimate(chart,structure,rules)
    patterns=pattern_estimates(chart,structure,strength,rules)
    useful=useful_god_estimates(chart,structure,strength,patterns,rules)
    return {'method_version':rules['version'],'method_name':rules['method_name'],'attribution':rules['attribution'],
            'strength':strength,'patterns':patterns,'useful_gods':useful,'source_ids':rules['source_ids'],
            'parameters':{k:rules[k] for k in ('stem_weight','branch_weight','month_weight','hidden_weights','season_multipliers','thresholds','sensitivity')},
            'limitations':'支持所有十干十二月的模型估计与条件规则，缺资料、特殊从化及学派冲突保留复核；模型参数未校准，不宣称权威命理结论或预测效力。'}
