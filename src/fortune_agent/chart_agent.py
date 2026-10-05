"""Grounded chart interpretation with a useful offline summary."""
import json


def offline_chart_reading(mode,result):
    if mode=='ziwei':
        c=result['chart'];soul=next(p for p in c['palaces'] if p['name']=='命宫')
        names='、'.join(s['name'] for s in soul['majorStars']) or '无主星，需结合对宫与三方四正'
        return f"命宫在{soul['earthlyBranch']}，主星：{names}；五行局为{c['fiveElementsClass']}。十二宫展示实际主辅杂曜、生年四化及大限年龄标签。可从命宫、官禄、财帛和迁移宫的配合提出反思问题；空宫不能当作没有相关人生领域。星曜标签不保证事件结果。"
    sun=next(p for p in result['planets'] if p['id']=='Sun');moon=next(p for p in result['planets'] if p['id']=='Moon');asc=result['angles']['ascendant']
    return f"太阳在{sun['sign']}座，月亮在{moon['sign']}座，上升在{asc['sign']}座。可以分别用来反思表达目标、日常情绪需求与对外互动习惯；这些标签不是性格事实或事件保证。宫位采用整宫制，主要相位与容许度可逐项查看。"


def interpret_chart(mode,result,question,client,model,style="gentle"):
    if style not in ("gentle","direct"):raise ValueError("无效回答风格")
    response=client.responses.create(model=model,store=False,
      instructions='用中文解释输入实际星盘，默认600字以内。必须保持星曜、宫位、四化、星座、度数和相位不变，不自行重新排盘。说明时间、历法或宫制约定。紫微只能引用提供原文；没有紫微斗数全书已校勘原文时不编造原文页码。解释是传统概念与现代反思，不保证婚姻财运疾病等事件。结合具体问题给两条行动建议，解释未算天体/宫制的限制。',
      input=[{'role':'user','content':json.dumps({'method':mode,'question':question,'result':result,'style':style},ensure_ascii=False)}])
    if not response.output_text.strip():raise RuntimeError('星盘模型返回空回答')
    return response.output_text.strip()
