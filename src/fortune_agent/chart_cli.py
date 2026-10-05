"""Natal Zi Wei and Western astrology command interface."""
import argparse
import json
from .ziwei import calculate_ziwei
from .astrology import calculate_astrology


def main():
    parser=argparse.ArgumentParser(description='紫微斗数／西方占星排盘')
    parser.add_argument('method',choices=['ziwei','astrology'])
    parser.add_argument('--birth',required=True,help='公历出生时间，必须含UTC偏移')
    parser.add_argument('--gender',choices=['male','female'])
    parser.add_argument('--timezone',default='Asia/Shanghai')
    parser.add_argument('--latitude',type=float)
    parser.add_argument('--longitude',type=float)
    parser.add_argument('--interpret',help='调用已配置中转站解释具体问题')
    args=parser.parse_args()
    try:
        result=calculate_ziwei(args.birth,args.gender) if args.method=='ziwei' else calculate_astrology(args.birth,args.timezone,args.latitude,args.longitude)
        if args.interpret:
            from .config import ApiConfig
            from .chart_agent import interpret_chart
            from openai import OpenAI
            config=ApiConfig.from_env()
            with OpenAI(api_key=config.api_key,base_url=config.base_url,timeout=60,max_retries=0) as client:
                result['interpretation']=interpret_chart(args.method,result,args.interpret,client,config.model)
    except (ValueError,RuntimeError) as exc:parser.error(str(exc))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
