"""Compile annual bond cash flows, discounted amounts and an independent check."""
from __future__ import annotations

import copy
from decimal import Decimal, localcontext, ROUND_HALF_UP
import re

from .common import public_case

VERSION = 'annual-bond-cashflows-v1'
BLUE, RED, INK, GREEN = '#1868ae', '#a93632', '#203b55', '#226c42'


def number(value):
    if type(value) not in (str, int, float, Decimal):
        raise ValueError('bond values must be decimal numbers')
    try:
        d = Decimal(str(value))
    except Exception as exc:
        raise ValueError('invalid bond number') from exc
    if not d.is_finite():
        raise ValueError('bond values must be finite')
    return d


def money(value):
    return '$'+format(number(value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP), ',.2f')


def plain(value):
    return format(number(value).normalize(), 'f')


def compute(coupon, principal, years, rate):
    coupon, principal, rate = map(number, (coupon, principal, rate))
    if type(years) is not int or not 1 <= years <= 12:
        raise ValueError('annual bond requires 1..12 years')
    if not 0 <= coupon <= 10000 or not 0 < principal <= 1000000 or not 0 <= rate <= Decimal('.25'):
        raise ValueError('bond parameters outside supported bounds')
    with localcontext() as ctx:
        ctx.prec = 40
        q = 1+rate
        rows = [{'year': t, 'coupon': str(coupon), 'principal': str(principal if t == years else Decimal(0)),
                 'coupon_pv': str(coupon/q**t),
                 'cash_flow': str(coupon+(principal if t == years else 0))}
                for t in range(1, years+1)]
        coupon_pv = sum(number(row['coupon_pv']) for row in rows)
        principal_pv = principal/q**years
        # Separate closed form and forward-accumulation calculations check the sum.
        annuity = coupon*years if rate == 0 else coupon*(1-q**(-years))/rate
        terminal_cash = sum(coupon*q**(years-t) for t in range(1, years+1))+principal
        pv = coupon_pv+principal_pv
        if abs(annuity-coupon_pv) > Decimal('1e-25') or abs(pv*q**years-terminal_cash) > Decimal('1e-25'):
            raise ValueError('independent bond calculation disagreement')
        return {'coupon': str(coupon), 'principal': str(principal), 'years': years, 'rate': str(rate),
                'rows': rows, 'coupon_pv': str(coupon_pv), 'principal_pv': str(principal_pv),
                'present_value': str(pv), 'annuity_check': str(annuity),
                'terminal_cash': str(terminal_cash), 'accumulated_price': str(pv*q**years),
                'coupon_rate': str(coupon/principal), 'is_par': coupon == rate*principal}


def validate_state(state):
    if not isinstance(state, dict) or not all(k in state for k in ('coupon', 'principal', 'years', 'rate')):
        raise ValueError('invalid bond state')
    expected = compute(*(state[k] for k in ('coupon', 'principal', 'years', 'rate')))
    if state != expected:
        raise ValueError('bond cash flows or check differ from recomputed state')
    return state


def parse(case):
    text = public_case(case).get('prompt_text', '')
    if re.search(r'\b(semi.?annual(?:ly)?|monthly|quarterly|continuously)\b', text, re.I):
        return None
    pattern = r'A bond pays \$([\d,]+(?:\.\d+)?) per year for (\d+) years? and \$([\d,]+(?:\.\d+)?) at the end'
    matches = re.findall(pattern, text, re.I)
    rates = re.findall(r'discount rate is (\d+(?:\.\d+)?)\s*%', text, re.I)
    if len(matches) != 1 or len(rates) != 1:
        return None
    c, n, f = matches[0]
    try:
        return compute(c.replace(',', ''), f.replace(',', ''), int(n), number(rates[0])/100)
    except ValueError:
        return None


