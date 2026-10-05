"""Synthetic container checks including request guards and volume persistence."""
import argparse
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','recover','cleanup']);parser.add_argument('--url',default='http://127.0.0.1:18766');parser.add_argument('--snapshot',type=Path,default=Path('work/web-validation/container-snapshot.json'));args=parser.parse_args()
page=urllib.request.urlopen(args.url,timeout=10).read().decode();token=re.search(r'<meta name="request-token" content="([^"]+)"',page).group(1)
def post(payload,provided_token=token):
    r=urllib.request.Request(args.url+'/api/run',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Fortune-Token':provided_token})
    return json.load(urllib.request.urlopen(r,timeout=30))
profile='synthetic-container-persistence-20261006'
if args.phase=='prepare':
    for bad in ('','wrong-token'):
        try:post({'mode':'profiles'},bad)
        except urllib.error.HTTPError as e:assert e.code==403
        else:raise AssertionError('invalid token accepted')
    request=urllib.request.Request(args.url,headers={'Host':'untrusted.example'})
    try:urllib.request.urlopen(request,timeout=5)
    except urllib.error.HTTPError as e:assert e.code==403
    else:raise AssertionError('untrusted Host accepted')
    post({'mode':'profile-save','profile':profile,'birth':'2000-01-01T12:00:00+08:00','gender':'female'})
    report=post({'mode':'daily-report','profile':profile,'date':'2026-10-06'})
    assert report['bazi_analysis']['luck']['current_cycle']['ganzhi']=='己卯'
    post({'mode':'daily-review','profile':profile,'key':report['key'],'review':'合成容器持久化测试'})
    bazi=post({'mode':'bazi','birth':'2000-01-01T12:00:00+08:00','gender':'female','date':'2026-10-06'})
    assert bazi['complete_analysis']['rule_judgment']['strength']['status']=='estimated'
    iching=post({'mode':'iching','lines':[9]*6})
    assert iching['cast']['main_hexagram']['name']=='乾'
    snapshot={'key':report['key'],'reading':report['reading'],'reference':'2026-10-06'}
    args.snapshot.parent.mkdir(parents=True,exist_ok=True);args.snapshot.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
    print('Container: token/Host guards, Ba Zi, I Ching, profile, report and review passed.')
elif args.phase=='recover':
    expected=json.loads(args.snapshot.read_text())
    report=post({'mode':'daily-report','profile':profile,'date':expected['reference']})
    assert report['cached'] and report['key']==expected['key'] and report['reading']==expected['reading']
    assert report['review']=='合成容器持久化测试'
    archive=post({'mode':'profile-export','profile':profile})
    assert len(archive['history'])==1
    print('Container restart: profile, daily card, cached report and review persisted.')
else:
    post({'mode':'profile-delete','profile':profile})
    assert not post({'mode':'daily-history','profile':profile})['history']
    print('Synthetic validation profile removed.')
