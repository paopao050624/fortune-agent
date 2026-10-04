"""Save fixed-cast evaluations with resumable model/prompt/source validation."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .config import ApiConfig
from .iching import build_cast
from .iching_agent import INSTRUCTIONS, interpret_cast
from .iching_reading import reference_sha256, select_passages


def main():
    parser = argparse.ArgumentParser(description="固定周易案例真实 API 评估")
    parser.add_argument("--cases",type=Path,default=Path("evals/iching_cases.json"))
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--timeout",type=float,default=90)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if len({case["id"] for case in cases})!=len(cases):
        parser.error("重复案例 ID")
    if not 0<args.timeout<=300:
        parser.error("超时须为 0–300 秒")
    config = ApiConfig.from_env()
    from openai import OpenAI, APIError
    client = OpenAI(api_key=config.api_key,base_url=config.base_url,timeout=args.timeout,max_retries=0)
    prompt_hash=hashlib.sha256(INSTRUCTIONS.encode()).hexdigest()
    completed=set()
    if args.resume:
        for line in args.output.read_text(encoding="utf-8").splitlines():
            record=json.loads(line)
            case=next((c for c in cases if c["id"]==record["case_id"]),None)
            if (case is None or record["case_id"] in completed or record["case"]!=case
                or record["model"]!=config.model or record["prompt_sha256"]!=prompt_hash
                or record["reference_sha256"]!=reference_sha256()
                or record["selection"]!=select_passages(build_cast(case["lines"]),case["policy"])
                or record["cast"]!=json.loads(json.dumps(asdict(build_cast(case["lines"]))))) :
                parser.error("续跑与原配置不一致，请新建结果文件")
            completed.add(record["case_id"])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("a" if args.resume else "x",encoding="utf-8") as stream:
        for case in cases:
            if case["id"] in completed: continue
            cast=build_cast(case["lines"])
            try:
                result=interpret_cast(cast,case["question"],client,config.model,case["policy"])
            except (APIError,RuntimeError) as exc:
                parser.exit(1,f"{case['id']}: {type(exc).__name__}，已完成结果保留，可续跑。\n")
            record={"case_id":case["id"],"case":case,"model":config.model,"prompt_sha256":prompt_hash,
                    "reference_sha256":reference_sha256(),"cast":asdict(cast),
                    "evaluated_at_utc":datetime.now(timezone.utc).isoformat(),**result}
            stream.write(json.dumps(record,ensure_ascii=False)+"\n");stream.flush()
            print(f"{case['id']}: 引用 ID 与完整输出通过校验",flush=True)


if __name__ == "__main__":
    main()
