# Round-two image probe on another machine

This entry point reproduces the **11-case image-backed GRADE probe**, not an
approved 60-case result. The earlier remote attempt was stopped before any
video completed. The 60-case list remains provisional in
`data/prompts/round2_candidate_60.jsonl`.

On a Linux machine with a CUDA GPU, Python 3.10, adequate RAM and disk space:

```bash
git clone https://github.com/Geniusyingmanji/video-teacher.git
cd video-teacher
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
CUDA_VISIBLE_DEVICES=0 bash scripts/run_round2_grade_probe.sh
```

The run script downloads the 11 GRADE source images from their original
dataset repository when they are absent. It verifies their hashes against
`data/round2_grade_probe11/image_manifest.jsonl`, converts them into local
first frames, and downloads the official Wan2.2 TI2V 5B Diffusers checkpoint
when no local checkpoint exists. The model repository is about 34 GB, so allow
additional space for the cache and generated videos. Third-party images and
model weights are deliberately not committed to this repository.

By default the command generates **one** case as a smoke run. After checking
that output, run all 11 with:

```bash
ROUND2_LIMIT=0 CUDA_VISIBLE_DEVICES=0 bash scripts/run_round2_grade_probe.sh
```

The runner resumes completed cases whose input and video hashes match. Its
outputs are under `results/round2_grade_probe11/`. To reuse an existing
checkpoint, set `MODEL_PATH=/absolute/path/to/Wan2.2-TI2V-5B-Diffusers`.
To use a different Python interpreter, set `PYTHON`.

`--cpu-offload` reduces GPU model memory use but still needs enough free GPU
memory for video activations. Preflight checks the model, images, Python
packages and CUDA before generation; it does not certify visual quality.
Inspect the generated clips before treating them as usable teaching videos.
