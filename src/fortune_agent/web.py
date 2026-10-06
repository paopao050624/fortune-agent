"""Local browser interface, using the existing domain and interpretation code."""

from __future__ import annotations

import argparse
from html import escape
import json
import secrets
from dataclasses import asdict,replace
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from threading import Lock,local
from typing import Any

from .agent import TarotAgent
from .bazi import calculate_bazi, parse_bazi_pillars
from .bazi_analysis import comprehensive_analysis
from .fortune_store import FortuneStore,profile_token
from .fortune_daily import make_daily_report, existing_daily_report
from .bazi_agent import interpret_bazi
from .bazi_facts import chart_facts
from .bazi_rules import wealth_checklist
from .bazi_sources import evidence_for as bazi_evidence
from .config import ApiConfig
from .daily import daily_draw
from .daily_service import get_daily
from .daily_store import DailyStore
from .meanings import evidence_for
from .tarot import draw_reading
from .tarot_sessions import TarotSessions
from .ziwei import calculate_ziwei
from .astrology import calculate_astrology
from .chart_agent import interpret_chart,offline_chart_reading
from .request_jobs import RequestJobs,ProgressClient,RequestCancelled
from .iching import build_cast, cast_coins, load_catalog as iching_catalog
from .iching_reading import select_passages, reference_hexagram
from .iching_agent import interpret_cast
from .conversation import ConversationStore
from .unified_agent import UnifiedAgent
from .bazi_daily import daily_bazi_context
from .bazi_structure import analyze_structure


def text_field(payload: dict, name: str, default: str = "", limit: int = 2000) -> str:
    value = payload.get(name, default)
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"字段 {name} 格式无效或过长")
    return value.strip()


