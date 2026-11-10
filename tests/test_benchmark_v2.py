import tempfile
import unittest
import json
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from eval import benchmark_operators as op
from eval import benchmark_scoring as scoring
from eval import compare_benchmark_v2 as comparison
from eval import benchmark_video_rubric as video_rubric
from eval import run_benchmark_v2 as runner
from eval.judges import gpt55


class ScoringPolicyTests(unittest.TestCase):
    def test_process_local_judge_route_restores_parent_environment(self):
        with patch.dict(os.environ, {'VIDEO_TEACHER_BASE_URL': 'http://parent/v1'}), \
             patch.object(runner, 'reusable', return_value=False), \
             patch.object(runner, 'evaluate_with_retry', side_effect=lambda *a, **k: os.environ['VIDEO_TEACHER_BASE_URL']):
            self.assertEqual(runner.evaluate_job({}, {}, None, 2, 832, 'ffmpeg', 'http://worker/v1'),
                             'http://worker/v1')
            self.assertEqual(os.environ['VIDEO_TEACHER_BASE_URL'], 'http://parent/v1')

    def test_parallel_missing_videos_preserve_all_ids_and_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ['first', 'second', 'third', 'fourth']
            (root/'prompts.jsonl').write_text(''.join(json.dumps({'id': i})+'\n' for i in ids))
            (root/'manifest.jsonl').write_text(''.join(json.dumps({'id': i, 'status': 'failed'})+'\n' for i in ids))
            env = {**os.environ, 'VIDEO_TEACHER_API_KEY': 'local',
                   'VIDEO_TEACHER_MODEL': 'test-only', 'VIDEO_TEACHER_BASE_URL': 'http://127.0.0.1:1/v1'}
            subprocess.run([sys.executable, '-m', 'eval.run_benchmark_v2', '--prompts', str(root/'prompts.jsonl'),
                            '--manifest', str(root/'manifest.jsonl'), '--out', str(root/'out'), '--workers', '2'],
                           env=env, cwd=Path(__file__).parents[1], check=True, capture_output=True, timeout=60)
            rows = runner.read_jsonl(root/'out/per_case.jsonl')
            self.assertEqual([r['id'] for r in rows], ids)
            self.assertTrue(all(r['assessment_coverage']['total']['status'] == 'unavailable_video' for r in rows))
            aggregate = json.loads((root/'out/aggregate.json').read_text())
            self.assertEqual(aggregate['n_total'], 4)
            self.assertIsNone(aggregate['ranking_score'])

    def test_coverage_distinguishes_zero_failure_and_unavailable_video(self):
        row = {'axes': {'visual_quality': {'score': 0},
                         'signal_quality': {'error': 'judge offline'}},
               'scoring': {'valid': False, 'score': None},
               'task_completion': {'valid': True, 'coverage': .5},
               'narration_required': True}
        cells = runner.assessment_coverage(row)
        self.assertEqual(cells['visual_quality']['status'], 'scored')
        self.assertEqual(cells['visual_quality']['score'], 0)
        self.assertEqual(cells['task_completion']['score'], .5)
        self.assertIsNone(cells['signal_quality']['score'])
        self.assertEqual(cells['signal_quality']['reason'], 'judge offline')
        self.assertIn('spoken_teaching', cells)
        row['errors'] = ['generation_missing_or_failed']
        self.assertTrue(all(c['status'] == 'unavailable_video' and c['score'] is None
                            for c in runner.assessment_coverage(row).values()))

    def setUp(self):
        self.axes = {a: 80 for names in scoring.GROUPS.values() for a in names}

    def test_equal_categories_and_strict_gate(self):
        self.axes.update({a: 100 for a in scoring.VIDEO_AXES})
        self.axes.update({a: 60 for a in scoring.TEACHING_AXES})
        result = scoring.score_case(self.axes)
        self.assertEqual(result["score"], 80)
        self.assertFalse(result["strict_pass"])

    def test_missing_nan_bool_and_required_audio_invalidate(self):
        for bad in (None, float("nan"), True, -1, 101):
            axes = dict(self.axes, visual_quality=bad)
            self.assertFalse(scoring.score_case(axes)["valid"])
        audio_missing = scoring.score_case(self.axes, narration_required=True,
                                           narration_detected=False)
        self.assertTrue(audio_missing["valid"])
        self.assertEqual(audio_missing["score"], 40)
        self.assertFalse(audio_missing["strict_pass"])
        self.assertFalse(scoring.score_case(self.axes, narration_required=True,
                                            narration_detected=None)["valid"])

    def test_incomplete_run_has_no_ranking(self):
        valid = {"id": "a", "axes": {a: {"score": v} for a, v in self.axes.items()},
                 "scoring": scoring.score_case(self.axes)}
        invalid = {"id": "b", "axes": {}, "scoring": scoring.score_case({})}
        rep = scoring.aggregate([valid, invalid])
        self.assertIsNone(rep["ranking_score"])
        self.assertFalse(rep["ranking_publishable"])
        self.assertEqual(rep["n_failed"], 1)

    def test_visible_intrusion_and_wrong_text_cannot_average_away(self):
        axes = dict(self.axes)
        axes["visual_quality"] = 95
        axes["conceptual_correctness"] = 90
        results = {
            "visual_quality": {"criteria": [{"id": "artifact_control", "applicable": True,
                                               "score": 2, "evidence_frames": [2],
                                               "finding": "unrelated hand covers the diagram"}]},
            "conceptual_correctness": {"criteria": [{"id": "symbols", "applicable": True,
                                                       "score": 1, "evidence_frames": [3],
                                                       "finding": "equation mutates"}]},
        }
        defects = scoring.evidence_defects(results)
        scored = scoring.score_case(axes, defects=defects)
        self.assertEqual(len(defects), 2)
        self.assertEqual(scored["score"], 50)
        self.assertEqual(scored["axis_scores_after_caps"]["visual_quality"], 40)
        self.assertFalse(scored["strict_pass"])

    def test_freeze_gate_is_task_aware(self):
        self.assertEqual(scoring.evidence_defects({}, expected_steps=1,
                                                   freeze_seconds=2), [])
        defects = scoring.evidence_defects({}, expected_steps=4,
                                            freeze_seconds=2)
        self.assertEqual(defects[0]["reason"], "requested_multistep_action_frozen")

    def test_paired_comparison_requires_same_cases_and_version(self):
        left = [{"id": "a", "version": scoring.VERSION,
                 "case_sha256": "same", "evaluation_config": {"sample_fps": 2},
                 "scoring": {"valid": True, "score": 75}}]
        right = [{"id": "a", "version": scoring.VERSION,
                  "case_sha256": "same", "evaluation_config": {"sample_fps": 2},
                  "scoring": {"valid": True, "score": 70}}]
        result = comparison.compare(left, right, iterations=100, seed=1)
        self.assertEqual(result["mean_left_minus_right"], 5)
        self.assertIsNone(result["paired_bootstrap_95_ci"])
        with self.assertRaises(ValueError):
            comparison.compare(left, right + [{"id": "b", "version": scoring.VERSION,
                                               "scoring": {"valid": True, "score": 70}}])
        with self.assertRaises(ValueError):
            comparison.compare(left, [dict(right[0], version="obsolete")])
        with self.assertRaises(ValueError):
            comparison.compare(left, [dict(right[0], case_sha256="different")])


