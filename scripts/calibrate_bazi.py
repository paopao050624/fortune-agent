"""Train/holdout structural sanity audit, without inventing expert truth labels."""
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from fortune_agent.bazi import parse_bazi_pillars
from fortune_agent.bazi_judgment import load_judgment_rules,strength_estimate,judge_chart
from fortune_agent.bazi_structure import analyze_structure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cases',type=Path,default=Path('evals/bazi_calibration_cases.json'));parser.add_argument('--output',type=Path,default=Path('evals/results/bazi-calibration-2026-10-06.json'));args=parser.parse_args()
    cases=json.loads(args.cases.read_text());baseline=load_judgment_rules();candidates=[]
    for low,high in ((.38,.62),(.40,.60),(.42,.58),(.44,.56)):
        rules=deepcopy(baseline);rules['thresholds'].update(weak=low,strong=high);results=[]
        for case in cases:
            chart=parse_bazi_pillars(case['pillars']);strength=strength_estimate(chart,analyze_structure(chart),rules)
            results.append({'id':case['id'],'split':case['split'],'classification':strength['classification'],'ratio':strength['support_ratio'],'parameter_stability':strength['parameter_stability'],
                            'matches_structural_anchor':strength['classification']==case.get('structural_expectation') if case.get('structural_expectation') else None})
        candidates.append({'weak_threshold':low,'strong_threshold':high,'train_matches':sum(r['matches_structural_anchor'] is True for r in results if r['split']=='train'),
                           'holdout_matches':sum(r['matches_structural_anchor'] is True for r in results if r['split']=='holdout'),'results':results})
    audits=[]
    for case in cases:
        result=judge_chart(parse_bazi_pillars(case['pillars']));checks={}
        if case.get('requires_abstention'):checks['abstention']=result['strength']['decision_status']=='abstain_final' and result['useful_gods']['balance']['preferred']==[]
        if case.get('requires_special_review'):checks['special_guard']=bool(result['strength']['special_reviews']) and result['useful_gods']['balance']['preferred']==[]
        audits.append({'id':case['id'],'checks':checks,'passed':all(checks.values())})
    report={'method':'robustness-audit-v1','generated_utc':datetime.now(timezone.utc).isoformat(),'cases_sha256':hashlib.sha256(args.cases.read_bytes()).hexdigest(),
            'rules_sha256':hashlib.sha256(json.dumps(baseline,sort_keys=True).encode()).hexdigest(),'candidates':candidates,'policy_audits':audits,
            'decision':'保留既有0.42/0.58阈值；结构锚点不足以证明某个阈值更准确。不按合成标签优化命理结论。新增参数敏感时暂停扶抑取用的保守策略。',
            'expert_label_count':0,'limitations':'训练/留出均为工程合成结构锚点，不是独立专家或古籍判例真值；没有现实预测/命理准确率结论。'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['decision']);print('policy audits',all(a['passed'] for a in audits))


if __name__=='__main__':main()
