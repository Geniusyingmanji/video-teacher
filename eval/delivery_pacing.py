"""Measured actual-track pauses and static/silent holds; no script-based evidence."""
import math
from numbers import Real
import subprocess
import cv2
import numpy as np

VERSION = 'delivery-pacing-v2-evidence-only'


def measure(frames, fps, transcript, path=None, ffmpeg='ffmpeg'):
    if not frames or not math.isfinite(fps) or fps <= 0 or transcript.get('valid') is not True:
        raise ValueError('decoded frames and verified actual speech are required')
    duration = len(frames) / fps
    intervals = []
    words = 0
    for segment in transcript.get('segments', []):
        entries = segment.get('words') or [segment]
        words += len(segment.get('words') or segment.get('text', '').split())
        for entry in entries:
            start, end = entry['start_s'], entry['end_s']
            if not all(isinstance(t, Real) and not isinstance(t, (bool, np.bool_)) and math.isfinite(t) for t in (start, end)) or end < start:
                raise ValueError('invalid actual speech timestamps')
            start, end = max(0., float(start)), min(duration, float(end))
            if end > start: intervals.append((start, end))
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]: merged[-1][1] = max(end, merged[-1][1])
        else: merged.append([start, end])
    gaps = []; end = 0.
    for start, finish in merged:
        if start > end: gaps.append((end, start))
        end = finish
    if end < duration: gaps.append((end, duration))
    still = []; start = None
    previous = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    for i, frame in enumerate(frames[1:], 1):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        duplicate = np.mean(cv2.absdiff(previous, gray))/255 < .002
        if duplicate and start is None: start = (i-1)/fps
        if not duplicate and start is not None: still.append((start, i/fps)); start = None
        previous = gray
    if start is not None: still.append((start, duration))
    holds = [(max(a,c), min(b,d)) for a,b in still for c,d in gaps if min(b,d)>max(a,c)]
    longest_gap = max((b-a for a,b in gaps), default=duration)
    longest_hold = max((b-a for a,b in holds), default=0.)
    speech_seconds = sum(b-a for a,b in merged)
    coverage = speech_seconds/duration
    wpm = words/max(speech_seconds, .001)*60
    failures = []
    if longest_hold > 4: failures.append('static_without_speech_over_4s')
    if longest_gap > 8: failures.append('speech_gap_over_8s')
    if coverage < .45: failures.append('sparse_actual_speech')
    if words and not 80 <= wpm <= 220: failures.append('speech_rate_outside_80_220_wpm')
    audio = {}
    if path is not None:
        result = subprocess.run([ffmpeg,'-v','error','-i',str(path),'-vn','-ac','1','-ar','16000',
                                 '-f','f32le','pipe:1'],capture_output=True,check=True,timeout=120)
        samples = np.frombuffer(result.stdout,dtype='<f4')
        if not samples.size or not np.isfinite(samples).all(): raise ValueError('invalid decoded audio samples')
        clipping = float(np.mean(np.abs(samples) >= .99))
        audio = {'clipped_fraction':clipping,'rms_dbfs':float(20*np.log10(max(1e-9,float(np.sqrt(np.mean(samples**2))))))}
        if clipping > .005: failures.append('audio_clipping')
        if audio['rms_dbfs'] < -40: failures.append('audio_too_quiet')
    return {'version':VERSION,'valid':True,'passed':None,'score':None,'review_required':bool(failures),
            'failures':failures,'speech_coverage':coverage,'speech_wpm':wpm,
            'longest_speech_gap_s':longest_gap,'longest_static_silent_hold_s':longest_hold,
            'static_silent_holds':holds,'speech_gaps':gaps,'audio_signal':audio,
            'policy':'diagnostic thresholds select evidence for review; no automatic point deductions',
            'meaning':'ASR timing and decoded signal diagnostics; not a direct listening quality judgment'}


def apply(scoring, report):
    """Attach measurements without treating diagnostic thresholds as quality scores."""
    return {**scoring, 'delivery_pacing_evidence': report,
            'delivery_pacing_review_required': report.get('valid') is not True or report.get('review_required', False)}
