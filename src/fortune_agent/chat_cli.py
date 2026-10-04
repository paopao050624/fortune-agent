"""Interactive single-process conversation; history is held only in memory."""
import argparse
from pathlib import Path
from threading import Lock

from .config import ApiConfig
from .conversation import ConversationStore
from .unified_agent import UnifiedAgent


def main():
    parser=argparse.ArgumentParser(description="统一对话 Agent")
    parser.add_argument("--profile",default="reader-01")
    parser.add_argument("--timezone",default="Asia/Shanghai")
    parser.add_argument("--cache",type=Path,default=Path("work/daily.sqlite3"))
    args=parser.parse_args()
    config=ApiConfig.from_env()
    from openai import OpenAI,APIError
    client=OpenAI(api_key=config.api_key,base_url=config.base_url,timeout=90,max_retries=0)
    agent=UnifiedAgent(client,config.model,args.cache,Lock())
    store=ConversationStore()
    session=store.get()
    print("统一对话：塔罗、每日提示、八字、周易。/new 清除本次对话，/exit 退出。")
    try:
        while True:
            message=input("你：").strip()
            if message=="/exit":break
            if message=="/new":
                store.clear(session.id);session=store.get();print("已开启新对话。");continue
            if not message:continue
            try:
                result=agent.turn(session,message,args.profile,args.timezone)
                print(f"助手：{result['reply']}")
            except (ValueError,RuntimeError) as exc:
                print(f"暂未完成：{exc}")
            except APIError as exc:
                print(f"模型请求失败（{type(exc).__name__}），可以继续重试。")
    except (EOFError,KeyboardInterrupt):
        pass
    finally:
        store.clear(session.id)
        client.close()


if __name__=="__main__":main()
