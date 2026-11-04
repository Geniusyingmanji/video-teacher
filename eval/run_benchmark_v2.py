"""Two-category educational video benchmark, version 2x8-v4.

Run from repository root: python -m eval.run_benchmark_v2 --prompts P.jsonl
--manifest M.jsonl --out OUTPUT_DIR. Requires the existing Azure judge for the
six semantic axes. It never emits a publishable ranking for incomplete runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
from pathlib import Path

from eval import benchmark_operators as operators
from eval import benchmark_scoring as scoring
from eval.frame_extractor import extract_frames
from eval.rubric_6x6 import DIMENSIONS
from eval.benchmark_video_rubric import DIMENSIONS as VIDEO_DIMENSIONS
from eval.judges.gpt55 import judge_config
from eval import teaching_engagement
from eval import grounded_observations, task_completion, instructional_video
from eval.rubric_6x6 import RUBRIC_VERSION
from generation.lesson_spec import is_lesson, duration_spec
from eval import narration, delivery_pacing

MAX_JUDGE_FRAMES = 24


def scoring_code_sha256() -> str:
    root = Path(__file__).parent
    return hashlib.sha256(b"".join((root / name).read_bytes() for name in
                                    ("benchmark_scoring.py", "benchmark_operators.py", "frame_extractor.py",
                                     "benchmark_video_rubric.py", "rubric_6x6.py",
                                     "run_benchmark_v2.py", "teaching_engagement.py", "judges/gpt55.py",
                                     "judges/structured_rubric.py", "judges/structured_json.py", "grounded_observations.py", "task_completion.py", "numeric_evidence.py", "instructional_video.py",
                                     "narration.py", "delivery_pacing.py", "evidence_audit.py", "../generation/task_requirements.py", "../generation/lesson_spec.py"))).hexdigest()


def evaluation_config(sample_fps: float, frame_max_px: int) -> dict:
    return {"sample_fps": sample_fps, "frame_max_px": frame_max_px,
            "max_judge_frames": MAX_JUDGE_FRAMES, "judge": judge_config(),
            "instructional_video_version": instructional_video.VERSION,
            "teaching_rubric_version": RUBRIC_VERSION,
            "engagement_rubric_version": teaching_engagement.VERSION,
            "spoken_teaching":narration.asr_config(),
            "scoring_code_sha256": scoring_code_sha256()}


def read_jsonl(path: str | Path) -> list[dict]:
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                raise ValueError(f"{path}:{number}: expected nonempty id")
            rows.append(row)
    return rows


def unique_by_id(rows: list[dict], *, latest: bool = False) -> dict[str, dict]:
    out = {}
    for row in rows:
        if row["id"] in out and not latest:
            raise ValueError(f"duplicate prompt ID: {row['id']}")
        out[row["id"]] = row
    return out


def _semantic_score(raw: dict) -> float:
    score = raw.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 1 <= score <= 5:
        raise ValueError("invalid 1..5 rubric score")
    return round((float(score) - 1) * 25, 4)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate(case: dict, manifest: dict, *, sample_fps: float = 2.0,
             frame_max_px: int = 832, ffmpeg: str = "ffmpeg", previous: dict | None = None) -> dict:
    result = {"id": case["id"], "axes": {}, "errors": [],
              "narration_required": case.get("audio_narration_required") is True,
              "video_path": manifest.get("video_path"), "version": scoring.VERSION,
              "case_sha256": hashlib.sha256(json.dumps(case, ensure_ascii=False, sort_keys=True,
                                                    separators=(",", ":")).encode("utf-8")).hexdigest(),
              "evaluation_config": evaluation_config(sample_fps, frame_max_px)}
    if manifest.get("status") != "ok" or not manifest.get("video_path"):
        result["errors"].append("generation_missing_or_failed")
        result["scoring"] = scoring.score_case({})
        return result
    path = str(manifest["video_path"])
    try:
        video = Path(path)
        if not video.is_file():
            raise FileNotFoundError(path)
        result["video_sha256"] = file_sha256(video)
        cached = previous if cache_matches(previous, case, manifest, sample_fps, frame_max_px) else {}
        frames, fps = operators.decode_video(path)
        result["source_fps"] = fps
        result["source_frame_count"] = len(frames)
        judged_case = {**case, 'actual_duration_s': len(frames)/fps}
        result['render_geometry'] = manifest.get('render_diagnostics', {}).get('layout', {})
        if is_lesson(case):
            target=duration_spec(case)
            result['duration_validation']={'valid':len(frames)==target['frame_count'] and abs(fps-target['fps'])<1e-6,
                                           **target,'actual_duration_s':len(frames)/fps}
        expected_steps = len(case.get("expected_narrative_order") or [])
        result["operators"] = {
            "signal_quality": operators.signal_quality(frames),
            "temporal_consistency": operators.temporal_consistency(frames, fps, expected_steps),
        }
        if result["narration_required"]:
            try:
                result["narration"] = operators.narration_presence(path, ffmpeg)
            except Exception as exc:
                result["narration"] = {"detected": None,
                                        "reason": f"audio_probe_failed: {type(exc).__name__}: {exc}"[:300]}
            try:
                if result['narration'].get('detected') is not True:
                    raise ValueError('actual speech track is absent or unverified')
                transcript=cached.get('speech_transcript') or narration.transcribe(path)
                result['speech_transcript']=transcript
                try:
                    result['delivery_pacing']=delivery_pacing.measure(frames, fps, transcript, path, ffmpeg)
                except Exception as exc:
                    result['delivery_pacing']={'valid':False,'error':f'{type(exc).__name__}: {exc}'[:600]}
                    result['errors'].append('delivery_pacing_measurement_failed')
                judged_case={**judged_case,'speech_transcript':transcript,
                    'delivery_pacing_evidence':result.get('delivery_pacing',{}),
                    'actual_spoken_segments':[{k:r[k] for k in ('id','start_s','end_s','text')} for r in transcript['segments']]}
            except Exception as exc:
                result['narration_review']={'valid':False,'passed':False,'score':None,'error':f'{type(exc).__name__}: {exc}'[:600]}
                result['errors'].append('speech_transcription_failed')
        else:
            result["narration"] = {"detected": None, "reason": "not_required"}
        sampled = extract_frames(path, sample_fps=sample_fps, resize_max=frame_max_px)
        if len(sampled) > MAX_JUDGE_FRAMES:
            selected = sorted({round(i * (len(sampled) - 1) / (MAX_JUDGE_FRAMES - 1))
                               for i in range(MAX_JUDGE_FRAMES)})
            result["judge_frame_indices_in_sample"] = selected
            sampled = [sampled[i] for i in selected]
        else:
            result["judge_frame_indices_in_sample"] = list(range(len(sampled)))
        result["sampled_frame_count"] = len(sampled)
        try:
            saved_presentation = cached.get('instructional_presentation',{})
            result['instructional_presentation'] = (saved_presentation if saved_presentation.get('valid') is True
                else instructional_video.assess_video(judged_case,path,resize_max=frame_max_px,previous=saved_presentation))
        except Exception as exc:
            result['instructional_presentation'] = {'valid':False,'passed':False,
                'version':instructional_video.VERSION,'error':f'{type(exc).__name__}: {exc}'[:600]}
            result['errors'].append('instructional_presentation_failed')
        if is_lesson(case):
            ledger=result['instructional_presentation'].get('segment_evidence')
            if ledger is not None:
                judged_case={**judged_case,'segment_evidence':ledger}
            if result['instructional_presentation'].get('all_windows_reviewed') is not True:
                result['errors'].append('lesson_segment_coverage_failed')
        if result['narration_required'] and result.get('speech_transcript',{}).get('valid') is True:
            try:
                saved=cached.get('narration_review',{})
                result['narration_review']=saved if saved.get('valid') is True else narration.review(
                    judged_case,result['speech_transcript'],result['instructional_presentation'].get('segment_evidence',[]))
            except Exception as exc:
                result['narration_review']={'valid':False,'passed':False,'score':None,'error':f'{type(exc).__name__}: {exc}'[:600]}
                result['errors'].append('spoken_teaching_failed')
        result['task_completion'] = cached.get('task_completion') or task_completion.review(judged_case, sampled)
        observations = cached.get('grounded_observations') or grounded_observations.observe(judged_case, sampled)
        observations = {**observations, 'task_completion': result['task_completion']}
        result['grounded_observations'] = observations
        judged_case = {**judged_case, 'grounded_observations': observations}
        for name, dimension in DIMENSIONS.items():
            try:
                saved = cached.get('axes', {}).get(name, {})
                if saved.get('score') is not None and not saved.get('error'):
                    result['axes'][name] = saved
                    continue
                judged = dimension.score(judged_case, sampled)
                result["axes"][name] = {**judged, "score": _semantic_score(judged),
                                         "rubric_score_1_to_5": judged["score"],
                                         "method": "evidence_backed_6x6_vlm_v2"}
            except Exception as exc:
                result["axes"][name] = {"error": f"{type(exc).__name__}: {exc}"[:400]}
                result["errors"].append(f"{name}_failed")
        for name, dimension in VIDEO_DIMENSIONS.items():
            try:
                saved = cached.get('axes', {}).get(name, {})
                if saved.get('score') is not None and not saved.get('error'):
                    result['axes'][name] = saved
                    continue
                judged = dimension.score(judged_case, sampled)
                if name == "signal_quality":
                    diagnostic = result["operators"][name]
                    if diagnostic["exposure_penalty_applicable"] and diagnostic["clipped_fraction_p90"] >= 0.95:
                        judged["score"] = min(judged["score"], 40.0)
                        judged["operator_cap"] = "near_blank_or_clipped_frames"
                result["axes"][name] = judged
            except Exception as exc:
                result["axes"][name] = {"error": f"{type(exc).__name__}: {exc}"[:400]}
                result["errors"].append(f"{name}_failed")
        result['consistency_review'] = grounded_observations.consistency(judged_case, observations, result['axes'], sampled)
        if not result['consistency_review']['valid']:
            for name in result['consistency_review']['conflicting_axes']:
                dimension = DIMENSIONS.get(name) or VIDEO_DIMENSIONS[name]
                revised_case = {**judged_case, 'consistency_correction': result['consistency_review']}
                revised = dimension.score(revised_case, sampled)
                if name in DIMENSIONS:
                    revised = {**revised, 'score': _semantic_score(revised), 'rubric_score_1_to_5': revised['score'], 'method':'evidence_backed_6x6_vlm_v2'}
                result['axes'][name] = revised
            result['consistency_review'] = grounded_observations.consistency(judged_case, observations, result['axes'], sampled)
            if not result['consistency_review']['valid']:
                result['errors'].append('unresolved_cross_axis_contradictions')
        try:
            saved = cached.get('supplementary', {}).get('teaching_engagement', {})
            result['supplementary'] = {'teaching_engagement': saved if saved.get('valid') is True
                                       else teaching_engagement.score(judged_case, sampled)}
        except Exception as exc:
            result['supplementary'] = {'teaching_engagement': {
                'valid': False, 'score': None, 'included_in_total': False,
                'rubric_version': teaching_engagement.VERSION,
                'error': f'{type(exc).__name__}: {exc}'[:400]}}
    except Exception as exc:
        result["errors"].append(f"evaluation_failed: {type(exc).__name__}: {exc}"[:400])
    signal = result.get('axes', {}).get('signal_quality', {})
    diagnostic = result.get('operators', {}).get('signal_quality', {})
    if (signal.get('score') is not None and diagnostic.get('exposure_penalty_applicable')
            and diagnostic.get('clipped_fraction_p90', 0) >= .95):
        signal['score'] = min(signal['score'],40.0)
        signal['operator_cap'] = 'near_blank_or_clipped_frames'
    from eval.evidence_audit import reconcile
    reconcile(result)
    flat = {name: value.get("score") for name, value in result["axes"].items()}
    freeze = result.get("operators", {}).get("temporal_consistency", {}).get(
        "longest_duplicate_run_seconds", 0.0)
    result["defects"] = scoring.evidence_defects(result["axes"],
                                                 expected_steps=len(case.get("expected_narrative_order") or []),
                                                 freeze_seconds=freeze,
                                                 completion_reviewed=result.get('task_completion', {}).get('valid') is True,
                                                 progression_verified=(result.get('grounded_observations', {}).get('visible_progression') is True
                                                   and result.get('grounded_observations', {}).get('completed_task') is True
                                                   and not result.get('grounded_observations', {}).get('uncertainties')
                                                   and result.get('consistency_review', {}).get('valid') is True
                                                   and result.get('task_completion', {}).get('passed') is True))
    result['defects'].extend(task_completion.defects(result.get('task_completion', {})))
    if is_lesson(case) and result.get('duration_validation',{}).get('valid') is not True:
        result['defects'].append({'axis':'temporal_consistency','axis_cap':40.,'overall_cap':40.,
                                 'reason':'lesson_duration_mismatch'})
    result["scoring"] = scoring.score_case(
        flat, narration_required=result["narration_required"],
        narration_detected=result.get("narration", {}).get("detected"),
        defects=result["defects"])
    if result.get('axes') and result.get('consistency_review', {}).get('valid') is not True:
        result['errors'].append('consistency_review_missing_or_failed')
    if any(error in result['errors'] for error in ('unresolved_cross_axis_contradictions','consistency_review_missing_or_failed')):
        result['scoring'] = {**result['scoring'], 'valid': False, 'strict_pass': False,
                             'score': None, 'groups': None, 'errors': ['unresolved_cross_axis_contradictions']}
    if result.get('task_completion', {}).get('valid') is not True and result.get('axes'):
        result['scoring'].update(valid=False, strict_pass=False, score=None, groups=None)
        result['errors'].append('task_completion_missing_or_invalid')
    elif result.get('task_completion', {}).get('passed') is not True:
        result['scoring']['strict_pass'] = False
        result['scoring'].setdefault('gates', []).append('task_completion_not_verified')
    result['scoring'] = instructional_video.apply(result['scoring'],result.get('instructional_presentation',{}))
    if result['narration_required']:
        result['scoring']=narration.apply(result['scoring'],result.get('narration_review',{}))
        result['scoring']=delivery_pacing.apply(result['scoring'],result.get('delivery_pacing',{}))
    if is_lesson(case) and result.get('instructional_presentation',{}).get('all_windows_reviewed') is not True:
        result['scoring'].update(valid=False,strict_pass=False,score=None,groups=None)
    return result


def evaluate_with_retry(case, manifest, **kwargs):
    """Retry an invalid judge once on the same video, reusing validated axes.

    A valid low score or observed task omission is never retried to fish for
    a pass. Generation failures need generation repair, not more judge calls.
    """
    result = evaluate(case, manifest, **kwargs)
    transient = any(error.endswith('_failed') or error.startswith('evaluation_failed:')
                    for error in result.get('errors', []))
    supplement_failed = result.get('supplementary', {}).get('teaching_engagement', {}).get('valid') is not True
    presentation_failed = ('instructional_presentation' in result and result['instructional_presentation'].get('valid') is not True)
    spoken_failed = (result.get('narration_required') is True and result.get('narration_review',{}).get('valid') is not True)
    if manifest.get('status') == 'ok' and (transient or supplement_failed or presentation_failed or spoken_failed):
        prior_errors = list(result.get('errors', []))
        kwargs['previous'] = result
        result = evaluate(case, manifest, **kwargs)
        result['evaluation_retry'] = {'attempts': 2, 'previous_errors': prior_errors,
                                      'same_video': True}
    return result


def bootstrap_ci(values: list[float], *, seed: int = 20261031,
                 iterations: int = 2000) -> list[float] | None:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values)
                   for _ in range(iterations))
    return [round(means[int(0.025 * iterations)], 4),
            round(means[min(iterations - 1, int(0.975 * iterations))], 4)]


def report(rows: list[dict], prompts: dict[str, dict]) -> dict:
    rep = scoring.aggregate(rows)
    spoken=[r for r in rows if prompts[r['id']].get('audio_narration_required') is True]
    rep['spoken_teaching']={'n_required':len(spoken),
        'n_transcribed':sum(r.get('speech_transcript',{}).get('valid') is True for r in spoken),
        'n_reviewed':sum(r.get('narration_review',{}).get('valid') is True for r in spoken),
        'n_passed':sum(r.get('narration_review',{}).get('passed') is True for r in spoken),
        'failed_ids':[r['id'] for r in spoken if r.get('narration_review',{}).get('passed') is not True]}
    rep['instructional_presentation'] = {
        'n_total':len(rows),
        'n_reviewed':sum(r.get('instructional_presentation',{}).get('valid') is True for r in rows),
        'n_passed':sum(r.get('instructional_presentation',{}).get('passed') is True for r in rows),
        'mean_valid_only':(sum(r['instructional_presentation']['score'] for r in rows if r.get('instructional_presentation',{}).get('valid') is True) /
            sum(r.get('instructional_presentation',{}).get('valid') is True for r in rows)) if any(r.get('instructional_presentation',{}).get('valid') is True for r in rows) else None}
    rep['task_completion'] = {
        'n_total': len(rows),
        'n_reviewed': sum(r.get('task_completion', {}).get('valid') is True for r in rows),
        'n_passed': sum(r.get('task_completion', {}).get('passed') is True for r in rows),
        'failed_ids': [r['id'] for r in rows if r.get('task_completion', {}).get('passed') is not True],
        'pass_rate_all_cases': sum(r.get('task_completion', {}).get('passed') is True for r in rows)/len(rows) if rows else None}
    rep['supplementary'] = {'teaching_engagement': teaching_engagement.aggregate(rows)}
    valid = [r for r in rows if r["scoring"]["valid"]]
    rep["bootstrap_95_ci_case_mean"] = (bootstrap_ci([r["scoring"]["score"] for r in valid])
                                         if rep["ranking_publishable"] else None)
    rep["bootstrap_seed"] = 20261031
    rep["bootstrap_iterations"] = 2000
    rep["strata"] = {}
    for field in ("discipline", "task_type", "difficulty", "audio_narration_required"):
        groups: dict[str, list[float]] = {}
        for row in valid:
            value = str(prompts[row["id"]].get(field, "unknown"))
            groups.setdefault(value, []).append(row["scoring"]["score"])
        rep["strata"][field] = {k: {"n": len(v), "mean_valid_only": round(sum(v)/len(v), 4)}
                                 for k, v in sorted(groups.items())}
    return rep


def cache_matches(previous: dict | None, case: dict, manifest: dict,
                  sample_fps: float, frame_max_px: int) -> bool:
    """Match provenance before reusing any independently validated dimension."""
    if not previous or previous.get("version") != scoring.VERSION:
        return False
    expected_case = hashlib.sha256(json.dumps(case, ensure_ascii=False, sort_keys=True,
                                              separators=(",", ":")).encode("utf-8")).hexdigest()
    if previous.get("case_sha256") != expected_case:
        return False
    if previous.get("evaluation_config") != evaluation_config(sample_fps, frame_max_px):
        return False
    video = Path(str(manifest.get("video_path") or ""))
    return (manifest.get("status") == "ok" and video.is_file()
            and previous.get("video_sha256") == file_sha256(video))


def reusable(previous: dict | None, case: dict, manifest: dict,
             sample_fps: float, frame_max_px: int) -> bool:
    return (cache_matches(previous, case, manifest, sample_fps, frame_max_px)
            and previous.get('scoring', {}).get('valid') is True
            and previous.get('supplementary', {}).get('teaching_engagement', {}).get('valid') is True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--frame-max-px", type=int, default=832)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--limit", type=int, default=0, help="Debug only; output is never ranking-publishable")
    parser.add_argument("--preflight", action="store_true", help="Validate inputs and local dependencies without calling the judge")
    args = parser.parse_args()
    if not math.isfinite(args.sample_fps) or args.sample_fps <= 0 or args.frame_max_px <= 0 or args.limit < 0:
        parser.error("invalid sampling or limit")
    try:
        config = evaluation_config(args.sample_fps, args.frame_max_px)
    except ValueError as exc:
        parser.error(str(exc))
    if config["judge"]["provider"] == "azure_cli" and shutil.which("az") is None:
        parser.error("Azure CLI 'az' is required; alternatively configure VIDEO_TEACHER_API_KEY, VIDEO_TEACHER_BASE_URL and VIDEO_TEACHER_MODEL")
    if args.ffmpeg == "ffmpeg" and shutil.which("ffmpeg") is None:
        try:
            import imageio_ffmpeg
            args.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    prompts = unique_by_id(read_jsonl(args.prompts))
    manifest = unique_by_id(read_jsonl(args.manifest), latest=True)
    ids = list(prompts)[:args.limit] if args.limit else list(prompts)
    if not ids:
        parser.error("prompt file contains no cases")
    if any(prompts[id].get("audio_narration_required") is True for id in ids) and not Path(args.ffmpeg).is_file() and shutil.which(args.ffmpeg) is None:
        parser.error("ffmpeg is required for narration checks")
    if args.preflight:
        unavailable = [id for id in ids if manifest.get(id, {}).get("status") != "ok"]
        missing = [id for id in ids if manifest.get(id, {}).get("status") == "ok"
                   and not Path(str(manifest[id].get("video_path") or "")).is_file()]
        print(json.dumps({"preflight": "ok" if not missing and not unavailable else "incomplete_inputs",
                          "n_cases": len(ids), "n_manifest_entries": len(manifest),
                          "missing_video_ids": missing, "unavailable_generation_ids": unavailable,
                          "judge": config["judge"]}, ensure_ascii=False))
        if missing or unavailable:
            parser.exit(2)
        return
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    per_case = out / "per_case.jsonl"
    previous = unique_by_id(read_jsonl(per_case), latest=True) if per_case.is_file() else {}
    rows = []
    # Persist each completed case, so interruption loses at most the active case.
    with per_case.open("a", encoding="utf-8") as f:
        for id in ids:
            item = manifest.get(id, {"id": id})
            row = previous.get(id)
            if not reusable(row, prompts[id], item, args.sample_fps, args.frame_max_px):
                row = evaluate(prompts[id], item, sample_fps=args.sample_fps,
                               frame_max_px=args.frame_max_px, ffmpeg=args.ffmpeg, previous=row)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
            rows.append(row)
    # Compact historical attempts after a successful traversal.
    per_case.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                        encoding="utf-8")
    aggregate = report(rows, prompts)
    if args.limit:
        aggregate["ranking_publishable"] = False
        aggregate["ranking_score"] = None
        aggregate["bootstrap_95_ci_case_mean"] = None
        aggregate["debug_subset"] = True
    aggregate["config"] = {**config,
                           "prompt_sha256": hashlib.sha256(Path(args.prompts).read_bytes()).hexdigest(),
                           "manifest_sha256": hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest(),
                           "scoring_code_sha256": config["scoring_code_sha256"]}
    (out / "aggregate.json").write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"n_total": aggregate["n_total"], "n_valid": aggregate["n_valid"],
                      "ranking_publishable": aggregate["ranking_publishable"],
                      "out": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
