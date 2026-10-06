"""Script-free report export from explicit public sections, with opt-in birth details."""
from html import escape
from datetime import datetime
import json
import re
import textwrap
from . import __version__

SENSITIVE_KEYS={'birth_time','birth','chart_birth','utc_time','timezone','chart_timezone','latitude','longitude','profile','profile_key','key','session_id','gender','gender_parameter','review','display_name'}
LABELS={'bazi':'八字报告','tarot':'塔罗反思报告','daily':'每日塔罗提示','daily-report':'每日运势报告','ziwei':'紫微斗数报告','astrology':'西方占星报告','iching':'周易报告'}


def report_sections(data,include_private=False,include_sources=True):
    if not isinstance(data,dict) or data.get('mode') not in LABELS:raise ValueError('请选择可导出的实际结果')
    if not isinstance(include_private,bool) or not isinstance(include_sources,bool):raise ValueError('导出选项须为布尔值')
    # Values redacted from generated narrative as well as omitted metadata.
    sensitive=[]
    def collect(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in SENSITIVE_KEYS and isinstance(item,(str,int,float)) and not isinstance(item,bool) and str(item):sensitive.append(str(item))
                else:collect(item)
        elif isinstance(value,list):
            for item in value:collect(item)
    collect(data)
    def clean(text):
        text=str(text)
        if not include_private:
            for value in sorted(set(sensitive),key=len,reverse=True):
                if len(value)>=4:text=text.replace(value,'[已隐藏]')
            text=re.sub(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}[T ]\d{1,2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2})?','[出生时刻已隐藏]',text)
            text=re.sub(r'(?:北纬|南纬|东经|西经|纬度|经度|latitude|longitude)\s*[:：]?\s*-?\d+(?:\.\d+)?','[坐标已隐藏]',text,flags=re.I)
        return text
    sections=[]
    def add(title,lines):
        if lines:sections.append({'title':title,'lines':[clean(x) for x in lines]})
    if data.get('day'):add('报告日期',[data['day']])
    if include_private:
        chart=data.get('chart') or data.get('natal_chart') or data.get('chart_result') or {}
        add('用户选择包含的出生资料',[f'{key}：{chart[key]}' for key in ('birth_time','timezone','latitude','longitude','gender_parameter') if chart.get(key) is not None])
    if data.get('reading'):add('实际牌面',[f"{c['position']}：{c['card']['name']}（{'逆位' if c['reversed'] else '正位'}）" for c in data['reading']['cards']])
    if data.get('chart'):add('实际四柱',[f"{name}：{data['chart'][key]}" for name,key in [('年柱','year'),('月柱','month'),('日柱','day'),('时柱','hour')]])
    if data.get('cast'):
        c=data['cast'];add('实际卦象',[f"主卦：{c['main_hexagram']['name']}；变卦：{c['changed_hexagram']['name']}", '动爻：'+('、'.join(map(str,c['moving_positions'])) or '无')])
    if data.get('chart_result'):
        r=data['chart_result']
        if data['mode']=='ziwei':add('本命十二宫',[p['name']+'宫 '+p['earthlyBranch']+'：'+('、'.join(s['name']+(('化'+s['mutagen']) if s.get('mutagen') else '') for s in p['majorStars']) or '无主星') for p in r['chart']['palaces']])
        else:add('本命天体',[f"{p['name']}：{p['sign']} {p['degree_in_sign']:.2f}°，第{p['house']}宫，{'逆行' if p['retrograde'] else '顺行'}" for p in r['planets']])
    add('解读与建议',[data['interpretation']] if data.get('interpretation') else [])
    complete=data.get('complete_analysis') or data.get('bazi_analysis')
    if complete:
        add('模型估计',[complete['strength'].get('label') or complete['strength']['conclusion']])
        luck=complete['luck']
        if luck['status']=='calculated':add('参考运段',[f"当前大运：{luck['current_cycle']['ganzhi'] if luck['current_cycle'] else '不在展示区间'}；流年：{luck['annual_reference']['ganzhi']}"])
        add('取用与方法边界',[method['label']+'：'+method['conclusion'] for method in complete['useful_god_methods']])
    add('今日行动',data.get('actions',[]))
    if include_sources:
        add('来源与版本',[f"{e.get('heading') or e.get('id') or e.get('card_id') or '资料'}：{e.get('locator','')}\n{e.get('source_url') or '该方向尚无核对原文'}" for e in data.get('evidence',[])])
    add('适用说明',[data.get('limitations') or '结果为传统概念和现代反思，不是未来事件保证。软件校验不证明预测效力。'])
    add('导出说明',['包含出生资料。' if include_private else '默认隐藏明确出生时刻、坐标和档案标识；模型自由文本仍请在分享前核查，避免包含你自行输入的私人信息。'])
    return {'title':LABELS[data['mode']],'version':__version__,'sections':sections,'include_private':include_private}


def export_report(data,format='html',include_private=False,include_sources=True):
    if format not in ('html','svg'):raise ValueError('导出格式支持html/svg；PDF和PNG由浏览器打印或转换')
    report=report_sections(data,include_private,include_sources)
    def plain(text):return re.sub(r'(?m)^#{1,6}\s*','',text).replace('**','').replace('__','')
    if format=='html':
        sections=''.join('<section><h2>'+escape(s['title'])+'</h2>'+''.join('<p>'+escape(plain(line)).replace('\n','<br>')+'</p>' for line in s['lines'])+'</section>' for s in report['sections'])
        content='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(report['title'])+'</title><style>body{font:15px/1.8 system-ui,sans-serif;color:#20312d;background:#faf9f3;margin:0}main{max-width:760px;margin:32px auto;padding:32px;background:white;border:1px solid #d6ddd4;border-radius:12px}h1{font-size:26px}h2{font-size:18px;color:#325949;border-bottom:1px solid #ddd;padding-bottom:8px}p{overflow-wrap:anywhere}section{margin:24px 0}@media print{body{background:white}main{margin:0;border:0;padding:0}h2{break-after:avoid}p{orphans:3;widows:3}section{break-inside:auto}@page{margin:18mm}}</style><main><h1>'+escape(report['title'])+'</h1><p>Fortune Agent '+report['version']+'</p>'+sections+'</main></html>'
        return {'content':content,'mime_type':'text/html;charset=utf-8','filename':'fortune-report.html','report':report}
    rows=[(report['title'],28),('Fortune Agent '+report['version'],14)]
    for section in report['sections']:
        rows.append(('',12));rows.append((section['title'],20))
        for line in section['lines']:
            for para in plain(line).splitlines():
                rows.extend((wrapped,15) for wrapped in textwrap.wrap(para,width=48,break_long_words=True) or [''])
    y=45;parts=[]
    for text,size in rows:
        parts.append(f'<text x="36" y="{y}" font-size="{size}" fill="#20312d">{escape(text)}</text>');y+=size+12
    height=y+30
    if height>24000:raise ValueError('报告过长，图片导出请关闭来源或改用HTML/PDF')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="840" height="{height}" viewBox="0 0 840 {height}"><rect width="840" height="{height}" fill="#faf9f3"/><g font-family="sans-serif">'+''.join(parts)+'</g></svg>'
    return {'content':svg,'mime_type':'image/svg+xml;charset=utf-8','filename':'fortune-report.svg','report':report}
