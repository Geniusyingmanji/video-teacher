"""Detailed criteria for full narrated-video and layout assessment.
Not human-calibrated; no target score distribution.
"""

CRITERIA = {
    "conceptual_correctness": {
        "facts": "The central scientific or factual claim is correct.",
        "relationships": "Causal, spatial, or logical relationships are correct.",
        "notation": "Numbers, labels, equations, and units are correct and stable.",
        "reasoning": "Shown operations or intermediate states follow valid rules.",
        "final_state": "The visible result or answer matches the task.",
        "no_contradiction": "No frame contradicts the intended lesson."
    },
    "instructional_structure": {
        "setup": "The starting state is identifiable.",
        "target": "The intended change or question is identifiable.",
        "order": "Visible events occur in a comprehensible order.",
        "transition": "At each essential instructional transition, the lesson identifies what changes and connects the preceding state to the next step through the modalities permitted by the task.",
        "closure": "The resulting state is visible long enough to inspect.",
        "chunking": "Operations that depend on one another are introduced in separable teaching units, retaining the prior state needed to interpret the next unit; inspect the densest segment rather than counting slides."
    },
    "pedagogical_clarity": {
        "focus": "The stated audience can identify the one task and learning target without reconstructing omitted context.",
        "attention": "Cues guide the audience to the critical object or step at the right time, without competing highlights.",
        "why": "For each task-essential inference or mechanism, the spoken and/or visual explanation connects the given condition, the applied rule or cause, and the resulting change; naming an operation alone does not explain why it is valid.",
        "readability": "At an essential teaching step, labels and explanatory cues let the viewer locate and connect the givens, operation and result during playback; score instructional search effort, not glyph quality or presumed learning gains.",
        "grounding": "Each essential symbol, quantity and spoken reference has an identifiable referent at first use; givens, operations and results are distinguished without the viewer inventing a mapping.",
        "takeaway": "The final visible state communicates the requested conclusion without needing an off-screen explanation."
    },
    "visual_teaching": {
        "representation": "A concrete representation makes the task-relevant state, relation or before-and-after change visible; decorative movement and answer-only text do not substitute for a requested demonstration.",
        "explanatory_value": "Identify the task-relevant relationship or operation made inspectable by the visual encoding, such as changes to both sides of an equation; topic-related decoration or a conclusion caption alone is insufficient. Correctly localized labels can suffice for a labeling task.",
        "reference_anchor": "Stable objects, scales or correspondences support comparison and reveal the intended relationship without misleading changes.",
        "correspondence": "Visual shapes, positions, arrows, colors and labels map accurately to the knowledge being explained; an analogy, if used, preserves the relevant relationship.",
        "inspectability": "The actual result exposes the essential quantities, endpoints, labels or relationships needed to check it at native display size; pausing may locate evidence but cannot establish adequate playback time.",
        "diagnosability": "Name a concrete task-relevant alternative error and identify which visible quantity or relationship would distinguish it from the shown result; this is inspectability of an error, not proof that a student actually detects one."
    },
    "audience_appropriateness": {
        "prerequisites": "The clip fits the stated audience's prior knowledge.",
        "language": "Terminology and symbols suit that audience.",
        "complexity": "The visual load is manageable for that audience.",
        "speed": "Compare the observed time available for the most demanding step with the reading, comparison and reasoning it asks of the stated audience; speech rate or total duration alone cannot establish appropriate pacing.",
        "accessibility": "Essential distinctions remain identifiable through labels, shapes, positions or spoken naming when a color cue alone is insufficient; assess perceptual access separately from font rendering and do not assume unstated user impairments.",
        "depth": "The explanation develops the task-essential rule or mechanism to the stated audience's prerequisite level, without skipping a necessary bridge or adding inaccessible detail; evaluate audience fit, not topic count or measured learning."
    },
    "visual_quality": {
        "legibility": "Essential text, formulas and labels are readable at native display size and during the actual hold; enlarged crops help diagnose defects but do not establish native readability.",
        "text_overlap": "Text lines and labels do not collide with each other or become obscured by unrelated arrows, marks or shapes.",
        "containment": "Text fits its intended container with usable padding; no essential text or glyph is clipped by a box, viewport, or frame edge.",
        "composition": "Alignment, grouping, spacing and visual hierarchy clearly separate the title, diagram, labels and caption without crowding or excessive dead space that makes essential content tiny.",
        "contrast": "Text and essential diagram strokes contrast adequately with their actual local backgrounds; color choices do not hide content.",
        "artifact_control": "Glyphs, equations, lines and shapes are rendered cleanly without corruption, missing characters, or intrusive artifacts."
    },
    "temporal_consistency": {
        "identity": "Objects and diagrams preserve identity through time unless intentionally transformed.",
        "motion": "Initiated motions follow coherent trajectories without unexplained jumps, flicker or reversals. Intentional stillness is acceptable.",
        "state_continuity": "Labels, quantities and visual states remain consistent between steps, or visibly change when intended.",
        "transitions": "Cuts and transitions preserve the context needed to follow the visible events.",
        "event_integrity": "A visibly initiated action progresses without accidental freezes, disappearance or truncation; do not infer an omitted task from task-free frames.",
        "temporal_readability": "Visible changes and holds provide sufficient time to perceive and inspect essential text or events."
    },
    "audio_quality": {
        "intelligibility": "Spoken words are intelligible throughout the actual audio.",
        "signal": "Audio is free of disruptive noise, distortion, clipping or dropouts.",
        "delivery": "Speech articulation and rhythm support sustained listening; speech is actually present.",
        "pronunciation": "Audible technical terms, numbers and symbols are pronounced distinctly; assess acoustic clarity, not factual truth.",
        "continuity": "Sentences and word endings are complete without cut-off speech or accidental gaps.",
        "level_stability": "Speech volume remains usable and reasonably stable across segments."
    },
    "task_completeness": {
        "givens": "The actual task, quantities, original objects and constraints are preserved.",
        "coverage": "All explicitly required subquestions, concepts and operations are addressed with identifiable evidence.",
        "demonstration": "Every explicitly required visual demonstration is actually visible; narration or a final answer alone does not replace it.",
        "result": "The requested final result is shown or spoken in the modality required by the task and held long enough to inspect.",
        "verification": "Any requested verification actually checks a relationship or answer, rather than simply repeating it or saying it is correct.",
        "constraints": "Explicit prohibitions and source-preservation constraints are obeyed; no unauthorized target changes are visible."
    },
    "crossmodal_alignment": {
        "referents": "Spoken references identify the same objects, labels and quantities visible at that time.",
        "synchrony": "The spoken explanation accompanies the relevant visible step at an instructional timescale.",
        "agreement": "Speech and the visible diagram make compatible claims about relationships, direction, quantities and operations.",
        "text_visual_consistency": "On-screen text, arrowheads, labels and geometry agree about the represented relationship; do not excuse a contradiction using an unstated convention.",
        "state_tracking": "Narrated changes correspond to the actual current visual state, without silently describing a prior or future scene.",
        "completion_claims": "Compare each observed substantive conclusion or completed-state claim with the visible outcome at that time. Separate instructions and ongoing actions from claims of completion; a later correct endpoint does not justify an earlier false completed-state claim."
    }
}