def lesson_text(state):
    c, f, n, r = (state[k] for k in ('coupon', 'principal', 'years', 'rate'))
    rate_pct = plain(number(r)*100)
    total, cpv, fpv = (money(state[k]) for k in ('present_value', 'coupon_pv', 'principal_pv'))
    discount_explanation = 'Discount each payment by one plus the rate raised to its year number. The same coupon received later has a lower present value, because it waits longer to earn the required return.'
    if number(r) == 0:
        discount_explanation = 'The discount rate is zero, so each future payment has the same present value as its cash amount. Add each coupon and the final principal once.'
    elif number(c) == 0:
        discount_explanation = 'Each coupon is zero, so its discounted value is also zero. Only the final principal contributes to the present value, after discounting for the maturity date.'
    elif n == 1:
        discount_explanation = 'The coupon is received at year one. Divide it by one plus the annual discount rate to find its value today. Discount the separate principal payment in the same way.'
    titles = ['Bond Cash Flows', 'Bring Each Payment to Today', 'Add All Discounted Coupons',
              'Discount the Principal', 'Combine and Check the Result']
    captions = [f'{n} annual coupons; year {n} also includes the principal.',
                f'PV = cash flow / (1 + {plain(r)})^year; discount each payment separately.',
                f'{n} discounted coupons total {cpv}; round after summing.',
                f'Principal PV = {money(f)} / (1 + {plain(r)})^{n} = {fpv}.',
                f'Coupon PV {cpv} + principal PV {fpv} = {total}.']
    narration = [
        f'This bond pays {plain(c)} dollars each year for {n} years. Year {n} includes the last coupon plus {plain(f)} dollars of principal. We use a {rate_pct} percent annual discount rate.',
        discount_explanation,
        f'Add the discounted value of every coupon, including the last year. The annuity formula gives the same sum, {plain(number(state["coupon_pv"]).quantize(Decimal(".01")))} dollars. Round only after adding the unrounded values.',
        f'Discount the {plain(f)} dollar principal for {n} years. Its present value is {plain(number(state["principal_pv"]).quantize(Decimal(".01")))} dollars. The last coupon is already in the coupon sum; do not count it twice.',
        f'The two present values total {plain(number(state["present_value"]).quantize(Decimal(".01")))} dollars. Check independently: the coupon rate is {rate_pct} percent, equal to the required return. The bond should be worth its face value, which agrees.' if state['is_par'] else
        f'The two present values total {plain(number(state["present_value"]).quantize(Decimal(".01")))} dollars. Check by moving every cash flow forward to maturity. That total matches the calculated price grown at the discount rate for {n} years.'
    ]
    return list(zip(titles, captions, narration))


def diagram(phase, state):
    state = validate_state(state)
    if type(phase) is not int or not 0 <= phase < 5:
        raise ValueError('invalid bond phase')
    c, f, n, r = (state[k] for k in ('coupon', 'principal', 'years', 'rate'))
    q = 1+number(r); parts = []
    def text(x, y, value, size=24, color=INK, align='center'):
        parts.append({'type': 'text', 'x': (x-64)/896, 'y': (y-112)/302,
                      'text': value, 'font_size': size, 'color': color, 'align': align})
    def line(x, y, x2, y2, color=INK, width=3, arrow=False):
        parts.append({'type': 'arrow' if arrow else 'line', 'x': (x-64)/896, 'y': (y-112)/302,
                      'x2': (x2-64)/896, 'y2': (y2-112)/302, 'color': color, 'stroke': width})
    if phase == 0:
        text(490, 143, f'Coupon: {money(c)} every year', 24, BLUE)
        text(490, 184, f'Year {n}: {money(c)} coupon + {money(f)} principal', 24, RED)
        line(108, 328, 910, 328)
        for t in range(n+1):
            x = 108+792*t/n
            line(x, 323, x, 333)
            text(x, 356, str(t), 20)
            if t:
                endpoint = x-16 if t == n else x
                line(x, 326, endpoint, 267, BLUE, arrow=True)
                text(endpoint, 248, '$'+plain(c), 18, BLUE)
        # A separate arrow at the final year explicitly adds principal to its coupon.
        line(900, 326, 916, 211, RED, arrow=True)
        text(908, 186, '$'+plain(f), 18, RED)
        text(510, 401, 'Years from today; each blue arrow is one coupon', 20)
    elif phase == 1:
        text(510, 145, 'PV = cash flow / (1 + rate)^year', 28)
        text(285, 213, f'Year 1: {money(c)}', 25, BLUE)
        text(735, 213, f'Year {n}: {money(c)}', 25, BLUE)
        for x, t in ((285, 1), (735, n)):
            line(x-100, 240, x-100, 314, BLUE, arrow=True)
            text(x+20, 270, f'divide by {plain(q)}^{t}', 22)
            text(x, 347, money(number(c)/q**t)+' today', 26, GREEN)
        takeaway = ('Zero rate: no discounting' if number(r) == 0 else
                    'Zero coupons contribute zero present value' if number(c) == 0 else
                    'One annual discount period' if n == 1 else 'Later equal payments have lower PV')
        text(510, 401, takeaway, 22)
    elif phase == 2:
        text(510, 137, 'Present value of each coupon', 24, BLUE)
        split = (n+1)//2
        for j, row in enumerate(state['rows']):
            col, index = divmod(j, split)
            x, y = 290+420*col, 178+29*index
            text(x-88, y, f'Year {row["year"]}', 20)
            text(x+42, y, money(row['coupon_pv']), 20, BLUE)
        text(510, 360, f'Sum of all {n} coupon PVs = {money(state["coupon_pv"])}', 26, BLUE)
        formula = f'{plain(c)} x [1 - {plain(q)}^(-{n})] / {plain(r)}' if number(r) else f'{n} x {plain(c)}'
        text(510, 402, 'Annuity check: '+formula+' = '+money(state['annuity_check']), 20)
    elif phase == 3:
        text(510, 157, f'{money(f)} principal at year {n}', 28, RED)
        line(245, 200, 245, 310, RED, arrow=True)
        text(540, 247, f'Divide by {plain(q)}^{n}', 28)
        text(510, 334, 'Principal PV = '+money(state['principal_pv']), 30, RED)
        text(510, 403, 'The final coupon is already included in the coupon sum.', 21)
    else:
        text(285, 145, 'Coupon PV', 22, BLUE)
        text(735, 145, 'Principal PV', 22, RED)
        text(285, 188, money(state['coupon_pv']), 30, BLUE)
        text(510, 188, '+', 28)
        text(735, 188, money(state['principal_pv']), 30, RED)
        line(155, 221, 865, 221)
        text(510, 263, 'Present value = '+money(state['present_value']), 30)
        if state['is_par']:
            text(510, 317, f'Independent check: {plain(c)} / {plain(f)} = {plain(number(state["coupon_rate"])*100)}% coupon rate', 22, GREEN)
            text(510, 359, f'Coupon rate = {plain(number(r)*100)}% required return', 22, GREEN)
            text(510, 402, 'Expected price = face value = '+money(f)+'; agrees.', 23, GREEN)
        else:
            text(510, 314, f'Check at year {n}: coupons reinvested + principal', 22, GREEN)
            text(510, 355, 'Future cash-flow total = '+money(state['terminal_cash']), 22, GREEN)
            text(510, 398, f'PV x {plain(q)}^{n} = '+money(state['accumulated_price'])+'; agrees.', 22, GREEN)
    return parts


