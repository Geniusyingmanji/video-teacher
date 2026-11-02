import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from scripts import run_qwen_sample10 as batch


class BatchTests(unittest.TestCase):
    def test_failures_are_bounded_and_all_ten_remain_in_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'new_run'
            response = MagicMock()
            response.__enter__.return_value.status = 200
            with patch('sys.argv', ['run_qwen_sample10', '--out', str(out)]), \
                 patch.object(batch.urllib.request, 'urlopen', return_value=response), \
                 patch.object(batch.subprocess, 'check_output', return_value='fixture_commit'), \
                 patch.object(batch.subprocess, 'run', return_value=SimpleNamespace(returncode=1)) as run, \
                 patch.object(batch, 'evaluate', return_value={'scoring': {'valid': False}}), \
                 patch.dict(batch.os.environ, {}, clear=False):
                self.assertEqual(batch.main(), 1)
            generation_calls = [call for call in run.call_args_list if call.args[0][0] == 'bash']
            self.assertEqual(len(generation_calls), 30)
            completion = json.loads((out/'completion.json').read_text())
            self.assertEqual(completion['total'], 10)
            self.assertEqual(completion['quality_passed'], 0)
            self.assertFalse(completion['complete'])
            self.assertEqual(len((out/'manifest.jsonl').read_text().splitlines()), 10)
            self.assertEqual(len(list(out.glob('attempt_*/*_evaluation.json'))), 30)
