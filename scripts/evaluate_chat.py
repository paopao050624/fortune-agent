"""Real model conversations using only synthetic questions and birth data."""
import hashlib
import argparse
import json
from pathlib import Path
from threading import Lock

from fortune_agent.config import ApiConfig
from fortune_agent.conversation import ConversationStore
from fortune_agent.unified_agent import ROUTER_INSTRUCTIONS, UnifiedAgent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--cases",type=Path,default=Path("evals/chat_cases.json"))
    parser.add_argument("--output",type=Path,default=Path("evals/results/chat-2026-10-04.jsonl"))
    parser.add_argument("--timeout",type=float,default=120)
    args=parser.parse_args()
    if not 0<args.timeout<=300:parser.error("请求超时须为 0–300 秒")
    from openai import OpenAI,APIError
    config=ApiConfig.from_env()
    client=OpenAI(api_key=config.api_key,base_url=config.base_url,timeout=args.timeout,max_retries=0)
    cases=json.loads(args.cases.read_text())
    store=ConversationStore()
    agent=UnifiedAgent(client,config.model,Path("work/chat-eval-daily.sqlite3"),Lock())
    output=args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf-8") as stream:
        for case in cases:
            session=store.get()
            for index,message in enumerate(case["messages"],1):
                try:
                    result=agent.turn(session,message,profile="synthetic-chat-eval",zone="Asia/Shanghai")
                except (APIError,RuntimeError) as exc:
                    record={"case_id":case["id"],"turn":index,"message":message,"model":config.model,
                            "status":"failed","error_type":type(exc).__name__,
                            "agent_code_sha256":hashlib.sha256(Path("src/fortune_agent/unified_agent.py").read_bytes()).hexdigest()}
                    stream.write(json.dumps(record,ensure_ascii=False)+"\n");stream.flush()
                    print(f"{case['id']} turn {index}: failed ({type(exc).__name__}); later turns in this case skipped",flush=True)
                    break
                result.pop("session_id",None)
                if result.get("result"): result["result"].pop("profile_key",None)
                record={"case_id":case["id"],"turn":index,"message":message,"model":config.model,
                        "agent_code_sha256":hashlib.sha256(Path("src/fortune_agent/unified_agent.py").read_bytes()).hexdigest(),
                        "router_prompt_sha256":hashlib.sha256(ROUTER_INSTRUCTIONS.encode()).hexdigest(),**result}
                stream.write(json.dumps(record,ensure_ascii=False)+"\n");stream.flush()
                print(f"{case['id']} turn {index}: {result['status']} / {result['method']}",flush=True)
            store.clear(session.id)
    client.close()


if __name__=="__main__":main()