def validate_scene(scene, case=None):
    spec = scene['bond_cashflows']
    if not isinstance(spec, dict) or spec.get('version') != VERSION:
        raise ValueError('invalid bond compiler version')
    state, phase = validate_state(spec.get('state')), spec.get('phase')
    if type(phase) is not int or not 0 <= phase < 5:
        raise ValueError('invalid bond phase')
    if case is not None and state != parse(case):
        raise ValueError('bond state differs from public task')
    if scene.get('source_visual') or scene.get('state_visual'):
        raise ValueError('bond diagram cannot be overridden by another visual')
    if scene['primitives'] != diagram(phase, state):
        raise ValueError('bond primitives differ from computed cash flows')
    if tuple(scene[k] for k in ('title', 'caption', 'narration')) != lesson_text(state)[phase]:
        raise ValueError('bond explanation differs from computed state')


def bind(plan, case):
    result = copy.deepcopy(plan); unsupported = {'status': 'unsupported', 'version': VERSION}
    state = parse(case)
    if state is None or len(result.get('scenes', [])) != 5:
        return result, unsupported
    if any(s.get('source_visual') or s.get('state_visual') or s.get('bond_cashflows') for s in result['scenes']):
        return result, unsupported
    for i, (scene, texts) in enumerate(zip(result['scenes'], lesson_text(state))):
        for stale in ('spoken_units', 'spoken_unit_timing', 'teaching_cues', 'slide_text'):
            scene.pop(stale, None)
        scene.update(zip(('title', 'caption', 'narration'), texts))
        scene['arithmetic_checks'] = []
        scene['primitives'] = diagram(i, state)
        scene['bond_cashflows'] = {'version': VERSION, 'phase': i, 'state': copy.deepcopy(state)}
    return result, {'status': 'compiled', 'version': VERSION, 'changed_narration_scenes': list(range(5)),
                    'scope': 'Fixed annual coupon, end-year redemption, 1..12 years and nonnegative annual discount rate.',
                    'check': 'Par-rate identity when applicable; otherwise independent terminal cash-flow accumulation.',
                    'parameters_from_public_prompt': {k: state[k] for k in ('coupon', 'principal', 'years', 'rate')}}
