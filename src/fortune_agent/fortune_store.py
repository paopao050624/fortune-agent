"""Local profiles, versioned daily reports, and user review notes."""
from contextlib import closing
import json
import os
import sqlite3
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
            con.execute('CREATE TABLE IF NOT EXISTS reports (key TEXT PRIMARY KEY, profile TEXT NOT NULL, day TEXT NOT NULL, data TEXT NOT NULL, review TEXT NOT NULL DEFAULT "")')

    def connect(self):
        connection=sqlite3.connect(self.path,timeout=10)
        connection.execute("PRAGMA secure_delete=ON")
        return connection

    def save_profile(self, identifier, birth='', pillars='', gender=None, timezone='Asia/Shanghai'):
        identifier=identifier.strip()
        daily_draw(identifier,timezone)
        if timezone!='Asia/Shanghai' and (birth or pillars):
            raise ValueError('整合八字的日报目前仅支持 Asia/Shanghai 时区')
        if birth and pillars: raise ValueError('出生时间与四柱请选择一种')
        if birth: calculate_bazi(birth)
        if pillars: parse_bazi_pillars(pillars)
        if gender not in (None,'male','female'): raise ValueError('无效起运参数')
        data={'id':identifier,'birth':birth,'pillars':pillars,'gender':gender,'timezone':timezone}
        with closing(self.connect()) as con,con:
            con.execute('INSERT INTO profiles VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(identifier,json.dumps(data,ensure_ascii=False)))
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
        return {'profile':self.get_profile(profile),'history':self.history(profile,None)}

    def delete(self,profile):
        with closing(self.connect()) as con,con:
            con.execute('DELETE FROM reports WHERE profile=?',(profile,))
            con.execute('DELETE FROM profiles WHERE id=?',(profile,))

