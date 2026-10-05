"""A reproducible integrated daily reflection report, with offline fallback."""
from dataclasses import asdict
from datetime import date, datetime
from zoneinfo import ZoneInfo
import hashlib
import json

from .daily import daily_draw
from .bazi import calculate_bazi,parse_bazi_pillars
from .bazi_daily import daily_bazi_context
from .bazi_analysis import comprehensive_analysis
from .bazi_interactions import analyze_interactions
from .bazi_facts import chart_facts,HIDDEN_STEMS,stem_facts
from .meanings import evidence_for,load_catalog
from .bazi_sources import catalog_sha256,evidence_for as bazi_evidence

VERSION='integrated-daily-v5'
REFLECTIONS={
 '比肩':('自主与合作','今天哪些任务适合自己完成，哪些需要明确分工？'),
 '劫财':('共享与边界','是否需要先确认资源、时间或费用如何分配？'),
 '食神':('练习与表达','可以完成哪一个小作品，并给自己留出恢复时间？'),
 '伤官':('改进与沟通','想提出改进时，怎样用事实和具体建议表达？'),
 '正财':('计划与资源','今天可以核对哪一项预算或稳定投入？'),
 '偏财':('机会与筛选','面对新机会，先核实哪些成本和条件？'),
 '正官':('责任与秩序','今天最需要兑现的约定是哪一个？'),
 '七杀':('压力与优先级','可以删减哪一件事，为重要任务留出空间？'),
 '正印':('学习与支持','今天可以向谁请教，或补齐哪项知识？'),
 '偏印':('探索与验证','新想法可以通过哪个小实验验证？')}


def report_identity(store,profile_id,day=None):
    profile=store.get_profile(profile_id)
    selected=day or datetime.now(ZoneInfo(profile['timezone'])).date()
    if type(selected) is not date:raise ValueError('日报日期必须为公历日期')
    if not 1900<=selected.year<=2100:raise ValueError('日报支持1900–2100年')
    instant=datetime.combine(selected,datetime.min.time(),ZoneInfo(profile['timezone'])).replace(hour=12)
    draw=daily_draw(profile_id,profile['timezone'],instant)
    material=json.dumps([VERSION,profile,selected.isoformat(),catalog_sha256(),load_catalog()],sort_keys=True,ensure_ascii=False)
    key=hashlib.sha256(material.encode()).hexdigest()
    return profile,selected,draw,key


def existing_daily_report(store,profile_id,day=None):
    return store.get_report(report_identity(store,profile_id,day)[3])

def make_daily_report(store,profile_id,day=None,client=None,model=None):
    profile, selected, draw, key = report_identity(store,profile_id,day)
    old=store.get_report(key)
    if old:return old
    reading=asdict(draw.reading)
    evidence=list(evidence_for(draw.reading))
    card=draw.reading.cards[0]
    reflection=[{'topic':'每日塔罗','question':f'把“{card.card.name}”作为今天的反思提示，写下一件你可以主动完成的小事。','basis':'项目反思练习；并非古籍译义'}]
    chart=None; context=None; full=None; cross=None
    if profile['birth'] or profile['pillars']:
        chart=calculate_bazi(profile['birth']) if profile['birth'] else parse_bazi_pillars(profile['pillars'])
        if chart.birth_time and selected<datetime.fromisoformat(chart.birth_time).date():raise ValueError('日报日期不能早于出生日期')
        context=daily_bazi_context(chart,selected)
        full=comprehensive_analysis(chart,profile['gender'],selected)
        today=context['pillars'][2]
        god=today['heavenly_stem']['ten_god']
        topic,question=REFLECTIONS[god]
        reflection.append({'topic':topic,'question':question,'basis':f'当日干{today["ganzhi"][0]}相对日主{chart.day_master}为{god}；现代类比，不是吉凶结论'})
        natal=chart_facts(chart)['pillars']
        # Pair each natal pillar with the daily pillar without mistaking it for natal hour.
        pairs=[]
        for pillar in natal:
            other={'position':'当日','branch':today['ganzhi'][1],
                   'heavenly_stem':today['heavenly_stem'],'hidden_stems':today['hidden_stems']}
            events=analyze_interactions({'pillars':[pillar,other]},[],[])['observations']
            for event in events:
                event["id"] = pillar["position"] + "-" + event["id"]
            pairs.extend(events)
        cross={'observations':pairs,'limitations':'逐本命柱与当日干支比对关系名称，非全盘效力分析，不代表今天发生对应事件。'}
        evidence.extend(bazi_evidence(chart))
    data={'mode':'daily-report','key':key,'day':selected.isoformat(),'timezone':profile['timezone'],
          'reading':reading,'evidence':evidence,'daily_context':context,'bazi_analysis':full,
          'natal_chart':asdict(chart) if chart else None, 'natal_facts':chart_facts(chart) if chart else None,
          'daily_interactions':cross,'reflections':reflection,
          'actions':['选择一件20分钟内能推进的具体任务。','记录实际完成情况和影响因素，晚上回顾。'],
          'interpretation':None,'interpretation_mode':'offline','cached':False,
          'limitations':'塔罗与八字分别作为反思依据，不合成为客观好运分数。天气、睡眠、计划与真实反馈应优先用于决策。',
          'method_version':VERSION}
    if client is not None:
        if not model:raise ValueError('缺少日报模型配置')
        response=client.responses.create(model=model,store=False,
            instructions='用中文写简洁每日反思报告，分为总体提示、学习工作、关系沟通、资源安排、今日行动。塔罗与八字分别说明依据，不把十神或牌义当事件预言，不打运势分。只能使用输入计算数据和提供原文；natal_chart是本命四柱，daily_context是当日参考，两者本来就不同，不把不同当数据矛盾。资料不足明确说明。可以复述bazi_analysis.rule_judgment的项目旺衰估计和喜用候选，必须标明工程近似与参数敏感性；不能把它当经典最终旺衰、喜用神或成格，不预测灾祸。给2条可执行建议。',
            input=[{'role':'user','content':json.dumps(data,ensure_ascii=False)}])
        answer=response.output_text.strip()
        if not answer:raise RuntimeError('模型返回空日报；未保存，可重试')
        data['interpretation']=answer;data['interpretation_mode']='model';data['model']=model
    saved=store.save_report(key,profile_id,selected.isoformat(),data)
    saved['cached']=False
    return saved
