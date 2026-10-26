"""Render a deterministic reference frame from a reviewed teaching contract.

This is a code-rendered first-frame arm, not a pixel-video generator. Visual
primitives are declarative and can bind coordinates/counts/text to knowledge
state paths, so the rendered frame and the asserted state share one source.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from generation.teaching_contract import ContractError, _operand, _validate_layout


def _value(item: object, beat: dict) -> object:
    return _operand(item, beat) if isinstance(item, dict) else item


def _number(item: object, beat: dict) -> float:
    value = _value(item, beat)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractError(f"drawing coordinate must be a finite number: {value!r}")
    if not 0 <= value <= 1:
        raise ContractError(f"drawing coordinate is outside normalized canvas: {value}")
    return float(value)


def _point(pair: object, beat: dict, width: int, height: int) -> tuple[int, int]:
    if not isinstance(pair, list) or len(pair) != 2:
        raise ContractError("drawing point must be [x, y]")
    return (round(_number(pair[0], beat) * width),
            round(_number(pair[1], beat) * height))


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (Path("C:/Windows/Fonts/arial.ttf"),
                 Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def _draw_primitive(draw: ImageDraw.ImageDraw, primitive: dict, beat: dict,
                    width: int, height: int, scale: int) -> None:
    kind = primitive.get("type")
    color = primitive.get("color", "#162331")
    stroke = max(1, round(primitive.get("stroke_px", 3) * scale))
    if kind in ("line", "arrow"):
        start = _point(primitive.get("start"), beat, width, height)
        end = _point(primitive.get("end"), beat, width, height)
        draw.line((start, end), fill=color, width=stroke)
        if kind == "arrow":
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            length = 12 * scale
            for direction in (-0.55, 0.55):
                tip = (round(end[0] - length * math.cos(angle + direction)),
                       round(end[1] - length * math.sin(angle + direction)))
                draw.line((tip, end), fill=color, width=stroke)
    elif kind == "ellipse":
        box = primitive.get("box")
        if not isinstance(box, list) or len(box) != 4:
            raise ContractError("ellipse box must be [left, top, right, bottom]")
        left, top = _point(box[:2], beat, width, height)
        right, bottom = _point(box[2:], beat, width, height)
        if left >= right or top >= bottom:
            raise ContractError("ellipse box is inverted")
        draw.ellipse((left, top, right, bottom), fill=primitive.get("fill"),
                     outline=color, width=stroke)
    elif kind == "text":
        position = _point(primitive.get("position"), beat, width, height)
        value = _value(primitive.get("text_path"), beat) if "text_path" in primitive else primitive.get("text")
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ContractError("drawing text must resolve to a string or number")
        label = primitive.get("prefix", "") + str(value)
        font = _font(round(primitive.get("font_px", 26) * scale))
        if primitive.get("align", "left") == "right":
            position = (position[0] - round(draw.textlength(label, font=font)), position[1])
        elif primitive.get("align", "left") != "left":
            raise ContractError("drawing text align must be left or right")
        draw.text(position, label, fill=color, font=font)
    elif kind == "dot":
        x, y = _point(primitive.get("center"), beat, width, height)
        radius = max(1, round(primitive.get("radius_px", 8) * scale))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=primitive.get("fill", color), outline=color)
    elif kind == "radial_dots":
        center = _point(primitive.get("center"), beat, width, height)
        count = _value(primitive.get("count"), beat)
        if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= 32:
            raise ContractError("radial_dots count must be an integer 0..32")
        slots = primitive.get("slots", max(count, 1))
        if not isinstance(slots, int) or isinstance(slots, bool) or not 1 <= slots <= 32 or count > slots:
            raise ContractError("radial_dots slots must be an integer from count to 32")
        radius = round(_number(primitive.get("radius"), beat) * min(width, height))
        dot = max(2, round(primitive.get("dot_px", 6) * scale))
        for index in range(count):
            angle = -math.pi / 2 + index * 2 * math.pi / slots
            x = round(center[0] + radius * math.cos(angle))
            y = round(center[1] + radius * math.sin(angle))
            draw.ellipse((x - dot, y - dot, x + dot, y + dot), fill=color)
    else:
        raise ContractError(f"unsupported drawing primitive: {kind!r}")


def render_first_frame(contract: dict, width: int = 832, height: int = 480,
                       phase: str = "setup", scale: int = 2) -> Image.Image:
    if width <= 0 or height <= 0 or scale < 1:
        raise ValueError("width, height, and scale must be positive")
    _validate_layout(contract.get("layout"), width, height,
                     contract.get("background", "#ffffff"))
    canvas = Image.new("RGB", (width * scale, height * scale),
                       contract.get("background", "#ffffff"))
    draw = ImageDraw.Draw(canvas)
    beat = contract["beat"]
    for element in contract["layout"]:
        if element.get("phase", "all") not in ("all", phase):
            continue
        if element.get("kind") == "text":
            value = (_value(element["text_path"], beat) if "text_path" in element
                     else element["text"])
            if not isinstance(value, str):
                raise ContractError(f"{element['id']}: text_path must resolve to text")
            rect = element["rect"]
            left, top = round(rect[0] * width * scale), round(rect[1] * height * scale)
            draw.text((left + 6 * scale, top + 3 * scale),
                      element.get("prefix", "") + value,
                      fill=element.get("color", "#162331"),
                      font=_font(round(element["font_px"] * scale)))
        for primitive in element.get("draw", []):
            if primitive.get("phase", "all") not in ("all", phase):
                continue
            _draw_primitive(draw, primitive, beat, width * scale, height * scale, scale)
    return canvas.resize((width, height), Image.Resampling.LANCZOS)
