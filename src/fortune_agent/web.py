"""Local browser interface, using the existing domain and interpretation code."""

from __future__ import annotations

import argparse
from html import escape
import json
import secrets
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from threading import Lock
from typing import Any

from .agent import TarotAgent
from .bazi import calculate_bazi, parse_bazi_pillars
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

    def model_client(self) -> tuple[Any, str]:
        config = ApiConfig.from_env()
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ValueError("请先安装模型依赖：pip install -e '.[agent,bazi]'") from exc
        return OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=60, max_retries=0), config.model

    def run(self, payload: dict) -> dict:
        mode = text_field(payload, "mode", limit=20)
        interpret = payload.get("interpret", False)
        if not isinstance(interpret, bool):
            raise ValueError("interpret 必须为布尔值")
        style = text_field(payload, "style", "gentle", 20)
        if style not in ("direct", "gentle"):
            raise ValueError("无效回答风格")

        if mode == "chat-clear":
            identifier=text_field(payload,"session_id",limit=100)
            return self.conversations.clear(identifier)
        if mode == "chat":
            message=text_field(payload,"message")
            if not message:
                raise ValueError("请输入消息")
            profile=text_field(payload,"profile","reader-01",128)
            zone=text_field(payload,"timezone","Asia/Shanghai",100)
            daily_draw(profile,zone)  # Validate settings before a model request.
            identifier=text_field(payload,"session_id",limit=100)
            session=self.conversations.get(identifier) if identifier else None
            client,model=self.model_client()
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
                agent=UnifiedAgent(client,model,self.cache_path,self.daily_lock)
                try:
                    result=agent.turn(session,message,profile,zone)
                except ValueError:
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
            result = cast_coins() if lines is None else build_cast(lines)
            policy = text_field(payload, "policy", "moving-count-v1", 40)
            selection = select_passages(result, policy)
            interpreted = None
            if interpret:
                question = text_field(payload, "question")
                if not question:
                    raise ValueError("解读需要一个具体问题")
                client, model = self.model_client()
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
            reading = draw_reading(question, spread, picks)
            if interpret:
                client, model = self.model_client()
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
                    client, model = self.model_client()
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
            daily_context=daily_bazi_context(chart) if daily else None
            question = text_field(payload, "question", "请说明排盘和所提供的依据。")
            if interpret and not question:
                raise ValueError("解读问题不能为空")
            answer = None
            if interpret:
                client, model = self.model_client()
                answer = interpret_bazi(chart, question, client, model,style=style,daily_context=daily_context)
            return {"mode": mode, "chart": asdict(chart), "derived_facts": chart_facts(chart),
                    "method_checklist": wealth_checklist(chart),
                    "interpretation": answer, "evidence": bazi_evidence(chart),"daily_context":daily_context,
                    "structural_analysis":analyze_structure(chart)}
        raise ValueError("未知功能")


def make_server(port: int, cache_path: Path) -> ThreadingHTTPServer:
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
                f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}",
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
                if not 0 < length <= 16384:
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

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="启动 Fortune Agent 本地网页")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cache", type=Path, default=Path("work/daily.sqlite3"))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口须为 1–65535")
    with make_server(args.port, args.cache) as server:
        print(f"本地网页：http://127.0.0.1:{args.port}（Ctrl+C 停止）", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
