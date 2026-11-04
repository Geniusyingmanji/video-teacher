import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from generation.lesson_spec import VERSION, chapter_schedule, validate_timeline
from generation.strict_video_contract import make_contract
from generation.strict_manim import inspect_exact
from generation.narration import RATE, fit_draft_speech


class DraftDeliveryTests(unittest.TestCase):
    def contract(self, profile='draft'):
        return make_contract({'id':'fixture','lesson_version':VERSION,'target_duration_s':60,
                              'prompt_text':'Solve 2x+5=17.','audio_narration_required':True},
                             generation_profile=profile)

    def timeline(self, contract):
        return [{**row,'goal':f'Explain step {i}','visible_evidence':f'Equation state {i}',
                 'requirement_ids':[], 'narration':'We subtract five from each side to keep the equation balanced.'}
                for i,row in enumerate(chapter_schedule(contract))]

    def test_coverage_metadata_is_warning_only_in_draft(self):
        contract=self.contract();plan={'teaching_timeline':self.timeline(contract)}
        self.assertEqual(len(validate_timeline(plan,contract)),3)
        strict=copy.deepcopy(contract);strict['generation_profile']='strict'
        with self.assertRaises(ValueError):validate_timeline(plan,strict)

    def test_small_speech_overrun_is_fitted_without_truncating_speech(self):
        tone=(np.sin(np.arange(round(RATE*21.62))*.04)*5000).astype('<i2')
        fitted,factor=fit_draft_speech(tone,20)
        self.assertGreater(factor,1);self.assertLessEqual(factor,1.35)
        self.assertLess(len(fitted)/RATE,19.8);self.assertGreater(len(fitted)/RATE,19)
        with self.assertRaises(ValueError):fit_draft_speech(np.tile(tone,2),20)

    def test_small_source_label_does_not_block_draft(self):
        from PIL import Image
        from generation.source_primitives import SourcePrimitives
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.png';Image.new('RGB',(1000,1000),'white').save(source)
            box=[100,100,200,130]
            with self.assertRaisesRegex(ValueError,'below 16'):
                SourcePrimitives(source,[box],[0,0,1,.6]).text('x=6',box)
            label=SourcePrimitives(source,[box],[0,0,1,.6],min_label_pixels=0).text('x=6',box)
            self.assertGreater(label.height,0)

    def test_real_draft_retains_pacing_defects_for_quality_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);contract=self.contract()
            (root/'contract.json').write_text(json.dumps(contract))
            (root/'storyboard.json').write_text(json.dumps({'teaching_timeline':self.timeline(contract),'source_edit_regions':[]}))
            code=root/'section_1.py'
            code.write_text('from manim import *\nclass Section1Scene(Scene):\n def construct(self):\n'
                '  for i,seconds in enumerate([21,20,19]):\n'
                '   self.begin_teaching_step(f"chapter_{i+1}")\n'
                '   self.clear()\n'
                '   a=Text(["2x + 5 = 17","2x = 12","x = 6"][i],font_size=36)\n'
                '   b=Text("review layout",font_size=30)\n'
                '   self.play(FadeIn(a),FadeIn(b),run_time=2)\n'
                '   self.wait(6)\n   self.wait(6)\n   self.wait(seconds-14)\n')
            env=dict(os.environ,PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH',''))
            run=subprocess.run([sys.executable,'-m','generation.strict_manim','--code',str(code),'--scene','Section1Scene',
                                '--contract',str(root/'contract.json')],capture_output=True,text=True,env=env,timeout=180)
            self.assertEqual(run.returncode,0,run.stderr[-2000:])
            diagnostics=json.loads((root/'strict_diagnostics.json').read_text())
            self.assertTrue(diagnostics['timing']['valid'])
            self.assertTrue(diagnostics['delivery_warnings'])
