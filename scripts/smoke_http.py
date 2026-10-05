"""Synthetic, API-free end-to-end checks for a local web server."""
import json
import re
import sys
import time
import urllib.request

base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8766'
for attempt in range(30):
    try:
        page=urllib.request.urlopen(base,timeout=5).read().decode();break
    except OSError:
        if attempt==29:raise
        time.sleep(1)
token=re.search(r'<meta name="request-token" content="([^"]+)"',page).group(1)
def post(data):
    request=urllib.request.Request(base+'/api/run',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Fortune-Token':token})
    return json.load(urllib.request.urlopen(request,timeout=20))
ziwei=post({'mode':'ziwei','birth':'2000-01-01T12:00:00+08:00','gender':'female'})
assert len(ziwei['chart_result']['chart']['palaces'])==12
astro=post({'mode':'astrology','birth':'2000-01-01T12:00:00+00:00','chart_timezone':'Europe/London','latitude':51.4779,'longitude':0})
assert len(astro['chart_result']['planets'])==10
shuffle=post({'mode':'tarot-shuffle','question':'合成案例：安排学习','spread':'five'})
reading=post({'mode':'tarot-reveal','draw_id':shuffle['draw_id'],'picks':[1,15,33,60,78]})
again=post({'mode':'tarot-reveal','draw_id':shuffle['draw_id'],'picks':[1,15,33,60,78]})
assert reading['reading']==again['reading']
assert len(reading['reading']['cards'])==5
print('Zi Wei, astrology and stable visual tarot HTTP flows passed.')
