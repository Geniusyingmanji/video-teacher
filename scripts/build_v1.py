"""Build the complete offline research prototype from checked-in evidence.

No model inference is performed. Missing model runs remain visible in the report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from html import escape
from pathlib import Path

from generation.contract_frame import render_first_frame
from generation.contract_video import render_contract_video
from generation.interactive_lesson import build_from_files
from generation.teaching_contract import load_contracts, prepare_cases
from eval.contract_video_audit import audit_contract_video


ROOT = Path(__file__).resolve().parent.parent
PROMPTS = Path("data/prompts/pilot_v0_1.jsonl")
CONTRACTS = Path("data/teaching_contracts/examples.jsonl")
LESSON = Path("data/interactive/convex_lens.json")

# These names describe stored evidence, not fresh runs performed by this command.
ARMS = (
    ("Wan 5B · 3 秒 · 三维", "results/eval_pilot_v0_1", "standard"),
    ("Wan 5B · 3 秒 · 六维", "results/eval_pilot_v0_1_extended6", "standard"),
    ("Wan 1.3B · 3 秒 · 三维", "results/eval_pilot_v0_1_wan13b", "standard"),
    ("Wan 5B · 5 秒 · 三维", "results/eval_pilot_v0_1_5s", "standard"),
    ("Wan 1.3B · 5 秒 · 三维", "results/eval_pilot_v0_1_wan13b_5s", "standard"),
    ("Wan 5B · 3 秒 · 代理测验", "results/teachquiz_5b_qwen3vl_autoprobe", "proxy"),
    ("Wan 1.3B · 3 秒 · 代理测验", "results/teachquiz_13b_qwen3vl_autoprobe", "proxy"),
)


def read_jsonl(path: Path, id_key: str) -> dict[str, dict]:
    rows = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = row.get(id_key)
        if not isinstance(case_id, str) or not case_id or case_id in rows:
            raise ValueError(f"{path}:{line_number}: missing or repeated {id_key}")
        rows[case_id] = row
    return rows


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_arm(root: Path, label: str, relative: str, kind: str,
                 pilot_ids: set[str]) -> dict:
    directory = root / relative
    aggregate_path = directory / "aggregate.json"
    cases_path = directory / "per_case.jsonl"
    arm = {"label": label, "kind": kind, "path": relative, "available": False}
    if not aggregate_path.is_file() or not cases_path.is_file():
        arm["reason"] = "缺少 aggregate.json 或 per_case.jsonl"
        return arm
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    cases = read_jsonl(cases_path, "id")
    shared = set(cases) & pilot_ids
    arm.update({
        "available": True,
        "rows": len(cases),
        "pilot_overlap": len(shared),
        "missing_pilot_ids": sorted(pilot_ids - set(cases)),
        "extra_ids": sorted(set(cases) - pilot_ids),
        "aggregate_n": aggregate.get("n_total"),
        "aggregate_sha256": digest(aggregate_path),
    })
    if kind == "standard":
        arm["mean_aggregate"] = aggregate.get("mean_aggregate")
        arm["dimensions"] = list(aggregate.get("per_dim_mean", {}))
    else:
        arm["valid_n"] = aggregate.get("n_valid")
        arm["normalized_proxy_gain"] = aggregate.get("overall", {}).get("normalized_gain")
    arm["consistent"] = len(cases) == aggregate.get("n_total") and len(shared) == len(pilot_ids)
    return arm


def link(out: Path, target: Path, label: str) -> str:
    relative = Path(os.path.relpath(target, out)).as_posix()
    return f'<a href="{escape(relative, quote=True)}">{escape(label)}</a>'


def build(root: Path = ROOT, out: Path | None = None) -> dict:
    out = out or root / "results/v1"
    out.mkdir(parents=True, exist_ok=True)
    prompt_path = root / PROMPTS
    prompts = read_jsonl(prompt_path, "id")
    if len(prompts) != 60:
        raise ValueError(f"pilot_v0_1 must have 60 unique prompts; found {len(prompts)}")
    pilot_ids = set(prompts)
    for case_id, row in prompts.items():
        if row.get("task_type") not in {"explanation", "problem_solving"}:
            raise ValueError(f"{case_id}: unsupported task_type")
    disciplines = Counter(row["discipline"] for row in prompts.values())
    tasks = Counter(row["task_type"] for row in prompts.values())

    contracts_path = root / CONTRACTS
    contracts = load_contracts(contracts_path)
    contract_cases = [prompts[case_id] for case_id in sorted(pilot_ids & contracts.keys())]
    prepared = prepare_cases(contract_cases, contracts, 832, 480, 121, 24)
    eval_prompts = []
    for row in prepared:
        contract = contracts[row["id"]]
        evaluation_case = dict(row)
        evaluation_case["original_prompt_text"] = evaluation_case["prompt_text"]
        evaluation_case["prompt_text"] = row["video_prompt"]
        evaluation_case["expected_concepts"] = [contract["beat"]["claim"]]
        evaluation_case["expected_visual_elements"] = contract["beat"]["visible_evidence"]
        evaluation_case["expected_narrative_order"] = [
            "Show the checked initial state",
            contract["beat"]["claim"],
            "Hold the checked result state",
        ]
        evaluation_case["audio_narration_required"] = False
        eval_prompts.append(evaluation_case)
    eval_prompts_path = out / "eval_prompts.jsonl"
    eval_prompts_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                         for row in eval_prompts), encoding="utf-8")
    frame_dir = out / "contract_frames"
    frame_dir.mkdir(exist_ok=True)
    contract_records = []
    video_diagnostics = []
    video_audits = []
    generation_manifest = []
    for row in prepared:
        case_id = row["id"]
        setup = frame_dir / f"{case_id}_setup.png"
        result = frame_dir / f"{case_id}_result.png"
        render_first_frame(contracts[case_id], phase="setup").save(setup)
        render_first_frame(contracts[case_id], phase="result").save(result)
        clip = frame_dir.parent / "videos" / f"{case_id}.mp4"
        clip_record = render_contract_video(contracts[case_id], prompts[case_id], clip)
        audit = audit_contract_video(clip, contracts[case_id], prompts[case_id])
        if audit["status"] != "pass":
            raise ValueError(f"{case_id}: generated video failed timeline audit: {audit}")
        audit["video_path"] = str(clip.relative_to(out))
        video_audits.append(audit)
        generation_manifest.append({"id": case_id, "status": "ok",
                                    "video_path": str(clip.resolve()),
                                    "generation_mode": clip_record["generation_mode"],
                                    "teaching_contract_sha256": clip_record["contract_sha256"],
                                    "video_sha256": clip_record["video_sha256"]})
        clip_record["video_path"] = str(clip.relative_to(out))
        video_diagnostics.append(clip_record)
        contract_records.append({"id": case_id, "sha256": row["teaching_contract_sha256"],
                                 "setup": str(setup.relative_to(out)),
                                 "result": str(result.relative_to(out)),
                                 "video": str(clip.relative_to(out)),
                                 "video_sha256": clip_record["video_sha256"],
                                 "duration_s": clip_record["duration_s"],
                                 "frame_count": clip_record["frame_count"],
                                 "frames_checked": clip_record["frames_checked"],
                                 "worst_frame_mean_error": clip_record["worst_frame_mean_error"]})
    diagnostics_path = out / "contract_video_diagnostics.jsonl"
    diagnostics_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                        for row in video_diagnostics), encoding="utf-8")
    video_audit_path = out / "contract_video_audit.jsonl"
    video_audit_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                        for row in video_audits), encoding="utf-8")
    generation_manifest_path = out / "generated_video_manifest.jsonl"
    generation_manifest_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                                for row in generation_manifest), encoding="utf-8")

    lesson_path = out / "interactive_lesson.html"
    lesson = build_from_files(root / LESSON, contracts_path, lesson_path)
    arms = [evidence_arm(root, *spec, pilot_ids) for spec in ARMS]
    first_frames = {path.stem for path in (root / "data/first_frames").glob("*.png")}
    probes = {}
    for label, relative in (("5B", "data/teachquiz/visual_probe_auto_5b.jsonl"),
                            ("1.3B", "data/teachquiz/visual_probe_auto_1_3b.jsonl")):
        path = root / relative
        probes[label] = {"path": relative, "pilot_overlap": len(set(read_jsonl(path, "case_id")) & pilot_ids)} if path.is_file() else {"path": relative, "pilot_overlap": 0}
    videos = sorted((root / "data/videos").glob("*.mp4"))
    audit_path = root / "results/video_audit/audit.jsonl"
    audit = read_jsonl(audit_path, "id") if audit_path.is_file() else {}
    video_records = [{
        "id": path.stem,
        "path": path.relative_to(root).as_posix(),
        "duration_s": audit.get(path.stem, {}).get("duration_s"),
        "contact_sheet": (f"results/video_audit/contact_sheets/{path.stem}.jpg"
                          if (root / f"results/video_audit/contact_sheets/{path.stem}.jpg").is_file()
                          else None),
    } for path in videos]
    manifest = {
        "version": "local-research-v1",
        "scope": "60-case short-clip pilot; offline assembly of existing evidence",
        "prompts": {"path": str(PROMPTS).replace("\\", "/"), "count": len(prompts),
                    "sha256": digest(prompt_path), "disciplines": dict(sorted(disciplines.items())),
                    "tasks": dict(sorted(tasks.items()))},
        "first_frames": {"pilot_overlap": len(first_frames & pilot_ids),
                         "missing_ids": sorted(pilot_ids - first_frames)},
        "contracts": {"count": len(contract_records), "source_sha256": digest(contracts_path),
                      "cases": contract_records, "diagnostics_path": diagnostics_path.name,
                      "audit_path": video_audit_path.name,
                      "generation_manifest_path": generation_manifest_path.name,
                      "eval_prompts_path": eval_prompts_path.name},
        "interactive": {"path": lesson_path.name, "variants": len(lesson["variants"])},
        "probes": probes,
        "evidence_arms": arms,
        "local_reference_videos": video_records,
        "limitations": [
            "本命令只生成三条确定性代码视频，没有运行 Wan 像素视频生成或模型评测。",
            "代理测验题由各模型输出生成，现有结果只能作为模型特定的感知性代理证据，不能解释为人类学习增益或跨模型公平排名。",
            "三份示范契约只覆盖 pilot 的三个案例；内部断言不代替学科专家真值审核。",
            "契约生成的 MP4 是无声、按声明动作播放的确定性代码视频基线；逐帧相符仍不证明科学真值，也尚未用像素视频模型做同题对照。",
            "本地八条 Code2Video 长视频与 3–5 秒 Wan 短片不是时长匹配的对照。",
            "人工评分、独立模型家族和完整匹配的 TI2V 对照尚未收集。",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_index(root, out, manifest)
    return manifest


def write_index(root: Path, out: Path, manifest: dict) -> None:
    arms = manifest["evidence_arms"]
    rows = []
    for arm in arms:
        if arm["available"]:
            metric = (f"均分 {arm['mean_aggregate']:.3f}" if arm["kind"] == "standard"
                      else f"有效 {arm['valid_n']}；代理增益 {arm['normalized_proxy_gain']:.3f}")
            coverage = f"{arm['pilot_overlap']}/60" + ("（汇总或题目不一致）" if not arm["consistent"] else "")
            source = link(out, root / arm["path"] / "aggregate.json", "汇总 JSON")
        else:
            metric, coverage, source = arm["reason"], "—", "—"
        rows.append(f"<tr><td>{escape(arm['label'])}</td><td>{coverage}</td><td>{escape(metric)}</td><td>{source}</td></tr>")
    contract_cards = "".join(
        f"<div class='tile'><strong>{escape(item['id'])}</strong><div class='images'>"
        f"<figure><img src='{escape(item['setup'], quote=True)}' alt='初始状态'><figcaption>初始状态</figcaption></figure>"
        f"<figure><img src='{escape(item['result'], quote=True)}' alt='结果状态'><figcaption>结果状态</figcaption></figure>"
        f"</div><p>{link(out, out / item['video'], '播放生成的 5 秒 MP4')}</p></div>"
        for item in manifest["contracts"]["cases"]
    )
    video_rows = "".join(
        f"<tr><td>{escape(item['id'])}</td><td>{item['duration_s'] if item['duration_s'] is not None else '—'}</td>"
        f"<td>{link(out, root / item['path'], '播放 MP4')}</td>"
        f"<td>{link(out, root / item['contact_sheet'], '查看抽帧') if item['contact_sheet'] else '—'}</td></tr>"
        for item in manifest["local_reference_videos"]
    )
    limits = "".join(f"<li>{escape(item)}</li>" for item in manifest["limitations"])
    html = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>rise-teacher · 本地研究原型 v1</title>
<style>:root{{font-family:system-ui,'Microsoft YaHei',sans-serif;color:#19354b;background:#edf3f6}}
body{{margin:0}}main{{max-width:1120px;margin:auto;padding:32px 20px 70px}}h1{{margin-bottom:4px}}
.lead{{font-size:1.15rem;color:#455f70}}section{{background:white;border:1px solid #d7e3ea;border-radius:16px;padding:24px;margin:18px 0}}
.stats{{display:flex;gap:12px;flex-wrap:wrap}}.stat{{background:#e8f5f4;padding:14px 18px;border-radius:10px;min-width:150px}}
.stat b{{display:block;font-size:1.7rem}}a{{color:#096e80}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #e2e9ed;text-align:left}}
.scroll{{overflow:auto}}.tile{{border-top:1px solid #e2e9ed;padding:15px 0}}.images{{display:flex;gap:12px;flex-wrap:wrap}}
figure{{margin:10px 0;width:min(100%,400px)}}img{{width:100%;border:1px solid #d7e3ea}}figcaption{{color:#526b7a}}
.button{{display:inline-block;background:#147c8c;color:white;padding:12px 18px;border-radius:9px;text-decoration:none}}li{{margin:8px 0;line-height:1.5}}
</style></head><body><main><h1>rise-teacher · 本地研究原型 v1</h1>
<p class='lead'>从题目、知识契约、可观察画面到已有评测证据的一站式本地入口。此页只汇总仓库中实际存在的结果。</p>
<section><div class='stats'><div class='stat'><b>{manifest['prompts']['count']}</b>短片任务</div>
<div class='stat'><b>{len(manifest['prompts']['disciplines'])}</b>学科</div>
<div class='stat'><b>{manifest['first_frames']['pilot_overlap']}/60</b>已有首帧</div>
<div class='stat'><b>{manifest['contracts']['count']}</b>可执行示范契约</div></div>
<p>{link(out, root / PROMPTS, '查看冻结题目')} · {link(out, out / 'manifest.json', '下载证据清单')} · {link(out, root / 'docs/STATUS.md', '查看研究状态')}</p></section>
<section><h2>教学状态、视频生成与交互</h2><p>同一份契约经校验后生成初始与结果画面及可播放的 5 秒代码视频。MP4 编码后会逐帧比对契约预期画面，检查时长、顺序和图像偏差；这不等于专家知识审核。交互样例含 {manifest['interactive']['variants']} 个分支。</p>
<p>{link(out, out / manifest['contracts']['diagnostics_path'], '查看逐题成片诊断 JSONL')}</p>
<p>{link(out, out / manifest['contracts']['audit_path'], '查看独立逐帧审查 JSONL')}</p>
<p>{link(out, out / manifest['contracts']['generation_manifest_path'], '打开评测兼容的生成清单')}</p>
<p>{link(out, out / manifest['contracts']['eval_prompts_path'], '打开三题原子步骤评测题目')}</p>
<p><a class='button' href='interactive_lesson.html'>打开凸透镜交互实验</a></p>{contract_cards}</section>
<section><h2>已存储的 60 题评测</h2><p>三维和六维均分使用不同评分配置；代理测验基于模型输出生成的题目，不用于跨模型排名。</p>
<div class='scroll'><table><thead><tr><th>配置</th><th>题目覆盖</th><th>结果</th><th>原始汇总</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>{link(out, root / 'docs/TEACHQUIZ_REPORT.md', '代理测验解释')} · {link(out, root / 'docs/VIDEO_SAMPLE_AUDIT.md', '八条长视频样例审查')}</p></section>
<section><h2>本地长视频参照</h2><p>这些 Code2Video 样例是 50–97 秒的长视频，不能与上表 3–5 秒短片分数直接比较。</p>
<div class='scroll'><table><thead><tr><th>题目</th><th>时长（秒）</th><th>视频</th><th>证据帧</th></tr></thead><tbody>{video_rows or '<tr><td colspan="4">本地没有 MP4 样例</td></tr>'}</tbody></table></div></section>
<section><h2>证据边界与下一步</h2><ul>{limits}</ul>
<p>{link(out, root / 'docs/HUMAN_EVAL_PROTOCOL.md', '人工评分方案')} · {link(out, root / 'docs/PAPER_READINESS.md', '论文证据门槛')}</p></section>
</main></body></html>"""
    (out / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results/v1")
    args = parser.parse_args()
    manifest = build(ROOT, args.out.resolve())
    available = sum(arm["available"] for arm in manifest["evidence_arms"])
    print(f"Built {args.out / 'index.html'}: 60 prompts, {available}/{len(ARMS)} evidence arms, "
          f"{manifest['contracts']['count']} validated contracts")


if __name__ == "__main__":
    main()
