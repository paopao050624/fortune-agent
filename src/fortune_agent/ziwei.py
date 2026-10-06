"""Fixed iztro natal-chart adapter. Node executes only a bundled local program."""
from datetime import datetime
from importlib.resources import files,as_file
from pathlib import Path
import json
import os
import shutil
import subprocess
from .ziwei_sources import evidence_for,explanation_context,catalog_sha256


def node_executable():
    configured=os.environ.get('FORTUNE_NODE','')
    bundled=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
    found=configured or shutil.which('node') or (str(bundled) if bundled.is_file() else '')
    if not found:raise RuntimeError('紫微排盘需要 Node.js 18+；安装后设置 FORTUNE_NODE 或加入 PATH')
    return found


def calculate_ziwei(birth,gender):
    if gender not in ('male','female'):raise ValueError('紫微需要用户明确选择传统男/女排盘参数')
    try:instant=datetime.fromisoformat(birth)
    except (TypeError,ValueError) as exc:raise ValueError('请提供准确公历出生日期、时刻及 +08:00 偏移') from exc
    if instant.utcoffset() is None or instant.utcoffset().total_seconds()!=28800:raise ValueError('紫微本版本仅按中国标准时间 +08:00 排盘')
    if not 1900<=instant.year<=2100:raise ValueError('紫微支持1900–2100年出生时间')
    index=12 if instant.hour==23 else (instant.hour+1)//2
    payload={'date':instant.date().isoformat(),'time_index':index,'gender':gender}
    with as_file(files('fortune_agent').joinpath('static/ziwei.cjs')) as bridge:
        try:
            result=subprocess.run([node_executable(),str(bridge)],input=json.dumps(payload),capture_output=True,text=True,timeout=15,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:raise RuntimeError('紫微计算运行时不可用或超时') from exc
    if result.returncode:raise RuntimeError('紫微排盘失败，请核对输入与 Node 运行时')
    try:chart=json.loads(result.stdout)
    except ValueError as exc:raise RuntimeError('紫微运行时返回无效结果') from exc
    if len(chart.get('palaces',[]))!=12:raise RuntimeError('紫微十二宫数据不完整')
    retrieved=evidence_for(chart)
    return {'birth_time':instant.isoformat(),'gender_parameter':gender,'chart':chart,
            'method_version':'iztro-2.6.1-natal-sourced-v2','source_catalog_sha256':catalog_sha256(),
            'explanation_context':explanation_context(chart,retrieved),'calculator':'iztro 2.6.1 (MIT)',
            'conventions':['公历输入，农历年界；未校正真太阳时','23:00晚子时按次日规则；0:00早子时索引0','闰月前半按本月、后半按下月（iztro fixLeap=true）','算法default，十二宫、主辅杂曜、亮度与生年四化来自固定库'],
            'evidence':[*retrieved,{'heading':'紫微排盘算法与版本','source_url':'https://github.com/SylarLong/iztro','edition_note':'排盘来自固定开源库；原文来自固定电子修订，未完成纸本全书校勘。'}],
            'limitations':'计算结果遵循选定库与时间约定；性别参数用于传统算法，不能由姓名推测。星曜与四化不代表人生事件保证。'}
