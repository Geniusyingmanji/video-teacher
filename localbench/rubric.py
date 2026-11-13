"""Candidate ten-dimension protocol; calibrated results are not yet available."""
VERSION = 'localbench-ten-dimensions-dev14-integer-r4'

# Reporting hierarchy only. Existing seven-leaf teaching weights are preserved.
TEACHING_GROUPS = {
    'content': {'name': '内容', 'dimensions': ['conceptual_correctness', 'task_completeness']},
    'organization': {'name': '组织', 'dimensions': ['pedagogical_clarity', 'instructional_structure', 'audience_appropriateness']},
    'expression': {'name': '表达', 'dimensions': ['visual_teaching', 'crossmodal_alignment']},
}

# Each criterion belongs to one named dimension; applicability follows the task.
DIMENSIONS = {'visual_quality': {'group': 'video', 'name': '画面与文字呈现', 'requires': ['frames']},
 'temporal_consistency': {'group': 'video', 'name': '时间一致性', 'requires': ['dense_frames']},
 'audio_quality': {'group': 'video', 'name': '语音与音频质量', 'requires': ['audio']},
 'conceptual_correctness': {'group': 'teaching', 'name': '知识与解答正确性', 'requires': ['frames', 'transcript']},
 'task_completeness': {'group': 'teaching', 'name': '任务完成与内容覆盖', 'requires': ['frames', 'transcript']},
 'pedagogical_clarity': {'group': 'teaching', 'name': '解释与推理清晰度', 'requires': ['frames', 'transcript']},
 'instructional_structure': {'group': 'teaching', 'name': '教学组织与节奏', 'requires': ['frames', 'transcript']},
 'visual_teaching': {'group': 'teaching', 'name': '图示与教学辅助', 'requires': ['frames']},
 'audience_appropriateness': {'group': 'teaching', 'name': '受众适配', 'requires': ['frames', 'transcript']},
 'crossmodal_alignment': {'group': 'teaching', 'name': '音画文字配合', 'requires': ['frames', 'timed_transcript']}}

from .detailed_rubric import CRITERIA, ANCHORS, VISUAL_GUIDES
for _name, _criteria in CRITERIA.items():
    DIMENSIONS[_name]['criteria'] = _criteria
DIMENSIONS['visual_quality']['rating_guides'] = VISUAL_GUIDES
from .strict_anchors import ANCHOR_ROWS, CRITERION_DETAILS, OPTIONAL_CRITERIA
for _name,_rows in ANCHOR_ROWS.items():
    DIMENSIONS[_name]['behavior_anchors'] = {k:dict(zip(('major_defect','adequate','excellent_evidence'),v)) for k,v in _rows.items()}
    DIMENSIONS[_name]['optional_criteria'] = [k for k in DIMENSIONS[_name]['criteria'] if _name+'.'+k in OPTIONAL_CRITERIA]
    if _name in CRITERION_DETAILS:
        DIMENSIONS[_name]['criterion_details'] = CRITERION_DETAILS[_name]


def normalize_dimension_nesting(raw, allowed):
    """Flatten uniquely named dimension objects without inventing/changing scores."""
    if not isinstance(raw,dict) or not isinstance(raw.get('dimensions'),dict):
        return raw
    if set(raw['dimensions'])==set(allowed):
        return raw
    found={}
    def visit(value):
        if not isinstance(value,dict):return
        for key,item in value.items():
            if key in allowed and isinstance(item,dict) and 'criteria' in item:
                if key in found:raise ValueError('ambiguous duplicate nested dimension')
                found[key]={'criteria':item['criteria']}
            if key!='criteria':visit(item)
    visit(raw['dimensions'])
    if set(found)!=set(allowed):return raw
    return {**raw,'dimensions':found,
            'schema_normalization':'flattened unique named dimensions; criterion scores/reasons unchanged'}


