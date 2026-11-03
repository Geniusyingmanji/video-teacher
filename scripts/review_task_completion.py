"""Recheck actual batch videos without modifying historical scores or videos."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.frame_extractor import extract_frames
from eval.task_completion import review
from eval.judges.gpt55 import judge_config
from eval.run_benchmark_v2 import scoring_code_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--ids', nargs='*')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = {c['id']:c for c in map(json.loads, (args.run/'prompts.jsonl').read_text().splitlines())}
    for cid, case in cases.items():
        if args.ids and cid not in args.ids:
            continue
        final = json.loads((args.run/f'final_{cid}.json').read_text())
        video = final['entry'].get('video_path')
        row = {'id':cid, 'judge':judge_config(), 'code_sha256':scoring_code_sha256()}
        if video:
            row['video_sha256'] = hashlib.sha256(Path(video).read_bytes()).hexdigest()
            row['review'] = review(case, extract_frames(video, sample_fps=3, resize_max=854))
        else:
            row['review'] = {'valid':False, 'passed':False, 'error':'no accepted video'}
        (args.out/f'{cid}.json').write_text(json.dumps(row, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
