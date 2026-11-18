"""HTML output: the Claude Slides project folder, and a single file that opens in any browser.

Both use the same markup for a slide and the same `assets/deck.css`. They differ in one element:
the Slides page format draws arrows with its own `<x-connector>`, which a plain browser does not
know, so the single file draws them as SVG lines.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path as FilePath
from typing import Literal

from deckkit.model import (
    Block,
    Card,
    CardsSlide,
    Cover,
    DataTable,
    Deck,
    Def,
    DiagramSlide,
    Eq,
    Node,
    Note,
    PlotSlide,
    Say,
    Slide,
    Stat,
    Statement,
    TableSlide,
    TablesSlide,
    Tight,
)
from deckkit.richtext import equation_html, escape, to_html
from deckkit.scene import Circle, Key, Label, Mark, Path, RawSvg, Scene
from deckkit.theme import MUTED

Connectors = Literal["x-connector", "svg"]

SWATCH_CLASS = {"solid": "sw sw-solid", "dash": "sw sw-dash", "guide": "sw sw-dash", "dot": "sw sw-dot"}
DASH_ARRAY = {"solid": None, "dash": "12 8", "dot": "1 8", "guide": "6 8"}
FACES = {
    "source-serif-4": {
        "family": "Source Serif 4",
        "href": "https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400..700;1,400..700&display=swap",
    },
    "ibm-plex-sans": {
        "family": "IBM Plex Sans",
        "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap",
    },
}


def _n(value: float) -> str:
    """A length with at most one decimal and no trailing zero."""
    return f"{round(value, 1):g}"


# ---------------------------------------------------------------- scenes
def path_data(path: Path) -> str:
    parts = []
    for sub in path.subpaths:
        parts.append("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in sub) + ("Z" if path.closed else ""))
    return " ".join(parts)


def graphic_svg(item: Path | Circle | RawSvg) -> str:
    """One shape as an SVG element. Shared with the standalone SVG output."""
    if isinstance(item, RawSvg):
        return item.markup
    if isinstance(item, Circle):
        stroke = f' stroke="{item.stroke}" stroke-width="{item.width:g}"' if item.stroke else ""
        return f'<circle cx="{item.cx:.1f}" cy="{item.cy:.1f}" r="{item.r:g}" fill="{item.fill}"{stroke}/>'
    attrs = [f'd="{path_data(item)}"']
    if item.fill:
        attrs.append(f'fill="{item.fill}"')
        if item.opacity < 1:
            attrs.append(f'fill-opacity="{item.opacity:g}"')
    else:
        attrs.append('fill="none"')
    if item.stroke:
        attrs.append(f'stroke="{item.stroke}" stroke-width="{item.width:g}" stroke-linejoin="round"')
        if DASH_ARRAY[item.dash]:
            attrs.append(f'stroke-dasharray="{DASH_ARRAY[item.dash]}"')
        if item.round_cap:
            attrs.append('stroke-linecap="round"')
    return f"<path {' '.join(attrs)}/>"


def _label_html(label: Label) -> str:
    classes = ["lbl"]
    if label.strong:
        classes.append("strong")
    if label.math:
        classes.append("mth")
    if label.align != "l":
        classes.append(label.align)
    style = [f"left:{_n(label.x)}px", f"top:{_n(label.y)}px"]
    if label.width is not None:
        style.append(f"width:{_n(label.width)}px")
    if label.size != 24:
        style.append(f"font-size:{_n(label.size)}px")
    if label.line_height != 1.2:
        style.append(f"line-height:{_n(label.line_height)}")
    return f'<p class="{" ".join(classes)}" style="{"; ".join(style)}">{to_html(label.text)}</p>'


def key_html(mark: Mark, text: str, position: tuple[float, float] | None = None, tag: str = "p") -> str:
    style = f' style="position:absolute; left:{_n(position[0])}px; top:{_n(position[1])}px"' if position else ""
    cls = ' class="key-text"' if tag == "p" else ""
    if mark.line is None:
        swatch = f'<div class="dot" style="background:{mark.color}"></div>'
    else:
        swatch = f'<div class="{SWATCH_CLASS[mark.line]}" style="border-top-color:{mark.color}"></div>'
    return f'<div class="key"{style}>{swatch}<{tag}{cls}>{to_html(text)}</{tag}></div>'


def scene_html(scene: Scene, art: bool = True) -> str:
    """The inline SVG of a scene, followed by its labels as positioned paragraphs.

    The Slides page format does not allow text inside an SVG, so labels are HTML pinned over the
    drawing. The element that contains this markup must be positioned and of the scene's size.
    """
    cls = ' class="art"' if art else ""
    lines = [
        f'<svg{cls} width="{scene.width}" height="{scene.height}" viewBox="0 0 {scene.width} {scene.height}" '
        f'aria-label="{escape(scene.aria)}">'
    ]
    lines += [graphic_svg(item) for item in scene.graphics]
    lines.append("</svg>")
    for item in scene.labels:
        if isinstance(item, Key):
            lines.append(key_html(item.mark, item.text, (item.x, item.y)))
        else:
            lines.append(_label_html(item))
    return "\n".join(lines)


# ---------------------------------------------------------------- blocks
def _eq_html(eq: Eq) -> str:
    cls = {"s": "eq eq-s", "m": "eq", "l": "eq eq-l"}[eq.size]
    return f'<div class="{cls}">{equation_html(eq.text)}</div>'


def block_html(block: Block | Eq | Stat) -> str:
    if isinstance(block, Say):
        return f'<p class="say">{to_html(block.text)}</p>'
    if isinstance(block, Note):
        return f'<p class="note{" c" if block.centred else ""}">{to_html(block.text)}</p>'
    if isinstance(block, Eq):
        return _eq_html(block)
    if isinstance(block, Stat):
        return (
            f'<div class="stat"><p class="num">{escape(block.number)}</p>'
            f'<p class="note">{to_html(block.caption)}</p></div>'
        )
    if isinstance(block, Tight):
        return "<div>\n" + "\n".join(block_html(b) for b in block.blocks) + "\n</div>"
    return _def_html(block)


def _def_html(card: Def) -> str:
    lines = ['<div class="def">']
    if card.title:
        lines.append(f"<h3>{to_html(card.title)}</h3>")
    lines += [block_html(b) for b in card.body]
    lines.append("</div>")
    return "\n".join(lines)


def _head(eyebrow: str, title: str) -> str:
    return f'<div class="head">\n<p class="eyebrow">{escape(eyebrow)}</p>\n<h2>{to_html(title)}</h2>\n</div>'


def _section(slide_id: str, body: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<section id="{slide_id}"{c} data-transition="fade">\n{body}\n</section>\n'


# ---------------------------------------------------------------- slides
def _card_html(card: Card, compact: bool) -> str:
    lines = [f'<div class="card{" card-s" if compact else ""}">']
    if card.step:
        lines.append(f'<p class="step">{escape(card.step)}</p>')
    if card.scene:
        frame = "mini" if card.scene.height < 200 else "panel"
        lines.append(f'<div class="{frame}">\n{scene_html(card.scene)}\n</div>')
    lines.append(f"<h3>{to_html(card.title)}</h3>")
    lines.append(f'<p class="note">{to_html(card.note)}</p>')
    if card.tag or card.footer:
        lines.append('<div class="grow"></div>')
    if card.tag:
        lines.append(f'<p class="tag">{to_html(card.tag)}</p>')
    if card.footer:
        lines.append(_eq_html(card.footer))
    lines.append("</div>")
    return "\n".join(lines)


def _data_table_html(table: DataTable) -> str:
    lines = ['<div class="tbl">', key_html(table.key.mark, table.key.text), "<table>"]
    lines.append('<tr class="thead">' + "".join(f"<th>{to_html(t)}</th>" for t in table.header) + "</tr>")
    for index, row in enumerate(table.rows):
        cls = ' class="hl"' if index == table.highlight else ""
        lines.append(f"<tr{cls}>" + "".join(f"<td>{to_html(t)}</td>" for t in row) + "</tr>")
    lines.append("</table>")
    lines.append(
        f'<div class="pub"><p class="mid">{escape(table.value)}</p><p class="say">{to_html(table.caption)}</p></div>'
    )
    lines.append("</div>")
    return "\n".join(lines)


def _node_html(node: Node) -> str:
    style = f"left:{_n(node.x)}px; top:{_n(node.y)}px; width:{_n(node.width)}px; height:{_n(node.height)}px"
    lines = [f'<div class="node" style="{style}">']
    if node.scene:
        lines.append(scene_html(node.scene, art=False))
    if node.title and node.key:
        lines.append(key_html(node.key, node.title, tag="h3"))
    elif node.title:
        lines.append(f"<h3>{to_html(node.title)}</h3>")
    lines.append(f'<p class="note">{to_html(node.note)}</p>')
    lines.append("</div>")
    return "\n".join(lines)


def _arrows_html(slide: DiagramSlide, connectors: Connectors) -> str:
    if connectors == "x-connector":
        return "\n".join(
            f'<x-connector x1="{_n(x1)}" y1="{_n(y1)}" x2="{_n(x2)}" y2="{_n(y2)}" '
            f'style="color:{MUTED}; border-width:3px"></x-connector>'
            for x1, y1, x2, y2 in slide.arrows
        )
    width, height = slide.diagram_size
    lines = [
        f'<svg class="art" width="{width}" height="{height}" viewBox="0 0 {width} {height}" aria-hidden="true">',
        f'<defs><marker id="arrow-{slide.id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
        f'orient="auto"><path d="M0 0 L10 5 L0 10Z" fill="{MUTED}"/></marker></defs>',
    ]
    lines += [
        f'<path d="M{_n(x1)} {_n(y1)} L{_n(x2)} {_n(y2)}" stroke="{MUTED}" stroke-width="3" '
        f'marker-end="url(#arrow-{slide.id})"/>'
        for x1, y1, x2, y2 in slide.arrows
    ]
    lines.append("</svg>")
    return "\n".join(lines)


def slide_html(slide: Slide, connectors: Connectors = "x-connector") -> str:
    """The `<section>` of one slide."""
    if isinstance(slide, Cover):
        parts = [
            f'<p class="eyebrow">{escape(slide.eyebrow)}</p>',
            f"<h1>{to_html(slide.title)}</h1>",
            f'<p class="lead">{to_html(slide.lead)}</p>',
        ]
        if slide.art:
            parts.insert(0, scene_html(slide.art))
        return _section(slide.id, "\n".join(parts), "cover")
    if isinstance(slide, Statement):
        body = "\n".join(
            [
                f'<p class="eyebrow">{escape(slide.eyebrow)}</p>',
                f"<h2>{to_html(slide.title)}</h2>",
                f'<p class="lead" style="width:{slide.lead_width}px">{to_html(slide.lead)}</p>',
            ]
        )
        return _section(slide.id, body, "accent")
    head = _head(slide.eyebrow, slide.title)
    if isinstance(slide, PlotSlide):
        row, plot = ("row wide", "plot flush") if slide.flush else ("row", "plot")
        body = "\n".join(
            [
                head,
                f'<div class="{row}">',
                f'<div class="{plot}">',
                scene_html(slide.scene),
                "</div>",
                '<div class="side">',
                *[block_html(b) for b in slide.side],
                "</div>",
                "</div>",
            ]
        )
        return _section(slide.id, body)
    if isinstance(slide, CardsSlide):
        lines = [head]
        if slide.keys:
            lines += ['<div class="keys">', *[key_html(k.mark, k.text) for k in slide.keys], "</div>"]
        lines += ['<div class="cards">', *[_card_html(c, slide.compact) for c in slide.cards], "</div>"]
        if slide.lead:
            lines.append(f'<p class="lead">{to_html(slide.lead)}</p>')
        return _section(slide.id, "\n".join(lines), "" if slide.background == "paper" else slide.background)
    if isinstance(slide, TablesSlide):
        body = "\n".join(
            [
                head,
                '<div class="row">',
                '<div class="tbls">',
                *[_data_table_html(t) for t in slide.tables],
                "</div>",
                '<div class="side">',
                *[block_html(b) for b in slide.side],
                "</div>",
                "</div>",
            ]
        )
        return _section(slide.id, body)
    if isinstance(slide, DiagramSlide):
        return _section(slide.id, _diagram_body(slide, head, connectors))
    return _section(slide.id, _table_slide_body(slide, head))


def _diagram_body(slide: DiagramSlide, head: str, connectors: Connectors) -> str:
    width, height = slide.diagram_size
    lines = [head, f'<p class="lead">{to_html(slide.lead)}</p>']
    lines.append(f'<div class="host" style="width:{width}px; height:{height}px">')
    lines += [_node_html(n) for n in slide.nodes]
    lines.append(_arrows_html(slide, connectors))
    lines.append("</div>")
    lines += ['<div class="def">', '<div class="terms">']
    for term in slide.terms:
        caption = key_html(term.key, term.caption) if term.key else f'<p class="key-text">{to_html(term.caption)}</p>'
        lines += ['<div class="term">', f'<div class="eq">{equation_html(term.eq)}</div>', caption, "</div>"]
    lines += ["</div>", f'<p class="note c">{to_html(slide.note)}</p>', "</div>"]
    return "\n".join(lines)


def _table_slide_body(slide: TableSlide, head: str) -> str:
    lines = [head, "<table>"]
    lines.append(
        '<tr class="thead">'
        + "".join(f'<th style="width:{w}%">{to_html(t)}</th>' for t, w in zip(slide.header, slide.widths, strict=True))
        + "</tr>"
    )
    lines += ["<tr>" + "".join(f"<td>{to_html(t)}</td>" for t in row) + "</tr>" for row in slide.rows]
    lines.append("</table>")
    if slide.footer:
        lines += ['<div class="grow"></div>', _def_html(slide.footer)]
    return "\n".join(lines)


# ---------------------------------------------------------------- outputs
def _asset(name: str) -> str:
    return resources.files("deckkit").joinpath("assets", name).read_text(encoding="utf-8")


def deck_index(deck: Deck) -> dict[str, object]:
    """The `deck.json` of a Claude Slides project."""
    return {
        "v": 5,
        "createdOnFiles": {"v": 1, "at": "2026-11-17T12:00:00Z"},
        "lists": "css",
        "format": {"v": 1, "shared": ["project/deck.css"]},
        "title": deck.title,
        "cover": deck.slides[0].id,
        "order": [slide.id for slide in deck.slides],
        "sections": {s.key: {"description": s.description, "start": s.start} for s in deck.sections},
        "faces": FACES,
        "designSystems": [],
    }


def write_artifact(deck: Deck, out: FilePath) -> FilePath:
    """Write the folder that a Claude Slides artifact is published from. Returns the folder."""
    project = out / "project"
    (project / "slides").mkdir(parents=True, exist_ok=True)
    (project / "deck.json").write_text(json.dumps(deck_index(deck), ensure_ascii=False, indent=2) + "\n", "utf-8")
    (project / "deck.css").write_text(_asset("deck.css"), "utf-8")
    for slide in deck.slides:
        (project / "slides" / f"{slide.id}.html").write_text(slide_html(slide), "utf-8")
    return out


def write_standalone(deck: Deck, path: FilePath) -> FilePath:
    """Write one HTML file with every slide and a small viewer. Returns the file."""
    sections = "".join(slide_html(slide, connectors="svg") for slide in deck.slides)
    fonts = "".join(f'<link rel="stylesheet" href="{face["href"]}">' for face in FACES.values())
    html = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(deck.title)}</title>\n{fonts}\n"
        f"<style>\n{_asset('viewer.css')}\n{_asset('deck.css')}</style>\n</head>\n"
        f'<body>\n<main id="stage">\n{sections}</main>\n<script>\n{_asset("viewer.js")}</script>\n</body>\n</html>\n'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, "utf-8")
    return path
