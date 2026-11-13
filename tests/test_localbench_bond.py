import copy
from decimal import Decimal

import pytest

from localbench.bond import bind, compute, diagram, money, parse, validate_state
from localbench.scene import inspect_layout, validate_plan


def fixture(coupon=50, principal=1000, years=10, rate=5):
    case = {'id': 'bond', 'target_duration_s': 75,
            'prompt_text': f"A bond pays ${coupon} per year for {years} years and ${principal} at the end. If the discount rate is {rate}%, what is its present value?"}
    plan = {'case_id': 'bond', 'scenes': [{'title': 'Old diagram', 'caption': 'Old explanation.',
            'narration': 'An existing lesson diagram to be improved.', 'duration_s': 15,
            'primitives': [{'type': 'text', 'x': .2, 'y': .3, 'text': 'Old'}]} for _ in range(5)]}
    return plan, case


def test_cash_flows_include_last_coupon_and_redemption_once():
    state = compute(50, 1000, 10, '.05')
    assert len(state['rows']) == 10
    assert [Decimal(row['cash_flow']) for row in state['rows']] == [Decimal(50)]*9+[Decimal(1050)]
    assert sum(Decimal(row['principal']) for row in state['rows']) == 1000
    assert money(state['coupon_pv']) == '$386.09'
    assert money(state['principal_pv']) == '$613.91'
    assert money(state['present_value']) == '$1,000.00'
    assert state['is_par']
    # The final coupon and principal arrows share the year-10 origin but diverge.
    arrows = [p for p in diagram(0, state) if p['type'] == 'arrow']
    assert len(arrows) == 11
    assert arrows[-1]['x'] == arrows[-2]['x']
    assert arrows[-1]['x2'] != arrows[-2]['x2']


@pytest.mark.parametrize('coupon,face,n,rate,expected', [
    (0, 100, 1, '.1', '$90.91'), (6, 100, 2, '.05', '$101.86'),
    (5, 100, 2, '.10', '$91.32'), (5, 100, 2, '0', '$110.00')])
def test_nonpar_and_zero_rate_use_values_not_a_fixed_thousand(coupon, face, n, rate, expected):
    state = compute(coupon, face, n, rate)
    assert money(state['present_value']) == expected
    assert not state['is_par']
    assert abs(Decimal(state['accumulated_price'])-Decimal(state['terminal_cash'])) < Decimal('1e-25')


def test_corrupted_cash_flow_or_visible_text_cannot_retain_valid_receipt():
    state = compute(50, 1000, 10, '.05')
    for name in ('row', 'total', 'check', 'par'):
        broken = copy.deepcopy(state)
        if name == 'row': broken['rows'][-1]['cash_flow'] = '1000'
        elif name == 'total': broken['present_value'] = '1050'
        elif name == 'check': broken['terminal_cash'] = '1000'
        else: broken['is_par'] = False
        with pytest.raises(ValueError, match='recomputed'): validate_state(broken)
    plan, case = fixture(); candidate, _ = bind(plan, case)
    candidate['scenes'][4]['primitives'][-1]['text'] = 'Expected price = 900'
    with pytest.raises(ValueError, match='differ'): validate_plan(candidate, case)
    candidate, _ = bind(plan, case)
    candidate['scenes'][0]['narration'] += ' The final coupon is omitted.'
    with pytest.raises(ValueError, match='explanation'): validate_plan(candidate, case)


@pytest.mark.parametrize('coupon,principal,years,rate', [(50,1000,10,5), (125,2500,12,4), (0,100,1,10), (5,100,2,0)])
def test_bound_plan_uses_public_values_and_stays_legible(coupon, principal, years, rate):
    plan, case = fixture(coupon, principal, years, rate); before = copy.deepcopy(plan)
    candidate, receipt = bind(plan, case)
    assert plan == before and receipt['status'] == 'compiled'
    assert receipt['changed_narration_scenes'] == list(range(5))
    validate_plan(candidate, case)
    assert not inspect_layout(candidate, include_warnings=True)
    assert sum(s['duration_s'] for s in candidate['scenes']) == 75
    assert candidate['scenes'][0]['bond_cashflows']['state']['years'] == years


def test_out_of_scope_payment_frequency_or_ambiguous_prompt_is_rejected():
    plan, case = fixture()
    assert parse({**case, 'prompt_text': case['prompt_text']+' Coupons are paid semiannually.'}) is None
    assert parse({**case, 'prompt_text': case['prompt_text']+' The discount rate is 7%.'}) is None
    assert bind(plan, fixture(years=30)[1])[1]['status'] == 'unsupported'
    for x in ('NaN', 'Infinity', True):
        with pytest.raises(ValueError): compute(x, 1000, 10, '.05')


def test_self_consistent_state_must_match_the_public_task():
    plan, changed_case = fixture(coupon=60)
    candidate, _ = bind(plan, changed_case)
    with pytest.raises(ValueError, match='public task'):
        validate_plan(candidate, fixture(coupon=50)[1])


def test_bond_states_cannot_be_hidden_reordered_or_incomplete():
    plan, case = fixture()
    for kind in ('override', 'order', 'missing'):
        candidate, _ = bind(plan, case)
        if kind == 'override': candidate['scenes'][0]['state_visual'] = {'state': {}}
        elif kind == 'order': candidate['scenes'][1:3] = candidate['scenes'][1:3][::-1]
        else: candidate['scenes'][0]['bond_cashflows']['state'].pop('coupon')
        with pytest.raises(ValueError): validate_plan(candidate, case)
