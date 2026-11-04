import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from eval import claim_grounding as grounding, verified_scoring as verified, instructional_video as presentation


class ClaimGroundingTests(unittest.TestCase):
    def fixture(self, root):
        path = root/'clear.avi'
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 1, (320,120))
        self.assertTrue(writer.isOpened())
        for _ in range(3):
            image = np.zeros((120,320,3), dtype=np.uint8)
            cv2.putText(image,'CLEAR CAPTION',(20,70),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
            writer.write(image)
        writer.release()
        claim = {'kind':'overlap','severity':'severe','essential':True,'frames':[1,3],
                 'region':[0,0,1,1],'finding':'Two captions overlap and are unreadable.'}
        return {'id':'clear','video_path':str(path),'video_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'instructional_presentation':{'overview_timestamps_s':[0,1,2],'issues':[claim]}}, claim

    def answer(self, decision='rejected'):
        return {'observations':[{'frame':i,'visible_state':'CLEAR CAPTION is readable.'} for i in (1,2,3)],
                'decision':decision,'supporting_frames':[1,2],'persistent_in_settled_frames':False,
                'essential_content_unreadable':False,'reason':'One clear caption is visible in both frames.'}

    def test_rejected_claim_uses_exact_frames_and_source_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            row, claim = self.fixture(Path(tmp))
            result = grounding.verify(row,claim,chat_fn=lambda *a,**k:json.dumps(self.answer()))
            self.assertEqual(result['decision'],'rejected')
            self.assertEqual([s['time_s'] for s in result['sample_info']],[0,1,2])
            row['video_sha256']='changed'
            with self.assertRaisesRegex(ValueError,'source video changed'):
                grounding.verify(row,claim,chat_fn=lambda *a,**k:json.dumps(self.answer()))

    def test_severe_confirmation_requires_persistent_unreadable_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            row, claim = self.fixture(Path(tmp))
            with self.assertRaisesRegex(ValueError,'repeated settled'):
                grounding.verify(row,claim,chat_fn=lambda *a,**k:json.dumps(self.answer('confirmed')))

    def test_single_transition_is_bracketed_by_settled_neighbors(self):
        row={'instructional_presentation':{'overview_timestamps_s':[0,1,2]}}
        self.assertEqual([s['time_s'] for s in grounding.samples_for_claim(row,{'frames':[2]})],[0,1,2])

    def test_many_references_keep_originals_within_image_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            row,claim=self.fixture(Path(tmp))
            row['instructional_presentation']['overview_timestamps_s']=[i/11 for i in range(23)]
            claim['frames']=list(range(1,24))
            def answer(messages, **kwargs):
                images=[c for c in messages[0]['content'] if c['type']=='image_url']
                self.assertEqual(len(images),24)
                raw=self.answer()
                raw['observations']=[{'frame':i,'visible_state':'Clear caption.'} for i in range(1,24)]
                return json.dumps(raw)
            result=grounding.verify(row,claim,chat_fn=answer)
            self.assertEqual(len(result['sample_info']),23)

    def test_rejected_penalty_rerates_then_recomputes_same_formula(self):
        with tempfile.TemporaryDirectory() as tmp:
            row, claim = self.fixture(Path(tmp))
            pr = row['instructional_presentation']
            pr.update(criteria=[{'id':key,'score':3 if key=='layout_readability' else 4,
                                 'finding':'inspection','evidence_frames':[1,3]} for key in presentation.CRITERIA],
                      events=[{'transition_verified':True}],
                      still_comparisons=[{'preferred':label,'video_preferred':True,'advantage':'substantive'} for label in ('A','B')],
                      segments=[],all_windows_reviewed=True,summary='fixture')
            pr.update(presentation.score_review(pr,pr['events'],pr['still_comparisons']))
            self.assertEqual(pr['score'],39)
            row.update(axes={k:{'score':75} for k in verified.scoring.VIDEO_AXES+verified.scoring.TEACHING_AXES},
                       defects=[],scoring={'valid':True,'score':39},consistency_review={'valid':True},
                       task_completion={'valid':True,'passed':True})
            decision={'claim':claim,'decision':'rejected'}
            review={'claims':[decision],'rejected_claims':[decision],'uncertain_claims':[]}
            with patch.object(verified,'verify_presentation',return_value=review), \
                 patch.object(verified,'rerate',return_value={'criteria':[{'id':'layout_readability','score':4,
                     'finding':'One clear caption, with no overlap.','evidence_frames':[1,3]}]}):
                result=verified.apply_grounding(row,{})
            self.assertEqual(result['scoring']['score'],75)
            self.assertEqual(result['base_evaluation']['scoring']['score'],39)
            self.assertFalse(result['instructional_presentation']['issues'])
            self.assertEqual(len(result['claim_grounding']['criterion_corrections']),1)

    def test_uncertainty_invalidates_total_instead_of_inventing_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            row,_=self.fixture(Path(tmp))
            row['scoring']={'valid':True,'score':39}
            with patch.object(verified,'verify_presentation',return_value={'claims':[], 'rejected_claims':[], 'uncertain_claims':[{}]}):
                result=verified.apply_grounding(row,{})
            self.assertIsNone(result['scoring']['score'])
            self.assertFalse(result['scoring']['valid'])

    def test_uncertain_checkpoint_is_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            row, claim = self.fixture(Path(tmp))
            cached = {'claim_key': hashlib.sha256(json.dumps(claim, sort_keys=True).encode()).hexdigest(),
                      'video_sha256': row['video_sha256'], 'decision': 'uncertain',
                      'verification_code_sha256': hashlib.sha256(Path(grounding.__file__).read_bytes()).hexdigest(),
                      'judge': grounding.judge_config()}
            with patch.object(grounding, 'verify', return_value={'decision': 'rejected', 'claim': claim}) as verify:
                result = grounding.verify_presentation(row, previous=[cached])
            verify.assert_called_once()
            self.assertFalse(result['uncertain_claims'])
            self.assertEqual(result['rejected_claims'][0]['decision'], 'rejected')
