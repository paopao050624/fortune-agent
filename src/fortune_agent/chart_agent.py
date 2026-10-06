"""Grounded chart interpretation with a useful offline summary."""
import json
from .question_focus import question_guidance


def offline_chart_reading(mode,result):
    if mode=='ziwei':
        c=result['chart'];soul=next(p for p in c['palaces'] if p['name']=='命宫')
        names='、'.join(s['name'] for s in soul['majorStars']) or '无主星，需结合对宫与三方四正'
        base=f"命宫在{soul['earthlyBranch']}，主星：{names}；五行局为{c['fiveElementsClass']}。"
        relevant=[e for e in result['evidence'] if e.get('star') in {s['name'] for s in soul['majorStars']}]
        lines=['### 本次概览',base,'### 反思方向']
        for e in relevant[:2]:lines.extend(['**'+e['topic']+'**',e['reflection'],'> '+e['source_text'],f"[《{e['work']}》{e['chapter']}]({e['source_url']})"])
        if not relevant:lines.append('命宫无主星，需一起查看对宫与三方；没有主星不代表没有人生主题。')
        lines.extend(['现代反思问题是项目整理，不是古籍对当前用户的断言。','原文依据为固定电子转录，尚未与纸本全书校勘；星曜及四化不能保证未来事件。'])
        return '\n\n'.join(lines)

    sun=next(p for p in result['planets'] if p['id']=='Sun');moon=next(p for p in result['planets'] if p['id']=='Moon');asc=result['angles']['ascendant']
    return f"太阳在{sun['sign']}座，月亮在{moon['sign']}座，上升在{asc['sign']}座。可以分别用来反思表达目标、日常情绪需求与对外互动习惯；这些标签不是性格事实或事件保证。宫位采用整宫制，主要相位与容许度可逐项查看。"


ZIWEI_SCHEMA={"type":"object","additionalProperties":False,"properties":{
    "summary":{"type":"string"},
    "explanations":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{"source_id":{"type":"string"},"meaning":{"type":"string"},"application":{"type":"string"}},"required":["source_id","meaning","application"]}},
    "advice":{"type":"array","items":{"type":"string"}},"limitations":{"type":"array","items":{"type":"string"}}},"required":["summary","explanations","advice","limitations"]}


def render_ziwei_analysis(analysis,result):
    if not isinstance(analysis,dict) or set(analysis)!=set(ZIWEI_SCHEMA['required']):raise RuntimeError('紫微解释结构不完整')
    if not isinstance(analysis['summary'],str) or not analysis['summary'].strip():raise RuntimeError('紫微解释概要为空')
    if not isinstance(analysis['explanations'],list) or not 1<=len(analysis['explanations'])<=6:raise RuntimeError('紫微解释应包含1–6条实际依据')
    lookup={e['id']:e for e in result['evidence'] if e.get('id')}
    selected=[];seen=set()
    for item in analysis['explanations']:
        if not isinstance(item,dict) or set(item)!={'source_id','meaning','application'} or item['source_id'] not in lookup or item['source_id'] in seen:raise RuntimeError('紫微引用了未提供或重复的条目')
        if any(not isinstance(item[k],str) or not item[k].strip() for k in ('meaning','application')):raise RuntimeError('紫微条目解释为空')
        selected.append((item,lookup[item['source_id']]));seen.add(item['source_id'])
    for key in ('advice','limitations'):
        if not isinstance(analysis[key],list) or not 1<=len(analysis[key])<=6 or any(not isinstance(v,str) or not v.strip() for v in analysis[key]):raise RuntimeError('紫微建议或边界字段无效')
    parts=['### 本次提示',analysis['summary'],'### 原文与解释']
    for item,entry in selected:
        positions='、'.join(p['palace']+('' if p['palace'].endswith('宫') else '宫')+' · '+p['star'] for p in entry['matched_positions']) or '综合判断原则'
        parts.extend([f"**{entry['topic']}** · {positions}",'> '+entry['source_text'],f"[《{entry['work']}》{entry['chapter']}]({entry['source_url']})",'传统概念：'+item['meaning'],'现代反思：'+item['application']])
    parts.extend(['### 可以采取的行动',*['- '+a for a in analysis['advice']],'### 适用边界',*['- '+a for a in analysis['limitations']],'- 引用为固定电子转录，尚未与纸本完整校勘；不提供未经核实的纸本页码。'])
    return '\n\n'.join(parts)


def interpret_chart(mode,result,question,client,model,style="gentle"):
    if style not in ("gentle","direct"):raise ValueError("无效回答风格")
    if mode=='ziwei':
        response=client.responses.create(model=model,store=False,
          instructions='根据实际紫微本命盘返回结构化中文解释，summary简洁，explanations选2–3个直接相关source_id。只选输入evidence中实际提供的id，结合命宫、身宫与对宫三方，不改变星曜/亮度/四化。原文和来源由程序展示，模型字段不另造经典引文或纸本页码。meaning解释历史概念，application是现代反思，不能混为原文。旧时代性别偏见、疾病、寿夭、贫富和宿命断语不能套用为用户事实或预言；化忌不代表灾祸。给两条行动建议与明确版本限制。'+question_guidance(question),
          input=[{'role':'user','content':json.dumps({'question':question,'result':result,'style':style},ensure_ascii=False)}],
          text={'format':{'type':'json_schema','name':'ziwei_interpretation','schema':ZIWEI_SCHEMA,'strict':True}})
        try:analysis=json.loads(response.output_text)
        except (ValueError,TypeError):raise RuntimeError('紫微模型返回的解释结构无效')
        return render_ziwei_analysis(analysis,result)
    response=client.responses.create(model=model,store=False,
      instructions='用中文解释输入实际星盘，默认600字以内。保持星座、度数、宫位和相位不变，不重新排盘。说明热带黄道与整宫制约定。解释是传统概念与现代反思，不保证婚姻财运疾病等事件。结合问题给两条行动建议，说明未算天体/宫制限制。'+question_guidance(question),
      input=[{'role':'user','content':json.dumps({'method':mode,'question':question,'result':result,'style':style},ensure_ascii=False)}])
    if not response.output_text.strip():raise RuntimeError('星盘模型返回空回答')
    return response.output_text.strip()
