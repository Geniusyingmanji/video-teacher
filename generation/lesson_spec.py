"""Explicit lesson duration and storyboard validation; legacy clips stay readable."""
import math

VERSION = 'instructional-lesson-v2'
CONTRACT_VERSION = 'instructional-lesson-contract-v2'
LESSON_CONTRACTS = ('instructional-lesson-contract-v1', CONTRACT_VERSION)


def is_lesson(case):
    return case.get('lesson_version') in ('instructional-lesson-v1',VERSION)


def contract_version(case):
    return CONTRACT_VERSION if case.get('lesson_version')==VERSION else 'instructional-lesson-contract-v1' if is_lesson(case) else 'strict-five-seconds-v5'


def single_scene_outline(case):
    """Lossless structural adapter; creative teaching is planned in the storyboard.

    The vendor requires a sections array, but all chapters share one scene.
    Do not ask a language model to discard extra sections or silently keep only
    its first introduction. Pass every current obligation into the storyboard.
    """
    from generation.task_requirements import requirements
    obligations=requirements(case)
    return {'topic':case['id'],'target_audience':case.get('pedagogical_target_audience','general'),
            'sections':[{'id':'section_1','title':case.get('subdomain') or case.get('discipline') or 'Teaching lesson',
                         'content':'\n'.join(f'{row["id"]}: {row["text"]}' for row in obligations),
                         'example':'Preserve the original givens and answer constraints. Plan the full lesson, verification and recap in this one continuous scene.'}]}


def duration_spec(case):
    if case.get('lesson_version')==VERSION and case.get('audio_narration_required') is not True:
        raise ValueError('current narrated lessons require explicit spoken narration')
    duration = case.get('target_duration_s', 120 if is_lesson(case) else 5)
    fps = 15
    if type(duration) not in (int, float) or not math.isfinite(duration):
        raise ValueError('duration must be a finite number')
    if is_lesson(case):
        if not 30 <= duration <= 180:
            raise ValueError('lesson duration must be 30..180 seconds')
    elif duration != 5:
        raise ValueError('non-five-second tasks require an explicit lesson version')
    frames = round(duration * fps)
    if abs(frames / fps - duration) > 1e-8:
        raise ValueError('duration must be representable as complete frames')
    return {'duration_seconds': duration, 'fps': fps, 'frame_count': frames}


def validate_timeline(plan, contract):
    """A continuous authored timeline, with evidence targets for each chapter."""
    if contract['version'] not in LESSON_CONTRACTS:
        return []
    rows = plan.get('teaching_timeline')
    minimum=max(3,math.ceil(contract['duration_seconds']/20))
    if not isinstance(rows, list) or not minimum <= len(rows) <= 18:
        raise ValueError(f'lesson needs {minimum}..18 teaching chapters for this duration')
    end = 0
    ids = set()
    goals=set();evidence=set();covered=set()
    from generation.task_requirements import requirements
    expected={r['id'] for r in requirements(contract['task'])}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'] or row['id'] in ids:
            raise ValueError('teaching chapters need unique IDs')
        ids.add(row['id'])
        start, finish = row.get('start_s'), row.get('end_s')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,finish)):
            raise ValueError('chapter times must be finite numbers')
        if abs(start-end) > 1e-6 or not 3 <= finish-start <= 30:
            raise ValueError('chapters must cover the timeline continuously in 3..30 second segments')
        for field in ('goal','visible_evidence'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError('chapter needs a goal and inspectable evidence')
        goal=' '.join(row['goal'].lower().split());visible=' '.join(row['visible_evidence'].lower().split())
        if goal in goals or visible in evidence:
            raise ValueError('chapters must have distinct goals and visible evidence, not repeated filler')
        goals.add(goal);evidence.add(visible)
        obligations=row.get('requirement_ids')
        if not isinstance(obligations,list) or not obligations or any(not isinstance(key,str) or key not in expected for key in obligations):
            raise ValueError('each chapter must map to current task requirement IDs')
        covered.update(obligations)
        if contract['task'].get('audio_narration_required') is True:
            narration=row.get('narration')
            if not isinstance(narration,str) or not narration.strip():
                raise ValueError('every chapter needs a spoken explanation, not only captions')
        end = finish
    if abs(end-contract['duration_seconds']) > 1e-6:
        raise ValueError('teaching timeline must match the full duration including initial/final holds')
    if covered!=expected:
        raise ValueError('timeline omits current task requirements: '+', '.join(sorted(expected-covered)))
    return rows
