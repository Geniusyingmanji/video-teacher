"""Frame-exact scene allocation from measured speech, independent of model timing."""
from __future__ import annotations

import math

from .scene import FPS


def allocate_frames(weights, total_frames, minimum, maximum):
    """Bounded proportional allocation with stable largest-remainder rounding."""
    n = len(weights)
    if not n or len(minimum) != n or len(maximum) != n:
        raise ValueError('timing arrays must have the same nonzero length')
    if any(type(w) not in (int, float) or not math.isfinite(w) or w <= 0 for w in weights):
        raise ValueError('scene timing weights must be positive and finite')
    if any(type(v) is not int or v < 0 for v in [total_frames, *minimum, *maximum]):
        raise ValueError('frame counts must be nonnegative integers')
    if any(lo > hi for lo, hi in zip(minimum, maximum)) or not sum(minimum) <= total_frames <= sum(maximum):
        raise ValueError('speech and scene bounds do not fit the target duration')
    values = [float(x) for x in minimum]
    remaining = total_frames - sum(minimum)
    active = {i for i in range(n) if maximum[i] > minimum[i]}
    while remaining > 1e-8 and active:
        denominator = sum(weights[i] for i in active)
        saturated = [i for i in sorted(active) if remaining * weights[i] / denominator >= maximum[i] - values[i]]
        if saturated:
            for i in saturated:
                remaining -= maximum[i] - values[i]
                values[i] = float(maximum[i])
                active.remove(i)
        else:
            for i in active:
                values[i] += remaining * weights[i] / denominator
            remaining = 0
    result = [math.floor(v) for v in values]
    order = sorted(range(n), key=lambda i: (-(values[i] - result[i]), i))
    for i in [i for i in order if result[i] < maximum[i]][:total_frames - sum(result)]:
        result[i] += 1
    if sum(result) != total_frames:
        raise ValueError('could not allocate exact target frames')
    return result


def normalize_plan_timing(plan, target_s):
    scenes = plan.get('scenes', [])
    weights = [s.get('duration_s') for s in scenes]
    if type(target_s) not in (int, float) or not math.isfinite(target_s) or target_s <= 0:
        raise ValueError('target duration must be positive and finite')
    frames = allocate_frames(weights, round(target_s * FPS), [4 * FPS] * len(scenes), [24 * FPS] * len(scenes))
    # Preserve the author's relative durations as the initial scheduling preference.
    for scene, count in zip(scenes, frames):
        scene.setdefault('authored_duration_s', scene['duration_s'])
        scene['duration_s'] = count / FPS
    plan['timing_normalization'] = {'target_s': target_s, 'authored_weights': weights,
                                  'normalized_frames': frames}
    return plan


def speech_frames(plan, spoken_seconds, pause_s=.25):
    scenes = plan['scenes']
    if len(scenes) != len(spoken_seconds) or any(not math.isfinite(x) or x <= 0 for x in spoken_seconds):
        raise ValueError('invalid measured speech durations')
    minimum = [max(4 * FPS, math.ceil((x + pause_s) * FPS)) for x in spoken_seconds]
    target = round(sum(s['duration_s'] for s in scenes) * FPS)
    weights = [s['duration_s'] for s in scenes]
    return allocate_frames(weights, target, minimum, [24 * FPS] * len(scenes))
