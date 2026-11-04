"""Deliver an already rendered lesson with draft narration, preserving prior runs."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generation.narration import attach
from generation.strict_video_contract import ContractAPI, contract_hash
from generation.strict_manim import inspect_exact
from generation.quality_gate import assess
from scripts.run_qwen_multigpu import dump, SCORING_VERSION


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out=args.out.resolve();args.result=args.result.resolve()
    config=json.loads((args.out/'run_config.json').read_text())
    if config.get('generation_profile') != 'draft':raise ValueError('target run must be draft')
    old=json.loads(args.result.read_text());cid=old['source_case_id'];source=Path(old['output_dir'])
    contract=json.loads((source/'task_contract.json').read_text());contract['generation_profile']='draft'
    cases=[json.loads(line) for line in (args.out/'prompts.jsonl').read_text().splitlines() if line.strip()]
    case=next(case for case in cases if case['id']==cid)
    if case['prompt_text'] != contract['task']['prompt_text']:raise ValueError('task changed')
    original=source/f'{cid}.mp4'
    timing=inspect_exact(original,contract['duration_seconds'],contract['fps'])
    if not timing['valid']:raise ValueError('recovery requires a complete decoded video')
    target=args.out/'draft_artifacts'/cid;target.mkdir(parents=True,exist_ok=True)
    video=target/f'{cid}.mp4';shutil.copy2(original,video)
    diagnostics=json.loads((source/'strict_diagnostics.json').read_text())
    chapters=contract['teaching_timeline'];actual=diagnostics.get('teaching_timeline',{}).get('chapters',[])
    if len(actual)==len(chapters) and [r['id'] for r in actual]==[r['id'] for r in chapters]:
        starts=[0.]+[r['actual_start_s'] for r in actual[1:]]+[contract['duration_seconds']]
        if all(b>a for a,b in zip(starts,starts[1:])):
            chapters=[{**row,'start_s':starts[i],'end_s':starts[i+1]} for i,row in enumerate(chapters)]
    contract['teaching_timeline']=chapters
    dump(target/'task_contract.json',contract)
    narrated,narration=attach(video,contract,target/'narration',api=ContractAPI(contract,target))
    result=copy.deepcopy(old)
    for key in ('error','failure_stage','quality_gate','candidate_history'):
        result.pop(key,None)
    result.update(complete=True,video=str(narrated),narration=narration,generation_profile='draft',
        output_dir=str(target),contract_sha256=contract_hash(contract),
        timing=inspect_exact(narrated,contract['duration_seconds'],contract['fps']),
        reused_rendered_video=str(original),recovery_source_result=str(args.result),
        semantic_review_status='deferred_draft_delivery',delivery_warnings=narration.get('delivery_warnings',[]))
    if not result['timing']['valid']:raise ValueError('narrated video did not preserve frames')
    evaluation={'id':cid,'version':SCORING_VERSION,'status':'deferred',
                'scoring':{'valid':False,'strict_pass':False,'score':None},
                'errors':['Full quality evaluation deferred: generation-first draft delivery']}
    result['quality_gate']=assess(result,evaluation)
    directory=args.out/'attempt_0';directory.mkdir(exist_ok=True)
    dump(directory/f'model_result_{cid}.json',result)
    dump(directory/f'{cid}_evaluation.json',evaluation)
    print(json.dumps({'id':cid,'video':str(narrated),'generated':True,'quality_review':'deferred'},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