class LocalApp:
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.daily_lock = Lock()
        self.conversations = ConversationStore()
        self.tarot_sessions = TarotSessions()
        self.request_jobs=RequestJobs()
        self.request_context=local()

    def model_client(self) -> tuple[Any, str]:
        config = ApiConfig.from_env()
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ValueError("请先安装模型依赖：pip install -e '.[agent,bazi]'") from exc
        return OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=60, max_retries=0), config.model

    def get_model_client(self):
        client,model=self.model_client()
        job=getattr(self.request_context,'job',None)
        if job:
            client=ProgressClient(client,job)
            self.request_context.clients.append(client)
        return client,model

    def request_progress(self,stage,session_id=None,preview=None):
        job=getattr(self.request_context,'job',None)
        if job:job.progress(stage,session_id,preview)

    def run_job(self,payload,job):
        self.request_context.job=job
        self.request_context.clients=[]
        try:return self.run(payload)
        finally:
            for client in self.request_context.clients:
                try:client.close()
                except Exception:pass
            del self.request_context.clients
            del self.request_context.job

    def run(self, payload: dict) -> dict:
        mode = text_field(payload, "mode", limit=20)
        interpret = payload.get("interpret", False)
        if not isinstance(interpret, bool):
            raise ValueError("interpret 必须为布尔值")
        for flag in ("use_profile","save_history"):
            if flag in payload and not isinstance(payload[flag],bool):raise ValueError(f"{flag} 必须为布尔值")
        style = text_field(payload, "style", "gentle", 20)
        if style not in ("direct", "gentle"):
            raise ValueError("无效回答风格")

        if mode=='job-start':
            request=payload.get('request')
            allowed={'chat','tarot','tarot-reveal','tarot-followup','bazi','ziwei','astrology','iching','daily','daily-report'}
            if not isinstance(request,dict) or request.get('mode') not in allowed:raise ValueError('无效后台请求类型')
            return self.request_jobs.start(request,self.run_job)
        if mode=='job-retry':
            return self.request_jobs.retry(text_field(payload,'job_id',limit=100),self.run_job)
        if mode in ('job-status','job-cancel'):
            identifier=text_field(payload,'job_id',limit=100)
            return self.request_jobs.cancel(identifier) if mode=='job-cancel' else self.request_jobs.status(identifier)
        if mode=='profile-preview':
            saved=FortuneStore(self.cache_path.parent/'fortune.sqlite3').get_profile(text_field(payload,'profile',limit=128))
            return {'profile':saved,'confirmation_token':profile_token(saved)}

        if mode in ("profiles", "profile-save", "profile-delete", "profile-export", "daily-report", "daily-history", "daily-review", "profile-import", "reading-history"):
            store = FortuneStore(self.cache_path.parent / "fortune.sqlite3")
            profile = text_field(payload, "profile", "reader-01", 128)
            if mode == "profile-import":
                return {"profile":store.import_archive(payload.get("archive"))}
            if mode == "reading-history":
                return {"readings":store.readings(profile)}
            if mode == "profiles":
                return {"profiles": store.profiles()}
            if mode == "profile-save":
                gender = text_field(payload, "gender", "", 10) or None
                return {"profile": store.save_profile(profile, text_field(payload,"birth",limit=60), text_field(payload,"pillars",limit=60), gender, text_field(payload,"timezone","Asia/Shanghai",100), chart_birth=text_field(payload,"chart_birth",limit=60), chart_timezone=text_field(payload,"chart_timezone","Asia/Shanghai",100), latitude=payload.get("latitude"), longitude=payload.get("longitude"), style=style, preferred_method=text_field(payload,"preferred_method","none",20), display_name=text_field(payload,"display_name",limit=80))}
            if mode == "profile-delete":
                store.delete(profile)
                return {"deleted": True}
            if mode == "profile-export":
                return store.export(profile)
            if mode == "daily-history":
                return {"history": store.history(profile)}
            if mode == "daily-review":
                store.review(profile, text_field(payload,"key",limit=64), text_field(payload,"review"))
                return {"saved": True}
            selected = text_field(payload,"date",limit=10)
            selected = date.fromisoformat(selected) if selected else None
            with self.daily_lock:
                cached = existing_daily_report(store,profile,selected)
                if cached: return cached
                if interpret:
                    client, model = self.get_model_client()
                    try: return make_daily_report(store,profile,selected,client,model)
                    finally: client.close()
                return make_daily_report(store,profile,selected)

        if mode in ("ziwei", "astrology"):
            profile = text_field(payload,"profile",limit=128)
            birth=text_field(payload,"birth",limit=60)
            gender=text_field(payload,"gender",limit=10) or None
            zone=text_field(payload,"chart_timezone","Asia/Shanghai",100)
            latitude,longitude=payload.get("latitude"),payload.get("longitude")
            if payload.get("use_profile"):
                saved=FortuneStore(self.cache_path.parent/"fortune.sqlite3").get_profile(profile)
                birth=saved.get("chart_birth") or saved["birth"]
                gender=saved["gender"];style=saved.get("style","gentle");zone=saved.get("chart_timezone","Asia/Shanghai")
                latitude,longitude=saved.get("latitude"),saved.get("longitude")
            domain=calculate_ziwei(birth,gender) if mode=="ziwei" else calculate_astrology(birth,zone,latitude,longitude)
            answer=offline_chart_reading(mode,domain)
            self.request_progress("星盘已计算，正在准备解读",preview={"mode":mode,"chart_result":domain,"interpretation":answer,"evidence":domain["evidence"]})
            if interpret:
                client,model=self.get_model_client()
                try:answer=interpret_chart(mode,domain,text_field(payload,"question","请解释这张星盘"),client,model,style)
                finally:client.close()
            result={"mode":mode,"chart_result":domain,"interpretation":answer,"evidence":domain["evidence"]}
            if payload.get("save_history"):
                result["history_key"]=FortuneStore(self.cache_path.parent/"fortune.sqlite3").save_reading(profile,mode,result)
            return result

        if mode=="tarot-shuffle":
            return self.tarot_sessions.create(text_field(payload,"question"),text_field(payload,"spread","three",20))
        if mode in ("tarot-reveal","tarot-followup"):
            key=text_field(payload,"draw_id",limit=100)
            reading=self.tarot_sessions.reveal(key,payload.get("picks")) if mode=="tarot-reveal" else self.tarot_sessions.reading(key)
            question=text_field(payload,"question",reading.question)
            if mode=="tarot-followup" and not question:raise ValueError('追问不能为空')
            answer=None
            self.request_progress("牌面已固定，正在准备解读",preview={"mode":"tarot","draw_id":key,"reading":asdict(reading),"evidence":evidence_for(reading)})
            if interpret or mode=="tarot-followup":
                client,model=self.get_model_client()
                fixed=replace(reading,question=question)
                try:answer=TarotAgent(client,model,draw=lambda *_:fixed).read(question,reading.spread,style=style).interpretation
                finally:client.close()
            result={"mode":"tarot","draw_id":key,"reading":asdict(reading),"interpretation":answer,"evidence":evidence_for(reading)}
            if payload.get("save_history"):
                profile=text_field(payload,"profile",limit=128)
                result["history_key"]=FortuneStore(self.cache_path.parent/"fortune.sqlite3").save_reading(profile,"tarot",result)
            return result

        if mode == "chat-clear":
            identifier=text_field(payload,"session_id",limit=100)
            return self.conversations.clear(identifier)
        if mode == "chat":
            message=text_field(payload,"message")
            if not message:
                raise ValueError("请输入消息")
            profile=text_field(payload,"profile","reader-01",128)
            zone=text_field(payload,"timezone","Asia/Shanghai",100)
            use_saved=False
            confirmation=text_field(payload,'profile_confirmation',limit=64)
            if confirmation:
                saved=FortuneStore(self.cache_path.parent/'fortune.sqlite3').get_profile(profile)
                if not secrets.compare_digest(confirmation,profile_token(saved)):raise ValueError('档案资料已修改，请重新确认后使用')
                use_saved=True
                zone=saved['timezone']
            daily_draw(profile,zone)  # Validate settings before a model request.
            identifier=text_field(payload,"session_id",limit=100)
            session=self.conversations.get(identifier) if identifier else None
            client,model=self.get_model_client()
            if session is None:
                try:session=self.conversations.get()
                except Exception:
                    close=getattr(client,"close",None)
                    if close:close()
                    raise
            if not session.lock.acquire(blocking=False):
                close=getattr(client,"close",None)
                if close:close()
                raise ValueError("当前对话正在处理，请稍候")
            try:
                self.request_progress("正在核对对话资料",session.id)
                agent=UnifiedAgent(client,model,self.cache_path,self.daily_lock)
                try:
                    result=agent.turn(session,message,profile,zone,use_saved_profile=use_saved)
                except (ValueError,RequestCancelled):
                    raise
                except Exception:
                    reply="本次模型请求未完成。已保留当前对话和已有计算结果，可以说‘重试解读’；不会因此重新抽牌或起卦。"
                    session.messages.extend([{"role":"user","content":message},{"role":"assistant","content":reply}])
                    result={"session_id":session.id,"reply":reply,"status":"failed",
                            "method":session.slots.get("method","none"),"trace":[],
                            "result":dict(session.artifact.data) if session.artifact else None,
                            "turns":len(session.messages)//2}
                if result.get("result"):
                    result["result"]={key:value for key,value in result["result"].items() if key!="profile_key"}
                return result
            finally:
                session.lock.release()
                close=getattr(client,"close",None)
                if close:close()

        if mode == "iching":
            reference = payload.get("reference")
            if reference is not None:
                if interpret or payload.get("lines") is not None:
                    raise ValueError("参考库查阅不能同时起卦或解读")
                return {"mode": mode, "reference": reference_hexagram(reference)}
            lines = payload.get("lines")
            retry_id=text_field(payload,'retry_job_id',limit=100)
            if retry_id:
                previous=self.request_jobs.get(retry_id)
                if previous.payload.get('mode')!='iching' or not previous.preview or not previous.done.is_set():raise ValueError('无法复用此卦象')
                old=previous.preview['cast']
                result=build_cast(old['lines_bottom_to_top'],old['coins_bottom_to_top'])
            else:result = cast_coins() if lines is None else build_cast(lines)
            policy = text_field(payload, "policy", "moving-count-v1", 40)
            selection = select_passages(result, policy)
            interpreted = None
            self.request_progress("卦象已计算，正在准备解读",preview={"mode":"iching","cast":asdict(result),"selection":selection,"evidence":selection["passages"]})
            if interpret:
                question = text_field(payload, "question")
                if not question:
                    raise ValueError("解读需要一个具体问题")
                client, model = self.get_model_client()
                interpreted = interpret_cast(result, question, client, model, policy, style)
            return {"mode": mode, "cast": asdict(result), "selection": selection,
                    "interpretation": interpreted["interpretation"] if interpreted else None,
                    "analysis": interpreted["analysis"] if interpreted else None,
                    "evidence": selection["passages"]}

        if mode == "tarot":
            question = text_field(payload, "question")
            spread = text_field(payload, "spread", "single", 20)
            picks = payload.get("picks")
            if picks is not None:
                if not isinstance(picks, list) or any(type(item) is not int for item in picks):
                    raise ValueError("选牌位置必须是整数列表")
                picks = tuple(picks)
            retry_id=text_field(payload,'retry_job_id',limit=100)
            if retry_id:
                from .tarot import Reading,DrawnCard,DECK
                previous=self.request_jobs.get(retry_id)
                if previous.payload.get('mode')!='tarot' or not previous.preview or not previous.done.is_set():raise ValueError('无法复用此牌面')
                data=previous.preview['reading'];deck={card.id:card for card in DECK}
                reading=Reading(data['question'],data['spread'],tuple(DrawnCard(c['position'],deck[c['card']['id']],c['reversed']) for c in data['cards']))
            else:reading = draw_reading(question, spread, picks)
            self.request_progress("牌面已固定，正在准备解读",preview={"mode":"tarot","reading":asdict(reading),"evidence":evidence_for(reading)})
            if interpret:
                client, model = self.get_model_client()
                result = TarotAgent(client, model, draw=lambda *_: reading).read(question, spread, style=style)
                return {"mode": mode, **asdict(result)}
            return {"mode": mode, "reading": asdict(reading), "interpretation": None,
                    "evidence": evidence_for(reading)}

        if mode == "daily":
            profile = text_field(payload, "profile", limit=128)
            zone = text_field(payload, "timezone", "Asia/Shanghai", 100)
            instant = datetime.now(timezone.utc)
            draw = daily_draw(profile, zone, instant)
            if not interpret:
                result = get_daily(profile, zone, at=instant)
                return {"mode": mode, **asdict(result), "evidence": evidence_for(result.reading)}
            # Prevent simultaneous browser requests from billing two first reads.
            with self.daily_lock:
                store = DailyStore(self.cache_path)
                if store.get(draw) is not None:
                    result = get_daily(profile, zone, store=store, at=instant)
                else:
                    client, model = self.get_model_client()
                    result = get_daily(profile, zone, store=store, client=client,
                                       model=model, style=style, at=instant)
                return {"mode": mode, **asdict(result)}

        if mode == "bazi":
            birth = text_field(payload, "birth", limit=60)
            pillars = text_field(payload, "pillars", limit=60)
            if bool(birth) == bool(pillars):
                raise ValueError("请提供出生时间或四柱之一，不能同时提供")
            chart = parse_bazi_pillars(pillars) if pillars else calculate_bazi(birth)
            daily=payload.get("daily_bazi",False)
            if not isinstance(daily,bool):raise ValueError("daily_bazi 必须为布尔值")
            reference = text_field(payload,"date",limit=10)
            reference = date.fromisoformat(reference) if reference else None
            gender = text_field(payload,"gender","",10) or None
            complete = comprehensive_analysis(chart,gender,reference)
            daily_context=daily_bazi_context(chart,reference) if daily else None
            question = text_field(payload, "question", "请说明排盘和所提供的依据。")
            if interpret and not question:
                raise ValueError("解读问题不能为空")
            answer = None
            self.request_progress("命盘已计算，正在准备解读",preview={"mode":"bazi","chart":asdict(chart),"derived_facts":chart_facts(chart),"structural_analysis":analyze_structure(chart),"method_checklist":wealth_checklist(chart),"complete_analysis":complete,"evidence":bazi_evidence(chart)})
            if interpret:
                client, model = self.get_model_client()
                answer = interpret_bazi(chart, question, client, model,style=style,daily_context=daily_context,full_analysis=complete)
            return {"mode": mode, "chart": asdict(chart), "derived_facts": chart_facts(chart),
                    "method_checklist": wealth_checklist(chart),
                    "interpretation": answer, "evidence": bazi_evidence(chart),"daily_context":daily_context,
                    "structural_analysis":analyze_structure(chart), "complete_analysis":complete}
        raise ValueError("未知功能")


def make_server(port: int, cache_path: Path, bind: str = "127.0.0.1", external_port: int | None = None) -> ThreadingHTTPServer:
    if external_port is not None and (type(external_port) is not int or not 1 <= external_port <= 65535):
        raise ValueError("外部端口须为1–65535的整数")
    app = LocalApp(cache_path)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:
            # Do not log request bodies, questions, or birth information.
            pass

        def send(self, status: int, content: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(content)

        def json_response(self, status: int, data: dict) -> None:
            self.send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def local_request(self) -> bool:
            return self.headers.get("Host") in {
                f"{hostname}:{allowed_port}"
                for hostname in ("127.0.0.1", "localhost")
                for allowed_port in (self.server.server_port, external_port) if allowed_port is not None
            }

        def do_GET(self) -> None:
            if not self.local_request():
                self.json_response(403, {"error": "仅允许本机访问"})
            elif self.path == "/":
                page = files("fortune_agent").joinpath("static/index.html").read_text(encoding="utf-8")
                options = "".join(f'<option value="{e["number"]}">第{e["number"]}卦 · {escape(e["name"])}</option>'
                                  for e in sorted(iching_catalog()["hexagrams"],key=lambda e:e["number"]))
                page = page.replace("__ICHING_REFERENCE_OPTIONS__",options)
                self.send(200, page.replace("__REQUEST_TOKEN__", token).encode("utf-8"), "text/html; charset=utf-8")
            elif self.path.startswith("/assets/tarot/"):
                identifier=self.path[len("/assets/tarot/"):]
                import re
                from .tarot import DECK
                if not re.fullmatch(r"(?:major-\d{2}|[1-4]-\d{2})\.svg",identifier) or identifier[:-4] not in {card.id for card in DECK}:
                    self.json_response(404,{"error":"牌图不存在"})
                    return
                asset=files("fortune_agent").joinpath("static/tarot",identifier)
                self.send(200,asset.read_bytes(),"image/svg+xml; charset=utf-8")
            else:
                self.json_response(404, {"error": "页面不存在"})

        def do_POST(self) -> None:
            if not self.local_request() or not secrets.compare_digest(self.headers.get("X-Fortune-Token", ""), token):
                self.json_response(403, {"error": "请从本地页面提交请求"})
                return
            if self.path != "/api/run":
                self.json_response(404, {"error": "接口不存在"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4*1024*1024:
                    raise ValueError("请求为空或过大")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("请求应为 JSON 对象")
                self.json_response(200, app.run(payload))
            except (ValueError, UnicodeError) as exc:
                self.json_response(400, {"error": str(exc)})
            except RuntimeError as exc:
                self.json_response(422, {"error": str(exc)})
            except Exception:
                # Provider error bodies may contain confidential details.
                self.json_response(502, {"error": "模型请求或本地处理失败，请检查中转站配置和运行依赖。"})

    return ThreadingHTTPServer((bind, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="启动 Fortune Agent 本地网页")
    parser.add_argument("--bind",choices=("127.0.0.1","0.0.0.0"),default="127.0.0.1",help="容器内部可显式绑定0.0.0.0；默认仅回环")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--external-port",type=int,help="Docker映射的宿主机端口，仅允许该端口的localhost/127.0.0.1 Host")
    parser.add_argument("--cache", type=Path, default=Path("work/daily.sqlite3"))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口须为 1–65535")
    if args.external_port is not None and not 1 <= args.external_port <= 65535:
        parser.error("外部端口须为1–65535")
    with make_server(args.port, args.cache,args.bind,args.external_port) as server:
        print(f"本地网页：http://127.0.0.1:{args.port}（Ctrl+C 停止）", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
