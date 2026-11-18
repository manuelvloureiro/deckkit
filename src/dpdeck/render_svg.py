"""Standalone SVG and PNG output of a scene.

Two uses. `plots` exports each plot as a file, with its labels. The PowerPoint output calls
`raster` for shapes that PowerPoint cannot draw.

Every image covers the whole canvas of its scene and has no background. It is never cropped to
what it shows, so an image placed at the plot position lines up with the plots of the other slides.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence

from dpdeck.fonts import Measurer
from dpdeck.render_html import graphic_svg
from dpdeck.richtext import escape, parse_lines
from dpdeck.scene import Circle, Key, KeyKind, Label, Path, RawSvg, Scene
from dpdeck.theme import BLUE, BODY, INK, MUTED, ORANGE, STYLES, VIOLET, TextStyle

Graphic = Path | Circle | RawSvg
KEY_COLOR: dict[KeyKind, str] = {
    "d": BLUE,
    "dp": ORANGE,
    "l": VIOLET,
    "dash": ORANGE,
    "dot": ORANGE,
    "solid": ORANGE,
    "dot-ink": MUTED,
    "solid-ink": MUTED,
}
KEY_DASH: dict[KeyKind, str | None] = {"dash": "8 5", "dot": "0.1 6", "dot-ink": "0.1 6"}
DOT_KEYS = ("d", "dp", "l")
KEY_TEXT_OFFSET = {True: 28.0, False: 40.0}  # after a dot, after a line swatch


def label_style(label: Label) -> TextStyle:
    """The type of a plot label: serif and ink for mathematics, ink and bold for strong labels."""
    return TextStyle(
        "serif" if label.math else "sans",
        label.size,
        label.line_height,
        INK if (label.strong or label.math) else BODY,
        bold=label.strong,
    )


def _text_svg(
    x: float, top: float, markup: str, style: TextStyle, measurer: Measurer, anchor: str = "start"
) -> list[str]:
    family = (
        f"'{measurer.fonts.name(style.family)}', {'Georgia, serif' if style.family == 'serif' else 'Arial, sans-serif'}"
    )
    baseline = measurer.baseline(style)
    out: list[str] = []
    for index, line in enumerate(parse_lines(markup)):
        spans = []
        for run in line:
            attrs = []
            if run.italic:
                attrs.append('font-style="italic"')
            if run.bold and not style.bold:
                attrs.append(f'font-weight="600" fill="{INK}"')
            spans.append(f"<tspan {' '.join(attrs)}>{escape(run.text)}</tspan>" if attrs else escape(run.text))
        weight = ' font-weight="600"' if style.bold else ""
        out.append(
            f'<text x="{x:.1f}" y="{top + baseline + index * style.line:.1f}" font-family="{family}" '
            f'font-size="{style.size:g}"{weight} fill="{style.color}" text-anchor="{anchor}" '
            f'xml:space="preserve">{"".join(spans)}</text>'
        )
    return out


def _label_svg(label: Label, measurer: Measurer) -> list[str]:
    width = label.width or 0.0
    x, anchor = {"l": (label.x, "start"), "c": (label.x + width / 2, "middle"), "r": (label.x + width, "end")}[
        label.align
    ]
    return _text_svg(x, label.y, label.text, label_style(label), measurer, anchor)


def _key_svg(key: Key, measurer: Measurer) -> list[str]:
    style = STYLES["key"]
    middle = key.y + style.line / 2
    color = KEY_COLOR[key.kind]
    is_dot = key.kind in DOT_KEYS
    if is_dot:
        mark = f'<circle cx="{key.x + 8:.1f}" cy="{middle:.1f}" r="8" fill="{color}"/>'
    else:
        dash = KEY_DASH.get(key.kind)
        extra = f' stroke-dasharray="{dash}" stroke-linecap="round"' if dash else ""
        mark = (
            f'<path d="M{key.x:.1f} {middle:.1f} L{key.x + 28:.1f} {middle:.1f}" stroke="{color}" '
            f'stroke-width="3"{extra}/>'
        )
    return [mark, *_text_svg(key.x + KEY_TEXT_OFFSET[is_dot], key.y, key.text, style, measurer)]


def graphics_svg(width: int, height: int, graphics: Sequence[Graphic]) -> str:
    """A transparent SVG of the given shapes on a canvas of the given size."""
    body = "\n".join(graphic_svg(item) for item in graphics)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n{body}\n</svg>\n'
    )


def scene_svg(scene: Scene, measurer: Measurer) -> str:
    """A scene as one SVG file, labels included, on a transparent background."""
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{scene.width}" height="{scene.height}" '
        f'viewBox="0 0 {scene.width} {scene.height}" role="img" aria-label="{escape(scene.aria)}">'
    ]
    lines += [graphic_svg(item) for item in scene.graphics]
    for item in scene.labels:
        lines += _key_svg(item, measurer) if isinstance(item, Key) else _label_svg(item, measurer)
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def raster(svg: str, scale: float = 3.0, env: dict[str, str] | None = None) -> bytes:
    """Render an SVG to PNG bytes at `scale` times its size. The background stays transparent."""
    if shutil.which("rsvg-convert"):
        done = subprocess.run(
            ["rsvg-convert", "--zoom", f"{scale:g}", "--format", "png"],
            input=svg.encode("utf-8"),
            capture_output=True,
            check=True,
            env=env,
        )
        return done.stdout
    try:
        import cairosvg  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError(
            "exporting an image needs an SVG renderer: install rsvg-convert (package librsvg2-bin) "
            "or the Python package cairosvg"
        ) from error
    return cairosvg.svg2png(bytestring=svg.encode("utf-8"), scale=scale)  # type: ignore[no-any-return]
