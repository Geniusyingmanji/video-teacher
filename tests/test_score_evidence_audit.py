import tempfile
from pathlib import Path
import unittest

from scripts.audit_score_evidence import audit


class EvidenceExportAuditTests(unittest.TestCase):
    def test_total_cannot_bypass_required_reviews(self):
        errors = audit({'id':'unchecked','axes':{},'scoring':{'valid':True,'score':0}})['errors']
        self.assertIn('accepted total lacks verified report consistency', errors)
        self.assertIn('accepted total lacks verified task completion', errors)

    def test_missing_video_is_explicit_and_invented_zero_is_rejected(self):
        row = {'id': 'missing', 'errors': ['generation_missing_or_failed'],
               'scoring': {'valid': False, 'score': None}}
        self.assertEqual(audit(row)['errors'], [])
        row['scoring']['score'] = 0
        self.assertIn('missing video has a fabricated score', audit(row)['errors'])

    def test_tampered_source_and_unsupported_axis_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'video.mp4'
            path.write_bytes(b'changed source')
            row = {'id': 'tampered', 'video_path': str(path), 'video_sha256': 'old digest',
                   'sampled_frame_count': 18, 'axes': {'visual_quality': {'score': 99}},
                   'scoring': {'valid': False, 'score': None}}
            errors = audit(row)['errors']
            self.assertIn('video hash mismatch', errors)
            self.assertTrue(any(e.startswith('visual_quality:') for e in errors))
