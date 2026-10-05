"""One server-side shuffle per visual selection, stable reveals and followups."""
from dataclasses import dataclass
from random import SystemRandom
import secrets
from threading import Lock
import time

from .tarot import DECK,SPREADS,Reading,DrawnCard


@dataclass
class DrawSession:
    question:str
    spread:str
    deck:list
    orientations:list
    created:float
    reading:Reading|None=None
    picks:tuple|None=None


class TarotSessions:
    def __init__(self,ttl=3600,limit=200):self.ttl=ttl;self.limit=limit;self.sessions={};self.lock=Lock()
    def create(self,question,spread):
        if spread not in SPREADS or not isinstance(question,str) or not question.strip() or len(question)>2000:raise ValueError('请提供有效问题与牌阵')
        with self.lock:
            now=time.monotonic();self.sessions={k:v for k,v in self.sessions.items() if now-v.created<self.ttl}
            if len(self.sessions)>=self.limit:raise ValueError('抽牌会话已满，请稍后重试')
            rng=SystemRandom();deck=list(DECK);rng.shuffle(deck)
            key=secrets.token_urlsafe(24);self.sessions[key]=DrawSession(question.strip(),spread,deck,[bool(rng.randrange(2)) for _ in deck],now)
            return {'draw_id':key,'slots':78,'required_picks':len(SPREADS[spread]),'positions':SPREADS[spread],'expires_in_seconds':self.ttl}
    def get(self,key):
        session=self.sessions.get(key)
        if not session or time.monotonic()-session.created>=self.ttl:raise ValueError('抽牌会话已过期，请重新洗牌')
        return session
    def reveal(self,key,picks):
        with self.lock:
            session=self.get(key)
            if not isinstance(picks,list) or len(picks)!=len(SPREADS[session.spread]) or any(type(p) is not int or not 1<=p<=78 for p in picks) or len(set(picks))!=len(picks):raise ValueError('选牌数量须符合牌阵，每个位置为1–78的不同整数')
            chosen=tuple(picks)
            if session.reading:
                if session.picks!=chosen:raise ValueError('此牌面已揭示；改选请明确重新洗牌')
                return session.reading
            session.picks=chosen
            session.reading=Reading(session.question,session.spread,tuple(DrawnCard(label,session.deck[index-1],session.orientations[index-1]) for label,index in zip(SPREADS[session.spread],chosen,strict=True)))
            return session.reading
    def reading(self,key):
        with self.lock:
            reading=self.get(key).reading
            if reading is None:raise ValueError('请先选牌并翻牌')
            return reading
