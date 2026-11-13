import concurrent.futures
import json
import threading
import time

import httpx
import pytest

from localbench.client import BudgetExceeded, MatrixClient


def test_concurrent_identical_calls_are_billed_once_and_budget_is_persistent(tmp_path,monkeypatch):
    monkeypatch.setenv('MATRIX_API_KEY','not-a-real-key')
    monkeypatch.setenv('MATRIX_CHAT_URL','https://example.invalid/chat')
    monkeypatch.setenv('VIDEO_TEACHER_CREDENTIALS',str(tmp_path/'nonexistent.json'))
    calls=[];lock=threading.Lock()
    def fake_post(self,url,**kwargs):
        with lock:calls.append(kwargs['json'])
        time.sleep(.03)
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}'},'finish_reason':'stop'}],
                                        'usage':{'total_tokens':10}})
    monkeypatch.setattr(httpx.Client,'post',fake_post)
    c=MatrixClient(tmp_path,max_calls=1,max_tokens_total=10000)
    messages=[{'role':'user','content':'one question'}]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:c.chat(messages,purpose='test',max_tokens=100),range(4)))
    assert results==[{'ok':True}]*4
    assert len(calls)==1
    resumed=MatrixClient(tmp_path,max_calls=1,max_tokens_total=10000)
    assert resumed.chat(messages,purpose='resumed',max_tokens=100)=={'ok':True}
    with pytest.raises(BudgetExceeded):
        resumed.chat([{'role':'user','content':'different'}],purpose='over-budget',max_tokens=100)
    ledger=[json.loads(line) for line in (tmp_path/'usage.jsonl').read_text().splitlines()]
    assert [x['event'] for x in ledger if x['event']!='cache_reuse']==['start','end']
    reused=[x for x in ledger if x['event']=='cache_reuse']
    assert len(reused)==4 and all(x['cache_kind']=='local' for x in reused)
    assert 'not-a-real-key' not in (tmp_path/'usage.jsonl').read_text()


def test_explicit_cache_reuse_needs_exact_request_and_records_provenance(tmp_path,monkeypatch):
    monkeypatch.setenv('MATRIX_API_KEY','not-a-real-key')
    monkeypatch.setenv('MATRIX_CHAT_URL','https://example.invalid/chat')
    monkeypatch.setenv('VIDEO_TEACHER_CREDENTIALS',str(tmp_path/'missing.json'))
    calls=[]
    def fake_post(self,url,**kwargs):
        calls.append(1)
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}'},'finish_reason':'stop'}],
                                        'usage':{'total_tokens':10}})
    monkeypatch.setattr(httpx.Client,'post',fake_post)
    source=MatrixClient(tmp_path/'source',max_calls=1,max_tokens_total=10000)
    request=[{'role':'user','content':'same verified input'}]
    assert source.chat(request,purpose='source',max_tokens=100)=={'ok':True}
    target=MatrixClient(tmp_path/'target',max_calls=0,max_tokens_total=0,cache_sources=[tmp_path/'source'])
    assert target.chat(request,purpose='reuse',max_tokens=100)=={'ok':True}
    assert len(calls)==1
    ledger=[json.loads(x) for x in (tmp_path/'target/usage.jsonl').read_text().splitlines()]
    assert ledger[0]['event']=='cache_reuse' and ledger[0]['source']==str(tmp_path/'source')
    with pytest.raises(BudgetExceeded):
        target.chat([{'role':'user','content':'different input'}],purpose='new',max_tokens=100)


def test_invalid_completion_retains_measured_usage_without_local_credentials(tmp_path, monkeypatch):
    broken = tmp_path/'broken-private.json'; broken.write_text('not json')
    monkeypatch.setenv('VIDEO_TEACHER_CREDENTIALS', str(broken))
    monkeypatch.setattr(httpx.Client, 'post', lambda *a, **k: httpx.Response(200, json={
        'choices': [{'message': {'content': "{'invalid': True}"}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}}))
    client = MatrixClient(tmp_path/'run', endpoint='https://example.test/v1/chat/completions', api_key='TEST_SECRET')
    with pytest.raises(ValueError): client.chat([{'role': 'user', 'content': 'test'}], purpose='invalid')
    rows = [json.loads(l) for l in client.ledger.read_text().splitlines()]
    assert rows[-1]['status'] == 'error' and rows[-1]['usage']['total_tokens'] == 30
    assert rows[-1]['charged_tokens'] == 30
    assert len(list((client.run_dir/'invalid_responses').glob('*.json'))) == 1


def test_rate_limit_honors_retry_after_and_retains_failure_receipt(tmp_path,monkeypatch):
    waits=[];calls=[]
    monkeypatch.setattr('localbench.client.time.sleep',lambda seconds:waits.append(seconds))
    def post(*args,**kwargs):
        calls.append(1)
        if len(calls)==1:return httpx.Response(429,headers={'Retry-After':'7'})
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}'},'finish_reason':'stop'}],
            'usage':{'total_tokens':12}})
    monkeypatch.setattr(httpx.Client,'post',post)
    c=MatrixClient(tmp_path/'r',api_key='fake',endpoint='https://example.invalid/v1/chat/completions',max_calls=4,max_tokens_total=100000)
    assert c.chat([{'role':'user','content':'one question'}],purpose='retry',max_tokens=100)=={'ok':True}
    assert waits==[7] and len(calls)==2
    rows=[json.loads(x) for x in c.ledger.read_text().splitlines()]
    assert any(r.get('http_status')==429 for r in rows)
    assert any(r['event']=='retry_wait' and r['reason']=='rate_limit' for r in rows)
