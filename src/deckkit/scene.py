"""A plot as data: shapes and labels on a fixed canvas, with no output format in it.

A deck builds scenes; the renderers turn a scene into inline SVG for the HTML deck, a standalone
SVG or PNG, or native PowerPoint shapes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

Point = tuple[float, float]
Dash = Literal["solid", "dash", "dot", "guide"]
Align = Literal["l", "c", "r"]


@dataclass(frozen=True)
class Path:
    """One or more polylines sharing a stroke and a fill.

    A filled path that is not `closed` is filled as if its ends were joined, but only the drawn
    segments are stroked.
    """

    subpaths: tuple[tuple[Point, ...], ...]
    stroke: str | None = None
    width: float = 3.0
    dash: Dash = "solid"
    round_cap: bool = False
    fill: str | None = None
    opacity: float = 1.0
    closed: bool = False


@dataclass(frozen=True)
class Circle:
    cx: float
    cy: float
    r: float
    fill: str
    stroke: str | None = None
    width: float = 0.0


@dataclass(frozen=True)
class Label:
    """Text pinned at its top-left corner. With a `width`, the text is aligned inside it."""

    x: float
    y: float
    text: str
    width: float | None = None
    align: Align = "l"
    strong: bool = False
    math: bool = False
    size: float = 24.0
    line_height: float = 1.2


@dataclass(frozen=True)
class Mark:
    """What a legend entry shows before its text, in the colour of what it names.

    Without `line` it is a dot. With `line` it is a short line drawn with that dash, for telling
    apart curves of one colour.
    """

    color: str
    line: Dash | None = None


@dataclass(frozen=True)
class Key:
    """A legend entry: a mark, then its text."""

    x: float
    y: float
    mark: Mark
    text: str


@dataclass(frozen=True)
class RawSvg:
    """SVG markup with no PowerPoint equivalent, such as a gradient or a filter.

    The HTML and SVG outputs include it as it is. The PowerPoint output renders it to a
    transparent image that covers the whole scene, so it stays aligned with the native shapes.
    """

    markup: str


Graphic = Path | Circle | RawSvg
Item = Path | Circle | RawSvg | Label | Key


@dataclass
class Scene:
    """A drawing on a canvas of fixed size. Items are painted in order; text always sits on top."""

    width: int
    height: int
    aria: str
    items: list[Item] = field(default_factory=lambda: list[Item]())

    # ------------------------------------------------------------------ shapes
    def line(
        self,
        points: Sequence[Point] | Sequence[Sequence[Point]],
        color: str,
        width: float = 3.0,
        dash: Dash = "solid",
        round_cap: bool = False,
    ) -> None:
        """A polyline, or several when given a list of polylines."""
        self.items.append(Path(_subpaths(points), stroke=color, width=width, dash=dash, round_cap=round_cap))

    def segments(
        self,
        segments: Sequence[tuple[float, float, float, float]],
        color: str,
        width: float = 3.0,
        dash: Dash = "solid",
        round_cap: bool = False,
    ) -> None:
        """Separate straight segments, each given as x1, y1, x2, y2."""
        subpaths = tuple(((x1, y1), (x2, y2)) for x1, y1, x2, y2 in segments)
        self.items.append(Path(subpaths, stroke=color, width=width, dash=dash, round_cap=round_cap))

    def area(self, points: Sequence[Point], color: str, opacity: float, baseline: float) -> None:
        """The region between a curve and a horizontal baseline."""
        closed = ((points[0][0], baseline), *points, (points[-1][0], baseline))
        self.items.append(Path((closed,), fill=color, opacity=opacity, closed=True))

    def polygon(self, points: Sequence[Point], color: str, opacity: float) -> None:
        self.items.append(Path((tuple(points),), fill=color, opacity=opacity, closed=True))

    def filled_line(
        self, points: Sequence[Point], color: str, opacity: float, width: float = 3.0, closed: bool = False
    ) -> None:
        """A curve drawn with its stroke and a lighter fill of the same colour underneath."""
        self.items.append(Path((tuple(points),), stroke=color, width=width, fill=color, opacity=opacity, closed=closed))

    def circle(self, cx: float, cy: float, r: float, fill: str, stroke: str | None = None, width: float = 0) -> None:
        self.items.append(Circle(cx, cy, r, fill, stroke, width))

    def raw(self, markup: str) -> None:
        self.items.append(RawSvg(markup))

    # ------------------------------------------------------------------ text
    def label(
        self,
        x: float,
        y: float,
        text: str,
        width: float | None = None,
        align: Align = "l",
        strong: bool = False,
        math: bool = False,
        size: float = 24.0,
        line_height: float = 1.2,
    ) -> None:
        self.items.append(Label(x, y, text, width, align, strong, math, size, line_height))

    def key(self, x: float, y: float, mark: Mark, text: str) -> None:
        self.items.append(Key(x, y, mark, text))

    # ------------------------------------------------------------------ views
    @property
    def graphics(self) -> list[Graphic]:
        return [item for item in self.items if isinstance(item, Path | Circle | RawSvg)]

    @property
    def labels(self) -> list[Label | Key]:
        return [item for item in self.items if isinstance(item, Label | Key)]


def _subpaths(points: Sequence[Point] | Sequence[Sequence[Point]]) -> tuple[tuple[Point, ...], ...]:
    if not points:
        return ()
    first = points[0]
    if isinstance(first[0], int | float):
        return (tuple(points),)  # type: ignore[arg-type]
    return tuple(tuple(sub) for sub in points)  # type: ignore[arg-type]


def clip(points: Sequence[Point], y_low: float, y_high: float) -> list[list[Point]]:
    """The parts of a polyline that lie between two heights, cut exactly at the limits."""
    out: list[list[Point]] = []
    current: list[Point] = []

    def inside(p: Point) -> bool:
        return y_low - 1e-9 <= p[1] <= y_high + 1e-9

    def cut(a: Point, b: Point, outside: Point) -> Point:
        limit = y_low if outside[1] < y_low else y_high
        t = (limit - a[1]) / (b[1] - a[1])
        return (a[0] + t * (b[0] - a[0]), limit)

    for a, b in zip(points, points[1:], strict=False):
        a_in, b_in = inside(a), inside(b)
        if a_in and not current:
            current = [a]
        if a_in and b_in:
            current.append(b)
        elif a_in:
            current.append(cut(a, b, b))
            out.append(current)
            current = []
        elif b_in:
            current = [cut(a, b, a), b]
    if len(current) > 1:
        out.append(current)
    return out
