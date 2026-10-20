"""Build a small interactive lesson from validated teaching-contract states."""

from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
from html import escape
from pathlib import Path

from generation.contract_frame import render_first_frame
from generation.teaching_contract import ContractError, _operand, load_contracts, validate_contract


def _set_path(document: dict, path: str, value: object) -> None:
    if not path.startswith(("beat.pre_state.", "beat.post_state.", "invariants.")):
        raise ContractError(f"interactive override cannot edit {path}")
    parts = path.split(".")
    node = document
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            raise ContractError(f"interactive override path does not exist: {path}")
        node = node[part]
    if not isinstance(node, dict) or parts[-1] not in node:
        raise ContractError(f"interactive override path does not exist: {path}")
    node[parts[-1]] = copy.deepcopy(value)


def _draw_primitive(contract: dict, selector: str) -> dict:
    elements = {element["id"]: element for element in contract["layout"]}
    try:
        element_id, index_text = selector.rsplit(":", 1)
        return elements[element_id]["draw"][int(index_text)]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ContractError(f"invalid drawing primitive selector: {selector}") from exc


def _hide_setup_primitives(contract: dict, selectors: list[str]) -> None:
    for selector in selectors:
        primitive = _draw_primitive(contract, selector)
        if primitive.get("phase", "all") != "all":
            raise ContractError(f"hidden setup primitive is already phased: {selector}")
        primitive["phase"] = "result"


def _coordinate(value: object, beat: dict) -> float:
    resolved = _operand(value, beat) if isinstance(value, dict) else value
    if isinstance(resolved, bool) or not isinstance(resolved, (int, float)) or not 0 <= resolved <= 1:
        raise ContractError(f"invalid animation coordinate: {resolved!r}")
    return float(resolved)


def _animation_images(contract: dict, selectors: list[str], frames: int,
                      width: int, height: int) -> list[str]:
    if not selectors:
        return []
    if not 2 <= frames <= 12:
        raise ContractError("animation_frames must be between 2 and 12")
    lines = []
    for selector in selectors:
        primitive = _draw_primitive(contract, selector)
        if primitive.get("type") not in ("line", "arrow") or primitive.get("phase") != "result":
            raise ContractError(f"animation primitive must be a result-phase line: {selector}")
        start, end = primitive.get("start"), primitive.get("end")
        if not isinstance(start, list) or not isinstance(end, list) or len(start) != 2 or len(end) != 2:
            raise ContractError(f"animation line needs start and end points: {selector}")
        beat = contract["beat"]
        lines.append((selector, [_coordinate(x, beat) for x in start],
                      [_coordinate(x, beat) for x in end]))
    images = []
    for step in range(1, frames + 1):
        frame_contract = copy.deepcopy(contract)
        fraction = step / frames
        for selector, start, end in lines:
            _draw_primitive(frame_contract, selector)["end"] = [
                start[i] + (end[i] - start[i]) * fraction for i in range(2)
            ]
        images.append(_image_data(render_first_frame(frame_contract, width, height, "result")))
    return images


