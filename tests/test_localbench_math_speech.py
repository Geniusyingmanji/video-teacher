from localbench.math_speech import verbalize_math
from localbench.pipeline import spoken_text


def test_inline_inequality_retains_both_comparisons_in_actual_tts_input():
    value=verbalize_math('Shade where g(x) < y < f(x), with g(x) = 0.25x.')
    assert value=='Shade where g of x less than y less than f of x, with g of x equals zero point two five times x.'
    assert '<' not in value and value.count('less than')==2


def test_compound_comparisons_and_decimals_are_not_split_incorrectly():
    assert verbalize_math('x <= 2.50 and y ≠ 1.')=='x less than or equal to two point five zero and y not equal to 1.'
    assert verbalize_math('x >= -3.25')=='x greater than or equal to minus three point two five'


def test_normal_prose_and_genotype_spelling_are_preserved():
    text='A parent is Aa. Keep the caption (for now) unchanged.'
    assert verbalize_math(text)==text
    scene={'narration':"A parent is Aa. The 'A' allele differs from the 'a' allele. Count aa.",
           'state_visual':{'state':{'kind':'punnett','parents':['Aa','Aa'],'outcomes':['AA','Aa','Aa','aa']}}}
    spoken=spoken_text(scene)
    assert 'capital A' in spoken and 'lowercase a' in spoken
