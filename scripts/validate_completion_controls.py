"""Contrast a known wrong/omitted answer video with the repaired same task."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from eval.task_completion import review
from eval.frame_extractor import extract_frames
from eval.run_benchmark_v2 import scoring_code_sha256
from eval.judges.gpt55 import judge_config


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--prompts',type=Path,required=True)
    p.add_argument('--case',required=True)
    p.add_argument('--negative',type=Path,required=True)
    p.add_argument('--positive',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    case=next(c for c in map(json.loads,a.prompts.read_text().splitlines()) if c['id']==a.case)
    rows=[]
    for name,path,expected in [('negative',a.negative,False),('positive',a.positive,True)]:
        result=review(case,extract_frames(path,sample_fps=3,resize_max=854))
        row={'control':name,'id':a.case,'expected_pass':expected,
             'expectation_matches':result['passed']==expected,'review':result,
             'video_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'code_sha256':scoring_code_sha256(),'judge':judge_config()}
        (a.out/f'{name}.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps(row),flush=True)
    raise SystemExit(0 if all(r['expectation_matches'] for r in rows) else 1)


if __name__=='__main__':main()
