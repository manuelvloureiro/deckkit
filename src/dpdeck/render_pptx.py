"""PowerPoint output.

Everything is placed by this module: PowerPoint has no flow layout, so each slide type computes
its own positions from the same sizes and gaps as `assets/deck.css`.

What is native and what is an image
-----------------------------------
A plot is drawn with native shapes: freeforms for curves and areas, connectors for straight
segments, ovals, text boxes. They stay editable in PowerPoint. A shape with no PowerPoint
equivalent (`scene.RawSvg`) is rendered to a transparent PNG instead. `plots="image"` does that
for all the shapes of every plot, and `plots="native"` refuses to build if a shape would need an
image. Labels are always native text.

How plots stay aligned
----------------------
Every plot is a group whose first member is an invisible frame of the full plot size, and every
image covers that whole frame. So the group, or the image, has the same position and size on
every slide, whatever is drawn inside it.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path as FilePath
from typing import Any, Literal

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from dpdeck.fonts import Measurer
from dpdeck.model import (
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
from dpdeck.render_svg import DOT_KEYS, KEY_COLOR, KEY_TEXT_OFFSET, graphics_svg, label_style, raster
from dpdeck.richtext import Run, parse, parse_lines, plain
from dpdeck.scene import Align, Circle, Dash, Key, KeyKind, Label, Path, RawSvg, Scene
from dpdeck.theme import (
    ACCENT_TEXT,
    BACKGROUNDS,
    CARD,
    COVER_TEXT,
    GAP,
    HAIRLINE,
    INK,
    MARGIN,
    MUTED,
    PAPER,
    PAPER_2,
    PLOT_W,
    SLIDE_H,
    SLIDE_W,
    STYLES,
    TextStyle,
)

PlotMode = Literal["auto", "native", "image"]

PX = 6350  # EMU per pixel: a 1920 px slide is 13.333 in wide
UNITS = 100  # freeform coordinates per pixel, so that a tenth of a pixel survives rounding
CONTENT_W = SLIDE_W - 2 * MARGIN
BOTTOM = SLIDE_H - MARGIN
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
NO_STYLE_TABLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
ALIGN = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}
DASH = {"dash": MSO_LINE.DASH, "guide": MSO_LINE.DASH, "dot": MSO_LINE.ROUND_DOT}
KEY_DASH: dict[KeyKind, Dash] = {"dash": "dash", "dot": "dot", "dot-ink": "dot"}
EQ_STYLE = {"s": "eq-s", "m": "eq", "l": "eq-l"}
TABLE_ROW = 60.8  # one text line of the table style, its padding and a border
NEAR_MISS = 0.03  # how far a single line may run past its column before it is wrapped
TABLE_BORDER = "C5C3BE"  # the deck's 20% black hairline, on paper


def emu(px: float) -> Emu:
    return Emu(round(px * PX))


def rgb(color: str) -> RGBColor:
    return RGBColor.from_string(color.lstrip("#").upper())


# ---------------------------------------------------------------- low-level XML helpers
def _unstyle(shape: Any) -> None:
    """Drop the theme style reference, which would add the theme's outline, fill and shadow."""
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)


def _describe(shape: Any, name: str, description: str = "") -> None:
    shape.name = name
    if description:
        props = next(shape._element.iter(qn("p:cNvPr")))
        props.set("descr", description)


def _set_line(shape: Any, color: str | None, width: float, dash: Dash = "solid", round_cap: bool = False) -> None:
    if color is None:
        shape.line.fill.background()
        return
    shape.line.color.rgb = rgb(color)
    shape.line.width = emu(width)
    if dash != "solid":
        shape.line.dash_style = DASH[dash]
    ln = shape.line._get_or_add_ln()
    if round_cap or dash == "dot":
        ln.set("cap", "rnd")
    ln.append(parse_xml(f'<a:round xmlns:a="{A_NS}"/>'))


