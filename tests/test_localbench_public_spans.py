import pytest
from localbench.public_spans import inventory,resolve


def test_spans_are_exact_offsets_and_do_not_break_decimal_values():
    case={'id':'x','prompt_text':'  Show 0.40 s. Keep A–B linked!\nExplain why.  ',
          'expected_concepts':['PRIVATE_REFERENCE']}
    result=inventory(case)
    assert [x['text'] for x in result['spans']]==['Show 0.40 s.','Keep A–B linked!','Explain why.']
    for r in result['spans']:
        assert case['prompt_text'][r['start_char']:r['end_char']]==r['text']
        assert resolve(case,r['id'])==r['text']
    assert 'PRIVATE_REFERENCE' not in str(result)


def test_unknown_or_nontext_ids_cannot_supply_a_paraphrased_requirement():
    case={'id':'x','prompt_text':'Show size shrinking with distance.'}
    for invalid in ['P1','Objects further away appear smaller',None,0]:
        with pytest.raises(ValueError):resolve(case,invalid)
