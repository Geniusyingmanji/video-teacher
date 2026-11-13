"""Criterion-specific failure and high-score evidence anchors. Development rubric."""

# Each tuple is (major defect, merely adequate, evidence needed for excellence).
ANCHOR_ROWS = {
'visual_quality': {
'legibility': ('Essential words/formulas cannot be read at native size.', 'Most labels can be read but some require effort or pausing.', 'Inspect the smallest essential labels at native size and their actual hold intervals.'),
 'text_overlap': ('Collisions hide essential symbols or merge separate labels.', 'Local contact/collision is visible but most content remains recoverable.', 'Check dense regions, moving objects and all diagram labels; identify clear separation.'),
 'containment': ('Essential text is cut off or repeatedly exits its intended container.', 'Several labels touch/cross borders or have cramped padding.', 'Check small boxes/circles and all frame edges; external labels must remain clearly external.'),
 'composition': ('Crowding/grouping prevents identifying which label belongs to which object.', 'Grouping is usable but spacing, alignment or hierarchy is inconsistent.', 'Show how scale, grouping and alignment preserve object-label association across scene types.'),
 'contrast': ('Essential text or marks blend into their actual local background.', 'Some labels have weak local contrast but remain decipherable.', 'Inspect the weakest-contrast label/mark, especially colored text on colored fills; overall brightness is not evidence.'),
 'artifact_control': ('Corrupted/missing glyphs or visual artifacts change essential content.', 'Local rendering defects remain but content is mostly decipherable.', 'Inspect small notation, curves and strokes for clean rendering across representative frames.'),
},
 'temporal_consistency': {
 'identity': ('An object silently becomes another object or changes identifying attributes.', 'Identity is mostly stable with occasional distracting changes.', 'Track the same objects through each available transition; a single frame cannot establish stability.'),
 'motion': ('Observed movement jumps, reverses or disappears without explanation.', 'Movement/stillness is usable but some jitter or rough changes are visible.', 'Use adjacent dense frames to trace movement, or explicitly establish intentional stable holds.'),
 'state_continuity': ('Labels or quantities silently change to incompatible states.', 'Most states persist but a local unexplained inconsistency remains.', 'Compare named quantities, labels and geometry before/after each observed state change.'),
 'transitions': ('Cuts destroy necessary object/context continuity.', 'Order remains understandable despite abrupt or weakly linked cuts.', 'Identify what is preserved and what changes at actual sampled boundaries.'),
 'event_integrity': ('An initiated visual event freezes, vanishes or is visibly truncated.', 'Events usually complete but some endings are rough or unclear.', 'Observe the initiated event and resulting state; a written completion claim is insufficient.'),
 'temporal_readability': ('Essential information disappears before it can be perceived.', 'Main content is perceivable but some changes/holds demand pausing.', 'Cite time intervals and content load for the fastest essential segment; still frames alone cannot prove dwell time.'),
 },
 'audio_quality': {
 'intelligibility': ('Essential words are unintelligible or spoken narration is absent.', 'Speech is mostly understandable but some words require effort.', 'Listen to the least clear segment and identify audible words; script plausibility is irrelevant.'),
 'signal': ('Noise, clipping, dropouts or silence make the signal unusable.', 'Signal is usable with noticeable local defects.', 'Check quiet/loud portions and segment boundaries in the actual audio.'),
 'delivery': ('Speech articulation or rhythm prevents following sentences.', 'Speech is understandable but mechanical, rushed or awkward.', 'Describe actual articulation and pacing at the most demanding sentence, not merely speech presence.'),
 'pronunciation': ('Key terms/numbers are acoustically mangled or speech is absent.', 'Terms can be recognized but some articulation is ambiguous.', 'Identify actual heard technical terms/numbers and their clarity; do not infer from screen text.'),
 'continuity': ('Words/sentences are cut off or broken by disruptive gaps.', 'Sentences mostly survive but local starts/endings are rough.', 'Listen to the starts, endings and boundaries of the actual chunk, preserving sampling limits.'),
 'level_stability': ('Speech volume is inaudible or changes so much that listening fails.', 'Levels are usable but have noticeable imbalance.', 'Compare actual loud/quiet portions and boundaries; no cross-chunk claim from one chunk.'),
 },
 'conceptual_correctness': {
 'facts': ('A central taught fact is false.', 'Central facts are right but some statements are imprecise or insufficiently qualified.', 'Check each substantive taught claim against task/reference and actual content, including limiting conditions.'),
 'relationships': ('A central causal, directional, spatial or logical relation is wrong.', 'The relationship is broadly right but local ambiguity/oversimplification remains.', 'Trace arrowheads/endpoints, causal direction, axes or object associations independently of captions.'),
 'notation': ('An essential quantity, sign, unit or label has the wrong meaning/value.', 'Notation is mostly valid with localized ambiguity/inconsistency.', 'Read actual symbols/numbers and map each to its visible object; do not trust a title or fluent narration.'),
 'reasoning': ('An essential inference or intermediate operation is invalid.', 'The main inference is valid but justification has a local gap.', 'Reconstruct the shown inference from actual givens and intermediate states; correctness of the final answer alone is insufficient.'),
 'final_state': ('The displayed/spoken final answer or resulting state is wrong.', 'The result is broadly right but qualification/precision is limited.', 'Compare actual final quantities/geometry/labels with the requested outcome.'),
 'no_contradiction': ('A frame or utterance materially contradicts another or the central lesson.', 'No central contradiction, but a localized unresolved ambiguity remains.', 'Actively compare diagram geometry, caption and speech at the riskiest state; do not invent an unstated legend to excuse conflict.'),
 },
 'task_completeness': {
 'givens': ('The task, input values, source objects or required conditions are materially changed.', 'Most givens are retained but a noncentral constraint is unclear.', 'Match all relevant public givens/source objects to actual final media.'),
 'coverage': ('A required subquestion or core requested explanation is absent.', 'Main request is addressed with a secondary omission.', 'Map every explicit public subrequirement to identifiable actual content; do not add reference-only preferences.'),
 'demonstration': ('A requested visual operation is only asserted or shown as an unsupported final answer.', 'The key demonstration is partly visible but some essential transition is unclear.', 'Locate the actual requested operation and result; captions and narration cannot replace a required visual demonstration.'),
 'result': ('The requested result is never delivered in its required modality.', 'The result is present but its conclusion or inspectability is incomplete.', 'Identify the completed public outcome and an adequate observation interval.'),
 'verification': ('A requested check is absent or only says that the answer is correct.', 'A requested check is attempted but does not fully test the result.', 'Locate the actual independent calculation/comparison/check required by the public task; if no check is requested, use not_applicable.'),
 'constraints': ('An explicit prohibition/source-preservation restriction is violated.', 'Restrictions are mostly followed with a local deviation.', 'Check each explicit prohibition against final evidence; if the task has no such restrictions, use not_applicable.'),
 },
 'pedagogical_clarity': {
 'focus': ('The learning target cannot be identified or competing messages obscure it.', 'The target is identifiable with some distraction or reconstruction.', 'Identify the actual teaching target and how essential information remains focused on it.'),
 'attention': ('Cues direct attention to wrong objects or competing cues hide the key step.', 'Cues are helpful but sometimes late, weak or distracting.', 'Check cues at the moment of a difficult step; mere presence of colors/arrows is insufficient.'),
 'why': ('The requested mechanism/reasoning is replaced by naming or asserting the answer.', 'The basic explanation is understandable with some unbridged steps.', 'Locate the explanation of why the key transition follows, in permitted visual and/or spoken evidence.'),
 'readability': ('The audience cannot follow essential labels/changes within actual time.', 'The sequence is followable with some effort or pausing.', 'Check the densest/fastest teaching segment using actual content load and duration.'),
 'grounding': ('Conditions, operations, results or symbol referents are confused.', 'Main referents are recoverable with localized ambiguity.', 'Identify each essential symbol/object and distinguish initial condition, operation and outcome.'),
 'takeaway': ('The requested conclusion is absent or contradictory.', 'The conclusion is present but its meaning is weakly connected to the lesson.', 'Identify a clear task-specific conclusion supported by the preceding explanation, without demanding a fixed recap template.'),
 },
 'instructional_structure': {
 'setup': ('The initial state needed to understand the lesson is absent.', 'The starting context is recoverable but incomplete.', 'Identify the actual starting state and prerequisites needed by this task.'),
 'target': ('The question/intended change is not identifiable.', 'The aim becomes clear only after reconstruction.', 'Identify where the learner can understand the task-specific aim without extra unstated context.'),
 'order': ('Steps are reversed or disconnected so the explanation cannot be followed.', 'The main order works with some abrupt jumps.', 'Trace the actual sequence of prerequisite, operation and consequence; do not impose a preferred lesson template.'),
 'transition': ('The key instructional transition is omitted or only promised.', 'The transition is partly explained but a meaningful gap remains.', 'Locate the key change and the explanatory bridge linking its preceding and resulting states.'),
 'closure': ('The result is not observable or the explanation is cut off.', 'The result appears but its closure/hold is weak.', 'Observe the completed state for a sufficient interval; a formal summary heading is not mandatory.'),
 'chunking': ('Too many simultaneous/rapid events prevent following the main reasoning.', 'Segmentation is usable with locally dense/rushed stretches.', 'Inspect information density and actual scene timing at the most demanding part.'),
 },
 'visual_teaching': {
 'representation': ('The requested relation/state lacks a usable concrete representation.', 'A relevant representation exists but leaves an important aspect implicit.', 'Point to actual geometry/state/changes that represent the public task; decorative motion does not count.'),
 'explanatory_value': ('A required operation is replaced by decorative motion or answer-only text.', 'Visuals support the topic but explain the key operation only partly.', 'Identify what the visual teaches that an unsupported assertion would not; localized labeling can suffice when that is the task.'),
 'reference_anchor': ('Changing scales/objects/correspondences make the intended comparison misleading.', 'A comparison is possible with weak or unstable anchors.', 'Track stable reference objects/scales needed by this explanation; do not invent an unnecessary axis or quantitative scale.'),
 'correspondence': ('Arrows, shapes, labels or colors map to the wrong knowledge relationships.', 'Mappings are broadly right with localized ambiguity.', 'Trace actual arrowheads/objects, label attachment and legends; a true caption cannot certify incorrect geometry.'),
 'inspectability': ('Essential results are hidden or impossible to inspect.', 'The result can be inspected but some relevant details are ambiguous.', 'Point to visible details that allow the result to be checked, with native-size limitations retained.'),
 'diagnosability': ('The display would look the same for a materially wrong answer/step.', 'Some mistakes would be visible but a key distinction is hidden.', 'Identify the visible state/quantity/relation that distinguishes correct from incorrect execution.'),
 },
 'audience_appropriateness': {
 'prerequisites': ('Essential assumed knowledge is materially above the stated audience.', 'The assumed background is broadly suitable but some bridging is missing.', 'Identify actual prerequisites and their match/bridging for the stated audience.'),
 'language': ('Unexplained essential terminology makes the lesson inaccessible.', 'Language is mostly suitable but some terms remain unexplained.', 'Check the hardest actual terminology and its explanation for this audience.'),
 'complexity': ('Simultaneous information overload prevents the audience following the lesson.', 'Load is manageable except for some dense regions.', 'Inspect the densest segment, its grouping and the audience-specific load.'),
 'speed': ('The audience has insufficient time to follow essential steps.', 'Pacing is broadly suitable with a rushed/slow segment.', 'Use actual duration and information load at the fastest essential step, not generic praise of pacing.'),
 'accessibility': ('Color/contrast/scale hides essential distinctions for the stated audience.', 'Content is mostly perceptible with localized barriers.', 'Check smallest/lowest-contrast essential content and whether color-only distinctions remain understandable.'),
 'depth': ('The explanation is materially too shallow/advanced for the stated task and audience.', 'Depth meets the basic request with limited useful elaboration.', 'Show task-relevant explanatory depth at the stated audience level without imposing extra curriculum.'),
 },
 'crossmodal_alignment': {
 'referents': ('Speech identifies different objects/quantities from those currently visible.', 'Main referents agree with some ambiguous local references.', 'Map spoken terms to the actual contemporaneous labels/objects.'),
 'synchrony': ('Speech explains a different scene/step for a substantial interval.', 'Speech broadly follows the visual with noticeable local offsets.', 'Cite matched utterance times and actual visual events; appearance elsewhere in the video is insufficient.'),
 'agreement': ('Speech and the current diagram assert incompatible central relationships.', 'Main claims agree but a local mismatch/ambiguity remains.', 'Compare literal spoken claims with independently traced diagram geometry/quantities.'),
 'text_visual_consistency': ('On-screen text asserts a relationship contradicted by arrows/geometry.', 'Text and diagram mostly agree with a local ambiguity.', 'Read caption claims and trace arrowheads, endpoints, counts or axes independently; no invented convention to excuse a conflict.'),
 'state_tracking': ('Narration persistently describes a previous/future incompatible state.', 'Current state is usually tracked with some local lag/lead.', 'Check whether narrated operations refer to the visible current state in each paired probe.'),
 'completion_claims': ('The narrated/screen conclusion contradicts the shown outcome, or the required outcome is observably never delivered.', 'The conclusion is broadly supported but some relevant endpoint is unclear.', 'Compare the substantive concluding statement with the visible outcome at that time. A recap such as active puts the doer first is a conclusion even without the words done or complete. A completion label alone is insufficient.'),
 },
}