def _set_fill(shape: Any, color: str | None, opacity: float = 1.0) -> None:
    if color is None:
        shape.fill.background()
        return
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(color)
    if opacity < 1:
        clr = shape._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
        clr.append(parse_xml(f'<a:alpha xmlns:a="{A_NS}" val="{round(opacity * 100000)}"/>'))


def _paragraphs(
    frame: Any,
    lines: Sequence[Sequence[Run]],
    style: TextStyle,
    font: str,
    align: Align = "l",
    color: str | None = None,
) -> None:
    """Fill a text frame, one paragraph per line, with exact line spacing."""
    for index, runs in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = ALIGN[align]
        paragraph.line_spacing = Pt(style.line / 2)
        paragraph.space_before = paragraph.space_after = Pt(0)
        for run in runs:
            r = paragraph.add_run()
            r.text = run.text.upper() if style.upper else run.text
            r.font.name = font
            r.font.size = Pt(style.size / 2)
            r.font.bold = style.bold or run.bold
            r.font.italic = run.italic
            # A strong phrase inside ordinary text is set in ink, as in the HTML deck.
            r.font.color.rgb = rgb(color or (INK if run.bold and not style.bold else style.color))
            props = r._r.get_or_add_rPr()
            if abs(style.spacing) >= 1:  # a smaller tracking only breaks ligatures apart
                props.set("spc", str(round(style.spacing * 50)))
            if run.shift:
                props.set("baseline", "30000" if run.shift > 0 else "-25000")


def _frame(shape: Any, wrap: bool) -> Any:
    frame = shape.text_frame
    frame.word_wrap = wrap
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.TOP
    return frame


