"""Pilot task-specific visual verification using enlarged final-video evidence.

These checks inspect final pixels and public task requirements. They never read
the generator's code or state. This small adapter library is not a universal verifier.
"""
from __future__ import annotations

import base64
import io
import json
import copy
from pathlib import Path

from PIL import Image

from .evidence import image_content, source_evidence
from .common import write_json


def normalize_absence_observation(raw):
    result=copy.deepcopy(raw)
    if not isinstance(result,dict):return result
    for check in result.get('checks',[]):
        if (isinstance(check,dict) and check.get('verdict')=='fail' and check.get('failure_type')=='missing_visual'
                and not check.get('observed_positions_or_counts') and isinstance(check.get('reason'),str) and check['reason'].strip()):
            check['observed_positions_or_counts']=check['reason']
            check['schema_normalization']='missing-object observation copied verbatim from the existing absence reason; no score or verdict changed'
    return result


def checks_for(case):
    text=case['prompt_text'].lower()
    if case.get('source',{}).get('source_image_path') and 'shade' in text.split('\n')[0]:
        return [{'id':'source_curve_preservation',
                 'question':'Compare the original S00 plot with the final upper reference viewport. Are the original curves, axes, ticks and labels preserved? Added background shading is authorized; erased or displaced boundaries, labels or axes are not. Do not demand text replacement for a shading task. Describe actual curve and axis positions.',
                 'review_last_frame':True,
                 'affected':['task_completeness.givens','visual_teaching.correspondence']},
                {'id':'source_inequality_region_coverage',
                 'question':'Read the public inequality and inspect the ENTIRE visible x-domain in the original and final plots, including negative x when visible. Identify every interval where the requested upper boundary lies above the lower boundary. Does the final shaded area include all such visible intervals and stay vertically between the required curves? A correct caption or narrated solution does not prove that a region is shaded. Report separately which left/negative and right/positive regions are actually colored, missing, or incorrectly colored. Do not restrict the task to positive x unless the PUBLIC prompt says so. Missing part of the required shading is missing_visual; shade outside the stated bounds is incorrect_relation. An unshaded source plot with correct lower-panel text is still missing the requested edit.',
                 'review_last_frame':True,
                 'affected':['task_completeness.coverage','task_completeness.result','visual_teaching.representation','crossmodal_alignment.agreement']}]
    if 'convex lens' in text and 'parallel' in text:
        return [{'id':'parallel_incidence_and_shared_focus',
                 'question':'Trace each of the requested three rays across the lens plane in the FINAL visible construction. Before the lens, all three must remain parallel to the principal axis. At/through the lens, the off-axis rays change direction; after it, they meet the axial ray at one common focal point F to the right on the principal axis. Rays already sloping toward F before reaching the lens are an incorrect relation even if the caption says parallel rays. An upright line/rectangle may be a thin-lens schematic; do not require photorealistic lens curvature. Distinguish the initial setup from the completed construction and report the actual ray segments.',
                 'review_last_frame':True,
                 'affected':['conceptual_correctness.reasoning','task_completeness.coverage','visual_teaching.representation']}]
    if case.get('source',{}).get('source_image_path'):
        return [{'id':'source_preservation_and_target_edit',
                 'question':'Compare S00 with the upper reference viewport across time. Trace every diagram line CONTINUOUSLY, especially near replaced labels: a white erasure gap in a previously continuous line is an unauthorized geometry change. Confirm the original labels and exact target replacements on the SAME objects. Correct lower-panel answers do not fulfill requested source edits. An unchanged target label is missing_visual; a wrong replacement or erased unrelated line is incorrect_relation. Report the concrete positions of labels and any line gap, not a generic preservation claim.',
                 'affected':['task_completeness.givens','task_completeness.result','visual_teaching.correspondence']},
                {'id':'source_measurement_grounding',
                 'question':'Read the ORIGINAL source image independently. For each length/quantity label, locate the exact object or endpoints it measures and its orientation. In particular, a whole-span dimension arrow must not be described as a single subsegment, and a shared horizontal side must not be described as vertical. Compare these source facts with the actual screen explanations. Report concrete label/object correspondences before judging any contradiction. Do not add facts or tasks not visible in the source.',
                 'affected':['conceptual_correctness.facts','conceptual_correctness.notation','crossmodal_alignment.agreement']}]
    if 'triangle' in text and '180' in text:
        return [{'id':'shared_vertex_straight_angle',
                 'question':'In the final rearrangement, do the ORIGINAL three interior angle pieces share ONE common vertex and tile a straight angle (one semicircle)? Separate triangles merely placed along a line do not satisfy this relationship. Inspect actual angle vertices rather than the true theorem written in captions.',
                 'affected':['conceptual_correctness.reasoning','task_completeness.result','visual_teaching.representation','crossmodal_alignment.agreement']}]
    if 'binary search' in text:
        return [{'id':'array_trace_consistency',
                 'question':'Do shown midpoint indices, array values, comparison results, and bounds match the actual supplied array/target? A successful equality must stop the search. Check each visible comparison, not only a correct final answer.',
                 'affected':['conceptual_correctness.reasoning','conceptual_correctness.notation','task_completeness.result']}]
    if 'electron' in text and 'neutral na' in text and 'neutral cl' in text:
        return [{'id':'electron_charge_bookkeeping',
                 'question':'Does one electron move from Na to Cl, with unchanged proton counts, ending in Na+ with 10 electrons and Cl- with 18 electrons? Check signs, labels and visible electron counts; a general caption about attraction is insufficient.',
                 'affected':['conceptual_correctness.facts','conceptual_correctness.notation','visual_teaching.correspondence']}]
    if 'punnett' in text:
        return [{'id':'punnett_cell_bookkeeping',
                 'question':'Check the parental genotypes in the public question against the actual visible gamete headers and four offspring cells. Does each cell combine its row and column gamete correctly, and does the stated homozygous-recessive fraction equal the visible count divided by four? Uppercase/lowercase distinctions must be readable. A narrated fraction without the requested square is a missing visual.',
                 'affected':['conceptual_correctness.reasoning','conceptual_correctness.notation','visual_teaching.correspondence']}]
    if 'find x such that' in text:
        return [{'id':'equation_equivalent_steps',
                 'question':'Read the equation supplied in the public task. Do the visible operations apply equally to BOTH sides, preserve equality at every displayed step, and end in a value that satisfies the original equation? Verify the actual numbers and symbols rather than accepting the written claim that a step is balanced.',
                 'affected':['conceptual_correctness.reasoning','conceptual_correctness.notation','task_completeness.result']}]
    if 'chronology question' in text and 'timeline' in text:
        return [{'id':'timeline_event_order',
                 'question':'Are all requested historical events visibly connected to appropriate dates or approximate periods and ordered chronologically on the timeline? The Industrial Revolution began gradually in eighteenth-century Britain; an approximate date is acceptable, a falsely exact universal start is not. Do not require proportional date spacing unless the timeline claims a quantitative scale. A list without the requested timeline is a missing visual.',
                 'affected':['conceptual_correctness.facts','conceptual_correctness.reasoning','visual_teaching.correspondence']}]
    return []


