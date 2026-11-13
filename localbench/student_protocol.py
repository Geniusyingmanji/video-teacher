"""Matched dev5 learner protocols: the only input difference is a notebook."""
from __future__ import annotations

import json

BASELINE = 'student-diagnostics-dev5'
PERCEPTION = 'student-diagnostics-dev5-perception'
VERSIONS = {BASELINE, PERCEPTION}
EXAMPLE = {
    'understandings': [{'claim': 'One observation supported by the supplied media.',
                        'basis': 'visual_observation', 'evidence_ids': ['F00']}],
    'questions': [], 'prerequisite_used': [],
    'state_update': 'What changed in the newly available segment.'}

RULES = '''
Separate visible relationships (basis visual_observation), what text/narration
explicitly CLAIMS (basis media_claim), and your interpretation (basis inference).
For media_claim attribute the statement to the text or narrator; an assertion
does not establish that a diagram demonstrates it. Ground inference in supplied
media or declared prerequisites. Do not solve from your general knowledge.
The prefix marks newly available evidence IDs. Inspect those frames and speech,
and include at least one understanding citing newly available evidence. Do not
merely repeat all earlier lesson steps. Earlier observations can provide context,
but an earlier correct state cannot establish correctness of a later changed
state. Follow actual objects, their relationships and any changes that you see.
If the later state is unclear, express that uncertainty without inventing a fault.
Distinguish ongoing operations from claims about completed results.
If a visual_notebook is present, it contains fallible descriptions by the same
model, not expert truth or extra observations. Check the original images. Agreement
with the notebook alone is not evidence. Absence of a notebook is not a defect.
Report a concrete discrepancy or question when the visible relation conflicts with
a media claim. Questions are optional; do not invent confusion on a clear segment.
Use exactly 1-4 understandings, 0-2 questions, valid evidence IDs and prerequisite
IDs from the profile. Each understanding has exactly claim, basis, evidence_ids;
each question has exactly question, evidence_ids. No extra fields or video score.
'''

REVIEW_RULES = '''
For each understanding check the stated basis: visual_observation needs visible
support; media_claim must explicitly attribute what text/narrator claims;
inference needs media or declared prerequisite support. Check the newly available
frames, including any changed completed state. An earlier correct state or a true
written equation does not validate conflicting later geometry. Inspect all cited
states before marking a claim about them supported. If sampling cannot resolve it,
use unverified. Distinguish an ongoing operation from a completed-result claim.
Any visual_notebook is fallible model text: independently inspect the pixels.
Do not count a defect identified by you as one explicitly identified by the learner.
'''


def student_system(legacy):
    # Replace the complete old schema/example rather than append a conflicting one.
    return (legacy.split('Output JSON only:', 1)[0] + RULES +
            '\nOutput JSON only, following this complete schema example:\n' + json.dumps(EXAMPLE))


def repair_guidance():
    return ('Use exactly this student schema, including basis on EVERY understanding: '+
            json.dumps(EXAMPLE)+'. Allowed basis values: visual_observation, media_claim, inference. '+
            'Keep the same evidence and preserve the substance of your observations. No new evidence is provided.')


def add_recent_ids(observation, previous_cutoff):
    observation['new_evidence_ids'] = [r['id'] for r in observation['frames'] if
        previous_cutoff is None or r['time_s'] > previous_cutoff] + [r['id'] for r in observation['transcripts'] if
        previous_cutoff is None or r['source_chunk_end_s'] > previous_cutoff]
    observation['previous_cutoff_s'] = previous_cutoff


OBSERVER_ADDENDUM = '''
Each frame's description must be self-contained. Do not write "same as the prior
frame" or refer to another frame instead of describing this image. Describe actual
objects and visible spatial relations, including separation, contact and boundaries
where visible. Text stating a relation is a text claim, not proof of that relation.
Avoid page borders/progress bars when they displace descriptions of the lesson objects.
'''