# Explicit levels for criteria whose broad wording admitted generic full-score praise.
# Levels describe observed performance, not a target distribution. The evidence and
# boundary fields are sent to judges through DIMENSIONS and shared with human raters.
CRITERION_DETAILS = {
    'pedagogical_clarity': {
        'why': {
            'levels': {
                '1': 'The required explanation is absent: only a topic, operation list or answer is presented, with no account of the central mechanism.',
                '2': 'An explanation is attempted, but the central inference is asserted without its rule or causal link, so a necessary reasoning step is missing.',
                '3': 'The main rule or cause is stated, but its application to a specific essential step remains implicit and needs reconstruction.',
                '4': 'Essential steps are linked to their rules or causes; one localized wording or connection remains imprecise but the main reasoning is followable.',
                '5': 'Each task-essential inference explicitly connects its starting condition, applicable rule or cause, and consequence at the stated audience level.',
            },
            'evidence': 'Name the most demanding inference, its before/after states, and the actual words or visual relation explaining the rule. A title such as Balance Principle alone is insufficient.',
            'boundary': 'Score explanation of why here. Score factual validity under conceptual_correctness and a missing required visual demonstration under task_completeness. Speech can explain why unless the public task requires visual evidence.',
        },
        'readability': {
            'levels': {
                '1': 'Essential teaching elements cannot be located or related, leaving the main step uninterpretable.',
                '2': 'The main step requires repeated searching among unlinked labels, formulas or states; an essential explanatory association is obscured.',
                '3': 'The step can be reconstructed, but one necessary association requires backtracking or unsupported visual search.',
                '4': 'Givens, operation and result can be followed with only a minor local search or cue ambiguity.',
                '5': 'At every inspected essential step, placement and cues directly connect the givens, operation and result without requiring reconstruction of their associations.',
            },
            'evidence': 'Identify the densest step and the exact elements that must be connected; trace the actual cue or spatial association rather than saying text is clear.',
            'boundary': 'This item concerns instructional search and association. Glyph size/contrast belongs to visual_quality; time to process an otherwise clear step belongs to audience_appropriateness.speed. Do not duplicate a deduction without a separate observed consequence.',
        },
        'grounding': {
            'levels': {
                '1': 'The core symbols or objects lack identifiable referents, so givens, operations and results cannot be distinguished.',
                '2': 'A central symbol or spoken reference remains ambiguous at a necessary step and prevents interpreting that step.',
                '3': 'The main referents are recoverable, but an essential definition arrives late or requires inference from context.',
                '4': 'Essential referents are introduced and maintained; a local naming ambiguity is recoverable without changing the main interpretation.',
                '5': 'All essential symbols and references in the inspected lesson are grounded by their first needed use, and initial values, operations and resulting values remain distinguishable.',
            },
            'evidence': 'List the hardest symbol or pronoun reference, its first use and its visible/spoken definition. Show how the referent persists into the next relevant step.',
            'boundary': 'Ambiguous definition is grounding; an unambiguously wrong value or relationship is correctness. A clear referent introduced in speech need not also have a separate written definition.',
        },
    },
    'instructional_structure': {
        'transition': {
            'levels': {
                '1': 'The central teaching progression is absent or disconnected: the lesson jumps to an outcome without establishing a usable preceding state.',
                '2': 'An essential before-to-after transition is omitted or merely promised, breaking the instructional chain.',
                '3': 'The before/after states are present, but the bridge between them is partly implicit or introduced too late.',
                '4': 'Essential transitions identify what changes and preserve the needed context, with a minor local handoff ambiguity.',
                '5': 'Each essential handoff connects the preceding state, the intended change and the next state through clear spoken and/or visual cues permitted by the task.',
            },
            'evidence': 'Trace a specific boundary between two dependent teaching steps and cite the content that connects them. A crossfade or Next heading is not an explanatory bridge.',
            'boundary': 'This is instructional linkage, not visual transition smoothness. The reason an operation is valid belongs to why. Continuous animation is not mandatory unless the public task requests it.',
        },
        'chunking': {
            'levels': {
                '1': 'Several dependent operations are presented together without separable states, making the central sequence uninterpretable.',
                '2': 'A core operation is overwritten or combined with another before its needed intermediate state is established.',
                '3': 'The main sequence is segmented, but one teaching unit combines dependent operations that require reconstruction.',
                '4': 'Operations form coherent units with preserved context; a minor local grouping issue remains.',
                '5': 'Task-essential dependent operations are staged in interpretable units, and each unit retains or reintroduces the state needed to understand the next.',
            },
            'evidence': 'Name the dependent operations in the densest unit and identify their actual reveal order and retained intermediate states. Slide count alone is not evidence.',
            'boundary': 'Assess grouping and segmentation here, not total length. Once segmentation is clear, insufficient processing time belongs to audience_appropriateness.speed. Multiple items may share a frame if their dependency is clear.',
        },
    },
    'visual_teaching': {
        'explanatory_value': {
            'levels': {
                '1': 'The required visual explanation is absent; only unrelated decoration or an unsupported conclusion is shown.',
                '2': 'Visuals depict the topic but leave the central required relationship or operation visually unrepresented.',
                '3': 'The main relationship is partly represented, but a necessary visual association or intermediate change must be inferred.',
                '4': 'Visuals expose the essential relationship or operation, with a minor local weakness in its comparison or emphasis.',
                '5': 'The visual encoding makes each essential requested relationship or operation directly inspectable, showing what changes or what corresponds rather than merely naming the result.',
            },
            'evidence': 'Identify the specific relationship taught by a visible encoding and trace its objects, quantities or before/after states. For a labeling task, inspect the actual label-to-object attachment.',
            'boundary': 'Evaluate the explanatory function of visuals, not decorative complexity. Static diagrams, symbolic equations and localized labels can qualify. Narration-only reasoning may be clear while providing little visual explanation.',
        },
        'inspectability': {
            'levels': {
                '1': 'The core result has no observable representation that can be checked.',
                '2': 'The result appears, but an essential endpoint, value or association is hidden, preventing its verification.',
                '3': 'The main result is checkable, but one relevant detail is only partially visible or ambiguously attached.',
                '4': 'Essential result details are exposed, with a minor ambiguity that does not block the principal check.',
                '5': 'The visible result exposes all task-essential values, endpoints and relationships needed for its check, with unambiguous associations at native display size.',
            },
            'evidence': 'Name the proposed check and the actual details that make it possible, such as both sides of the final equation or the common vertex and outer rays of the final angle.',
            'boundary': 'This is visibility of checkable details, not proof of correctness. A clear wrong answer can be inspectable. Font defects belong to visual_quality; available viewing time belongs to pacing.',
        },
        'diagnosability': {
            'levels': {
                '1': 'The display conceals the task-critical distinction: a materially wrong result would have the same observable representation.',
                '2': 'Some state is visible, but the specific value or relationship needed to distinguish a plausible central error is not exposed.',
                '3': 'One relevant error could be distinguished, but another essential distinction is obscured or requires an unstated mapping.',
                '4': 'The relevant error alternatives are distinguishable, with a minor ambiguity in one visible indicator.',
                '5': 'For each essential distinction needed by the task, the display exposes a concrete value or relationship that separates the shown execution from a plausible wrong alternative.',
            },
            'evidence': 'State one concrete wrong alternative and the exact visible feature that would differ. For 2x+5=17, compare subtracting 5 on both sides with doing so on only one side, using the actual displayed states.',
            'boundary': 'This is an evaluator counterfactual about visible information, not measured student error detection. Do not require the video to include a deliberate wrong example. Clear procedure or errors would stand out is not specific evidence.',
        },
    },
    'audience_appropriateness': {
        'depth': {
            'levels': {
                '1': 'The lesson never develops the requested concept at a level usable by the stated audience.',
                '2': 'A central prerequisite bridge is missing, or unexplained advanced material makes the core explanation inaccessible for the stated audience.',
                '3': 'The main task is addressed, but one audience-relevant bridge remains compressed or an unnecessary advanced detour obscures it.',
                '4': 'Task-essential explanations match the audience prerequisites, with a minor over-compression or digression.',
                '5': 'The lesson develops the requested rule or mechanism through the prerequisite bridges needed by the stated audience, with sufficient task-relevant detail and without inaccessible or distracting detours.',
            },
            'evidence': 'Name the audience, the hardest prerequisite or inference, and the actual explanation bridging it. More topics, longer duration and generic praise of balance do not establish depth.',
            'boundary': 'Assess audience fit, not factual truth or real learning. Do not demand additional examples, a formal proof or extra curriculum unless the public task or its necessary explanation requires them.',
        },
        'speed': {
            'levels': {
                '1': 'Essential steps repeatedly vanish before the stated audience could perform the required reading or comparison, making the lesson unusable.',
                '2': 'A central step gives too little observed time for its required processing, so following the explanation requires pausing or replaying it.',
                '3': 'The lesson is broadly followable, but one demanding step is rushed or an extended uninformative hold disrupts progression.',
                '4': 'Essential steps allow their required processing, with a minor local rush or unnecessary wait.',
                '5': 'Observed processing intervals accommodate the reading, comparison and reasoning of each inspected essential step for the stated audience; changes follow adequate inspection of their prerequisites.',
            },
            'evidence': 'Identify the most demanding segment, its observed time interval and the reading/comparison/reasoning it requires. Use matched timing evidence; sparse endpoints alone do not prove uninterrupted dwell.',
            'boundary': 'This is an evidence-based pacing judgment, not an actual student learning measurement. Do not impose universal words-per-minute or fixed-seconds thresholds. Missing timing evidence remains unverified.',
        },
        'accessibility': {
            'levels': {
                '1': 'The core distinctions cannot be identified through the available visual or spoken cues.',
                '2': 'An essential distinction depends on a locally indistinguishable or ambiguous color cue without a usable label, shape, position or spoken referent.',
                '3': 'Essential distinctions are mostly recoverable, but one weak cue requires inference or repeated matching.',
                '4': 'Essential distinctions have usable identifying cues; a minor local cue ambiguity remains.',
                '5': 'Essential distinctions remain identifiable through explicit labels, shapes, positions or spoken references, including where colors are similar or otherwise insufficient.',
            },
            'evidence': 'Name the hardest pair of objects/states to distinguish and the actual identifying cue beyond an insufficient color difference. No failure should be inferred solely because color is used.',
            'boundary': 'Do not claim universal accessibility or assume an unstated disability. Native-size legibility and local contrast belong to visual_quality; score here only a distinct failure to identify instructional categories or referents.',
        },
    },
    'crossmodal_alignment': {
        'completion_claims': {
            'levels': {
                '1': 'A central conclusion claims an outcome that is visibly absent or contradicted at the end of the required demonstration.',
                '2': 'An explicit completed-state claim materially disagrees with the contemporaneous outcome, including a central operation still being unfinished when declared complete.',
                '3': 'The concluding claim broadly fits the result, but a localized timing or referent ambiguity remains.',
                '4': 'Substantive conclusions match their visible outcomes, with a minor local ambiguity that does not misstate completion.',
                '5': 'Each observed substantive conclusion or completed-state claim is supported by its contemporaneous visible result, with the named quantities, objects or relations matching.',
            },
            'evidence': 'Quote the actual conclusion, classify it as a completed-state claim or substantive recap, and identify the paired frame/time and visible supporting state. For moved to a common vertex, verify the shared vertex at the claim time.',
            'boundary': 'Move and Moving are instructions/ongoing actions, not completion claims. A later correct result cannot excuse an earlier false completed-state claim. A recap needs no done/complete wording; an observed absent required conclusion is a defect, while unavailable timing is unverified.',
        },
    },
}

