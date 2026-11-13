import copy
import json

from PIL import Image
import pytest

from localbench import student
from localbench.student_retention import VERSION, audit, ensure_preserved


PROFILE={'id':'beginner','description':'Reads English','known':{'K0':'A push acts on an object.'},
         'not_assumed':["Newton's third law"]}
OBS={'evidence_ids':['F0'],'is_final':True}


def six():
    claims=['A person contacts a wall.','The red vector acts on the wall.',
            'The green vector acts on the person.','The arrows have equal length.',
            'The two forces do not cancel on one body because their recipients differ.',
            'The recap states the interaction has two opposite forces.']
    return {'understandings':[{'claim':c,'evidence_ids':['F0']} for c in claims],
            'questions':[],'prerequisite_used':['K0'],'state_update':'The different recipients explain noncancellation.'}


def test_six_distinct_observations_reach_review_without_count_repair(tmp_path):
    raw=six()
    with pytest.raises(ValueError,match='count'):student.validate_response(copy.deepcopy(raw),PROFILE,OBS)
    class Client:
        calls=0
        def chat(self,*args,**kwargs):self.calls+=1;return copy.deepcopy(raw)
    client=Client()
    result=student.request_validated(client,[],lambda r:student.validate_response(r,PROFILE,OBS,protocol=VERSION),
        tmp_path,'student','fixture',1800,preserve_observations=True)
    assert client.calls==1 and result==raw
    log=json.loads((tmp_path/'response_preservation.json').read_text())
    assert log['original_exceeded_preferred_count'] is True
    assert log['sections']['understandings']['dropped_original_indices']==[]
    assert log['sections']['understandings']['mapping'][-1]['result_index']==5


def test_structure_fix_may_remove_extra_field_but_cannot_delete_late_concept(tmp_path):
    raw=six();raw['extra']='invalid field'
    class Client:
        calls=0
        def chat(self,*args,**kwargs):
            self.calls+=1
            return copy.deepcopy(raw if self.calls==1 else six())
    good=Client()
    accepted=student.request_validated(good,[],lambda r:student.validate_response(r,PROFILE,OBS,protocol=VERSION),
        tmp_path/'good','student','fixture',1800,preserve_observations=True)
    assert accepted['understandings'][4]==raw['understandings'][4]
    class Lossy(Client):
        def chat(self,*args,**kwargs):
            self.calls+=1
            if self.calls==1:return copy.deepcopy(raw)
            result=six();result['understandings']=result['understandings'][:4];return result
    bad=Lossy()
    with pytest.raises(ValueError,match='dropped'):
        student.request_validated(bad,[],lambda r:student.validate_response(r,PROFILE,OBS,protocol=VERSION),
            tmp_path/'bad','student','fixture',1800,preserve_observations=True)
    log=json.loads((tmp_path/'bad/response_preservation.json').read_text())
    assert bad.calls==2 and log['accepted'] is False
    assert log['sections']['understandings']['dropped_original_indices']==[4,5]


@pytest.mark.parametrize('change',['sign','reorder','state'])
def test_exact_preservation_rejects_semantic_edits(change):
    original=six();candidate=copy.deepcopy(original)
    if change=='sign':candidate['understandings'][4]['claim']='The two forces cancel on one body.'
    elif change=='reorder':candidate['understandings'].reverse()
    else:candidate['state_update']='The wall exerts no force.'
    with pytest.raises(ValueError,match='changed'):ensure_preserved(original,candidate)


def test_overflow_and_missing_identity_do_not_trigger_lossy_regeneration(tmp_path):
    raw=six();raw['understandings']*=3
    class Client:
        calls=0
        def chat(self,*args,**kwargs):self.calls+=1;return copy.deepcopy(raw)
    client=Client()
    with pytest.raises(ValueError,match='deletion'):
        student.request_validated(client,[],lambda r:student.validate_response(r,PROFILE,OBS,protocol=VERSION),
            tmp_path,'student','fixture',1800,preserve_observations=True)
    assert client.calls==1


def test_audit_tracks_duplicate_identity_and_changed_evidence():
    before=six();before['understandings'].append(copy.deepcopy(before['understandings'][0]))
    after=copy.deepcopy(before);after['understandings'][-1]['evidence_ids']=['F1']
    result=audit(before,after,accepted=True,repaired=True)['sections']['understandings']
    assert result['all_text_preserved'] and result['order_preserved']
    assert result['mapping'][-1]['original_index']==6
    assert not result['mapping'][-1]['evidence_ids_unchanged']


def test_same_prompts_full_session_keeps_all_six_and_hides_future(tmp_path):
    frame=tmp_path/'frame.jpg';Image.new('RGB',(16,16)).save(frame)
    evidence={'duration_s':30,'frames':[{'id':'F0','time_s':0,'path':str(frame)}],
        'transcripts':[{'id':'T0','source_chunk_end_s':30,'end_s':30,'text':'FUTURE_ONLY'}],
        'valid_audio_intervals':[{'start_s':0,'end_s':30}],'audio_chunk_ends':[10,20,30],'evidence_errors':[]}
    prefix=student.prefix(evidence,10)
    old=student.messages({'id':'a'},PROFILE,prefix,None)
    new=student.messages({'id':'a'},PROFILE,prefix,None,protocol=VERSION)
    assert old==new and 'FUTURE_ONLY' not in json.dumps(new)
    class Learner:
        def chat(self,*args,**kwargs):return six()
    class Reviewer:
        def chat(self,messages,**kwargs):
            data=json.loads(messages[1]['content'][0]['text'])
            assert len(data['student_response']['understandings'])==6
            return {'understandings':[{'index':i,'status':'supported','evidence_ids':['F0'],
                'reason':'Fixture observation'} for i in range(6)],'questions':[],
                'profile_consistency':{'status':'consistent','reason':'Fixture profile'}}
    result=student.run_session({'id':'a'},PROFILE,evidence,tmp_path/'run',Learner(),Reviewer(),protocol=VERSION)
    assert result['status']=='complete'
    assert all(c['response']['understandings'][-1]==six()['understandings'][-1] for c in result['checkpoints'])
    assert all(c['response_preservation']['accepted'] for c in result['checkpoints'])
