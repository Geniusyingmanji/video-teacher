from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from eval.judges import gpt55
from eval.structured_transport import structured_stop_token_guard, guard_config
from scripts.verify_benchmark_scores import choose_endpoint


class StructuredTransportTests(unittest.TestCase):
    def test_guard_keeps_schema_and_other_request_parameters(self):
        response=object();create=Mock(return_value=response)
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        schema={'type':'json_schema','json_schema':{'schema':{'type':'object'}}}
        with patch.object(gpt55,'configured_client',return_value=client):
            with structured_stop_token_guard([248046,248044]):
                result=gpt55.configured_client().chat.completions.create(
                    response_format=schema,max_completion_tokens=3450,logit_bias={'7':-2})
        self.assertIs(result,response)
        args=create.call_args.kwargs
        self.assertIs(args['response_format'],schema)
        self.assertEqual(args['max_completion_tokens'],3450)
        self.assertEqual(args['logit_bias'],{'7':-2,'248044':-100,'248046':-100})

    def test_guard_does_not_affect_unstructured_calls_and_restores_on_error(self):
        create=Mock(return_value='normal')
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with patch.object(gpt55,'configured_client',return_value=client) as original:
            with self.assertRaisesRegex(RuntimeError,'test'):
                with structured_stop_token_guard([248046]):
                    self.assertEqual(gpt55.configured_client().chat.completions.create(model='local'),'normal')
                    raise RuntimeError('test')
            self.assertIs(gpt55.configured_client,original)
        self.assertNotIn('logit_bias',create.call_args.kwargs)

    def test_guard_rejects_invalid_ids(self):
        for ids in ([-1],[True],['248046']):
            with self.assertRaises(ValueError):guard_config(ids)
        self.assertIsNone(guard_config([]))

    def test_resume_keeps_allowed_endpoint_and_ignores_unknown_hosts(self):
        endpoints=['http://127.0.0.1:8000/v1','http://127.0.0.1:8001/v1']
        self.assertEqual(choose_endpoint([{'judge':{'base_url':endpoints[1]}}],endpoints,0),endpoints[1])
        self.assertEqual(choose_endpoint([{'judge':{'base_url':'https://unknown.example'}}],endpoints,0),endpoints[0])