for _dimension, _items in CRITERION_DETAILS.items():
    for _criterion, _detail in _items.items():
        ANCHOR_ROWS[_dimension][_criterion] = (
            _detail['levels']['2'], _detail['levels']['3'],
            _detail['levels']['5'] + ' Evidence: ' + _detail['evidence'])

STRICT_INSTRUCTIONS = '''For every observed criterion also return severity (none|minor|moderate|major|critical),
limitation (the strongest actual defect, or "none observed"), and high_score_evidence (specific
support for a score 5; empty otherwise). These are concise findings, not hidden reasoning.
Use only integer rating levels 1, 2, 3, 4, 5.
Severity/score consistency: critical=1; major=2; moderate=3; minor=4; none=4 or 5. Score 5 is not the default for basically correct content.
It requires the criterion-specific excellent evidence and no established contradiction.
Where criterion_details are provided, use their levels, evidence and boundary together.
In reason/high_score_evidence answer the specified evidence question with actual objects,
claims or intervals. Generic praise does not meet an evidence requirement. A score 4 with
severity=none can describe strong observed performance that does not meet the explicit
level-5 condition; if observation itself is insufficient, use unverified, not an invented flaw.
Do not score one defect repeatedly across neighboring criteria without identifying a separate
effect covered by each criterion's boundary. Correctness can be excellent on a simple task;
it does not confer excellence on organization, audience fit or visual explanation.
A localized visible error cannot be cancelled by many easy correct frames. Judge its educational
importance and persistence, not a desired score distribution. Do not invent faults or add task requirements.
The only optional criteria are task_completeness.verification and task_completeness.constraints:
when the public task contains no such request/restriction, return status=not_applicable, score=null,
evidence_ids=[], and a concrete applicability reason. Never use not_applicable for an observed omission.
Do not use it for any other criterion. Unavailable evidence remains unverified, not not_applicable.
No criterion receives credit merely because its corresponding requirement was not requested.'''

