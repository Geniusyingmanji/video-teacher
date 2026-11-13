import copy

import pytest

from localbench.spatial_plan import compile_plan
from localbench.spatial_view_narration import apply, view_facts
from test_localbench_spatial_plan import case, lesson


def setup():
    p,_=compile_plan(lesson(),case())
    facts=view_facts(p,case(),[1])
    raw={'edits':[{'scene':1,'text':{'narration':'The nucleophile lies opposite the leaving group relative to carbon.'},
                   'fact_ids':[next(iter(facts))],'reason':'Use common-center language.'}]}
    return p,facts,raw


def test_view_facts_expose_strokes_and_text_repair_cannot_change_geometry():
    p,facts,raw=setup();before=copy.deepcopy(p)
    assert {'solid_wedge','hashed_wedge'} <= {r.get('style') for r in facts.values()}
    result,receipt=apply(p,case(),raw,[1],facts)
    assert p==before
    assert result['scenes'][1]['primitives']==p['scenes'][1]['primitives']
    assert all(result['scenes'][i]==p['scenes'][i] for i in [0,2,3])
    assert receipt['semantic_acceptance'].startswith('unverified')


def test_narration_respects_fixed_slot_word_limit():
    p,facts,raw=setup()
    with pytest.raises(ValueError,match='fixed-slot'):
        apply(p,case(),raw,[1],facts,scene_word_limits={1:5})


@pytest.mark.parametrize('change',['geometry','timing','scope','unknown_fact'])
def test_view_text_repair_rejects_nontext_and_invalid_citations(change):
    p,facts,raw=setup();edit=raw['edits'][0]
    if change=='geometry': edit['text']['primitives']=[]
    if change=='timing': edit['text']['duration_s']=12
    if change=='scope': edit['scene']=2
    if change=='unknown_fact': edit['fact_ids']=['invented']
    with pytest.raises(ValueError): apply(p,case(),raw,[1],facts)