def _image_data(image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def compile_lesson(spec: dict, contracts: dict[str, dict], *, width: int = 832,
                   height: int = 480) -> dict:
    """Validate every branch, then compile immutable images for a local player."""
    if width <= 0 or height <= 0:
        raise ContractError("interactive canvas dimensions must be positive")
    contract_id = spec.get("contract_id")
    if not isinstance(contract_id, str) or contract_id not in contracts:
        raise ContractError(f"unknown interactive contract: {contract_id}")
    variants = spec.get("variants")
    answers = spec.get("answers")
    if not isinstance(variants, list) or len(variants) < 2:
        raise ContractError("interactive lesson needs at least two variants")
    if not isinstance(answers, list) or len(answers) < 2:
        raise ContractError("interactive lesson needs at least two answers")
    answer_ids = [item.get("id") for item in answers if isinstance(item, dict)]
    if (len(answer_ids) != len(answers) or
            any(not isinstance(item, str) or not item for item in answer_ids) or
            len(set(answer_ids)) != len(answer_ids)):
        raise ContractError("answers need unique ids")
    if any(not isinstance(item.get("label"), str) or not item["label"] for item in answers):
        raise ContractError("answers need labels")
    hidden = spec.get("hide_setup_primitives", [])
    if not isinstance(hidden, list) or any(not isinstance(item, str) for item in hidden):
        raise ContractError("hide_setup_primitives must be a list of selectors")
    extra_checks = spec.get("extra_checks", [])
    if not isinstance(extra_checks, list) or any(not isinstance(item, dict) for item in extra_checks):
        raise ContractError("extra_checks must be a list of assertions")
    animated = spec.get("animate_primitives", [])
    if not isinstance(animated, list) or any(not isinstance(item, str) for item in animated):
        raise ContractError("animate_primitives must be a list of selectors")
    animation_frames = spec.get("animation_frames", 6)

    compiled = []
    seen = set()
    for variant in variants:
        if not isinstance(variant, dict):
            raise ContractError("interactive variant must be an object")
        key = variant.get("id")
        if not isinstance(key, str) or not key or key in seen:
            raise ContractError("interactive variants need unique nonempty ids")
        seen.add(key)
        if variant.get("answer") not in answer_ids:
            raise ContractError(f"{key}: answer is not in lesson answers")
        if not isinstance(variant.get("label"), str) or not variant["label"]:
            raise ContractError(f"{key}: label is required")
        overrides = variant.get("overrides")
        if not isinstance(overrides, dict) or not overrides:
            raise ContractError(f"{key}: nonempty overrides are required")
        contract = copy.deepcopy(contracts[contract_id])
        for path, value in overrides.items():
            _set_path(contract, path, value)
        contract["checks"].extend(copy.deepcopy(extra_checks))
        _hide_setup_primitives(contract, hidden)
        validate_contract(contract, {"id": contract_id}, width, height,
                          contract["target_duration_s"])
        compiled.append({
            "id": key,
            "label": variant["label"],
            "answer": variant["answer"],
            "explanation": variant.get("explanation", ""),
            "setup_image": _image_data(render_first_frame(contract, width, height, "setup")),
            "result_image": _image_data(render_first_frame(contract, width, height, "result")),
            "animation_images": _animation_images(contract, animated, animation_frames,
                                                   width, height),
            "contract_sha256": hashlib.sha256(
                json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        })
    reference = spec.get("reference_variant_id", compiled[0]["id"])
    if reference not in seen:
        raise ContractError("reference_variant_id is not a variant")
    return {
        "id": spec.get("id", contract_id),
        "title": spec.get("title", contracts[contract_id]["learning_objective"]),
        "instruction": spec.get("instruction", "选择条件，预测结果，再查看解释。"),
        "question": spec.get("question", "结果会如何变化？"),
        "prediction_prompt": spec.get("prediction_prompt", "请先选择条件，再预测结果。"),
        "animation_prompt": spec.get("animation_prompt", "请观察状态如何变化。"),
        "answers": answers,
        "variants": compiled,
        "reference_variant_id": reference,
    }


def write_lesson_html(lesson: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(lesson, ensure_ascii=False).replace("<", "\\u003c")
    html = _HTML.replace("__TITLE__", escape(str(lesson["title"]))).replace(
        "__LESSON_JSON__", payload
    )
    path.write_text(html, encoding="utf-8")


def build_from_files(spec_path: str | Path, contracts_path: str | Path,
                     out_path: str | Path) -> dict:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    lesson = compile_lesson(spec, load_contracts(contracts_path))
    write_lesson_html(lesson, out_path)
    return lesson


_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{font-family:system-ui,"Microsoft YaHei",sans-serif;color:#173049;background:#eef3f6}
*{box-sizing:border-box}body{margin:0;padding:24px}.wrap{max-width:1050px;margin:auto}
h1{font-size:clamp(1.5rem,3vw,2.1rem);margin:0 0 8px}p{line-height:1.55}
.card{background:#fff;border:1px solid #d7e3e9;border-radius:16px;padding:22px;margin:18px 0;box-shadow:0 8px 30px #1a476112}
.stage{width:100%;aspect-ratio:832/480;object-fit:contain;border:1px solid #dde5e9;border-radius:10px;background:white}
.row{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}.choice{border:2px solid #beced8;border-radius:10px;padding:10px 16px;background:#fff;color:#173049;cursor:pointer;font:inherit}
.choice[aria-pressed=true]{border-color:#147c8c;background:#e4f6f6}.choice:disabled{opacity:.55;cursor:not-allowed}.choice:focus-visible,button:focus-visible{outline:3px solid #ffb44e;outline-offset:2px}
.primary{background:#147c8c;color:#fff;border:0;border-radius:10px;padding:11px 20px;font:inherit;cursor:pointer}.primary:disabled{opacity:.45;cursor:not-allowed}
.feedback{min-height:3rem;padding:12px 15px;border-radius:10px;background:#f1f6f8}.ok{background:#e2f5e9}.retry{background:#fff0e5}
.muted{color:#526b7a;font-size:.94rem}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
</style></head><body><main class="wrap"><h1 id="title"></h1><p id="instruction"></p>
<section class="card"><div class="toolbar"><strong id="phase">选择条件</strong><span class="muted">选择 → 预测 → 揭示</span></div>
<img class="stage" id="stage" alt="教学状态示意图"><h2 style="font-size:1.05rem">调整条件</h2><div class="row" id="variants"></div>
<h2 id="question" style="font-size:1.05rem"></h2><div class="row" id="answers"></div>
<button class="primary" id="reveal" disabled>揭示结果</button><p class="feedback" id="feedback" role="status" aria-live="polite">请先选择条件和预测。</p></section>
<p class="muted">画面由已校验的知识状态生成。记录只保存在本页内；可下载用于后续学习效果对照。</p>
<button class="choice" id="download">下载本次交互记录</button></main>
<script type="application/json" id="lesson-data">__LESSON_JSON__</script><script>
const lesson=JSON.parse(document.getElementById('lesson-data').textContent);
const $=id=>document.getElementById(id);let selected=null,prediction=null,revealed=false,animating=false,animationToken=0;const events=[];
$('title').textContent=lesson.title;$('instruction').textContent=lesson.instruction;$('question').textContent=lesson.question;
function button(item,group,onClick){const b=document.createElement('button');b.className='choice';b.type='button';b.textContent=item.label;b.setAttribute('aria-pressed','false');b.onclick=()=>onClick(item.id);$(group).appendChild(b)}
function pressed(group,id,items){[...$(group).children].forEach((b,i)=>b.setAttribute('aria-pressed',String(items[i].id===id)))}
function refresh(){let v=lesson.variants.find(x=>x.id===selected);let reference=lesson.variants.find(x=>x.id===lesson.reference_variant_id);
 $('stage').src=v?(revealed?v.result_image:v.setup_image):reference.result_image;
 $('stage').alt=v?`${v.label}：${revealed?'结果':'预测前状态'}`:'初始状态';$('phase').textContent=!v?'初始状态':revealed?'已揭示结果':'预测结果';
 $('reveal').disabled=!selected||!prediction||revealed||animating;
 [...$('answers').children].forEach(b=>b.disabled=animating||revealed);}
lesson.variants.forEach(v=>button(v,'variants',id=>{animationToken++;selected=id;prediction=null;revealed=false;animating=false;pressed('variants',id,lesson.variants);pressed('answers',null,lesson.answers);$('feedback').className='feedback';$('feedback').textContent=lesson.prediction_prompt;refresh()}));
lesson.answers.forEach(a=>button(a,'answers',id=>{if(animating||revealed)return;prediction=id;pressed('answers',id,lesson.answers);refresh()}));
$('reveal').onclick=()=>{const v=lesson.variants.find(x=>x.id===selected),chosen=prediction;
 if(!v||!chosen||revealed||animating)return;const token=++animationToken;animating=true;refresh();$('phase').textContent='变化进行中';$('feedback').textContent=lesson.animation_prompt;
 const images=v.animation_images.length?v.animation_images:[v.result_image];let step=0;
 function next(){if(token!==animationToken)return;if(step<images.length){$('stage').src=images[step++];setTimeout(next,110);return}
  animating=false;revealed=true;const correct=chosen===v.answer;$('feedback').className='feedback '+(correct?'ok':'retry');
  $('feedback').textContent=(correct?'预测正确。':'预测有偏差。')+v.explanation;
  events.push({lesson_id:lesson.id,variant_id:v.id,prediction:chosen,answer:v.answer,correct,contract_sha256:v.contract_sha256,time:new Date().toISOString()});$('download').disabled=false;refresh()}
 next()};
$('download').onclick=()=>{const blob=new Blob([JSON.stringify({lesson_id:lesson.id,events},null,2)],{type:'application/json'});
 const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='interactive-lesson-events.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$('download').disabled=true;refresh();
</script></body></html>"""
