"""One real Code2Video case using the local Qwen service; verify every section."""
import json
from pathlib import Path
import sys
import time
import argparse
import base64
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Code2Video/src'))
sys.path.insert(0, str(ROOT.parents[1]))
from agent import TeachingVideoAgent, RunConfig
import agent as agent_module
from gpt_request import request_local_token
from generation.strict_video_contract import (make_contract, contract_hash, ContractAPI,
                                              install_prompts, install_renderer, validate_regions, VERSION)
from generation.strict_manim import inspect_exact
from generation.lesson_spec import CONTRACT_VERSION, is_lesson, validate_timeline, single_scene_outline
from generation.source_geometry import resolve_source, needs_source as requires_source
try:
    from scripts.audit_generated_videos import inspect_video
except ImportError:
    inspect_video = None


# Spatial anchors are sent to the planner before it writes section code. This
# text-only run cannot use Code2Video's vision Critic, so final layout review is
# still required after rendering.
LAYOUT_POLICY = (
    " At 854x480: title in top 15%; margins 4%/5%; stable notes and diagram; "
    "one step at a time; remove old formulas; large labels; no overlaps."
)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case-id', default='math_exp_01')
    parser.add_argument('--prompts', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--strict-contract', '--strict-five-seconds', dest='strict_five_seconds', action='store_true')
    parser.add_argument('--attempt', type=int, default=0)
    parser.add_argument('--quality-feedback', type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    source = args.prompts or ROOT.parents[1] / 'data/prompts/pilot_v0_1.jsonl'
    case = next(json.loads(row) for row in source.read_text().splitlines()
                if json.loads(row)['id'] == args.case_id)
    lesson = is_lesson(case)
    if lesson and not args.strict_five_seconds:
        parser.error('versioned lessons require --strict-contract')
    topics = {
        'math_exp_01': 'Geometric meaning of the derivative: a point moving on y=x², its tangent line, and derivative as the slope of that tangent',
        'math_exp_02': 'Why the three interior angles of a triangle sum to 180 degrees',
        'math_prob_01': 'Solve 2x + 5 = 17 step by step with visual algebra',
        'math_prob_02': 'Differentiate f(x) = x^3 + 2x using the power rule',
        'phys_exp_02': 'How a convex lens focuses parallel light rays at its focal point',
        'phys_prob_01': 'A 2 kg block on a frictionless floor under a 10 N force: find acceleration using Newton second law',
        'chem_exp_01': 'Ionic bonding: sodium transfers an electron to chlorine to form NaCl',
        'chem_prob_02': 'Calculate the pH of a solution with hydrogen ion concentration 1e-3 mol/L',
    }
    topic = (case['prompt_text'] if args.prompts else topics[args.case_id]) + LAYOUT_POLICY
    if args.prompts:
        topic += ((' Use one continuous scene with paced teaching chapters.' if lesson else ' Use exactly one section for this short clip, with a compact Manim scene under 160 lines.')
                  + ' The entire video, including all animations and waits, must match the target duration.'
                  + ' Target audience: ' + str(case.get('pedagogical_target_audience', 'general'))
                  + '. Target duration in seconds: ' + str(case.get('target_duration_s', 5))
                  + '. Use English labels. Required concepts: '
                  + json.dumps(case.get('expected_concepts', []))
                  + '. Required visual sequence: ' + json.dumps(case.get('expected_narrative_order', [])))
        # The upstream helper uses the entire prompt as a directory component.
        agent_module.get_output_dir = lambda idx, knowledge_point, base_dir: Path(base_dir) / args.case_id
        agent_module.topic_to_safe_name = lambda topic: args.case_id
    api = request_local_token
    source_id = case.get('source', {}).get('source_id')
    source_image = resolve_source(case, ROOT.parents[1] / 'data/sources/grade/selected_assets/before') if args.strict_five_seconds else ROOT.parents[1] / f'data/sources/grade/selected_assets/before/grade_{source_id}.png'
    needs_image = requires_source(case) if args.strict_five_seconds else bool(args.prompts and ('supplied' in case['prompt_text'] or 'source image' in case['prompt_text']))
    if needs_image:
        if not source_image.is_file():
            raise FileNotFoundError(f'Required source image unavailable: {source_image}')
        asset_image = ROOT / 'Code2Video/src/assets/icon' / source_image.name
        asset_image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_image, asset_image)
        source_image = asset_image
        topic += f' Source image is available at {source_image}. Use ImageMobject with this absolute path to preserve the supplied diagram.'
        from openai import OpenAI
        import os
        image_url = 'data:image/png;base64,' + base64.b64encode(source_image.read_bytes()).decode()
        def api(prompt, max_tokens=10000):
            response = OpenAI(base_url=os.getenv('LOCAL_BASE_URL', 'http://127.0.0.1:8000/v1'),
                              api_key='local', timeout=600, max_retries=1).chat.completions.create(
                model='qwen3.8-27b', messages=[{'role': 'user', 'content': [
                    {'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': image_url}}]}],
                max_tokens=max_tokens, temperature=0.6,
                extra_body={'chat_template_kwargs': {'enable_thinking': False}})
            if response.choices[0].finish_reason == 'length':
                raise RuntimeError('Local model output truncated')
            return response, response.usage.model_dump() if response.usage else {}
    agent = TeachingVideoAgent(0, topic,
        folder=ROOT / ('Code2Video/src/CASES/' + ((args.out.parent.name + '-' + args.out.name) if args.out else 'VIDEOTEACHER') + f'-qwen38-{args.case_id}-attempt{args.attempt}'),
        cfg=RunConfig(api=api, use_feedback=False, use_assets=False,
            max_code_token_length=8192 if lesson else 4096, max_fix_bug_tries=2, max_regenerate_tries=2))
    if args.strict_five_seconds:
        needs_source = needs_image
        contract = make_contract(case, source_image if needs_source else None)
        if args.quality_feedback:
            contract['quality_feedback'] = json.loads(args.quality_feedback.read_text())
        contract_path = agent.output_dir / 'task_contract.json'
        contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2))
        install_prompts(agent_module, contract)
        agent.API = ContractAPI(contract, agent.output_dir)
        agent.scope_refine_fixer.request_gpt = agent.API
        # Worker reconstruction must receive the same callable.
        agent.cfg.api = agent.API
        install_renderer(agent_module, contract_path)
    source_validation = {'valid': False, 'finding': 'not planned'}
    generation_error = None
    narration_result = None
    failure_stage = None
    try:
        if args.strict_five_seconds:
            from generation.verified_assets import molecule_assets
            verified = molecule_assets(case, agent.output_dir / 'verified_assets')
            if verified:
                contract['verified_assets'] = verified
                contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2))
        if args.strict_five_seconds:
            if lesson:
                (agent.output_dir/'outline.json').write_text(json.dumps(single_scene_outline(case),ensure_ascii=False,indent=2))
            for attempt in range(3):
                outline = agent.generate_outline()
                if len(outline.sections) == 1:
                    break
                (agent.output_dir / 'outline.json').rename(agent.output_dir / f'outline_rejected_{attempt}.json')
            else:
                raise ValueError('Outline must have exactly one scene')
            for attempt in range(3):
                source_validation = {'valid': False, 'finding': 'current storyboard not yet validated'}
                agent.generate_storyboard()
                try:
                    if len(agent.sections) != 1:
                        raise ValueError('Storyboard must have exactly one scene')
                    timeline = validate_timeline(agent.enhanced_storyboard, contract)
                    if lesson:
                        contract['teaching_timeline'] = timeline
                        contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2))
                    validate_regions(agent.enhanced_storyboard.get('source_edit_regions', []), required=needs_source,
                                     source_size=contract.get('source_size_pixels'))
                    frozen = contract.get('quality_feedback', {}).get('frozen_source_edit_regions')
                    if frozen is not None and agent.enhanced_storyboard.get('source_edit_regions', []) != frozen:
                        raise ValueError('Quality repair changed frozen source target boxes')
                    if not needs_source and agent.enhanced_storyboard.get('source_edit_regions'):
                        raise ValueError('Standalone task must not reference source edit regions')
                    if needs_source:
                        from generation.source_plan import validate_plan, review_plan
                        validate_plan(agent.enhanced_storyboard, contract)
                        source_validation = review_plan(agent.API, agent.enhanced_storyboard, contract)
                        (agent.output_dir / f'source_plan_review_{attempt}.json').write_text(json.dumps(source_validation, indent=2))
                        if not source_validation['valid']:
                            raise ValueError(source_validation['finding'])
                    break
                except (ValueError, KeyError, TypeError) as exc:
                    source_validation = {'valid': False, 'finding': str(exc), 'attempt': attempt}
                    (agent.output_dir / f'source_plan_review_{attempt}.json').write_text(json.dumps(source_validation, indent=2))
                    contract['storyboard_repair'] = {'error': str(exc), 'instruction': 'Fix this plan using the original source and unchanged task. Do not reuse rejected regions.'}
                    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2))
                    (agent.output_dir / 'storyboard.json').rename(agent.output_dir / f'storyboard_rejected_{attempt}.json')
            else:
                raise ValueError('Storyboard validation exhausted: ' + source_validation['finding'])
        if args.strict_five_seconds and needs_source and not lesson:
            from generation.source_plan import compile_plan
            (agent.output_dir / 'section_1.py').write_text(compile_plan(agent.enhanced_storyboard, contract))
        video = agent.GENERATE_VIDEO()
        if video and case.get('audio_narration_required') is True:
            failure_stage='narration'
            from generation.narration import attach
            narrated,narration_result=attach(Path(video),contract,agent.output_dir/'narration',api=agent.API)
            video=str(narrated)
            failure_stage=None
    except Exception as exc:
        generation_error = f'{type(exc).__name__}: {exc}'
        video = None
    result = dict(model='Qwen/Qwen3.8-27B', source_case_id=case['id'],
        topic=topic, use_feedback=False, use_assets=False,
        layout_policy_version='safe_areas_v1',
        elapsed_seconds=time.monotonic()-started, token_usage=agent.token_usage,
        token_usage_scope='parent planner/storyboard/coder calls; excludes worker repair, narration rewrite, TTS and ASR',
        expected_sections=len(agent.sections), rendered_sections=len(agent.section_videos),
        video=video, output_dir=str(agent.output_dir))
    result['audio_narration_required']=case.get('audio_narration_required') is True
    result['narration']=narration_result
    result['complete'] = bool(video and Path(video).is_file() and agent.sections
                              and len(agent.sections)==len(agent.section_videos))
    if args.strict_five_seconds:
        result['contract_version'] = contract['version']
        result['contract_sha256'] = contract_hash(contract)
        diagnostics_path = agent.output_dir / 'strict_diagnostics.json'
        diagnostics = json.loads(diagnostics_path.read_text()) if diagnostics_path.exists() else {}
        result['timing'] = inspect_exact(Path(video),contract['duration_seconds'],contract['fps']) if video else diagnostics.get('timing', {'valid': False, 'reason': 'no rendered video'})
        result['target_duration_s'] = contract['duration_seconds']
        result['teaching_timeline'] = diagnostics.get('teaching_timeline')
        result['strict_diagnostics'] = diagnostics
        result['source_plan_validation'] = source_validation
        result['source_size_pixels'] = contract.get('source_size_pixels')
        result['verified_assets'] = contract.get('verified_assets')
        if not video and not diagnostics:
            result['failure_stage'] = 'storyboard' if contract.get('storyboard_repair') else 'planning_or_generation'
        if not video and diagnostics:
            result['failure_stage'] = ('source_preservation' if diagnostics.get('source_preservation', {}).get('valid') is False else 'layout' if diagnostics.get('layout', {}).get('valid') is False else 'render')
            if not generation_error:
                generation_error = 'Rejected render: ' + result['failure_stage']
        result['source_required'] = needs_source
        result['source_edit_regions'] = (getattr(agent, 'enhanced_storyboard', None) or {}).get('source_edit_regions')
        result['complete'] = (result['complete'] and result['timing']['valid'] and len(agent.sections) == 1
                              and diagnostics.get('layout', {'valid': True})['valid']
                              and (not needs_source or diagnostics.get('source_preservation', {}).get('valid') is True))
        result['semantic_review_status'] = 'pending_eight_axis_self_evaluation'
    if generation_error:
        result['error'] = generation_error
        if failure_stage:result['failure_stage']=failure_stage
    if result['complete'] and inspect_video is not None:
        audit_dir = ROOT / 'experiments' / 'layout_review' / args.case_id
        try:
            result['layout_review'] = inspect_video(Path(video), audit_dir, contract['duration_seconds'] if args.strict_five_seconds else None)
            result['layout_review']['meaning'] = (
                'Source-resolution frames and safe-area overlays require visual review; '
                'successful rendering is not a layout pass.'
            )
        except Exception as exc:
            result['layout_review'] = {'status': 'failed', 'reason': str(exc)}
    elif result['complete']:
        result['layout_review'] = {'status': 'unavailable', 'reason': 'OpenCV/Pillow audit dependencies missing'}
    else:
        result['layout_review'] = {'status': 'not_run_incomplete_video'}
    result_path = args.out / f'model_result_{args.case_id}.json' if args.out else ROOT / f'experiments/model_result_{args.case_id}.json'
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    if not result['complete']:
        raise SystemExit(1)