def final_color_crop(image):
    """Locate colored source-plot ink in the known upper reference viewport."""
    import numpy as np
    w,h=image.size;pixels=np.asarray(image.convert('RGB')).astype(int)
    colored=(pixels.max(axis=2)-pixels.min(axis=2))>35
    colored[:round(h*.1)]=False;colored[round(h*.73):]=False
    ys,xs=np.where(colored)
    if len(xs)<30:return [0,round(h*.1),w,round(h*.73)]
    pad=32
    return [max(0,int(xs.min())-pad),max(round(h*.1),int(ys.min())-pad),
            min(w,int(xs.max())+pad+1),min(round(h*.73),int(ys.max())+pad+1)]


def verify(client,case,packet,out=None,localized_source_observations=False,final_focused_source=False,max_output_tokens=1700):
    questions=checks_for(case)
    if not questions:return {'status':'no_specialized_adapter','checks':[]}
    if final_focused_source and not any(q['id']=='source_inequality_region_coverage' for q in questions):
        raise ValueError('final-focused source review is limited to shading tasks')
    frames=packet['frames'];n=len(frames)
    picked=[frames[-1]] if final_focused_source else [frames[round(i*(n-1)/5)] for i in range(6)]
    required_last={q['id']:frames[-1]['id'] for q in questions if q.get('review_last_frame')}
    content=[{'type':'text','text':json.dumps({'public_task':case['prompt_text'],'checks':questions},ensure_ascii=False)+'''
    Answer each check from actual pixels. Return JSON {checks:[{id,verdict:"pass"|"fail"|"unverified",
    failure_type:"incorrect_relation"|"missing_visual"|"unreadable_notation"|null,
    evidence_ids:[...],reason,observed_positions_or_counts}]}.
Each crop is part of its named frame, not a separate event. A true written theorem does not validate
an incorrect diagram. Locate/count actual objects and relationships. A missing requested visual
demonstration is fail if the frames show only text; inability to observe it is unverified.
  Use missing_visual when the diagram is absent, incorrect_relation when a shown diagram is wrong,
  and unreadable_notation when missing/garbled glyphs obscure a label rather than contradict a fact.
Do not infer a shared coordinate simply because a caption says 'same point'.'''}]
    allowed=set()
    if final_focused_source:
        content.append({'type':'text','text':'This experiment checks the completed construction in the final frame only. Compare it with the original source. Do not claim to certify intermediate frames or smooth motion.'})
    source,source_content=source_evidence(case)
    if source:
        content.extend(source_content)
        allowed.add(source['id'])
    focus=None
    if source and localized_source_observations:
        from .source_changes import verify_changed_regions
        focus=verify_changed_regions(client,case,packet)
        observations=[{'evidence_ids':c.get('evidence_ids'),
                       'observed_positions_or_counts':c.get('observed_positions_or_counts')} for c in focus['checks']]
        content.append({'type':'text','text':'A separate reading of automatically localized before/after image changes reported the following visible positions. These are fallible observations, NOT correctness or completeness verdicts. Check them against actual frames. A preserved curve is not proof that every required region is shaded. Resolve conflicts explicitly.\n'+json.dumps(observations,ensure_ascii=False)})
    for frame in picked:
        content.extend(image_content(frame));allowed.add(frame['id'])
        # Fixed overlapping crops are independent of the generator's internal layout.
        im=Image.open(frame['path']).convert('RGB');w,h=im.size
        if final_focused_source:
            bbox=final_color_crop(im);crop=im.crop(bbox)
            crop=crop.resize((1200,round(crop.height*1200/crop.width)))
            buffer=io.BytesIO();crop.save(buffer,format='PNG')
            content.extend([{'type':'text','text':f"Color-ink extent crop from final frame {frame['id']}, bbox {bbox}. This is the actual final diagram, not an expected answer."},
                            {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()}}])
            if out:write_json(out/'final_focus_crop.json',{'frame_id':frame['id'],'bbox':bbox,'selection':'colored pixels within upper reference viewport, no generator metadata'})
            continue
        regions=[('left',.0,.7),('right',.3,1.)]
        if source:regions.append(('center',.32,.7))
        for label,left,right in regions:
            crop=im.crop((int(w*left),int(h*.15),int(w*right),int(h*.8)))
            crop=crop.resize((1008,round(crop.height*1008/crop.width)))
            buffer=io.BytesIO();crop.save(buffer,format='JPEG',quality=92)
            content.extend([{'type':'text','text':f"Enlarged {label} region of {frame['id']}; same frame at {frame['time_s']} seconds."},
                            {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode()}}])
    content.append({'type':'text','text':'Available frame IDs: '+', '.join(sorted(allowed))+'. Even an absence finding must cite the frames that visibly show only text. Never return an empty evidence_ids list for pass/fail.'})
    if required_last:
        content.append({'type':'text','text':'For these checks you MUST also inspect and cite the last supplied frame: '+json.dumps(required_last)+'. Describe its actual incident and outgoing ray segments in observed_positions_or_counts. Earlier correct setup frames do not prove a later complete diagram is correct. If the last frame is only a recap/title card, say so and judge relevant diagrams earlier; do not require every frame to include a diagram.'})
    messages=[{'role':'user','content':content}]
    raw=client.chat(messages,purpose='critical_visual_relation:'+case['id'],max_tokens=max_output_tokens)
    if out:write_json(out/'raw_verification_0.json',raw)
    raw=normalize_absence_observation(raw)
    expected={q['id']:q for q in questions}
    def valid_checks(value):
        checks=value.get('checks') if isinstance(value,dict) else None
        return (isinstance(checks,list) and len(checks)==len(expected)
                and all(isinstance(c,dict) for c in checks)
                and {c.get('id') for c in checks}==set(expected)
                and all(c.get('evidence_ids') and any(x.startswith('F') for x in c['evidence_ids']) and all(x in allowed for x in c['evidence_ids'])
                        and bool(c.get('observed_positions_or_counts')) and bool(c.get('reason'))
                        and c.get('verdict') in {'pass','fail','unverified'}
                        and (c['verdict']!='fail' or c.get('failure_type') in {'incorrect_relation','missing_visual','unreadable_notation'})
                        and (c['id'] not in required_last or required_last[c['id']] in c['evidence_ids'])
                        for c in checks))
    if not valid_checks(raw):
        messages.extend([{'role':'assistant','content':json.dumps(raw,ensure_ascii=False)},
                         {'role':'user','content':'Correct citations, failure_type and observations using these real frame IDs: '+', '.join(sorted(allowed))+'. Required last-frame citations: '+json.dumps(required_last)+'. observed_positions_or_counts must be NONEMPTY and identify concrete positions, counts or label/object correspondences. Text-only frames ARE evidence of missing_visual; a shown but wrong diagram is incorrect_relation. Return the complete checks JSON.'}])
        raw=client.chat(messages,purpose='critical_check_evidence_repair:'+case['id'],max_tokens=max_output_tokens)
        if out:write_json(out/'raw_verification_1.json',raw)
        raw=normalize_absence_observation(raw)
        if not valid_checks(raw):raise ValueError('invalid repaired check schema')
    checks=raw['checks']
    for check in checks:
        if check.get('verdict') not in {'pass','fail','unverified'}:raise ValueError('invalid verdict')
        if not check.get('evidence_ids') or any(x not in allowed for x in check['evidence_ids']):
            raise ValueError('critical check has unsupported frame citations')
        if check.get('verdict')=='fail' and check.get('failure_type') not in {'incorrect_relation','missing_visual','unreadable_notation'}:
            raise ValueError('failed check needs a precise failure type')
        affected={'missing_visual':['task_completeness.coverage','visual_teaching.representation'],
                  'unreadable_notation':['visual_quality.legibility','conceptual_correctness.notation']}
        check['affected']=affected.get(check.get('failure_type'),expected[check['id']]['affected'])
    if source and focus is None:
        from .source_changes import verify_changed_regions
        focus=verify_changed_regions(client,case,packet)
        checks.extend(focus['checks'])
    return {'status':'reviewed','checks':checks,'adapter_scope':('source_region_shading_final_focus_dev3'
            if final_focused_source else 'source_region_shading_localized_dev2'
            if localized_source_observations else 'source_region_shading_dev1'
            if any(q['id']=='source_inequality_region_coverage' for q in questions)
            else 'pilot_text_families_and_source_image_profile'),
            'changed_region_verification':focus}
