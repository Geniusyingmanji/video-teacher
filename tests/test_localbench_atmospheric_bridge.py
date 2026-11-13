import copy

import pytest

from localbench.atmospheric_bridge import patch


def inputs():
    plan = {'scenes': [{'title': 'Warm Ocean'}, {'title': 'Low Pressure'}, {}, {}]}
    case = {'id': 'geo', 'prompt_text': 'Show a storm over a warm ocean: moist air rising around a low-pressure center with an eye.'}
    return plan, case


def test_recipe_surface_inflow_upper_outflow_and_rising_branches_are_distinct():
    plan, case = inputs(); before = copy.deepcopy(plan)
    raw = patch(plan, case, ['S1'])
    assert plan == before
    primitives = raw['replacements'][1]['updates']['primitives']
    arrows = [p for p in primitives if p['type'] == 'arrow']
    surface = [p for p in arrows if p['y'] == p['y2'] == .67]
    upper = [p for p in arrows if p['y'] == p['y2'] == .26]
    assert len(surface) == len(upper) == 2
    assert all(abs(p['x2'] - .5) < abs(p['x'] - .5) for p in surface)
    assert all(abs(p['x2'] - .5) > abs(p['x'] - .5) for p in upper)
    assert all(p['y2'] < p['y'] for p in arrows if p['x'] == p['x2'])


def test_recipe_requires_public_binding_and_does_not_match_hidden_answers():
    plan, case = inputs(); case['prompt_text'] = 'Explain a river basin.'
    case['expected_concepts'] = ['tropical storm ocean rising low-pressure']
    with pytest.raises(ValueError, match='public task'): patch(plan, case, ['S1'])
    plan, case = inputs(); plan['scenes'][1]['title'] = 'Unrelated chapter'
    with pytest.raises(ValueError, match='existing ocean'): patch(plan, case, ['S1'])