def validate_scores(raw, evidence_ids, allowed_dimensions=None, observed_ids=None, strict=False, applicability=None):
    import copy
    import re
    allowed = list(allowed_dimensions or DIMENSIONS)
    raw=copy.deepcopy(normalize_dimension_nesting(raw,allowed))
    dimensions = raw.get('dimensions') if isinstance(raw,dict) else None
    if not isinstance(dimensions, dict) or set(dimensions) != set(allowed):
        raise ValueError('missing or unexpected dimensions')
    result = {}
    for name in allowed:
        value = dimensions[name]
        # Two unambiguous JSON representations occur in inexpensive providers.
        # Normalize only an exact criterion-key mapping; never rename criteria or scores.
        if isinstance(value,dict) and set(value)==set(DIMENSIONS[name]['criteria']):
            value={'criteria':value}
        criteria = value.get('criteria') if isinstance(value,dict) else None
        if not isinstance(criteria, dict) or set(criteria) != set(DIMENSIONS[name]['criteria']):
            raise ValueError(f'{name}: incorrect criteria')
        scores = []
        expansions={}
        for key, criterion in criteria.items():
            if not isinstance(criterion,dict):
                raise ValueError(f'{name}.{key}: expected a criterion object')
            status, score = criterion.get('status'), criterion.get('score')
            if status not in ({'observed','unverified','not_applicable'} if strict else {'observed','unverified'}):
                raise ValueError(f'{name}.{key}: invalid status')
            if applicability is not None:
                from .applicability import validate_rating
                validate_rating(name, key, status, applicability)
            if status in {'unverified','not_applicable'}:
                if score is not None:
                    raise ValueError('unverified evidence must not receive a number')
            elif (type(score) not in (int, float) or not 1 <= score <= 5
                  or (score != round(score) if strict else score*2 != round(score*2))):
                raise ValueError('observed scores must be integer levels 1..5' if strict else 'observed scores must be 1..5 in half-point increments')
            citations = criterion.get('evidence_ids')
            if isinstance(citations,list):
                expanded=[]
                for id_ in citations:
                    match=re.fullmatch(r'([FA])(\d{2,3})\s*[-–]\s*\1(\d{2,3})',id_) if isinstance(id_,str) else None
                    if match:
                        prefix,start,end=match[1],int(match[2]),int(match[3])
                        if len(match[2])!=len(match[3]) or not 0<=end-start<len(evidence_ids):
                            raise ValueError('invalid evidence range')
                        actual=[prefix+str(i).zfill(len(match[2])) for i in range(start,end+1)]
                        if not all(x in evidence_ids for x in actual):raise ValueError('evidence range includes an unavailable ID')
                        expanded.extend(actual);expansions[id_]=actual
                    else:expanded.append(id_)
                citations=expanded;criterion['evidence_ids']=citations
            if not isinstance(citations, list) or any(not isinstance(x,str) or x not in evidence_ids for x in citations):
                raise ValueError('fabricated evidence id')
            if status == 'observed' and not citations:
                raise ValueError('observed score requires evidence')
            if status == 'observed' and observed_ids is not None and not any(x in observed_ids for x in citations):
                raise ValueError('observed score requires actual generated-video/audio evidence, not only a source/reference')
            if not isinstance(criterion.get('reason'), str) or not criterion['reason'].strip():
                raise ValueError('criterion needs a reason')
            if strict:
                from .strict_anchors import validate_strict_item
                validate_strict_item(criterion,name,key)
            if status!='not_applicable':scores.append(score)
        result[name] = {**value, 'score': round((sum(scores)/len(scores)-1)*25, 3)
                        if scores and all(x is not None for x in scores) else None,
                        'applicable_criteria_count':len(scores)}
        if expansions:result[name]['evidence_range_expansions']=expansions
    return result


def aggregate_dimensions(dimensions):
    groups = {}
    for group in ('video', 'teaching'):
        values = [dimensions.get(k, {}).get('score') for k, d in DIMENSIONS.items() if d['group'] == group]
        groups[group] = sum(values)/len(values) if all(x is not None for x in values) else None
    parents = {}
    for name, definition in TEACHING_GROUPS.items():
        values = [dimensions.get(k, {}).get('score') for k in definition['dimensions']]
        parents[name] = {'name': definition['name'], 'score': sum(values)/len(values) if all(x is not None for x in values) else None,
                         'dimensions': definition['dimensions'], 'weight_within_teaching': len(values)/7}
    return {'groups': groups, 'teaching_groups': parents,
            'hierarchy_version': 'video-teaching-content-organization-expression-v1',
            'overall': sum(groups.values())/2 if all(x is not None for x in groups.values()) else None,
            'weights': {'video': .5, 'teaching': .5}, 'version': VERSION,
            'validation_status': 'development_protocol_not_human_calibrated'}
