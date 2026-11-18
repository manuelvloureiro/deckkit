"""The slides as data: what is on each slide, with no output format in it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from dpdeck.scene import KeyKind, Scene


# ---------------------------------------------------------------- blocks of a text column
@dataclass(frozen=True)
class Say:
    """A sentence or two of running text."""

    text: str


@dataclass(frozen=True)
class Note:
    """Smaller, quieter text."""

    text: str
    centred: bool = False


@dataclass(frozen=True)
class Eq:
    """An equation on one line. Sizes: `m` is the default, `s` fits long formulas, `l` is for display."""

    text: str
    size: Literal["s", "m", "l"] = "m"


@dataclass(frozen=True)
class Stat:
    """A number with its caption on one line."""

    number: str
    caption: str


@dataclass(frozen=True)
class Tight:
    """Blocks stacked without the usual gap between them."""

    blocks: tuple[Eq | Stat, ...]


@dataclass(frozen=True)
class Def:
    """A definition card: an optional title, then equations and notes."""

    title: str | None
    body: tuple[Eq | Note | Tight | Stat, ...]


Block = Say | Note | Def | Tight


@dataclass(frozen=True)
class KeyLine:
    """A legend entry outside a plot."""

    kind: KeyKind
    text: str


# ---------------------------------------------------------------- slides
@dataclass(frozen=True)
class Cover:
    id: str
    eyebrow: str
    title: str
    lead: str
    art: Scene


@dataclass(frozen=True)
class Statement:
    """One sentence on a coloured slide, to open a section."""

    id: str
    eyebrow: str
    title: str
    lead: str
    lead_width: int = 1300


@dataclass(frozen=True)
class PlotSlide:
    """A plot on the left and its explanation on the right.

    `flush` moves the plot to the left edge of the heading and widens the text column. It is for
    plots without tick labels left of the axis.
    """

    id: str
    eyebrow: str
    title: str
    scene: Scene
    side: tuple[Block, ...]
    flush: bool = True


@dataclass(frozen=True)
class Card:
    title: str
    note: str
    step: str | None = None
    scene: Scene | None = None
    tag: str | None = None
    footer: Eq | None = None


@dataclass(frozen=True)
class CardsSlide:
    """A row of cards, with an optional row of keys above and a closing sentence below."""

    id: str
    eyebrow: str
    title: str
    cards: tuple[Card, ...]
    lead: str
    keys: tuple[KeyLine, ...] = ()
    compact: bool = False
    background: Literal["paper", "paper-2"] = "paper"


@dataclass(frozen=True)
class DataTable:
    """One version of the small dataset, with the number published from it."""

    key: KeyLine
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    published: str
    caption: str
    highlight: int | None = None


@dataclass(frozen=True)
class TablesSlide:
    id: str
    eyebrow: str
    title: str
    tables: tuple[DataTable, ...]
    side: tuple[Block, ...]


@dataclass(frozen=True)
class Node:
    """A box of a diagram, positioned inside the diagram's own frame."""

    x: float
    y: float
    width: float
    height: float
    note: str
    title: str | None = None
    key: KeyKind | None = None
    scene: Scene | None = None


@dataclass(frozen=True)
class Term:
    """One part of a displayed definition, with a caption under it."""

    eq: str
    caption: str
    key: KeyKind | None = None


@dataclass(frozen=True)
class DiagramSlide:
    """A sentence, a diagram of boxes and arrows, and a definition taken apart term by term."""

    id: str
    eyebrow: str
    title: str
    lead: str
    nodes: tuple[Node, ...]
    arrows: tuple[tuple[float, float, float, float], ...]
    terms: tuple[Term, ...]
    note: str
    diagram_size: tuple[int, int] = (1664, 320)


@dataclass(frozen=True)
class TableSlide:
    """A full-width table with a definition card pinned to the bottom of the slide."""

    id: str
    eyebrow: str
    title: str
    header: tuple[str, ...]
    widths: tuple[int, ...]
    rows: tuple[tuple[str, ...], ...]
    footer: Def


Slide = Cover | Statement | PlotSlide | CardsSlide | TablesSlide | DiagramSlide | TableSlide


@dataclass(frozen=True)
class Section:
    key: str
    start: str
    description: str


@dataclass(frozen=True)
class Deck:
    title: str
    slides: tuple[Slide, ...]
    sections: tuple[Section, ...] = field(default=())
