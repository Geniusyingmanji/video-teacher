import pytest
import json
import copy

from localbench.claim_scope import validate_claim,repair_targeted_claims,final_asr_items


def test_claim_counterexample_needs_exact_quote_and_real_evidence():
    items=[{'id':'A00','text':'In this route, the president signs the bill.'}]
    quote='the president signs the bill'
    result={'quote':quote,'decision':'supported','asserted_scope':'This route only.',
            'counterexample':'','reason':'Explicitly scoped.','evidence_ids':['A00']}
    validate_claim(result,quote,items)
    with pytest.raises(ValueError):validate_claim({**result,'quote':'invented'},quote,items)
    with pytest.raises(ValueError):validate_claim({**result,'evidence_ids':['A99']},quote,items)
    with pytest.raises(ValueError):validate_claim({**result,'decision':'counterexample'},quote,items)
    with pytest.raises(ValueError):validate_claim(result,quote,[{'id':'A00','text':'Unrelated words.'}])


def test_targeted_repair_rechecks_edits_and_keeps_private_answers_out(tmp_path):
    original={'case_id':'x','scenes':[{'title':'A route','narration':'Only a signature can make a law.',
       'caption':'Follow this route.','duration_s':12,'primitives':[
           {'type':'text','x':.5,'y':.5,'text':'Law'}]}]}
    snapshot=copy.deepcopy(original)
    class Client:
        def __init__(self):self.requests=[]
        def chat(self,messages,**kw):
            request=json.loads(messages[-1]['content']);self.requests.append(request)
            if kw['purpose'].startswith('targeted_claim_repair'):
                return {'replacements':[{'scene':0,'field':'narration',
                    'old_text':original['scenes'][0]['narration'],
                    'new_text':'In this route the President signs the bill into law.'}]}
            quote=request['quote_to_check'];wrong=quote.startswith('Only')
            return {'quote':quote,'decision':'counterexample' if wrong else 'supported',
                    'asserted_scope':'Universal' if wrong else 'This route',
                    'counterexample':'Veto override.' if wrong else '',
                    'reason':'Checked the stated conditions.','evidence_ids':['S00/narration']}
    client=Client()
    result=repair_targeted_claims(client,{'id':'x','prompt_text':'Show a signature route.',
        'reference_answer':'PRIVATE_SENTINEL'},original,[original['scenes'][0]['narration']],tmp_path)
    assert original==snapshot and result['scenes'][0]['duration_s']==12
    assert result['scenes'][0]['primitives']==original['scenes'][0]['primitives']
    assert len(client.requests)==3
    assert 'PRIVATE_SENTINEL' not in json.dumps(client.requests)
    assert client.requests[-1]['quote_to_check']==result['scenes'][0]['narration']
    with pytest.raises(ValueError,match='absent'):
        repair_targeted_claims(client,{'id':'x'},original,['A fabricated quote'],tmp_path/'missing')


def test_final_asr_diagnostic_rejects_changed_audio_or_generation_text(tmp_path):
    from localbench.provenance import file_hash
    from localbench.common import write_json
    video=tmp_path/'final.mp4';video.write_bytes(b'test media bytes')
    wav=tmp_path/'chunk.wav';wav.write_bytes(b'test decoded audio bytes')
    source={'id':'A00','path':str(wav),'sha256':file_hash(wav),'start_s':0,'end_s':10}
    packet={'source':'final_encoded_video_only','video_path':str(video),
            'video_sha256':file_hash(video),'audio':[source]}
    actual=[{**source,'local_asr':{'source':'local_asr_on_final_encoded_audio',
            'audio_sha256':file_hash(wav),'transcript':'Words recognized from the final audio.'}}]
    write_json(tmp_path/'evidence/packet.json',packet);write_json(tmp_path/'actual_audio.json',actual)
    items,provenance=final_asr_items(tmp_path)
    assert items[0]['id']=='ASR:A00' and not provenance['generator_plan_used']
    actual[0]['local_asr']['source']='generation_script'
    write_json(tmp_path/'actual_audio.json',actual)
    with pytest.raises(ValueError,match='independent ASR'):final_asr_items(tmp_path)
    actual[0]['local_asr']['source']='local_asr_on_final_encoded_audio'
    write_json(tmp_path/'actual_audio.json',actual);wav.write_bytes(b'changed audio')
    with pytest.raises(ValueError,match='provenance mismatch'):final_asr_items(tmp_path)
