"""Complete report orchestration with explicit evidence and unresolved judgments."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from functools import lru_cache
from importlib.resources import files
import json

from .bazi import calculate_bazi
from .bazi_facts import ELEMENTS, chart_facts, stem_facts
from .bazi_structure import analyze_structure
from .bazi_rules import wealth_checklist

VERSION = 'bazi-report-v2'


@lru_cache(maxsize=1)
def load_analysis_methods():
    methods=json.loads(files('fortune_agent').joinpath('data/bazi_analysis_methods.json').read_text(encoding='utf-8'))
    if set(methods['pattern_questions'])!={'正官','七杀','正财','偏财','正印','偏印','食神','伤官'}:
        raise ValueError('格局研究清单不完整')
    return methods


def luck_cycles(chart, gender=None, reference_date=None):
    """Library convention: year polarity + supplied sex parameter, minute-based start."""
    if gender not in (None, 'male', 'female'):
        raise ValueError('起运参数须为 male 或 female；不提供时不计算大运')
    if not chart.birth_time or gender is None:
        return {'status': 'needs_input', 'missing': [name for name, absent in
                [('准确出生时间', not chart.birth_time), ('传统顺逆运性别参数', gender is None)] if absent],
                'cycles': [], 'limitations': '四柱不能反推出唯一出生时间；不根据姓名或措辞猜测顺逆运参数。'}
    verified = calculate_bazi(chart.birth_time)
    if any(getattr(verified, key) != getattr(chart, key) for key in ('year','month','day','hour')):
        raise ValueError('出生时间与四柱不一致，不能计算大运')
    from lunar_python import Solar
    birth=datetime.fromisoformat(chart.birth_time)
    eight=Solar.fromYmdHms(birth.year,birth.month,birth.day,birth.hour,birth.minute,birth.second).getLunar().getEightChar()
    eight.setSect(2)
    yun=eight.getYun(1 if gender=='male' else 0,2)
    start=yun.getStartSolar()
    onset=datetime.fromisoformat(start.toYmdHms()).replace(tzinfo=ZoneInfo('Asia/Shanghai'))
    cycles=[]
    for cycle in yun.getDaYun(11)[1:]:
        # Use exact onset anniversaries, not library year buckets, for current-cycle selection.
        a=start.nextYear((cycle.getIndex()-1)*10)
        b=start.nextYear(cycle.getIndex()*10)
        ganzhi=cycle.getGanZhi()
        cycles.append({'index':cycle.getIndex(),'ganzhi':ganzhi,
                       'starts_at':a.toYmdHms()+'+08:00','ends_before':b.toYmdHms()+'+08:00',
                       'library_start_age':cycle.getStartAge(),'library_end_age':cycle.getEndAge(),
                       'heavenly_stem':stem_facts(ganzhi[0],chart.day_master)})
    selected=reference_date or datetime.now(ZoneInfo('Asia/Shanghai')).date()
    if type(selected) is not date or not 1900<=selected.year<=2100:
        raise ValueError('参考日期须为1900–2100年的公历日期')
    moment=datetime.combine(selected,datetime.min.time(),ZoneInfo('Asia/Shanghai')).replace(hour=12)
    active=next((c for c in cycles if datetime.fromisoformat(c['starts_at'])<=moment<datetime.fromisoformat(c['ends_before'])),None)
    year=calculate_bazi(selected.isoformat()+'T12:00:00+08:00').year
    return {'status':'calculated','gender_parameter':gender,'forward':yun.isForward(),
            'start_offset':{'years':yun.getStartYear(),'months':yun.getStartMonth(),'days':yun.getStartDay(),'hours':yun.getStartHour()},
            'starts_at':onset.isoformat(),'cycles':cycles,'reference_date':selected.isoformat(),
            'current_cycle':active,'current_state':'cycle' if active else ('before_start' if moment<onset else 'outside_range'),
            'annual_reference':{'ganzhi':year,'heavenly_stem':stem_facts(year[0],chart.day_master)},
            'method':'lunar-python 1.4.8 getYun(..., sect=2)：年干阴阳与用户提供的传统性别参数决定顺逆，按出生到前/后节的分钟差折算起运。',
            'limitations':'仅此顺逆起运体系，未校正真太阳时；显示年龄为库的年段标签，不是精确周岁。当前运按起运时刻十年周年区间判断，年柱按参考日12:00节气年计算。大运干支不直接等于吉凶。'}


def comprehensive_analysis(chart, gender=None, reference_date=None):
    facts=chart_facts(chart)
    structure=analyze_structure(chart)
    master=stem_facts(chart.day_master,chart.day_master)['element']
    supporting={master,ELEMENTS[(ELEMENTS.index(master)-1)%5]}
    # Evidence is listed, never summed into a fabricated classical strength score.
    support=[]; drain=[]
    for pillar in facts['pillars']:
        observations=([pillar['heavenly_stem']] if pillar['position']!='日柱' else [])+pillar['hidden_stems']
        for item in observations:
            (support if item['element'] in supporting else drain).append({'position':pillar['position'],**item})
    day_roots=structure['roots'][2]['locations']
    relation=structure['season']['relation_to_day_master']
    signals=[]
    if relation in ('同类','季节五行生日主'): signals.append('季节标签与日主同类或生助')
    elif relation: signals.append('季节标签与日主为生泄、克耗或受制关系')
    if day_roots: signals.append('四支有同干或同五行藏根观察')
    if support: signals.append('四柱可见同类或印星生助证据')
    if drain: signals.append('四柱可见食伤、财或官杀关系')
    selection=structure['research_selection']
    methods_catalog=load_analysis_methods()
    all_stars=[]
    for p in facts['pillars']:
        if p['position']!='日柱':all_stars.append({'position':p['position'],'location':'显干',**p['heavenly_stem']})
        all_stars.extend({'position':p['position'],'location':'藏干',**h} for h in p['hidden_stems'])
    patterns=[]
    for candidate in structure['pattern_candidates']:
        screening=next(i for i in selection['candidate_selection'] if i['candidate_id']==candidate['id'])
        review=next(i for i in structure['interactions']['candidate_reviews'] if i['candidate_id']==candidate['id'])
        questions=methods_catalog['pattern_questions'][candidate['ten_god']]
        observations={kind:[star for star in all_stars if star['ten_god'] in questions[kind]] for kind in ('cooperation','review')}
        patterns.append({**candidate,'screening':screening,'interaction_review':review,
                         'research_question':questions['question'],'cooperation_observations':observations['cooperation'],
                         'review_observations':observations['review'],'question_attribution':methods_catalog['attribution'],
                         'formation_status':'unresolved','failure_status':'unresolved'})
    season=structure['season']['label']
    climate={'冬':'寒暖核查：检查寒湿与温暖条件，不能仅见冬月便指定丙丁为用神。',
             '夏':'寒暖核查：检查炎燥与润泽条件，不能仅见夏月便指定壬癸为用神。',
             '春':'寒暖燥湿仍需结合节气位置与四柱，不从春季标签直接取用。',
             '秋':'寒暖燥湿仍需结合节气位置与四柱，不从秋季标签直接取用。',
             '季末月':'辰未戌丑须分别核查寒暖燥湿、人元司令与库气，不能统一当土旺。'}[season]
    methods=[
        {'id':'pattern','label':'格局取用','status':'conditional','evidence':selection['label'],
         'source_ids':['ziping-yongshen-month-origin','ziping-yongshen-pillar-coordination'],
         'conclusion':'按月令与四柱配合研究格局用神，候选尚未成格，暂不指定最终用神。'},
        {'id':'balance','label':'扶抑取用','status':'conditional','evidence':signals,
         'source_ids':['ziping-season-not-final','ziping-root-observation'],
         'conclusion':'一般研究方向：身强再查泄耗制、身弱再查生扶；整体旺衰尚未核实，因此不输出具体喜忌五行。'},
        {'id':'climate','label':'调候取用','status':'needs_source','evidence':climate,'source_ids':[],
         'conclusion':'季节检查提示为项目方法说明；《穷通宝鉴》指定日主月令条文尚未逐条核对，不冒充经典调候结论。'}]
    balance_scenarios=[{**scenario,'actual_observations':[star for star in all_stars if star['ten_god'] in scenario['relations']],
                        'status':'conditional_not_selected'} for scenario in methods_catalog['balance_scenarios']]
    return {'method_version':VERSION,'balance_scenarios':balance_scenarios,'strength' :{'status':'unresolved','signals':signals,
            'season':structure['season'],'roots':day_roots,'support_observations':support,'drain_control_observations':drain,
            'unresolved':['人元司令与本余气轻重','藏根有效性与合冲竞争','四柱生克制化的实际效力','从格化格及方法差异'],
            'conclusion':'已完成得时、得地、得助的证据汇总；不按五行数量或任意分数判身强身弱。'},
            'patterns':patterns,'special_route':selection,'wealth_conditions':wealth_checklist(chart),
            'useful_god_methods':methods,'luck':luck_cycles(chart,gender,reference_date),
            'source_ids':['ziping-season-not-final','ziping-root-observation','ziping-yongshen-pillar-coordination'],
            'limitations':'完整报告覆盖结构、旺衰证据、格局成败待核实项、三种取用方法及起运流年；最终旺衰、成格与喜用神仍依赖尚未核实的条件，不代表已实现完整古籍判命算法。'}