OPTIONAL_CRITERIA={'task_completeness.verification','task_completeness.constraints'}
BANDS={'critical':(1,1),'major':(2,2),'moderate':(3,3),'minor':(4,4),'none':(4,5)}


def validate_strict_item(item,name,key):
    score=item.get('score');status=item.get('status')
    if status=='not_applicable':
        if name+'.'+key not in OPTIONAL_CRITERIA:raise ValueError('criterion is not optional')
        if not (item.get('applicability_reason') or item.get('reason')):raise ValueError('not_applicable needs public-task justification')
    if status!='observed':return
    if type(score) not in (int,float) or not 1<=score<=5 or score!=round(score):
        raise ValueError('observed ratings must use integer levels 1..5')
    band=BANDS.get(item.get('severity'))
    if band is None or not band[0]<=score<=band[1]:raise ValueError(f'{name}.{key}: severity {item.get("severity")} contradicts score {score}; expected {band}')
    if not isinstance(item.get('limitation'),str) or not item['limitation'].strip():raise ValueError('strongest limitation or none observed is required')
    if score==5 and (not isinstance(item.get('high_score_evidence'),str) or not item['high_score_evidence'].strip()):
        raise ValueError('high score needs criterion-specific supporting evidence')


def score_review_conflicts(checks,dimensions):
    conflicts=[]
    for check in checks:
        if check.get('verdict')!='fail':continue
        for item in check.get('affected',[]):
            dimension,criterion=item.split('.')
            row=dimensions.get(dimension,{}).get('criteria',{}).get(criterion,{})
            score=row.get('score')
            if score is None:continue
            maximum={'critical':1,'major':2,'moderate':3,'minor':4}.get(check.get('severity'),2)
            incompatible=score>maximum
            if incompatible:conflicts.append({'check':check['id'],'criterion':item,'score':score,
                'review_severity':check.get('severity'),'reason':'Scoring and independent evidence review disagree; no numerical rating has been edited.'})
    return conflicts
