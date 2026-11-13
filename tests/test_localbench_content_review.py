import copy
import json
import pytest
from localbench.content_review import apply_text_repairs, review_input, validate_review, review_and_repair


def plan():
    return {'case_id':'x','scenes':[{'title':'Partition','narration':'Pick 2 of 3.',
      'caption':'CAP', 'duration_s':60,'primitives':[{'type':'text','x':.5,'y':.5,'text':'Pick 2 of 3'}]}]}


def review():
    return {'decision':'revise','issues':[{'scene':0,'field':'primitives/0/text','quote':'Pick 2 of 3',
      'severity':'error','reason':'Misstates the partition-conditional tradeoff.',
      'suggestion':'During a partition: C or A.'}]}


def test_critic_input_excludes_private_references_and_local_metadata():
    inp=review_input({'id':'x','prompt_text':'Teach CAP','reference_answer':'SECRET',
                     'rubric':'SECRET','solution':'SECRET'}, plan())
    assert 'SECRET' not in json.dumps(inp)
    assert inp['scenes'][0]['texts']['primitives/0/text']=='Pick 2 of 3'


def test_critic_requires_real_quote_location_and_consistent_decision():
    p=plan();r=review();validate_review(r,p)
    for key,value in [('scene',9),('field','duration_s'),('quote','invented'),('severity','maybe')]:
        bad=copy.deepcopy(r);bad['issues'][0][key]=value
        with pytest.raises(ValueError):validate_review(bad,p)
    r['decision']='pass'
    with pytest.raises(ValueError):validate_review(r,p)


def test_repairs_are_exact_text_only_and_do_not_modify_source():
    p=plan();patch={'replacements':[{'scene':0,'field':'primitives/0/text',
                      'old_text':'Pick 2 of 3','new_text':'During partition: C or A'}]}
    out=apply_text_repairs(p,patch)
    assert p['scenes'][0]['primitives'][0]['text']=='Pick 2 of 3'
    assert out['scenes'][0]['primitives'][0]['text']=='During partition: C or A'
    patch['replacements'][0]['field']='primitives/0/x'
    with pytest.raises(ValueError):apply_text_repairs(p,patch)


def test_uncertain_review_remains_unresolved(tmp_path):
    class Client:
        model='fake'
        def chat(self,*a,**kw):
            r=review();r['decision']='uncertain';r['issues'][0]['severity']='uncertain';return r
    with pytest.raises(ValueError,match='unresolved'):
        review_and_repair(Client(),{'id':'x'},plan(),tmp_path)
    assert not (tmp_path/'accepted.json').exists()


def test_location_normalization_preserves_findings_and_rejects_invented_quotes():
    from localbench.content_review import normalize_locations
    p=plan();r=review();r['issues'][0]['field']='diagram'
    fixed,changes=normalize_locations(r,p)
    # Same quote also occurs in narration: ambiguous locations must not be guessed.
    assert not changes
    with pytest.raises(ValueError):validate_review(fixed,p)
    p['scenes'][0]['narration']='A conditional tradeoff.'
    fixed,changes=normalize_locations(r,p)
    assert len(changes)==1
    assert fixed['issues'][0]['field']=='primitives/0/text'
    assert {k:v for k,v in fixed['issues'][0].items() if k!='field'}=={k:v for k,v in r['issues'][0].items() if k!='field'}
    validate_review(fixed,p)
    r['issues'][0]['quote']='Made up quote'
    fixed,changes=normalize_locations(r,p)
    assert not changes
    with pytest.raises(ValueError):validate_review(fixed,p)


def test_malformed_review_never_becomes_pass_on_retry(tmp_path):
    from localbench.content_review import review_plan
    class Client:
        model='fake'
        calls=0
        def chat(self,*a,**kw):
            self.calls+=1
            r=review();r['issues'][0].pop('suggestion');return r
    c=Client()
    with pytest.raises(ValueError):review_plan(c,{'id':'x'},plan(),tmp_path)
    assert c.calls==1
    assert (tmp_path/'raw_0.json').exists()
    assert not (tmp_path/'review.json').exists()


def test_formula_findings_are_recordable_but_not_silently_repaired_as_text(tmp_path):
    from localbench.content_review import normalize_locations
    p=plan();p['scenes'][0]['primitives']=[{'type':'chart','x_label':'Radius','x_unit':'km',
        'y_label':'Wind speed','y_unit':'mph','series':[{'label':'Profile','expression':'-(x-5)**2+25'}]}]
    field='primitives/0/series/0/expression'
    raw={'decision':'revise','issues':[{'scene':0,'field':'diagram/0/expression',
        'quote':'-(x-5)**2+25','severity':'error','reason':'Unsupported quantitative profile.',
        'suggestion':'Review the diagram and its data source.'}]}
    fixed,changes=normalize_locations(raw,p)
    assert fixed['issues'][0]['field']==field and len(changes)==1
    validate_review(fixed,p)
    assert field in review_input({'id':'x'},p)['scenes'][0]['read_only_fields']
    with pytest.raises(ValueError):
        apply_text_repairs(p,{'replacements':[{'scene':0,'field':field,'old_text':'-(x-5)**2+25','new_text':'75'}]})
    class Client:
        model='fake';calls=0
        def chat(self,*args,**kwargs):self.calls+=1;return raw
    client=Client()
    with pytest.raises(ValueError,match='diagram/formula revision required'):
        review_and_repair(client,{'id':'x'},p,tmp_path)
    assert client.calls==1 and (tmp_path/'review_0/review.json').exists()
    assert not (tmp_path/'accepted.json').exists()
