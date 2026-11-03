"""Version all 400 tasks for paced teaching; preserve exact legacy obligations."""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generation.lesson_spec import VERSION, duration_spec
from generation.source_geometry import needs_source

TIME = re.compile(r'\b(?:five|5|ten|10)[ -]seconds?\b(?=\s+(?:teaching|educational|worked|comparison|video|clip|animation|demonstration|explanation)\b)', re.I)


def revise(case):
    if case.get('lesson_version'):
        raise ValueError('input must be original tasks, not an already revised lesson set')
    row = copy.deepcopy(case)
    source = needs_source(case)
    # Source edits are naturally narrower tasks; do not inflate them into a full lecture.
    duration = 60 if source or case.get('difficulty') in ('low','k12') else 120
    if not source and (case.get('difficulty') == 'high' or case.get('difficulty_v0_1') == 'graduate'):
        duration = 180
    row['lesson_version'] = VERSION
    row['target_duration_s'] = duration
    kind='worked_solution' if case.get('task_type')=='problem_solving' else 'knowledge_explanation'
    row['lesson_profile']={'kind':kind,
        'difficulty_group':'advanced' if case.get('difficulty')=='high' else 'simple' if case.get('difficulty') in ('low','k12') else 'standard',
        'duration_reason':'bounded source operation' if source else 'simple objective' if duration==60 else 'advanced objective' if duration==180 else 'standard lesson'}
    row['revision_provenance'] = {
        'version': VERSION, 'original_case': copy.deepcopy(case),
        'original_case_sha256': hashlib.sha256(json.dumps(case,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
        'changes': ['explicit duration', 'visible explanation and verification', 'paced chapters',
                    'source reference viewport with separate teaching panel' if source else 'sequential standalone teaching diagrams'],
    }
    # Only presentation timing changes; never restore possibly inconsistent historical prompts.
    prompt = TIME.sub(f'{duration}-second', case['prompt_text'])
    row['prompt_text'] = (prompt + f'\nCreate a {duration}-second paced teaching video for the stated audience. '
        'Keep the original question, givens, answer constraints and prohibitions. '
        'Introduce the question, demonstrate the requested steps with the original objects, '
        'visually explain why the key relationship or operation is valid, check the result, and recap. '
        'Show reasoning through diagrams, correspondences or transformations, with short readable captions. '
        'Do not add unrelated syllabus content, unsupported answers, decorative motion, repeated footage or empty holds. '
        + ('Display the complete supplied image as a fixed reference in the upper reference viewport; '
           'only the originally authorized target marks may change there. Put temporary explanations in the separate lower teaching panel. '
           'Restrictions against changing the supplied diagram continue to apply inside the reference viewport. '
           if source else '')
        + 'No audio is required; visible explanation must stand on its own.')
    teaching = ('For this worked solution, identify the givens and goal, show the strategy, justify each operation, '
                'preserve intermediate values and units, and verify the final answer against the original problem.'
                if kind=='worked_solution' else
                'For this knowledge explanation, make the concept or mechanism visible through the requested objects, '
                'show how the relationship works, distinguish a relevant misconception, and recap its meaning without adding unrelated topics.')
    row['prompt_text'] += '\n'+teaching
    for key, value in {
        'expected_visual_elements': 'Readable visual reasoning connected to the requested objects, not only answer labels',
        'expected_narrative_order': 'Explain the key step and visibly check the result before a concise recap',
        'discipline_specific_rubric': 'The requested reasoning is visible at natural playback speed, without filler or unsupported claims',
    }.items():
        row[key] = list(row.get(key) or []) + [value]
    row['discipline_specific_rubric'].append(teaching)
    # Historical sampled-frame ranges are provenance, never a new timing specification.
    row.pop('narrative_beats', None)
    duration_spec(row)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'data/prompts/candidate_400.jsonl')
    p.add_argument('--out',type=Path,default=ROOT/'data/prompts/candidate_400_lessons_v1.jsonl')
    a=p.parse_args()
    if a.source.resolve()==a.out.resolve():p.error('preserve original tasks; output must be a separate version')
    cases=[json.loads(x) for x in a.source.read_text().splitlines() if x.strip()]
    if len(cases)!=400 or len({c['id'] for c in cases})!=400:p.error('expected 400 unique original tasks')
    rows=[revise(c) for c in cases]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in rows))
    print(json.dumps({'total':len(rows),'duration_counts':dict(collections.Counter(c['target_duration_s'] for c in rows)),
                      'version':VERSION,'output':str(a.out)}))


if __name__=='__main__':main()
