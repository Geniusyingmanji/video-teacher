# Reproducibility and release checklist

Complete this checklist for the final selected runs. An unchecked item is a
release gap, not implicit evidence that the item does not apply.

## Study freeze

- [ ] Commit/tag identifies the exact code used for every reported result.
- [ ] Prompt JSONL and schema are frozen and hashed.
- [ ] Generator name, revision, precision, scheduler, seed policy, frame count,
      FPS, resolution, steps, and conditioning mode are recorded.
- [ ] Generation manifests and every distributed video have SHA-256 hashes.
- [ ] Failed generations, retries, replacements, and exclusions are retained.
- [ ] Judge deployment identifier, exact prompts, frame-sampling settings, and
      authentication-independent invocation are recorded.
- [ ] Student model revision, quiz hash, random-control policy, decoding
      settings, and protocol metadata are recorded.

## Evidence

- [ ] Raw standard-eval `per_case.jsonl` and `aggregate.json` are retained.
- [ ] Raw TeachQuiz pre/post/random answers and aggregate output are retained.
- [ ] Every matched comparison uses the exact shared case intersection.
- [ ] Paired differences, 95% case-bootstrap CIs, Cohen's dz, paired sign-flip
      p-values, and Holm-adjusted p-values are reported.
- [ ] Multi-seed runs report prompt-level generation variability.
- [ ] Every table can be regenerated from frozen machine-readable inputs.

## Human validation

- [ ] Design and analysis were preregistered before ratings were inspected.
- [ ] Rater qualifications, calibration, consent, and compensation are logged.
- [ ] Each selected video has three valid independent ratings.
- [ ] Reassignments and exclusions are documented without silently scoring
      unplayable videos as zero.
- [ ] Ordinal Krippendorff alpha and judge--human Spearman correlation with
      case-bootstrap CIs are reported per dimension.
- [ ] Raw participant data are access-controlled; released data are anonymized
      and consistent with consent.

## Dataset and licensing

- [ ] Redistribution rights are verified per source and asset type.
- [ ] All rows are `reviewed_release_ready` or explicitly excluded.
- [ ] The three flagged music near-duplicate pairs are adjudicated.
- [ ] Provenance, source URL/version, license, transformation, and asset hash are
      recorded per released row.
- [ ] A data card documents intended use, limitations, known failure modes,
      demographics/locale assumptions, and takedown contact.
- [ ] Train/development/test boundaries are frozen and leakage checks recorded.

## Claims and packaging

- [ ] Claims distinguish automated learner gain from human learning.
- [ ] Claims are limited to short 3–5 s instructional clips unless longer-video
      evidence is added.
- [ ] Model-family claims include an independently developed model baseline.
- [ ] Audio claims are omitted unless an audio-capable protocol is validated.
- [ ] README, STATUS, paper tables, appendix, and released aggregates agree.
- [ ] Release archive includes commands, environment lockfiles, licenses,
      exclusion log, checksums, and a clean-room reproduction walkthrough.
