"""Explicit lesson duration and storyboard validation; legacy clips stay readable."""
import math

VERSION = 'instructional-lesson-v1'
CONTRACT_VERSION = 'instructional-lesson-contract-v1'


def is_lesson(case):
    return case.get('lesson_version') == VERSION


def contract_version(case):
    return CONTRACT_VERSION if is_lesson(case) else 'strict-five-seconds-v5'


def duration_spec(case):
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
    if contract['version'] != CONTRACT_VERSION:
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
        end = finish
    if abs(end-contract['duration_seconds']) > 1e-6:
        raise ValueError('teaching timeline must match the full duration including initial/final holds')
    if covered!=expected:
        raise ValueError('timeline omits current task requirements: '+', '.join(sorted(expected-covered)))
    return rows
