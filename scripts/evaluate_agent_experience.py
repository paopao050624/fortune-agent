"""Small real-provider sample, with explicit synthetic data and mechanical limits."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
from threading import Lock

from fortune_agent.config import ApiConfig
from fortune_agent.fortune_store import FortuneStore
from fortune_agent.conversation import ConversationStore
from fortune_agent.unified_agent import UnifiedAgent,ROUTER_INSTRUCTIONS
from fortune_agent.question_focus import guidance_signature
import hashlib


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cases',type=Path,default=Path('evals/agent_experience_cases.json'));parser.add_argument('--workers',type=int,default=3);parser.add_argument('--output',type=Path,default=Path('evals/results/agent-experience-model-2026-10-06.jsonl'));args=parser.parse_args()
    from openai import OpenAI
    config=ApiConfig.from_env();cases=json.loads(args.cases.read_text())
    def evaluate(case):
        record={'case_id':case['id'],'synthetic':True,'model':config.model,'guidance_sha256':guidance_signature(),'router_sha256':hashlib.sha256(ROUTER_INSTRUCTIONS.encode()).hexdigest(),'case':case,'turns':[]}
        try:
            with tempfile.TemporaryDirectory() as temp,OpenAI(api_key=config.api_key,base_url=config.base_url,timeout=90,max_retries=0) as client:
                store=FortuneStore(Path(temp)/'fortune.sqlite3');store.save_profile('synthetic-profile','2000-01-01T12:00:00+08:00',gender='female',style='direct',chart_birth='2000-01-01T12:00:00+08:00',chart_timezone='Asia/Shanghai',latitude=31.23,longitude=121.47)
                agent=UnifiedAgent(client,config.model,Path(temp)/'daily.sqlite3',Lock());session=ConversationStore().get()
                for message in case['messages']:record['turns'].append(agent.turn(session,message,'synthetic-profile',use_saved_profile=case['profile_confirmed']))
                last=record['turns'][-1];checks={'method':last['method']==case['expected_method'],'status':last['status']==case['expected_status']}
                if case.get('stable_result') or case.get('changed_result'):
                    first=record['turns'][0].get('result') or {};end=last.get('result') or {}
                    field=case.get('stable_field','reading')
                    if case.get('stable_result'):checks['stable_result']=first.get(field)==end.get(field) and bool(end.get('followup'))
                    if case.get('changed_result'):checks['changed_result']=first.get(field)!=end.get(field)
                if case.get('expect_reply_terms'):checks['required_terms']=all(term in last['reply'] for term in case['expect_reply_terms'])
                if last.get('result',{}):
                    domain=last['result']
                    if domain.get('chart_result',{}).get('source_catalog_sha256'):checks['source_citations']='oldid=' in last['reply']
                if case.get('expected_status')=='needs_input':checks['no_artifact']=last.get('result') is None
                if case['id']=='confirmed-profile':checks['profile_birth']=last.get('result',{}).get('chart',{}).get('birth_time')=='2000-01-01T12:00:00+08:00'
                record['checks']=checks;record['status']='success';record['mechanical_pass']=all(checks.values())
        except Exception as exc:record['status']='failed';record['error_type']=type(exc).__name__;record['mechanical_pass']=False
        print(case['id']+': '+record['status']+'; checks='+str(record.get('checks',{})),flush=True)
        return record
    with ThreadPoolExecutor(max_workers=max(1,min(4,args.workers))) as pool:results=list(pool.map(evaluate,cases))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results))


if __name__=='__main__':main()
