"""Freeze a balanced ten-case lesson validation set before any model outcomes."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# Deliberate representative selection, not a random or statistically representative sample.
IDS=['math_exp_02','phys_exp_02','math_prob_01','grade_ComputerScience_task_17',
     'phys_exp_03','math_prob_02','cs_prob_02','med_exp_01','lang_high_01','math_high_02']


def select(rows):
    by_id={r['id']:r for r in rows}
    cases=[by_id[cid] for cid in IDS]
    durations=collections.Counter(c['target_duration_s'] for c in cases)
    kinds=collections.Counter(c['task_type'] for c in cases)
    if durations!={60:4,120:3,180:3} or kinds!={'explanation':5,'problem_solving':5}:
        raise ValueError('validation set must retain predeclared timing and task-type coverage')
    for duration in durations:
        if {c['task_type'] for c in cases if c['target_duration_s']==duration}!={'explanation','problem_solving'}:
            raise ValueError('each duration must include both explanation and solution')
    if not {'simple','standard','advanced'}<={c['lesson_profile']['difficulty_group'] for c in cases}:
        raise ValueError('difficulty coverage is incomplete')
    return cases


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'data/prompts/candidate_400_lessons_v2.jsonl')
    p.add_argument('--out',type=Path,default=ROOT/'data/prompts/lesson_validation_10_v2.jsonl')
    a=p.parse_args()
    rows=[json.loads(x) for x in a.source.read_text().splitlines() if x.strip()]
    cases=select(rows)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in cases))
    manifest={'selection':'predeclared representative coverage; not a random sample or a ranking',
        'source':str(a.source.relative_to(ROOT)) if a.source.is_relative_to(ROOT) else str(a.source),
        'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),
        'task_type_counts':dict(collections.Counter(c['task_type'] for c in cases)),
        'duration_counts':dict(collections.Counter(c['target_duration_s'] for c in cases)),
        'cases':[{'id':c['id'],'task_type':c['task_type'],'difficulty':c['difficulty'],
                  'duration_s':c['target_duration_s'],'lesson_profile':c['lesson_profile']} for c in cases]}
    a.out.with_suffix('.selection.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('cases',)}))


if __name__=='__main__':main()
