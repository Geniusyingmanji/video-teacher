import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from eval.run_benchmark_v2 import assessment_coverage
from scripts.finalize_benchmark_scores import finalize


class FinalizeScoresTests(unittest.TestCase):
    def fixture(self, directory):
        row = {'id': 'failed', 'errors': ['generation_missing_or_failed'],
               'scoring': {'valid': False, 'score': None, 'strict_pass': False}}
        (directory/'prompts.jsonl').write_text(json.dumps({'id': 'failed'})+'\n')
        (directory/'per_case.jsonl').write_text(json.dumps(row)+'\n')
        aggregate = {'n_total': 1, 'n_valid': 0, 'ranking_publishable': False,
                     'per_case_sha256': hashlib.sha256((directory/'per_case.jsonl').read_bytes()).hexdigest(),
                     'assessment_coverage': {'failed': assessment_coverage(row)}}
        (directory/'aggregate.json').write_text(json.dumps(aggregate))
        return row, aggregate

    def test_failure_is_completed_execution_without_invented_scores_or_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture(directory)
            result = finalize(directory, directory/'prompts.jsonl')
            self.assertTrue(result['execution_completed'])
            self.assertEqual(result['n_generation_failed'], 1)
            self.assertEqual(result['n_valid'], 0)
            self.assertEqual(result['n_quality_accepted'], 0)
            self.assertIn('generation_failed | —', (directory/'scores.md').read_text())

    def test_stale_aggregate_and_missing_case_block_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            row, aggregate = self.fixture(directory)
            aggregate['assessment_coverage']['failed']['total']['score'] = 99
            (directory/'aggregate.json').write_text(json.dumps(aggregate))
            with self.assertRaisesRegex(ValueError, 'complete matching'):
                finalize(directory, directory/'prompts.jsonl')
            self.fixture(directory)
            with (directory/'prompts.jsonl').open('a') as handle:
                handle.write(json.dumps({'id': 'missing'})+'\n')
            with self.assertRaisesRegex(ValueError, 'complete matching'):
                finalize(directory, directory/'prompts.jsonl')
            self.assertFalse((directory/'all_scores.csv').exists())

    def test_fabricated_zero_fails_audit_even_when_aggregate_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            row, aggregate = self.fixture(directory)
            row['scoring']['score'] = 0
            (directory/'per_case.jsonl').write_text(json.dumps(row)+'\n')
            aggregate['per_case_sha256'] = hashlib.sha256((directory/'per_case.jsonl').read_bytes()).hexdigest()
            (directory/'aggregate.json').write_text(json.dumps(aggregate))
            with self.assertRaisesRegex(ValueError, 'evidence audit failed'):
                finalize(directory, directory/'prompts.jsonl')
            self.assertFalse((directory/'scores.md').exists())

    def test_changed_evidence_with_identical_scores_blocks_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            row, _ = self.fixture(directory)
            row['errors'].append('new_evidence')
            (directory/'per_case.jsonl').write_text(json.dumps(row)+'\n')
            with self.assertRaisesRegex(ValueError, 'complete matching'):
                finalize(directory, directory/'prompts.jsonl')
            self.assertFalse((directory/'finalization.json').exists())
