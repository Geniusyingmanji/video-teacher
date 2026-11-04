# Generation-first delivery and evidence reconciliation (v11)

Generation success means a decodable full-duration video with actual English spoken narration. Quality acceptance is recorded separately. Run the frozen ten tasks with `--generation-profile draft --evaluate-draft --workers-per-gpu 2 --gpus 0 1 --ports 8000 8001`. Runtime and TTS failures remain generation failures; they are never renamed quality warnings. Draft retains layout, pacing, and coverage defects for evaluation. It does not replace a failed task or invent a successful result. Attempts are bounded; ten successful videos are a measured outcome, not a guarantee from configuration.

## Resolution and anchors

Use 1..5 with 0.5 increments (nine possible categories). Whole anchors: 1 unusable/absent, 2 major defect, 3 adequate with limitations, 4 strong with minor defects, 5 exceptional with specific evidence. Intermediate values require evidence between adjacent anchors. Scores map to the existing reporting scale using `(rating - 1) * 25`. Decimal totals are arithmetic outputs, not measurement precision. Increasing the number of categories alone does not establish reliability.

## Contradictory evidence

A favorable overview cannot override an inspected essential failure. `eval/evidence_audit.py` declares mappings between local presentation/spoken criteria and corresponding axes. The same anchored scale supplies an upper bound: a major readability defect rated 2 limits the axes that require readable information to 25. This is a non-compensatory assessment design: clear compression cannot compensate for unreadable essential text. It is not an arbitrary subtraction or a rule that all failed videos score low on every axis. Unrelated axes are unaffected. Each bound stores its source, finding, rating, timestamps/local frame citations and previous score. Uncited findings and invalid reviews do not impose bounds. The raw overview is retained.

`layout_guard` also detects actual settled text bounding boxes outside the frame. At least 20% of a text box outside the frame at two distinct checks spanning at least one second is classified as a major clipping defect (rating 2). Smaller or transient clipping is not assigned this rating. The threshold is a declared engineering criterion, not a validated perceptual law. The recorded box, label, fraction and render times permit review. Geometry does not prove conceptual correctness; it is applied only to readability-related axes. Existing frame/window inspection still checks occlusion, reasoning transitions and audio/visual alignment.

Signal/freeze operators return raw measurements and diagnostic proxy indices with `score=null` and `quality_score=false`. Absence of detected noise is not evidence of overall excellence. Motion uses changed-pixel fraction as well as mean intensity difference so small moving line diagrams are not automatically reported as one long duplicate frame. ASR and CV diagnostic failures select evidence for review; silence or a pause does not automatically deduct points.

## Scientific limits and validation

The rubric, cross-links and clipping threshold are explicit and testable but are not yet calibrated against held-out human ratings. Do not claim scientific validity, learning effectiveness, inter-rater agreement or a calibrated uncertainty interval. The same model still generates and judges; this is recorded. Human comparison and defect-controlled tests are required before establishing reliability and validity. Low scores alone do not validate a metric.

Principles: AERA/APA/NCME *Standards for Educational and Psychological Testing* (2014), https://www.testingstandards.net/uploads/7/6/6/4/76643089/9780935302356.pdf (validity evidence and score precision); NIST measurement uncertainty guidance, https://www.nist.gov/itl/sed/topic-areas/measurement-uncertainty (report measurement limitations). These support evidence and validation requirements; neither endorses this project's particular numeric bounds.

Retained v10 evidence regression is saved separately under `results/reports/quality_fix_v11_20261104/`; it is explicitly not a fresh model judgment. Historical videos and scores remain unchanged.
