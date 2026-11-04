import copy
import json
import unittest
from unittest.mock import Mock

from eval.judges.structured_rubric import judge, response_format
from eval.rubric_6x6 import RUBRIC, validate_result


class StructuredTests(unittest.TestCase):
    def setUp(self):
        self.dimension = 'conceptual_correctness'
        self.ids = [key for key, _ in RUBRIC[self.dimension]]
        self.valid = {'summary': 'Visible evidence', 'criteria': [
            {'id': key, 'applicable': True, 'score': 4, 'evidence_frames': [1],
             'finding': 'Visible in frame one'} for key in self.ids]}

    def run_judge(self, chat):
        return judge(chat, [], self.ids, 2,
                     lambda raw: validate_result(self.dimension, raw, 2))

    def test_invalid_content_is_retried_without_coercion(self):
        for field, value in [('applicable', 'true'), ('score', True),
                             ('evidence_frames', []), ('finding', '')]:
            invalid = copy.deepcopy(self.valid)
            invalid['criteria'][0][field] = value
            chat = Mock(side_effect=[json.dumps(invalid), json.dumps(self.valid)])
            self.assertEqual(self.run_judge(chat)['structured_validation']['attempts'], 2)

    def test_duplicate_ids_and_exhaustion(self):
        invalid = copy.deepcopy(self.valid)
        invalid['criteria'][1]['id'] = self.ids[0]
        chat = Mock(return_value=json.dumps(invalid))
        with self.assertRaisesRegex(ValueError, 'bounded retries'):
            self.run_judge(chat)
        self.assertEqual(chat.call_count, 3)

    def test_truncation_retries_but_infrastructure_propagates(self):
        chat = Mock(side_effect=[ValueError('truncated'), json.dumps(self.valid)])
        self.assertEqual(self.run_judge(chat)['structured_validation']['attempts'], 2)
        chat = Mock(side_effect=ConnectionError('offline'))
        with self.assertRaises(ConnectionError):
            self.run_judge(chat)
        self.assertEqual(chat.call_count, 1)

    def test_schema_has_exact_count_and_boolean(self):
        schema = response_format(self.ids, 2)['json_schema']['schema']
        criteria = schema['properties']['criteria']
        self.assertEqual(criteria['minItems'], 6)
        self.assertEqual(criteria['maxItems'], 6)
        self.assertEqual(criteria['items']['properties']['applicable']['type'], 'boolean')
        rating = criteria['items']['properties']['score']['anyOf'][0]
        self.assertEqual(rating['enum'], [1,1.5,2,2.5,3,3.5,4,4.5,5])
        self.assertNotIn('multipleOf', rating)
        fields = list(criteria['items']['properties'])
        self.assertLess(fields.index('finding'), fields.index('score'))
        self.assertLess(fields.index('evidence_frames'), fields.index('score'))
