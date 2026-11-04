import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from eval.evidence_prompt import prompt_json
from scripts.verify_benchmark_scores import source_finished


class EvidencePromptTests(unittest.TestCase):
    def test_table_encoding_preserves_each_observation_and_reference(self):
        rows = [{'id': f'req:{i}', 'status': 'partial', 'evidence_frames': [1, 7],
                 'finding': 'A visible relation, with uncertain completion.'} for i in range(20)]
        evidence = {'segment_evidence': [{'id': 4, 'timestamps_s': [10.012345, 11.5],
                                        'requirement_evidence': rows}]}
        original = copy.deepcopy(evidence)
        packed = prompt_json(evidence)
        decoded = json.loads(packed)
        table = decoded['segment_evidence'][0]['requirement_evidence']
        decoded['segment_evidence'][0]['requirement_evidence'] = [
            dict(zip(table['columns'], row)) for row in table['rows']]
        self.assertEqual(decoded, original)
        self.assertEqual(evidence, original)
        self.assertLess(len(packed), len(json.dumps(evidence)))

    def test_heterogeneous_evidence_is_preserved_without_table_conversion(self):
        evidence = {'requirement_evidence': [{'id': 'a'}, {'id': 'b', 'finding': 'missing'}]}
        self.assertEqual(json.loads(prompt_json(evidence)), evidence)

    def test_follow_requires_aggregate_matching_latest_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'per_case.jsonl'
            source.write_text('{"id":"a"}\n')
            self.assertFalse(source_finished(root))
            (root/'aggregate.json').write_text(json.dumps({
                'per_case_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}))
            self.assertTrue(source_finished(root))
            self.assertFalse(source_finished(root, {'a': {'id': 'a', 'changed': True}}))
            self.assertTrue(source_finished(root, {'a': {'id': 'a'}}))
            source.write_text('{"id":"a","changed":true}\n')
            self.assertFalse(source_finished(root))
