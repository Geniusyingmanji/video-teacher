import io
from types import SimpleNamespace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.run_qwen_multigpu import reusable_render, run_worker_with_recovery


class RecoveryTests(unittest.TestCase):
    def test_only_exact_render_from_current_contract_can_skip_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory)/'video.mp4'
            video.write_bytes(b'fixture')
            result = {'complete':True,'contract_version':'v2','video':str(video)}
            timing = {'duration_seconds':60,'fps':15}
            with patch('generation.strict_manim.inspect_exact', return_value={'valid':True}) as check:
                self.assertTrue(reusable_render(result,'v2',timing))
                check.assert_called_once_with(video,60,15)
                self.assertFalse(reusable_render(result,'old',timing))
                self.assertFalse(reusable_render({**result,'complete':False},'v2',timing))
            with patch('generation.strict_manim.inspect_exact', return_value={'valid':False}):
                self.assertFalse(reusable_render(result,'v2',timing))
            self.assertFalse(reusable_render({**result,'video':None},'v2',timing))

    def test_native_crash_retries_same_command_without_losing_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);checkpoint=root/'checkpoint.json';checkpoint.write_text('evidence')
            command=['python','worker','--out',str(root)]
            with patch('scripts.run_qwen_multigpu.subprocess.run', side_effect=[
                    SimpleNamespace(returncode=134),SimpleNamespace(returncode=0)]) as run:
                self.assertEqual(run_worker_with_recovery(command,{},io.StringIO(),root/'final.json'),0)
                self.assertEqual(run.call_count,2)
                self.assertEqual(run.call_args_list[0],run.call_args_list[1])
                self.assertEqual(checkpoint.read_text(),'evidence')

    def test_repeated_crashes_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory, patch(
                'scripts.run_qwen_multigpu.subprocess.run',return_value=SimpleNamespace(returncode=134)) as run:
            self.assertEqual(run_worker_with_recovery(['worker'],{},io.StringIO(),Path(directory)/'final.json'),134)
            self.assertEqual(run.call_count,3)
