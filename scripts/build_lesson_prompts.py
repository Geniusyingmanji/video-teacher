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


def lesson_duration(case, source):
    """Budget the requested teaching actions, rather than a difficulty-wide minute quota."""
    steps = len(case.get('expected_narrative_order') or [])
    concepts = len(case.get('expected_concepts') or [])
    visuals = len(case.get('expected_visual_elements') or [])
    seconds = 24 + 7 * min(steps, 10) + 3 * min(concepts, 8) + 2 * min(visuals, 8)
    if case.get('task_type') == 'problem_solving':
        seconds += 8  # Show and check intermediate states.
    if case.get('difficulty') == 'high' or case.get('difficulty_v0_1') == 'graduate':
        seconds += 10
    if source:
        seconds = min(seconds, 85)  # A bounded edit should not become a lecture.
    return min(150, max(30, 5 * round(seconds / 5)))


def revise(case, language='en-US'):
    if case.get('lesson_version'):
        raise ValueError('input must be original tasks, not an already revised lesson set')
    row = copy.deepcopy(case)
    source = needs_source(case)
    duration = lesson_duration(case, source)
    row['lesson_version'] = VERSION
    row['target_duration_s'] = duration
    row['audio_narration_required'] = True
    row['narration_language'] = language
    kind='worked_solution' if case.get('task_type')=='problem_solving' else 'knowledge_explanation'
    row['lesson_profile']={'kind':kind,
        'difficulty_group':'advanced' if case.get('difficulty')=='high' else 'simple' if case.get('difficulty') in ('low','k12') else 'standard',
        'duration_reason':'requested steps, concepts and visuals; bounded source edit' if source else 'requested steps, concepts and visuals'}
    row['revision_provenance'] = {
        'version': VERSION, 'original_case': copy.deepcopy(case),
        'original_case_sha256': hashlib.sha256(json.dumps(case,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
        'changes': ['task-sized duration', 'visible explanation and verification', 'paced chapters',
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
        + ('Provide clear Mandarin Chinese spoken explanation, retaining necessary English technical terms. ' if language=='zh-CN' else 'Provide clear English spoken explanation. ')
        + 'Synchronize spoken reasons with the demonstrated steps. Narration must cover the question, key reasoning, verification and recap. '
        'Music, tones or reading labels alone do not satisfy narration. Keep essential diagram labels readable.')
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
    row['discipline_specific_rubric'].append('Intelligible spoken explanations agree with the visible steps, correct quantities, reasoning and final answer')
    # Historical sampled-frame ranges are provenance, never a new timing specification.
    row.pop('narrative_beats', None)
    duration_spec(row)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'data/prompts/candidate_400.jsonl')
    p.add_argument('--out',type=Path,default=ROOT/'data/prompts/candidate_400_lessons_v3.jsonl')
    p.add_argument('--language',choices=['zh-CN','en-US'],default='en-US')
    a=p.parse_args()
    if a.source.resolve()==a.out.resolve():p.error('preserve original tasks; output must be a separate version')
    cases=[json.loads(x) for x in a.source.read_text().splitlines() if x.strip()]
    if len(cases)!=400 or len({c['id'] for c in cases})!=400:p.error('expected 400 unique original tasks')
    rows=[revise(c,a.language) for c in cases]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in rows))
    print(json.dumps({'total':len(rows),'duration_counts':dict(collections.Counter(c['target_duration_s'] for c in rows)),
                      'version':VERSION,'output':str(a.out)}))


if __name__=='__main__':main()
