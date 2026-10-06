"""Interactive single-process conversation; history is held only in memory."""
import argparse
from pathlib import Path
from threading import Lock

from .config import ApiConfig
from .conversation import ConversationStore
from .unified_agent import UnifiedAgent
from .fortune_store import FortuneStore


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
    use_profile=False
    try:saved=FortuneStore(args.cache.parent/'fortune.sqlite3').get_profile(args.profile)
    except ValueError:saved=None
    if saved:
        print("找到本机档案："+saved['id']+"；使用后会向中转站发送本次所需资料。")
        print("出生资料："+(saved.get('birth') or saved.get('pillars') or saved.get('chart_birth') or '未填写'))
        use_profile=input("本次允许复用此档案？输入 yes 确认，其余为不使用：").strip().lower()=='yes'
    print("统一对话：塔罗、每日提示、八字、周易、紫微本命盘、西方占星。/new 清除本次对话，/exit 退出。")
    try:
        while True:
            message=input("你：").strip()
            if message=="/exit":break
            if message=="/new":
                store.clear(session.id);session=store.get();print("已开启新对话。");continue
            if not message:continue
            try:
                result=agent.turn(session,message,args.profile,args.timezone,use_saved_profile=use_profile)
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
