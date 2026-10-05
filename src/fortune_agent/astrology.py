"""Offline tropical geocentric chart and whole-sign houses using MIT ephemeris."""
from datetime import datetime,timedelta,timezone
import math
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

SIGNS=('白羊','金牛','双子','巨蟹','狮子','处女','天秤','天蝎','射手','摩羯','水瓶','双鱼')
BODIES={'Sun':'太阳','Moon':'月亮','Mercury':'水星','Venus':'金星','Mars':'火星','Jupiter':'木星','Saturn':'土星','Uranus':'天王星','Neptune':'海王星','Pluto':'冥王星'}
ASPECTS=((0,'合相'),(60,'六合'),(90,'刑相'),(120,'拱相'),(180,'对冲'))


def validate_birth(birth,zone):
    try:instant=datetime.fromisoformat(birth);local_zone=ZoneInfo(zone)
    except (ValueError,TypeError,ZoneInfoNotFoundError) as exc:raise ValueError('出生时间须含UTC偏移，并提供有效 IANA 出生时区') from exc
    if instant.utcoffset() is None:raise ValueError('出生时间必须含UTC偏移，不默认未知时刻')
    local=instant.astimezone(local_zone)
    if instant.utcoffset()!=local.utcoffset():raise ValueError('出生时间的UTC偏移与该IANA时区在此时刻不一致；夏令时重叠时请明确偏移')
    if not 1900<=local.year<=2100:raise ValueError('占星支持1900–2100年出生时间')
    return instant.astimezone(timezone.utc),local


def coordinates(latitude,longitude):
    if type(latitude) not in (int,float) or type(longitude) not in (int,float) or not math.isfinite(latitude) or not math.isfinite(longitude):raise ValueError('出生地经纬度必须是有限数值')
    if not -89.99<=latitude<=89.99 or not -180<=longitude<=180:raise ValueError('纬度范围为±89.99，经度范围为±180；东经为正')
    return float(latitude),float(longitude)


def zodiac(longitude):
    angle=longitude%360
    return {'longitude':round(angle,6),'sign':SIGNS[int(angle//30)],'degree_in_sign':round(angle%30,6)}


def calculate_astrology(birth,zone,latitude,longitude):
    utc,local=validate_birth(birth,zone);latitude,longitude=coordinates(latitude,longitude)
    try:import astronomy as engine
    except ImportError as exc:raise RuntimeError("请安装占星依赖：pip install -e '.[astro]'") from exc
    def astro_time(instant):return engine.Time.Make(instant.year,instant.month,instant.day,instant.hour,instant.minute,instant.second+instant.microsecond/1e6)
    moment=astro_time(utc)
    theta=math.radians((engine.SiderealTime(moment)*15+longitude)%360);phi=math.radians(latitude)
    zenith=engine.Vector(math.cos(phi)*math.cos(theta),math.cos(phi)*math.sin(theta),math.sin(phi),moment)
    east=engine.Vector(-math.sin(theta),math.cos(theta),0,moment)
    rotation=engine.Rotation_EQD_ECT(moment)
    z=engine.RotateVector(rotation,zenith);e=engine.RotateVector(rotation,east)
    def intersection(normal,positive):
        x,y=-normal.y,normal.x
        if x*positive.x+y*positive.y<0:x,y=-x,-y
        if math.hypot(x,y)<1e-10:raise ValueError('此位置的角点退化，不能提供有效宫位')
        return math.degrees(math.atan2(y,x))%360
    asc=intersection(z,e);mc=intersection(e,z)
    cusp=math.floor(asc/30)*30
    planets=[]
    for name,label in BODIES.items():
        body=getattr(engine.Body,name)
        angle=engine.Ecliptic(engine.GeoVector(body,moment,True)).elon
        before=engine.Ecliptic(engine.GeoVector(body,astro_time(utc-timedelta(hours=12)),True)).elon
        after=engine.Ecliptic(engine.GeoVector(body,astro_time(utc+timedelta(hours=12)),True)).elon
        speed=(after-before+180)%360-180
        planets.append({'id':name,'name':label,**zodiac(angle),'house':int(((angle-cusp)%360)//30)+1,
                        'longitude_speed_deg_per_day':round(speed,6),'retrograde':speed<0,'stationary_approx':abs(speed)<0.001})
    aspects=[]
    for i,a in enumerate(planets):
        for b in planets[i+1:]:
            separation=abs((a['longitude']-b['longitude']+180)%360-180)
            orb_limit=8 if a['id'] in ('Sun','Moon') or b['id'] in ('Sun','Moon') else 6
            for angle,label in ASPECTS:
                orb=abs(separation-angle)
                if orb<=orb_limit:aspects.append({'a':a['name'],'b':b['name'],'aspect':label,'angle':angle,'orb':round(orb,4),'orb_limit':orb_limit})
    return {'birth_time':local.isoformat(),'utc_time':utc.isoformat(),'timezone':zone,'latitude':latitude,'longitude':longitude,
            'planets':planets,'angles':{'ascendant':zodiac(asc),'midheaven':zodiac(mc),'descendant':zodiac(asc+180),'imum_coeli':zodiac(mc+180)},
            'houses':[{'house':i+1,**zodiac(cusp+i*30)} for i in range(12)],'aspects':sorted(aspects,key=lambda a:a['orb']),
            'method_version':'astronomy-engine-2.1.19-tropical-whole-sign-v1',
            'conventions':['热带黄道、日期黄道坐标、地心视位置（包含光行差）','整宫制：上升所在星座为第一宫，MC单独显示，不当作第十宫宫头','十大天体；五种主要相位，日月容许度8度，其他6度','逆行按前后12小时黄经差计算，不推导人生事件'],
            'evidence':[{'heading':'天文计算引擎与算法验证','source_url':'https://github.com/cosinekitty/astronomy','edition_note':'MIT天文库；天体位置的可计算性不证明占星解释的预测效力。'}],
            'limitations':'未包含凯龙星、交点、小行星或Placidus宫制；高纬整宫可计算，但角点对出生时间和地点敏感。不自动地理编码，不能猜测出生地。'}
