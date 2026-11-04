"""Supplemental design-based engagement evidence; never part of the public score."""
import json

from eval.frame_extractor import frames_as_multimodal_content
from eval.judges.gpt55 import chat
from eval.rubric_6x6 import validate_result
from eval.benchmark_scoring import valid_score
from eval.judges.structured_rubric import judge

VERSION = 'teaching-engagement-v1'
RUBRIC = {'teaching_engagement': (
    ('task_relevance', 'The material inviting attention is directly relevant to the requested knowledge or action.'),
    ('attention_invitation', 'The learning target or visual situation offers an accessible reason to attend; a clear concise task can suffice without a joke, story or character.'),
    ('meaningful_progress', 'The requested progression, contrast or reveal gives the viewer a meaningful change to follow; appropriate initial and final holds are acceptable.'),
    ('perceptual_salience', 'Task-relevant differences or outcomes are noticeable without excessive visual competition.'),
    ('coherence', 'There are no distracting additions that compete with learning, and emphasis serves the task rather than decoration.'),
    ('audience_fit', 'The presentation invites attention in a way suitable for the specified audience and topic; serious or minimal presentation is not a defect.'),
)}

SYSTEM = """Rate observable instructional engagement design, not entertainment or measured enjoyment.
Return JSON only with exactly six criteria and a summary. Each criterion needs id,
applicable (boolean), score (1..5, null only when genuinely inapplicable),
evidence_frames (1-based indices) and a concrete finding. Scores >=3 need cited frames.
1=clear failure, 2=weak, 3=partial or uncertain, 4=good, 5=strong visible support.
Missing evidence is not high quality. Do not infer actual student interest, motivation,
understanding, learning gain, or audio from frames. Do not reward jokes, cartoons,
bright colors, movement quantity, prediction questions or stories merely for existing;
their absence is not a defect. A sober, simple, accurate diagram can score highly.
An optional technique is useful only if relevant and non-distracting. State uncertainty
when sampled frames cannot establish timing. This is a supplemental design observation,
not an independent measure of teaching effectiveness or a way to excuse factual errors."""


def score(case, frames):
    task = {key: case.get(key) for key in ('prompt_text', 'pedagogical_target_audience',
            'expected_concepts', 'expected_visual_elements', 'expected_narrative_order', 'target_duration_s', 'actual_duration_s', 'segment_evidence', 'delivery_pacing_evidence')}
    spec = '\n'.join(f'- {key}: {description}' for key, description in RUBRIC['teaching_engagement'])
    content = frames_as_multimodal_content(frames,
        f'Task: {json.dumps(task, ensure_ascii=False)}\nCriteria:\n{spec}\nFrames: 1..{len(frames)}')
    result = judge(chat, [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': content}],
                   [key for key, _ in RUBRIC['teaching_engagement']], len(frames),
                   lambda raw: validate_result('teaching_engagement', raw, len(frames), rubric=RUBRIC))
    result.pop('binary', None)
    return {**result, 'score': round((result['score']-1)*25, 4),
            'rubric_score_1_to_5': result['score'], 'rubric_version': VERSION,
            'valid': True, 'included_in_total': False, 'interpretation': 'observable_design_only'}


def aggregate(rows):
    values = [r.get('supplementary', {}).get('teaching_engagement', {}) for r in rows]
    valid = [v['score'] for v in values if v.get('valid') is True and valid_score(v.get('score'))]
    mean = round(sum(valid)/len(valid), 4) if valid else None
    return {'rubric_version': VERSION, 'included_in_total': False, 'n_total': len(rows),
            'n_valid': len(valid), 'n_missing_or_failed': len(rows)-len(valid),
            'mean_complete_only': mean if len(valid) == len(rows) and rows else None,
            'diagnostic_mean_available_only': mean, 'interpretation': 'observable_design_only'}