class OperatorTests(unittest.TestCase):
    def setUp(self):
        observer = patch.object(runner.grounded_observations, 'observe', return_value={
            'observations':[{'fact':'fixture frame', 'frames':[1]}],
            'visible_progression':True, 'completed_task':True, 'uncertainties':[]})
        reviewer = patch.object(runner.grounded_observations, 'consistency', return_value={
            'valid':True, 'conflicting_axes':[], 'finding':'fixture reports agree'})
        completion = patch.object(runner.task_completion, 'review', return_value={
            'valid':True, 'passed':True, 'requirements':[], 'failures':[], 'coverage':1})
        completion.start(); self.addCleanup(completion.stop)
        presentation = patch.object(runner.instructional_video,'assess',return_value={
            'valid':True,'passed':True,'score':100,'failures':[],
            'criteria':[{'id':'layout_readability','score':5,'evidence_frames':[1]}]})
        presentation.start(); self.addCleanup(presentation.stop)
        observer.start(); reviewer.start()
        self.addCleanup(observer.stop); self.addCleanup(reviewer.stop)

    def test_video_rubric_rejects_missing_evidence_and_separates_scores(self):
        rows = [{"id": key, "applicable": True, "score": 4,
                 "evidence_frames": [1], "finding": "visible"}
                for key, _ in video_rubric.RUBRIC["signal_quality"]]
        self.assertEqual(video_rubric.validate_result("signal_quality", {"criteria": rows}, 1)["score"], 75)
        rows[0]["evidence_frames"] = []
        with self.assertRaises(ValueError):
            video_rubric.validate_result("signal_quality", {"criteria": rows}, 1)

    def test_static_requested_diagram_is_not_frozen_failure(self):
        frames = [np.full((144, 256, 3), 120, dtype=np.uint8) for _ in range(30)]
        still = op.temporal_consistency(frames, 30, expected_steps=1)
        changing = op.temporal_consistency(frames, 30, expected_steps=4)
        self.assertEqual(still["diagnostic_proxy_index"], 100)
        self.assertLess(changing["diagnostic_proxy_index"], still["diagnostic_proxy_index"])

    def test_signal_metrics_are_finite_and_explainable(self):
        frame = np.full((144, 256, 3), 128, dtype=np.uint8)
        result = op.signal_quality([frame] * 3)
        self.assertEqual(result["relative_focus_index"], 100)
        self.assertIn("clipped_fraction_p90", result)

    def test_evaluate_writes_evidence_and_score(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1]) as tmp:
            path = str(Path(tmp) / "clip.avi")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 10, (256, 144))
            self.assertTrue(writer.isOpened())
            for i in range(12):
                frame = np.full((144, 256, 3), 100 + i, dtype=np.uint8)
                writer.write(frame)
            writer.release()
            fake = {"score": 4, "binary": "PASS", "criteria": [{"id": "x", "evidence_frames": [1]}]}
            with patch.object(runner.teaching_engagement, 'score', return_value={'valid': True, 'score': 75}), \
                 patch.object(runner, "extract_frames", return_value=[object()] * 100), \
                 patch.object(runner, "DIMENSIONS", {a: type("Judge", (), {"score": lambda self, c, f: fake})()
                                                      for a in runner.DIMENSIONS}), \
                 patch.object(runner, "VIDEO_DIMENSIONS", {a: type("Judge", (), {"score": lambda self, c, f: {"score": 75}})()
                                                            for a in runner.VIDEO_DIMENSIONS}):
                row = runner.evaluate({"id": "x", "expected_narrative_order": ["step"]},
                                      {"status": "ok", "video_path": path})
                with patch.object(runner.task_completion, 'review', side_effect=RuntimeError('completion offline')), \
                     patch.object(runner.grounded_observations, 'consistency', side_effect=RuntimeError('consistency offline')):
                    partial = runner.evaluate({'id':'x','expected_narrative_order':['step']},
                                              {'status':'ok','video_path':path})
                    self.assertEqual(len(partial['axes']), 8)
                    self.assertTrue(partial['supplementary']['teaching_engagement']['valid'])
                    self.assertFalse(partial['scoring']['valid'])
                    self.assertIsNone(partial['scoring']['score'])
                    self.assertEqual(partial['assessment_coverage']['visual_quality']['status'], 'scored')
                    self.assertEqual(partial['assessment_coverage']['task_completion']['status'], 'evaluation_failed')
                with patch.object(runner.task_completion, 'review', return_value={
                        'valid': True, 'passed': False, 'failures':['flow'],
                        'requirements':[{'id':'flow','status':'missing','evidence_frames':[],
                                         'finding':'flow arrow or moving marker absent'}]}):
                    omitted = runner.evaluate({'id':'x','expected_narrative_order':['step']},
                                              {'status':'ok','video_path':path})
                    self.assertTrue(omitted['scoring']['valid'])
                    self.assertEqual(omitted['scoring']['score'],50)
                    self.assertFalse(omitted['scoring']['strict_pass'])
                    self.assertTrue(any('task_requirement_missing' in gate for gate in omitted['scoring']['gates']))
                with patch.object(runner.teaching_engagement, 'score', side_effect=RuntimeError('judge unavailable')):
                    supplemental_failed = runner.evaluate({'id': 'x', 'expected_narrative_order': ['step']},
                                                          {'status': 'ok', 'video_path': path})
                with patch.object(runner.grounded_observations, 'consistency', return_value={'valid':False, 'conflicting_axes':['conceptual_correctness'], 'finding':'literal answer conflicts'}):
                    inconsistent = runner.evaluate({'id':'x','expected_narrative_order':['step']}, {'status':'ok','video_path':path})
                    self.assertFalse(inconsistent['scoring']['valid'])
                    self.assertFalse(inconsistent['scoring']['strict_pass'])
                    self.assertIsNone(inconsistent['scoring']['score'])
                with patch.object(runner, 'DIMENSIONS', {'conceptual_correctness': MagicMock()}), \
                     patch.object(runner, 'VIDEO_DIMENSIONS', {'visual_quality': MagicMock()}):
                    resumed = runner.evaluate({'id': 'x', 'expected_narrative_order': ['step']},
                                              {'status': 'ok', 'video_path': path}, previous=supplemental_failed)
                    runner.DIMENSIONS['conceptual_correctness'].score.assert_not_called()
                    runner.VIDEO_DIMENSIONS['visual_quality'].score.assert_not_called()
                    self.assertTrue(resumed['supplementary']['teaching_engagement']['valid'])
            self.assertTrue(row["scoring"]["valid"])
            self.assertEqual(row["axes"]["conceptual_correctness"]["score"], 75)
            self.assertEqual(row["sampled_frame_count"], 24)
            self.assertEqual(row["judge_frame_indices_in_sample"][0], 0)
            self.assertEqual(row["judge_frame_indices_in_sample"][-1], 99)
            self.assertEqual(len(row["video_sha256"]), 64)
            self.assertTrue(supplemental_failed['scoring']['valid'])
            self.assertEqual(supplemental_failed['scoring']['score'], row['scoring']['score'])
            self.assertFalse(supplemental_failed['supplementary']['teaching_engagement']['valid'])
            self.assertFalse(runner.reusable(supplemental_failed, {'id': 'x', 'expected_narrative_order': ['step']},
                                             {'status': 'ok', 'video_path': path}, 2.0, 832))
            self.assertTrue(runner.reusable(row, {"id": "x", "expected_narrative_order": ["step"]},
                                            {"status": "ok", "video_path": path}, 2.0, 832))
            self.assertFalse(runner.reusable(row, {"id": "x", "expected_narrative_order": ["changed"]},
                                             {"status": "ok", "video_path": path}, 2.0, 832))

    def test_complete_cli_flow_and_resume_with_api_key(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1]) as tmp:
            root = Path(tmp)
            video = root / "clip.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
            self.assertTrue(writer.isOpened())
            for i in range(12):
                writer.write(np.full((48, 64, 3), 90 + i, dtype=np.uint8))
            writer.release()
            prompts = root / "prompts.jsonl"
            manifest = root / "manifest.jsonl"
            prompts.write_text(json.dumps({"id": "case1", "prompt_text": "show a process"}) + "\n", encoding="utf-8")
            manifest.write_text(json.dumps({"id": "case1", "status": "ok", "video_path": str(video)}) + "\n", encoding="utf-8")
            args = ["run_benchmark_v2", "--prompts", str(prompts), "--manifest", str(manifest),
                    "--out", str(root / "out")]
            env = {"VIDEO_TEACHER_API_KEY": "test-only", "VIDEO_TEACHER_BASE_URL": "https://example.test/v1",
                   "VIDEO_TEACHER_MODEL": "vision-model"}
            def judged(case, frames):
                return {"score": 4, "binary": "PASS", "criteria": [], "summary": "mock"}
            def video_judged(case, frames):
                return {"score": 75, "criteria": [], "summary": "mock"}
            with patch.object(runner.teaching_engagement, 'score', return_value={'valid': True, 'score': 75}), \
                 patch.dict(os.environ, env), patch.object(sys, "argv", args), \
                 patch.object(runner, "DIMENSIONS", {a: type("Judge", (), {"score": lambda self, c, f: judged(c, f)})()
                                                      for a in runner.DIMENSIONS}), \
                 patch.object(runner, "VIDEO_DIMENSIONS", {a: type("Judge", (), {"score": lambda self, c, f: video_judged(c, f)})()
                                                            for a in runner.VIDEO_DIMENSIONS}):
                runner.main()
                row = runner.read_jsonl(root / "out" / "per_case.jsonl")[0]
                self.assertTrue(row["scoring"]["valid"])
                self.assertEqual(row["evaluation_config"]["judge"]["model"], "vision-model")
                aggregate = json.loads((root / "out" / "aggregate.json").read_text(encoding="utf-8"))
                self.assertTrue(aggregate["ranking_publishable"])
                self.assertEqual(aggregate["n_valid"], 1)
                with patch.object(runner, "evaluate", side_effect=AssertionError("resume called judge")):
                    runner.main()
                self.assertEqual(len(runner.read_jsonl(root / "out" / "per_case.jsonl")), 1)
                with patch.dict(os.environ, {"VIDEO_TEACHER_MODEL": "changed-model"}):
                    self.assertFalse(runner.reusable(row, {"id": "case1", "prompt_text": "show a process"},
                                                     {"status": "ok", "video_path": str(video)}, 2.0, 832))

    def test_api_key_configuration_requires_base_url_and_model(self):
        with patch.dict(os.environ, {"VIDEO_TEACHER_API_KEY": "secret", "VIDEO_TEACHER_BASE_URL": "",
                                     "VIDEO_TEACHER_MODEL": ""}):
            with self.assertRaises(ValueError):
                gpt55.judge_config()

    def test_api_key_client_sends_configured_model_and_json_mode(self):
        env = {"VIDEO_TEACHER_API_KEY": "test-only", "VIDEO_TEACHER_BASE_URL": "https://example.test/v1",
               "VIDEO_TEACHER_MODEL": "vision-model"}
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value.choices = [
            type("Choice", (), {"message": type("Message", (), {"content": '{"ok":true}'})()})()]
        with patch.dict(os.environ, env), patch.object(gpt55, "OpenAI", return_value=fake_client) as factory:
            response = gpt55.chat([{"role": "user", "content": "test"}],
                                  response_format={"type": "json_object"})
        self.assertEqual(response, '{"ok":true}')
        factory.assert_called_once()
        self.assertEqual(factory.call_args.kwargs["base_url"], "https://example.test/v1")
        self.assertEqual(factory.call_args.kwargs['timeout'], 900)
        self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
        self.assertEqual(fake_client.chat.completions.create.call_args.kwargs["model"], "vision-model")
        self.assertEqual(fake_client.chat.completions.create.call_args.kwargs["response_format"],
                         {"type": "json_object"})

    def test_timeout_retry_is_named_truthfully_and_does_not_become_a_score(self):
        import contextlib
        import io
        import httpx
        from openai import APITimeoutError
        client = MagicMock()
        client.chat.completions.create.side_effect = APITimeoutError(request=httpx.Request('POST', 'http://judge.test'))
        output = io.StringIO()
        env = {'VIDEO_TEACHER_API_KEY':'local','VIDEO_TEACHER_BASE_URL':'http://judge.test/v1', 'VIDEO_TEACHER_MODEL':'test'}
        with patch.dict(os.environ, env), patch.object(gpt55.time, 'sleep'), contextlib.redirect_stdout(output):
            with self.assertRaises(APITimeoutError):
                gpt55.chat([], client=client, max_retries=2)
        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertIn('APITimeoutError', output.getvalue())
        self.assertNotIn('429', output.getvalue())


if __name__ == "__main__":
    unittest.main()
