import copy
import pytest

from localbench.compass_diagram import compile_diagram, DIRECTIONS


def fixture(from_='NE', to='SW'):
    refs={'R1':{'statement':'A source-specific direction declaration.'}}
    spec={'boundary_label':'Boundary','flows':[{'name':'Flow','from':from_,'to':to,
          'color':'#b32938','reference_id':'R1','reference_quote':'direction declaration'}]}
    return spec,refs


@pytest.mark.parametrize('from_,to',[('NE','SW'),('SE','NW'),('N','S'),('E','W'),('NW','SE'),('W','E'),('S','N'),('SW','NE')])
def test_all_declared_bearings_compile_to_matching_screen_direction(from_,to):
    spec,refs=fixture(from_,to)
    primitives,receipt=compile_diagram(spec,refs)
    arrow=primitives[receipt['flows'][0]['primitive_index']]
    sign=lambda v:0 if abs(v)<1e-9 else (1 if v>0 else -1)
    assert (sign(arrow['x2']-arrow['x']),sign(arrow['y2']-arrow['y']))==DIRECTIONS[to]
    assert {'N','E','S','W'}.issubset({p.get('text') for p in primitives})
    assert receipt['semantic_binding_status']=='model_declared_not_certified'


def test_conflicting_source_bearing_and_untraceable_quote_fail():
    spec,refs=fixture('NE','SE')
    with pytest.raises(ValueError,match='opposite'):
        compile_diagram(spec,refs)
    spec,refs=fixture()
    spec['flows'][0]['reference_quote']='invented reference'
    with pytest.raises(ValueError,match='quote'):
        compile_diagram(spec,refs)
