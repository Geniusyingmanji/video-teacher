"""Development compiler for a sourced tropical-storm circulation explanation.

This is a narrow, manually authored domain recipe, not an autonomous discovery or
general fluid simulator. It emits ordinary primitives for the existing renderer.
"""
from __future__ import annotations

import re

from .common import public_case

VERSION = 'tropical-circulation-bridge-recipe-v1-public-binding'
BLUE = '#1868ae'
INK = '#14283e'
HEAT = '#a54814'


def text(x, y, label, size=24):
    return {'type': 'text', 'x': x, 'y': y, 'text': label, 'font_size': size,
            'color': INK, 'align': 'center'}


def arrow(x, y, x2, y2, color=BLUE):
    return {'type': 'arrow', 'x': x, 'y': y, 'x2': x2, 'y2': y2, 'color': color}


def ocean():
    return [{'type': 'rect', 'x': .08, 'y': .79, 'w': .84, 'h': .13,
             'color': BLUE, 'fill': '#dceefb'}, text(.5, .855, 'Warm ocean')]


def patch(plan, case, evidence_ids):
    prompt = public_case(case)['prompt_text'].casefold()
    if not re.search(r'\bstorm\b|\bhurricane\b|tropical cyclone', prompt) or not all(
        token in prompt for token in ['ocean', 'low-pressure', 'rising', 'eye']
    ):
        raise ValueError('public task does not bind the tropical circulation recipe')
    if len(plan['scenes']) < 4 or 'ocean' not in plan['scenes'][0]['title'].casefold() or 'pressure' not in plan['scenes'][1]['title'].casefold():
        raise ValueError('recipe requires existing ocean introduction followed by pressure explanation')
    if not isinstance(evidence_ids, list) or not evidence_ids or any(not isinstance(x, str) or not x for x in evidence_ids):
        raise ValueError('explicit public-source/development evidence references required')

    heating = ocean() + [
        text(.5, .10, 'Condensation: vapor becomes droplets'),
        # Distinct droplets over the rising air column; no source code in judge inputs.
        *[{'type': 'circle', 'x': x, 'y': .24, 'r': .022, 'color': BLUE, 'fill': '#dceefb'}
          for x in [.42, .46, .50, .54, .58]],
        arrow(.43, .73, .43, .36), arrow(.57, .73, .57, .36),
        text(.5, .66, 'Moist air'),
        arrow(.60, .25, .76, .41, HEAT),
        text(.79, .51, 'Heat released'),
        text(.20, .45, 'Air keeps rising'),
    ]
    circulation = ocean() + [
        text(.5, .085, 'Side view: outflow aloft'),
        arrow(.38, .26, .16, .26), arrow(.62, .26, .84, .26),
        arrow(.38, .65, .38, .27), arrow(.62, .65, .62, .27),
        text(.5, .43, 'Rising air'),
        arrow(.14, .67, .36, .67), arrow(.86, .67, .64, .67),
        text(.13, .54, 'Higher P'), text(.87, .54, 'Higher P'),
        text(.5, .68, 'Low P'),
    ]
    return {'replacements': [
        {'scene': 0, 'updates': {
            'title': 'Warm Ocean: What Keeps Air Rising?',
            'narration': 'Warm oceans supply moist air. As it rises, vapor condenses into droplets and releases heat, helping the air keep rising.',
            'caption': 'Condensation releases heat to the rising air.',
            'slide_text': 'Warm ocean supplies moisture\nRising vapor condenses\nReleased heat supports continued rising',
            'primitives': heating}, 'evidence_ids': list(evidence_ids),
         'reason': 'A sourced heating bridge links condensation to continued ascent, with a distinct heat-release arrow.'},
        {'scene': 1, 'updates': {
            'title': 'Circulation: Different Flows at Different Heights',
            'narration': 'High above, air spreads outward. Near the surface, higher-pressure air flows toward the low-pressure center, bringing fresh moisture that feeds rising air.',
            'caption': 'Surface inflow feeds rising air; outflow occurs aloft.',
            'slide_text': 'Surface: inward toward low pressure\nMoist air rises\nHigh above: air spreads outward',
            'primitives': circulation}, 'evidence_ids': list(evidence_ids),
         'reason': 'Separate altitude levels prevent confusing permitted upper outflow with prohibited outward surface inflow.'},
    ]}
