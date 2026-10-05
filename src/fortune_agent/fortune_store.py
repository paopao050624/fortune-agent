"""Local profiles, versioned daily reports, and user review notes."""
from contextlib import closing
import json
import os
import sqlite3
import uuid
import hashlib
from datetime import datetime,timezone
from pathlib import Path

from .bazi import calculate_bazi, parse_bazi_pillars
from .daily import daily_draw


class FortuneStore:
    def __init__(self, path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(self.path,os.O_CREAT|os.O_WRONLY,0o600)
        os.close(descriptor)
        self.path.chmod(0o600)
        with closing(self.connect()) as con, con:
            con.execute('CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS readings (key TEXT PRIMARY KEY, profile TEXT NOT NULL, kind TEXT NOT NULL, created TEXT NOT NULL, data TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS reports (key TEXT PRIMARY KEY, profile TEXT NOT NULL, day TEXT NOT NULL, data TEXT NOT NULL, review TEXT NOT NULL DEFAULT "")')

    def connect(self):
        connection=sqlite3.connect(self.path,timeout=10)
        connection.execute("PRAGMA secure_delete=ON")
        return connection

    def _validated_profile(self, identifier, birth='', pillars='', gender=None, timezone='Asia/Shanghai', *, chart_birth='', chart_timezone='Asia/Shanghai', latitude=None, longitude=None, style='gentle', preferred_method='none', display_name=''):
        if not isinstance(identifier,str) or any(not isinstance(v,str) for v in (birth,pillars,timezone,chart_birth,chart_timezone)):raise ValueError("档案文字字段格式无效")
        identifier=identifier.strip()
        daily_draw(identifier,timezone)
        if timezone!='Asia/Shanghai' and (birth or pillars):
            raise ValueError('整合八字的日报目前仅支持 Asia/Shanghai 时区')
        if birth and pillars: raise ValueError('出生时间与四柱请选择一种')
        if birth: birth=calculate_bazi(birth).birth_time
        if pillars: parse_bazi_pillars(pillars)
        if gender not in (None,'male','female'): raise ValueError('无效起运参数')
        from .astrology import validate_birth,coordinates
        if chart_birth:chart_birth=validate_birth(chart_birth,chart_timezone)[1].isoformat(timespec="seconds")
        if latitude is not None or longitude is not None:latitude,longitude=coordinates(latitude,longitude)
        if style not in ('gentle','direct') or preferred_method not in ('none','tarot','bazi','ziwei','astrology','iching','daily'):raise ValueError('无效的档案偏好')
        if not isinstance(display_name,str) or len(display_name)>80:raise ValueError('显示名称最多80字')
        data={'id':identifier,'birth':birth,'pillars':pillars,'gender':gender,'timezone':timezone,
              'chart_birth':chart_birth,'chart_timezone':chart_timezone,'latitude':latitude,'longitude':longitude,
              'style':style,'preferred_method':preferred_method,'display_name':display_name.strip()}
        return data

    def save_profile(self, identifier, birth='', pillars='', gender=None, timezone='Asia/Shanghai', **options):
        data=self._validated_profile(identifier,birth,pillars,gender,timezone,**options)
        with closing(self.connect()) as con,con:
            con.execute('INSERT INTO profiles VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(data['id'],json.dumps(data,ensure_ascii=False)))
        return data

    def get_profile(self,identifier):
        with closing(self.connect()) as con:
            row=con.execute('SELECT data FROM profiles WHERE id=?',(identifier,)).fetchone()
        if not row: raise ValueError('请先保存此代号的档案')
        return json.loads(row[0])

    def profiles(self):
        with closing(self.connect()) as con:
            rows=con.execute('SELECT data FROM profiles ORDER BY id').fetchall()
        return [json.loads(row[0]) for row in rows]

    def get_report(self,key):
        with closing(self.connect()) as con:
            row=con.execute('SELECT data,review FROM reports WHERE key=?',(key,)).fetchone()
        if not row:return None
        return {**json.loads(row[0]),'review':row[1],'cached':True}

    def save_report(self,key,profile,day,data):
        with closing(self.connect()) as con,con:
            if con.execute('SELECT 1 FROM profiles WHERE id=?',(profile,)).fetchone() is None:
                raise ValueError('档案已删除，日报不再保存')
            con.execute('INSERT OR IGNORE INTO reports(key,profile,day,data) VALUES (?,?,?,?)',(key,profile,day,json.dumps(data,ensure_ascii=False)))
        return self.get_report(key)

    def history(self,profile,limit=366):
        with closing(self.connect()) as con:
            query='SELECT key,day,data,review FROM reports WHERE profile=? ORDER BY day DESC, key'
            rows=con.execute(query if limit is None else query+' LIMIT ?', (profile,) if limit is None else (profile,limit)).fetchall()
        return [{'key':key,'day':day,'report':json.loads(data),'review':review} for key,day,data,review in rows]

    def review(self,profile,key,note):
        if not isinstance(note,str) or len(note)>2000:raise ValueError('回顾须不超过2000字')
        with closing(self.connect()) as con,con:
            if con.execute('UPDATE reports SET review=? WHERE key=? AND profile=?',(note,key,profile)).rowcount!=1:
                raise ValueError('未找到此档案的日报')

    def export(self,profile):
        return {'schema_version':2,'profile':self.get_profile(profile),'history':self.history(profile,None),'readings':self.readings(profile,None)}

    def delete(self,profile):
        with closing(self.connect()) as con,con:
            con.execute('DELETE FROM readings WHERE profile=?',(profile,))
            con.execute('DELETE FROM reports WHERE profile=?',(profile,))
            con.execute('DELETE FROM profiles WHERE id=?',(profile,))


    def save_reading(self,profile,kind,data):
        if kind not in ('tarot','bazi','ziwei','astrology','iching'):raise ValueError('无效历史类型')
        key=uuid.uuid4().hex
        with closing(self.connect()) as con,con:
            if con.execute('SELECT 1 FROM profiles WHERE id=?',(profile,)).fetchone() is None:raise ValueError('请先保存档案')
            con.execute('INSERT INTO readings VALUES (?,?,?,?,?)',(key,profile,kind,datetime.now(timezone.utc).isoformat(),json.dumps(data,ensure_ascii=False)))
        return key

    def readings(self,profile,limit=100):
        with closing(self.connect()) as con:
            query='SELECT key,kind,created,data FROM readings WHERE profile=? ORDER BY created DESC'
            rows=con.execute(query if limit is None else query+' LIMIT ?',(profile,) if limit is None else (profile,limit)).fetchall()
        return [{'key':key,'kind':kind,'created':created,'result':json.loads(data)} for key,kind,created,data in rows]

    def import_archive(self,archive):
        if not isinstance(archive,dict) or archive.get('schema_version',1) not in (1,2):raise ValueError('不支持的档案版本')
        p=archive.get('profile');history=archive.get('history',[]);readings=archive.get('readings',[])
        if not isinstance(p,dict) or not isinstance(history,list) or not isinstance(readings,list) or len(history)+len(readings)>2000:raise ValueError('档案结构无效或记录过多')
        identifier=p.get('id')
        if not isinstance(identifier,str):raise ValueError('档案代号无效')
        identifier=identifier.strip()
        # Validate all records before mutating a profile; import is merge-only.
        if any(not isinstance(r,dict) or not isinstance(r.get('key'),str) for r in history):raise ValueError('日报key格式无效')
        if any(not isinstance(r,dict) or not isinstance(r.get('key'),str) for r in readings):raise ValueError('工具历史key格式无效')
        if len({r['key'] for r in history})!=len(history):raise ValueError('日报key重复或记录格式无效')
        if len({r['key'] for r in readings})!=len(readings):raise ValueError('工具历史key重复或记录格式无效')
        for r in history:
            if not isinstance(r,dict) or not isinstance(r.get('key'),str) or len(r['key'])!=64 or not isinstance(r.get('report'),dict) or not isinstance(r.get('review',''),str) or len(r.get('review',''))>2000:raise ValueError('日报记录无效')
            datetime.strptime(r.get('day',''),'%Y-%m-%d')
        for r in readings:
            if not isinstance(r,dict) or r.get('kind') not in ('tarot','bazi','ziwei','astrology','iching') or not isinstance(r.get('result'),dict) or not isinstance(r.get('key'),str):raise ValueError('工具历史记录无效')
            datetime.fromisoformat(r.get('created',''))
        try:self.get_profile(identifier)
        except ValueError:pass
        else:raise ValueError('同代号档案已存在；请先修改导入文件代号或另存档案，避免覆盖')
        allowed={k:p[k] for k in ('chart_birth','chart_timezone','latitude','longitude','style','preferred_method','display_name') if k in p}
        data=self._validated_profile(identifier,p.get('birth',''),p.get('pillars',''),p.get('gender'),p.get('timezone','Asia/Shanghai'),**allowed)
        with closing(self.connect()) as con,con:
            con.execute('BEGIN IMMEDIATE')
            if con.execute('SELECT 1 FROM profiles WHERE id=?',(identifier,)).fetchone():
                raise ValueError('同代号档案已存在，导入不会覆盖')
            con.execute('INSERT INTO profiles VALUES (?,?)',(identifier,json.dumps(data,ensure_ascii=False)))
            for r in history:
                key=r['key']
                owner=con.execute('SELECT profile FROM reports WHERE key=?',(key,)).fetchone()
                if owner and owner[0]!=identifier:key=hashlib.sha256((identifier+':'+key).encode()).hexdigest()
                report={**r['report'],'key':key,'imported':True}
                con.execute('INSERT OR IGNORE INTO reports VALUES (?,?,?,?,?)',(key,identifier,r['day'],json.dumps(report,ensure_ascii=False),r.get('review','')))
            for r in readings:
                key=r['key']
                owner=con.execute('SELECT profile FROM readings WHERE key=?',(key,)).fetchone()
                if owner and owner[0]!=identifier:key=uuid.uuid4().hex
                con.execute('INSERT OR IGNORE INTO readings VALUES (?,?,?,?,?)',(key,identifier,r['kind'],r['created'],json.dumps(r['result'],ensure_ascii=False)))
        return self.get_profile(identifier)