class Canvas:
    """One slide being drawn. Coordinates are pixels of the 1920 x 1080 slide."""

    def __init__(self, slide: Any, renderer: PptxRenderer) -> None:
        self.slide = slide
        self.shapes = slide.shapes
        self.r = renderer
        self.m = renderer.measurer

    # ------------------------------------------------------------------ text
    def lines(self, markup: str, style: TextStyle, width: float) -> int:
        """Number of lines the text takes at this width.

        A single line that misses the width by a hair counts as one line: `text` then sets it
        without wrapping, instead of leaving one word on a line of its own.
        """
        paragraphs = parse_lines(markup)
        if len(paragraphs) == 1 and self.m.width(paragraphs[0], style) <= width * (1 + NEAR_MISS):
            return 1
        return sum(self.m.line_count(line, style, width) for line in paragraphs)

    def text(
        self,
        x: float,
        y: float,
        width: float,
        markup: str,
        style: TextStyle | str,
        align: Align = "l",
        wrap: bool = True,
        color: str | None = None,
        shapes: Any = None,
        into: Any = None,
    ) -> float:
        """Place text and return its height. `into` fills an existing shape, such as the title placeholder."""
        st = STYLES[style] if isinstance(style, str) else style
        lines = parse_lines(markup)
        count = self.lines(markup, st, width) if wrap else len(lines)
        if len(lines) == 1 and count == 1:
            wrap = False  # one line stays one line, whatever the renderer measures
        height = count * st.line
        if into is None:
            shape = (self.shapes if shapes is None else shapes).add_textbox(emu(x), emu(y), emu(width), emu(height))
        else:
            shape = into
            shape.left, shape.top, shape.width, shape.height = emu(x), emu(y), emu(width), emu(height)
        _paragraphs(_frame(shape, wrap), lines, st, self.r.fonts.name(st.family), align, color)
        return height

    def width(self, markup: str, style: TextStyle | str) -> float:
        st = STYLES[style] if isinstance(style, str) else style
        return max(self.m.width(line, st) for line in parse_lines(markup))

    def one_line(self, x: float, y: float, markup: str, style: TextStyle | str, shapes: Any = None) -> float:
        """Text that must not wrap, in a box a little wider than the text. Returns the measured width."""
        width = self.width(markup, style)
        self.text(x, y, width * 1.05 + 8, markup, style, wrap=False, shapes=shapes)
        return width

    # ------------------------------------------------------------------ shapes
    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: str | None = None,
        line: str | None = None,
        radius: float = 0.0,
        name: str = "",
        shapes: Any = None,
    ) -> Any:
        kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        shape = (self.shapes if shapes is None else shapes).add_shape(kind, emu(x), emu(y), emu(width), emu(height))
        if radius:
            shape.adjustments[0] = radius / min(width, height)
        _unstyle(shape)
        _set_fill(shape, fill)
        _set_line(shape, line, 1.0)
        if name:
            shape.name = name
        return shape

    def card(self, x: float, y: float, width: float, height: float, name: str = "card") -> None:
        self.rect(x, y, width, height, CARD, HAIRLINE, radius=8, name=name)

    def segment(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: str,
        width: float,
        dash: Dash = "solid",
        round_cap: bool = False,
        arrow: bool = False,
        shapes: Any = None,
    ) -> Any:
        line = (self.shapes if shapes is None else shapes).add_connector(
            MSO_CONNECTOR.STRAIGHT, emu(x1), emu(y1), emu(x2), emu(y2)
        )
        _unstyle(line)
        _set_line(line, color, width, dash, round_cap)
        if arrow:
            line.line._get_or_add_ln().append(
                parse_xml(f'<a:tailEnd xmlns:a="{A_NS}" type="triangle" w="med" len="med"/>')
            )
        return line

    def key(
        self,
        x: float,
        y: float,
        kind: KeyKind,
        text: str,
        style: str = "key",
        shapes: Any = None,
        draw: bool = True,
    ) -> float:
        """A dot or a line swatch, then its text. Returns the total width; `draw=False` only measures."""
        st = STYLES[style]
        offset = KEY_TEXT_OFFSET[kind in DOT_KEYS]
        total = offset + self.width(text, st)
        if not draw:
            return total
        target = self.shapes if shapes is None else shapes
        middle = y + st.line / 2
        if kind in DOT_KEYS:
            dot = target.add_shape(MSO_SHAPE.OVAL, emu(x), emu(middle - 8), emu(16), emu(16))
            _unstyle(dot)
            _set_fill(dot, KEY_COLOR[kind])
            _set_line(dot, None, 0)
            dot.name = "key"
        else:
            self.segment(x, middle, x + 28, middle, KEY_COLOR[kind], 3, KEY_DASH.get(kind, "solid"), shapes=target)
        self.one_line(x + offset, y, text, st, shapes=target)
        return total

    # ------------------------------------------------------------------ plots
    def scene(self, scene: Scene, ox: float, oy: float, name: str) -> None:
        """Draw a scene with its top-left corner at (ox, oy), as one group."""
        group = self.shapes.add_group_shape()
        _describe(group, name, scene.aria)
        frame = self.rect(ox, oy, scene.width, scene.height, name="frame", shapes=group.shapes)
        frame.shadow.inherit = False
        pending: list[Path | Circle | RawSvg] = []

        def flush() -> None:
            if not pending:
                return
            png = raster(graphics_svg(scene.width, scene.height, pending), self.r.scale, self.r.env)
            picture = group.shapes.add_picture(io.BytesIO(png), emu(ox), emu(oy), emu(scene.width), emu(scene.height))
            picture.name = "image"
            self.r.images += 1
            pending.clear()

        for item in scene.graphics:
            if self.r.plots == "image" or isinstance(item, RawSvg):
                if self.r.plots == "native":
                    raise ValueError(
                        f"{name}: a shape has no PowerPoint equivalent. "
                        "Build with --plots auto to export it as an image."
                    )
                pending.append(item)
            else:
                flush()
                self._graphic(group.shapes, item, ox, oy)
        flush()
        for item in scene.labels:
            if isinstance(item, Key):
                self.key(ox + item.x, oy + item.y, item.kind, item.text, shapes=group.shapes)
            else:
                self._label(group.shapes, item, ox, oy)

    def _graphic(self, shapes: Any, item: Path | Circle, ox: float, oy: float) -> None:
        if isinstance(item, Circle):
            oval = shapes.add_shape(
                MSO_SHAPE.OVAL, emu(ox + item.cx - item.r), emu(oy + item.cy - item.r), emu(2 * item.r), emu(2 * item.r)
            )
            _unstyle(oval)
            _set_fill(oval, item.fill)
            _set_line(oval, item.stroke, item.width)
            return
        if item.fill is None and item.stroke and all(len(sub) == 2 for sub in item.subpaths):
            # Straight segments are connectors: a freeform cannot have zero width or height.
            for (x1, y1), (x2, y2) in item.subpaths:
                self.segment(
                    ox + x1,
                    oy + y1,
                    ox + x2,
                    oy + y2,
                    item.stroke,
                    item.width,
                    item.dash,
                    item.round_cap,
                    shapes=shapes,
                )
            return
        first = item.subpaths[0][0]
        builder = shapes.build_freeform(round(first[0] * UNITS), round(first[1] * UNITS), scale=PX / UNITS)
        for index, sub in enumerate(item.subpaths):
            if index:
                builder.move_to(round(sub[0][0] * UNITS), round(sub[0][1] * UNITS))
            builder.add_line_segments([(round(x * UNITS), round(y * UNITS)) for x, y in sub[1:]], close=item.closed)
        shape = builder.convert_to_shape(emu(ox), emu(oy))
        _unstyle(shape)
        _set_fill(shape, item.fill, item.opacity)
        _set_line(shape, item.stroke, item.width, item.dash, item.round_cap)

    def _label(self, shapes: Any, label: Label, ox: float, oy: float) -> None:
        style = label_style(label)
        width = label.width if label.width is not None else self.width(label.text, style) * 1.05 + 8
        self.text(ox + label.x, oy + label.y, width, label.text, style, label.align, wrap=False, shapes=shapes)

    # ------------------------------------------------------------------ blocks of a text column
    def block_height(self, block: Block | Eq | Stat, width: float) -> float:
        if isinstance(block, Say):
            return self.lines(block.text, STYLES["say"], width) * STYLES["say"].line
        if isinstance(block, Note):
            return self.lines(block.text, STYLES["note"], width) * STYLES["note"].line
        if isinstance(block, Eq):
            return STYLES[EQ_STYLE[block.size]].line
        if isinstance(block, Stat):
            return self._stat_layout(block, width)[1]
        if isinstance(block, Tight):
            return sum(self.block_height(b, width) for b in block.blocks)
        inner = width - 66
        parts = [self.block_height(b, inner) for b in block.body]
        if block.title:
            parts.insert(0, self.lines(block.title, STYLES["h3"], inner) * STYLES["h3"].line)
        return 58 + sum(parts) + 12 * (len(parts) - 1)

    def _stat_layout(self, stat: Stat, width: float) -> tuple[float, float]:
        """Offset of the caption below the top of the number, and the height of the pair.

        The two share a baseline, as `align-items: baseline` does in the HTML deck.
        """
        num, note = STYLES["num"], STYLES["note"]
        offset = self.m.baseline(num) - self.m.baseline(note)
        caption = self.lines(stat.caption, note, width - 124) * note.line
        return offset, max(num.line, offset + caption)

    def block(self, block: Block | Eq | Stat, x: float, y: float, width: float) -> float:
        """Draw one block and return its height."""
        if isinstance(block, Say):
            return self.text(x, y, width, block.text, "say")
        if isinstance(block, Note):
            return self.text(x, y, width, block.text, "note", "c" if block.centred else "l")
        if isinstance(block, Eq):
            return self.text(x, y, width, block.text, EQ_STYLE[block.size], wrap=False)
        if isinstance(block, Stat):
            offset, height = self._stat_layout(block, width)
            self.text(x, y, 104, block.number, "num", wrap=False)
            self.text(x + 124, y + offset, width - 124, block.caption, "note")
            return height
        if isinstance(block, Tight):
            return self.stack(block.blocks, x, y, width, 0)
        return self._def(block, x, y, width)

    def _def(self, card: Def, x: float, y: float, width: float) -> float:
        height = self.block_height(card, width)
        self.card(x, y, width, height, "definition")
        inner_x, inner, cursor = x + 33, width - 66, y + 29
        if card.title:
            cursor += self.text(inner_x, cursor, inner, card.title, "h3") + 12
        self.stack(card.body, inner_x, cursor, inner, 12)
        return height

    def stack(self, blocks: Sequence[Block | Eq | Stat], x: float, y: float, width: float, gap: float) -> float:
        """Draw blocks under one another and return the height of the stack."""
        cursor = y
        for index, block in enumerate(blocks):
            if index:
                cursor += gap
            cursor += self.block(block, x, cursor, width)
        return cursor - y

    # ------------------------------------------------------------------ parts shared by slides
    def head(self, eyebrow: str, title: str, style: str = "h2", colors: dict[str, str] | None = None) -> float:
        """Eyebrow and title. Returns the height of the block. The title fills the title placeholder."""
        colors = colors or {}
        y = MARGIN + self.text(MARGIN, MARGIN, CONTENT_W, eyebrow, "eyebrow", color=colors.get("eyebrow")) + 12
        y += self.text(MARGIN, y, CONTENT_W, title, style, color=colors.get(style), into=self.shapes.title)
        return y - MARGIN

    def table(
        self,
        x: float,
        y: float,
        width: float,
        header: Sequence[str],
        rows: Sequence[Sequence[str]],
        fractions: Sequence[float],
        highlight: int | None = None,
        header_fill: str = PAPER_2,
    ) -> float:
        """A native table in the deck's style. Returns its height."""
        height = TABLE_ROW * (len(rows) + 1)
        frame = self.shapes.add_table(len(rows) + 1, len(header), emu(x), emu(y), emu(width), emu(height))
        table = frame.table
        table.first_row = table.horz_banding = False
        table._tbl.tblPr.find(qn("a:tableStyleId")).text = NO_STYLE_TABLE
        for column, fraction in zip(table.columns, fractions, strict=True):
            column.width = emu(width * fraction)
        style = STYLES["table"]
        for r, row in enumerate([header, *rows]):
            table.rows[r].height = emu(TABLE_ROW)
            fill = header_fill if r == 0 else ("#FBE3D8" if highlight == r - 1 else None)
            for c, text in enumerate(row):
                cell = table.cell(r, c)
                cell.margin_left = cell.margin_right = emu(16.8)
                cell.margin_top = cell.margin_bottom = emu(9.8)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                lines = [[Run(run.text, run.italic, run.bold or r == 0, run.shift) for run in parse(text)]]
                _paragraphs(cell.text_frame, lines, style, self.r.fonts.name(style.family), color=INK)
                if fill:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = rgb(fill)
                else:
                    cell.fill.background()
                props = cell._tc.get_or_add_tcPr()
                for index, side in enumerate(("lnL", "lnR", "lnT", "lnB")):
                    props.insert(
                        index,
                        parse_xml(
                            f'<a:{side} xmlns:a="{A_NS}" w="{2 * PX}" cap="flat" cmpd="sng" algn="ctr">'
                            f'<a:solidFill><a:srgbClr val="{TABLE_BORDER}"/></a:solidFill>'
                            f'<a:prstDash val="solid"/></a:{side}>'
                        ),
                    )
        frame.name = "table"
        return height


