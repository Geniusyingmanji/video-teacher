"""One real Code2Video case using the local Qwen service; verify every section."""
import json
from pathlib import Path
import sys
import time
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Code2Video/src'))
sys.path.insert(0, str(ROOT.parents[1]))
from agent import TeachingVideoAgent, RunConfig
from gpt_request import request_local_token
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
    args = parser.parse_args()
    started = time.monotonic()
    source = ROOT.parents[1] / 'data/prompts/pilot_v0_1.jsonl'
    case = next(json.loads(row) for row in source.read_text().splitlines()
                if json.loads(row)['id'] == args.case_id)
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
    topic = topics[args.case_id] + LAYOUT_POLICY
    agent = TeachingVideoAgent(0, topic,
        folder=ROOT / f'Code2Video/src/CASES/VIDEOTEACHER-qwen38-{args.case_id}',
        cfg=RunConfig(api=request_local_token, use_feedback=False, use_assets=False,
            max_code_token_length=4096, max_fix_bug_tries=2, max_regenerate_tries=2))
    video = agent.GENERATE_VIDEO()
    result = dict(model='Qwen/Qwen3.8-27B', source_case_id=case['id'],
        topic=topic, use_feedback=False, use_assets=False,
        layout_policy_version='safe_areas_v1',
        elapsed_seconds=time.monotonic()-started, token_usage=agent.token_usage,
        token_usage_scope='parent planner/storyboard/coder calls; excludes worker repair calls',
        expected_sections=len(agent.sections), rendered_sections=len(agent.section_videos),
        video=video, output_dir=str(agent.output_dir))
    result['complete'] = bool(video and Path(video).is_file() and agent.sections
                              and len(agent.sections)==len(agent.section_videos))
    if result['complete'] and inspect_video is not None:
        audit_dir = ROOT / 'experiments' / 'layout_review' / args.case_id
        try:
            result['layout_review'] = inspect_video(Path(video), audit_dir, None)
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
    (ROOT / f'experiments/model_result_{args.case_id}.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    if not result['complete']:
        raise SystemExit(1)
