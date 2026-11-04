import json
import unittest
from unittest.mock import patch
from PIL import Image
from eval import verified_completion as completion


class VerifiedCompletionTests(unittest.TestCase):
    def setUp(self):
        self.required=[{'id':'a','text':'Show A','kind':'instruction'}, {'id':'b','text':'Show B','kind':'instruction'}]
        self.windows=[{'id':0,'requirement_evidence':[{'id':'a','evidence_frames':[2]}, {'id':'b','evidence_frames':[3]}]}]

    def test_schema_binds_each_obligation_to_its_own_recorded_frames(self):
        schema=completion.completion_schema(self.required,2,self.windows)['json_schema']['schema']
        rows=schema['properties']['requirements']['properties']
        for key,allowed in [('a',[2]),('b',[3])]:
            choices=rows[key]['properties']['segment_citations']['items']['anyOf']
            self.assertEqual(choices[0]['properties']['segment_id']['enum'],[0])
            self.assertEqual(choices[0]['properties']['frames']['items']['enum'],allowed)

    def test_object_entries_normalize_without_changing_scores_or_references(self):
        raw={'requirements':{key:{'expected':'required','observed':'visible','finding':'shown',
             'evidence_frames':[],'status':'met','segment_citations':[{'segment_id':0,'frames':[index]}]}
             for key,index in [('a',2),('b',3)]}}
        with patch.object(completion,'requirements',return_value=self.required), \
             patch.object(completion,'chat',return_value=json.dumps(raw)):
            report=completion.review({'segment_evidence':self.windows},[Image.new('RGB',(8,8))]*2)
        self.assertTrue(report['passed'])
        self.assertEqual(report['coverage'],1)
        self.assertEqual(report['requirements'][0]['segment_citations'][0]['frames'],[2])
        raw['requirements']['a']['segment_citations'][0]['frames']=[3]
        with patch.object(completion,'requirements',return_value=self.required), \
             patch.object(completion,'chat',return_value=json.dumps(raw)):
            with self.assertRaisesRegex(ValueError,'grounded completion review rejected'):
                completion.review({'segment_evidence':self.windows},[Image.new('RGB',(8,8))]*2)