class PptxRenderer:
    """Builds the PowerPoint file of a deck."""

    def __init__(
        self,
        measurer: Measurer,
        plots: PlotMode = "auto",
        scale: float = 3.0,
        env: dict[str, str] | None = None,
    ) -> None:
        self.measurer = measurer
        self.fonts = measurer.fonts
        self.plots: PlotMode = plots
        self.scale = scale
        self.env = env
        self.images = 0  # number of images exported so far

    def build(self, deck: Deck) -> Any:
        presentation = Presentation()
        presentation.slide_width, presentation.slide_height = emu(SLIDE_W), emu(SLIDE_H)
        core = presentation.core_properties
        core.title, core.author, core.last_modified_by = deck.title, "", ""
        layout = presentation.slide_layouts[5]  # title only: every slide keeps a real title
        for slide in deck.slides:
            page = presentation.slides.add_slide(layout)
            self._background(page, slide)
            self._slide(Canvas(page, self), slide)
            page._element.append(parse_xml(f'<p:transition xmlns:p="{P_NS}" spd="med"><p:fade/></p:transition>'))
        return presentation

    def write(self, deck: Deck, path: FilePath) -> FilePath:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.build(deck).save(str(path))
        return path

    @staticmethod
    def _background(page: Any, slide: Slide) -> None:
        if isinstance(slide, Cover):
            color = BACKGROUNDS["cover"]
        elif isinstance(slide, Statement):
            color = BACKGROUNDS["accent"]
        elif isinstance(slide, CardsSlide):
            color = BACKGROUNDS[slide.background]
        else:
            color = PAPER
        fill = page.background.fill
        fill.solid()
        fill.fore_color.rgb = rgb(color)

    def _slide(self, c: Canvas, slide: Slide) -> None:
        if isinstance(slide, Cover):
            self._cover(c, slide)
        elif isinstance(slide, Statement):
            self._statement(c, slide)
        elif isinstance(slide, PlotSlide):
            self._plot(c, slide)
        elif isinstance(slide, CardsSlide):
            self._cards(c, slide)
        elif isinstance(slide, TablesSlide):
            self._tables(c, slide)
        elif isinstance(slide, DiagramSlide):
            self._diagram(c, slide)
        else:
            self._table(c, slide)

    # ------------------------------------------------------------------ slide types
    def _cover(self, c: Canvas, slide: Cover) -> None:
        c.scene(slide.art, 0, 0, "cover art")
        y = MARGIN + c.text(MARGIN, MARGIN, CONTENT_W, slide.eyebrow, "eyebrow", color=COVER_TEXT["eyebrow"]) + 32
        y += c.text(MARGIN, y, CONTENT_W, slide.title, "h1", color=COVER_TEXT["h1"], into=c.shapes.title) + 32
        c.text(MARGIN, y, CONTENT_W, slide.lead, "lead", color=COVER_TEXT["lead"])

    def _statement(self, c: Canvas, slide: Statement) -> None:
        title, lead = STYLES["h2-xl"], STYLES["lead"]
        heights = (
            STYLES["eyebrow"].line,
            c.lines(slide.title, title, CONTENT_W) * title.line,
            c.lines(slide.lead, lead, slide.lead_width) * lead.line,
        )
        y = MARGIN + (BOTTOM - MARGIN - sum(heights) - 2 * GAP) / 2
        y += c.text(MARGIN, y, CONTENT_W, slide.eyebrow, "eyebrow", color=ACCENT_TEXT["eyebrow"]) + GAP
        y += c.text(MARGIN, y, CONTENT_W, slide.title, title, color=ACCENT_TEXT["h2-xl"], into=c.shapes.title) + GAP
        c.text(MARGIN, y, slide.lead_width, slide.lead, lead, color=ACCENT_TEXT["lead"])

    def _plot(self, c: Canvas, slide: PlotSlide) -> None:
        y = MARGIN + c.head(slide.eyebrow, slide.title) + GAP
        plot_x, gap = (MARGIN - 64, 40) if slide.flush else (MARGIN, 64)
        c.scene(slide.scene, plot_x, y, f"plot: {slide.id}")
        side_x = plot_x + PLOT_W + gap
        c.stack(slide.side, side_x, y, SLIDE_W - MARGIN - side_x, 32)

    def _cards(self, c: Canvas, slide: CardsSlide) -> None:
        y = MARGIN + c.head(slide.eyebrow, slide.title) + GAP
        if slide.keys:
            x = float(MARGIN)
            for key in slide.keys:
                x += c.key(x, y, key.kind, key.text) + 48
            y += STYLES["key"].line + GAP
        count = len(slide.cards)
        width = (CONTENT_W - 32 * (count - 1)) / count
        pad = 25 if slide.compact else 41  # padding plus the border
        inner = width - 2 * pad
        height = max(self._card_height(c, card, inner) for card in slide.cards) + 2 * pad
        for index, card in enumerate(slide.cards):
            x = MARGIN + index * (width + 32)
            c.card(x, y, width, height)
            self._card(c, card, x + pad, y + pad, inner, y + height - pad)
        c.text(MARGIN, y + height + GAP, CONTENT_W, slide.lead, "lead")

    @staticmethod
    def _card_parts(c: Canvas, card: Card, inner: float) -> list[float]:
        parts: list[float] = []
        if card.step:
            parts.append(STYLES["step"].line)
        if card.scene:
            parts.append(float(card.scene.height))
        parts.append(c.lines(card.title, STYLES["h3"], inner) * STYLES["h3"].line)
        parts.append(c.lines(card.note, STYLES["note"], inner) * STYLES["note"].line)
        return parts

    def _card_height(self, c: Canvas, card: Card, inner: float) -> float:
        parts = self._card_parts(c, card, inner)
        if card.tag or card.footer:
            parts.append(0.0)  # the spacer that pushes the tag and the rule to the bottom
        if card.tag:
            parts.append(STYLES["tag"].line)
        if card.footer:
            parts.append(STYLES[EQ_STYLE[card.footer.size]].line)
        return sum(parts) + 12 * (len(parts) - 1)

    @staticmethod
    def _card(c: Canvas, card: Card, x: float, y: float, inner: float, bottom: float) -> None:
        if card.step:
            y += c.text(x, y, inner, card.step, "step", wrap=False) + 12
        if card.scene:
            c.scene(card.scene, x, y, f"picture: {card.title}")
            y += card.scene.height + 12
        y += c.text(x, y, inner, card.title, "h3") + 12
        c.text(x, y, inner, card.note, "note")
        # The tag and the rule sit at the bottom of the card, whatever the length of the note.
        if card.footer:
            style = STYLES[EQ_STYLE[card.footer.size]]
            bottom -= style.line
            c.text(x, bottom, inner, card.footer.text, style, wrap=False)
            bottom -= 12
        if card.tag:
            c.text(x, bottom - STYLES["tag"].line, inner, card.tag, "tag", wrap=False)

    def _tables(self, c: Canvas, slide: TablesSlide) -> None:
        top = MARGIN + c.head(slide.eyebrow, slide.title) + GAP
        tables_w, gap = 1016.0, 32.0
        width = (tables_w - gap * (len(slide.tables) - 1)) / len(slide.tables)
        for index, table in enumerate(slide.tables):
            self._data_table(c, table, MARGIN + index * (width + gap), top, width)
        side_x = MARGIN + tables_w + 64
        c.stack(slide.side, side_x, top, SLIDE_W - MARGIN - side_x, 32)

    @staticmethod
    def _data_table(c: Canvas, table: DataTable, x: float, y: float, width: float) -> None:
        c.key(x, y, table.key.kind, table.key.text)
        y += STYLES["key"].line + 20
        y += c.table(x, y, width, table.header, table.rows, (0.54, 0.46), table.highlight) + 20
        mid, say = STYLES["mid"], STYLES["say"]
        number_w = c.width(table.published, mid)
        c.text(x, y, number_w * 1.05 + 8, table.published, mid, wrap=False)
        c.text(x + number_w + 20, y + c.m.baseline(mid) - c.m.baseline(say), width - number_w - 20, table.caption, say)

    def _diagram(self, c: Canvas, slide: DiagramSlide) -> None:
        y = MARGIN + c.head(slide.eyebrow, slide.title) + GAP
        y += c.text(MARGIN, y, CONTENT_W, slide.lead, "lead") + GAP
        for node in slide.nodes:
            self._node(c, node, MARGIN, y)
        for x1, y1, x2, y2 in slide.arrows:
            c.segment(MARGIN + x1, y + y1, MARGIN + x2, y + y2, MUTED, 3, arrow=True).name = "arrow"
        y += slide.diagram_size[1] + GAP
        # The definition, term by term, centred in its card.
        inner = CONTENT_W - 66
        eq, caption = STYLES["eq"], STYLES["key"]
        widths = [
            max(
                c.width(t.eq, eq),
                c.key(0, 0, t.key, t.caption, draw=False) if t.key else c.width(t.caption, caption),
            )
            for t in slide.terms
        ]
        note_h = c.lines(slide.note, STYLES["note"], inner) * STYLES["note"].line
        c.card(MARGIN, y, CONTENT_W, 58 + eq.line + 8 + caption.line + 12 + note_h, "definition")
        x = MARGIN + 33 + (inner - sum(widths) - 40 * (len(widths) - 1)) / 2
        top = y + 29
        for term, width in zip(slide.terms, widths, strict=True):
            c.text(x, top, width, term.eq, eq, "c", wrap=False)
            caption_y = top + eq.line + 8
            if term.key:
                key_w = c.key(0, 0, term.key, term.caption, draw=False)
                c.key(x + (width - key_w) / 2, caption_y, term.key, term.caption)
            else:
                c.text(x, caption_y, width, term.caption, caption, "c", wrap=False)
            x += width + 40
        c.text(MARGIN + 33, top + eq.line + 8 + caption.line + 12, inner, slide.note, "note", "c")

    @staticmethod
    def _node(c: Canvas, node: Node, ox: float, oy: float) -> None:
        x, y = ox + node.x, oy + node.y
        c.card(x, y, node.width, node.height, "node")
        inner = node.width - 66
        note = STYLES["note"]
        parts: list[float] = []
        if node.scene:
            parts.append(float(node.scene.height))
        if node.title:
            parts.append(STYLES["h3"].line)
        parts.append(c.lines(node.note, note, inner) * note.line)
        cursor = y + (node.height - sum(parts) - 8 * (len(parts) - 1)) / 2
        if node.scene:
            c.scene(node.scene, x + 33, cursor, "picture: outputs")
            cursor += node.scene.height + 8
        if node.title:
            if node.key:
                c.key(x + 33, cursor, node.key, node.title, style="h3")
            else:
                c.text(x + 33, cursor, inner, node.title, "h3", wrap=False)
            cursor += STYLES["h3"].line + 8
        c.text(x + 33, cursor, inner, node.note, note)

    def _table(self, c: Canvas, slide: TableSlide) -> None:
        y = MARGIN + c.head(slide.eyebrow, slide.title) + GAP
        c.table(MARGIN, y, CONTENT_W, slide.header, slide.rows, [w / 100 for w in slide.widths])
        height = c.block_height(slide.footer, CONTENT_W)
        c.block(slide.footer, MARGIN, BOTTOM - height, CONTENT_W)


def slide_titles(deck: Deck) -> list[str]:
    """Plain titles, in order. Used by tests and by the command line's summary."""
    return [plain(slide.title) for slide in deck.slides]
