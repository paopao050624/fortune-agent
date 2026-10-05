"""Local integrated daily report and profile commands."""
import argparse
from datetime import date
import json
from pathlib import Path

from .fortune_store import FortuneStore
from .fortune_daily import make_daily_report


def main():
    parser=argparse.ArgumentParser(description='每日运势、档案与历史回顾')
    parser.add_argument('action',choices=['save','report','history','review','export','delete'])
    parser.add_argument('--profile',required=True)
    parser.add_argument('--birth',default='')
    parser.add_argument('--pillars',default='')
    parser.add_argument('--gender',choices=['male','female'])
    parser.add_argument('--timezone',default='Asia/Shanghai')
    parser.add_argument('--date',type=date.fromisoformat)
    parser.add_argument('--store',type=Path,default=Path('work/fortune.sqlite3'))
    parser.add_argument('--key',help='回顾对应的日报key')
    parser.add_argument('--note',default='')
    parser.add_argument('--interpret',action='store_true')
    args=parser.parse_args()
    try:
        store=FortuneStore(args.store)
        if args.action=='save':result=store.save_profile(args.profile,args.birth,args.pillars,args.gender,args.timezone)
        elif args.action=='history':result=store.history(args.profile)
        elif args.action=='export':result=store.export(args.profile)
        elif args.action=='delete':store.delete(args.profile);result={'deleted':True}
        elif args.action=='review':store.review(args.profile,args.key,args.note);result={'saved':True}
        elif args.interpret:
            from .config import ApiConfig
            from openai import OpenAI
            config=ApiConfig.from_env()
            with OpenAI(api_key=config.api_key,base_url=config.base_url,timeout=60,max_retries=0) as client:
                result=make_daily_report(store,args.profile,args.date,client,config.model)
        else:result=make_daily_report(store,args.profile,args.date)
    except (ValueError,RuntimeError) as exc:parser.error(str(exc))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