ANCHORS = """Use only integer rating levels 1, 2, 3, 4, 5. Anchors: 1 unusable or required content absent; 2 major defect; 3 adequate with visible limitations; 4 strong with minor defects; 5 exceptional and fully demonstrated with specific evidence. Meeting a checklist is not automatically 5. Describe the strongest observed limitation before assigning a rating; if no defect is established, say so. Do not invent a defect to lower a score. Ordinary adequacy and absence of obvious failure are not evidence of exceptional execution. Missing observations are unverified, not low performance. Do not impose decorative complexity or content beyond the public task. Cite actual affected objects, relationships, time intervals or layout regions. Treat an unlabelled alternative interpretation as uncertain or ambiguous when the visible labels conflict with it; do not silently invent a legend."""


VISUAL_GUIDES = {
    'legibility': {'1':'Essential labels cannot be read at native size.',
                  '3':'Most text is readable but some required labels are too small or demand pausing.',
                  '5':'All essential text is immediately legible at native size, with visibly effective scale across the observed lesson.'},
    'text_overlap': {'1':'Collisions or occlusion make essential content unreadable.',
                     '3':'Localized collisions degrade reading while most content remains accessible.',
                     '5':'Clear separation is specifically evidenced across dense as well as sparse regions; no established collisions.'},
    'containment': {'1':'Essential text is cropped away or repeatedly exits its intended box/frame.',
                    '3':'Several glyphs touch/cross intended borders or padding is consistently cramped.',
                    '5':'Labels have comfortable verified padding in their actual containers throughout the inspected frames; external labels remain distinct.'},
    'composition': {'1':'Grouping and hierarchy cannot be followed due to severe crowding/disorganization.',
                    '3':'Usable grouping with visible uneven spacing, crowding or tiny content in an oversized empty layout.',
                    '5':'Consistent alignment, meaningful grouping and scale direct attention clearly across all inspected scene types.'},
    'contrast': {'1':'Essential labels or marks disappear into their local backgrounds.',
                 '3':'Some weak contrast requires effort but most essential content remains visible.',
                 '5':'Strong local distinction is evident for every essential label and mark, including text over colored shapes.'},
    'artifact_control': {'1':'Corrupted glyphs or rendering artifacts prevent comprehension.',
                         '3':'Localized malformed glyphs, ragged lines or artifacts are visible but most content survives.',
                         '5':'Glyphs, formulas and diagram strokes remain clean at native size across inspected frames.'},
}
