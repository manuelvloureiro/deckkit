"""Every plot of the deck, as a scene.

The running example is a survey count: 7 people say yes in D, and D' is D plus Alice, so 8. The
sensitivity is 1 and eps is 1 throughout, which makes the Laplace scale 1 and, for the Gaussian
pictures, sigma equal to the sensitivity.

Most plots share one horizontal axis, the published count from 3 to 12, so the curves keep their
place when the deck moves from one slide to the next.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from dpdeck.dpmath import (
    advanced_composition_epsilon,
    basic_composition_epsilon,
    gaussian_delta,
    laplace_pdf,
    linspace,
    loss_tail,
    normal_pdf,
    zcdp_epsilon,
)
from dpdeck.scene import Point, Scene, clip
from dpdeck.theme import AXIS, BLUE, DEEP, GREY, HAIRLINE, INK, ORANGE, PAPER, PLOT_H, PLOT_W, VIOLET

E = math.e
COUNT_D, COUNT_DP = 7.0, 8.0
EPS = 1.0
DELTA_1 = gaussian_delta(EPS, 1.0)  # sigma equal to the sensitivity
DELTA_2 = gaussian_delta(2 * EPS, math.sqrt(2))  # the sum of two such releases
TAIL_1 = loss_tail(EPS, 0.5, 1.0)

# ---------------------------------------------------------------- the shared frame
BASE = 548.0  # height of the horizontal axis
TOP = 44.0  # curves on a log scale are cut here


def x_count(y: float) -> float:
    """Horizontal position of a published count between 3 and 12."""
    return 64 + (y - 3) * 960 / 9


X7, X8, X9 = x_count(7), x_count(8), x_count(9)
GRID = sorted(set(linspace(3, 12, 180) + [7.0, 8.0, 6.5]))


def _curve(f: Callable[[float], float], to_y: Callable[[float], float], grid: list[float] = GRID) -> list[Point]:
    return [(x_count(y), to_y(f(y))) for y in grid]


def _plot(aria: str) -> Scene:
    return Scene(PLOT_W, PLOT_H, aria)


def _axis(scene: Scene, vertical: bool = False) -> None:
    if vertical:
        scene.line([(64, TOP), (64, BASE), (1024, BASE)], AXIS, 1.5)
    else:
        scene.line([(64, BASE), (1024, BASE)], AXIS, 1.5)


def _guides(scene: Scene, top: float, xs: tuple[float, ...] = (X7, X8)) -> None:
    scene.segments([(x, BASE, x, top) for x in xs], AXIS, 1.5, dash="guide")


def _h_bracket(scene: Scene, x1: float, x2: float, y: float) -> None:
    scene.segments([(x1, y, x2, y), (x1, y - 8, x1, y + 8), (x2, y - 8, x2, y + 8)], INK, 3, round_cap=True)


def _v_bracket(x: float, y0: float, y1: float) -> list[tuple[float, float, float, float]]:
    """A vertical bracket drawn just inside the two heights."""
    return [(x, y0 + 5, x, y1 - 5), (x - 8, y0 + 5, x + 8, y0 + 5), (x - 8, y1 - 5, x + 8, y1 - 5)]


def _sensitivity_mark(scene: Scene) -> None:
    _h_bracket(scene, X7, X8, 492)
    scene.label((X7 + X8) / 2 - 40, 502, "Δ", 80, "c", strong=True, math=True, size=32, line_height=1)


def _count_labels(scene: Scene, top: float = 560) -> None:
    scene.label(X7 + 18 - 160, top, "*f*(*D*) = 7", 160, "r", math=True)
    scene.label(X8 - 18, top, "*f*(*D′*) = 8", 160, math=True)
    scene.label(X7 + 18 - 200, top + 32, "without Alice", 200, "r")
    scene.label(X8 - 18, top + 32, "with Alice", 200)
    scene.label(784, top, "published count", 240, "r")


def _two_keys(scene: Scene, x: float, y: float) -> None:
    scene.key(x, y, "d", "published count on *D*")
    scene.key(x, y + 34, "dp", "published count on *D′*")


# ================================================================ Laplace noise, linear scale
def sensitivity() -> Scene:
    def to_y(d: float) -> float:
        return BASE - 800 * d

    blue = _curve(lambda y: laplace_pdf(y, COUNT_D), to_y)
    orange = _curve(lambda y: laplace_pdf(y, COUNT_DP), to_y)
    s = _plot(
        "Two identical peaked curves of possible published counts, one centred on 7 and one on 8, a distance Δ apart"
    )
    _axis(s)
    _guides(s, 130)
    s.area(blue, BLUE, 0.12, BASE)
    s.area(orange, ORANGE, 0.12, BASE)
    s.line(orange, ORANGE)
    s.line(blue, BLUE)
    _sensitivity_mark(s)
    s.label(64, 0, "how likely each published count is")
    _two_keys(s, 64, 52)
    _count_labels(s)
    return s


def _laplace_y(d: float) -> float:
    return BASE - 340 * d


def pure_dp() -> Scene:
    blue = _curve(lambda y: laplace_pdf(y, COUNT_D), _laplace_y)
    orange = _curve(lambda y: laplace_pdf(y, COUNT_DP), _laplace_y)
    stretched = _curve(lambda y: E * laplace_pdf(y, COUNT_DP), _laplace_y)
    s = _plot(
        "The same two curves, and a dashed copy of the orange curve multiplied by 2.7. The dashed "
        "curve lies on or above the blue curve everywhere"
    )
    _axis(s)
    _guides(s, 366)
    s.area(blue, BLUE, 0.12, BASE)
    s.area(orange, ORANGE, 0.12, BASE)
    s.line(orange, ORANGE)
    s.line(blue, BLUE)
    s.line(stretched, ORANGE, dash="dash")
    _h_bracket(s, X7, X8, 492)
    # One published count, 6.5, read on both curves: blue is exactly 2.7 times orange there.
    xm = x_count(6.5)
    y_blue, y_orange = _laplace_y(laplace_pdf(6.5, COUNT_D)), _laplace_y(laplace_pdf(6.5, COUNT_DP))
    s.segments([(xm, BASE, xm, y_blue)], INK, 2)
    s.circle(xm, y_orange, 9, ORANGE, PAPER, 3)
    s.circle(xm, y_blue, 9, BLUE, PAPER, 3)
    s.label(64, 0, "how likely each published count is")
    _two_keys(s, 64, 52)
    s.key(64, 120, "dash", "orange curve × 2.7")
    s.label(76, 396, "here blue is exactly 2.7 × orange", 344, "r", strong=True)
    s.label(664, 96, "**orange × 2.7**\ncovers blue everywhere", 340)
    s.label((X7 + X8) / 2 - 40, 502, "Δ", 80, "c", strong=True, math=True, size=32, line_height=1)
    _count_labels(s)
    return s


def calibration_panel(scale: float, aria: str, show_gap: bool) -> Scene:
    """Laplace curves for one noise scale, drawn so that the stretched peak has the same height."""
    base, peak = 222.0, 200.0
    k = peak * 2 * scale / E

    def x(y: float) -> float:
        return (y - 1.5) * 40

    def to_y(d: float) -> float:
        return base - k * d

    grid = sorted(set(linspace(1.5, 13.5, 240) + [7.0, 7.25, 8.0]))
    blue = [(x(y), to_y(laplace_pdf(y, COUNT_D, scale))) for y in grid]
    orange = [(x(y), to_y(laplace_pdf(y, COUNT_DP, scale))) for y in grid]
    stretched = [(x(y), to_y(E * laplace_pdf(y, COUNT_DP, scale))) for y in grid]
    s = Scene(480, 260, aria)
    s.line([(0, base), (480, base)], AXIS, 1.5)
    s.segments([(x(7), base, x(7), base + 8), (x(8), base, x(8), base + 8)], AXIS, 1.5)
    s.polygon([(0, base), *blue, (480, base)], BLUE, 0.12)
    s.polygon([(0, base), *orange, (480, base)], ORANGE, 0.12)
    if show_gap:
        left = [y for y in grid if y <= 7.25]
        s.polygon(
            [(x(y), to_y(laplace_pdf(y, COUNT_D, scale))) for y in left]
            + [(x(y), to_y(E * laplace_pdf(y, COUNT_DP, scale))) for y in reversed(left)],
            DEEP,
            0.45,
        )
    s.line(orange, ORANGE)
    s.line(blue, BLUE)
    s.line(stretched, ORANGE, dash="dash")
    if show_gap:
        s.segments([(150, 118, 228, 176)], INK, 2, round_cap=True)
        s.label(8, 84, "blue sticks out", 200, strong=True)
    s.label(x(7) - 20, 232, "7", 40, "c", math=True)
    s.label(x(8) - 20, 232, "8", 40, "c", math=True)
    return s


# ================================================================ Laplace noise, log scale
def log_scale() -> Scene:
    def to_y(v: float) -> float:
        return 48 + (0.6 - v) * 72

    def tent(centre: float, lift: float = 0.0) -> list[Point]:
        return [(x_count(y), to_y(math.log(laplace_pdf(y, centre)) + lift)) for y in (3, centre, 12)]

    xb = 620.0
    yb = (xb - 64) * 9 / 960 + 3
    y_orange = to_y(math.log(laplace_pdf(yb, COUNT_DP)))
    y_lifted = to_y(math.log(laplace_pdf(yb, COUNT_DP)) + EPS)
    s = _plot(
        "On a log scale the Laplace curves are straight lines. The orange line lifted by ε lies on "
        "or above the blue line everywhere, and exactly on it left of 7"
    )
    _axis(s, vertical=True)
    _guides(s, to_y(math.log(0.5)))
    s.line(tent(COUNT_DP), ORANGE)
    s.line(tent(COUNT_D), BLUE)
    s.line(tent(COUNT_DP, EPS), ORANGE, dash="dash")
    s.segments(_v_bracket(xb, y_lifted, y_orange), INK, 3, round_cap=True)
    s.label(64, 0, "how likely each published count is, on a log scale")
    s.label(76, 112, "**left of 7 the gap is exactly ε**\nblue meets the lifted curve", 380)
    s.label(xb + 14, round((y_orange + y_lifted) / 2 - 12), "ε", 40, strong=True, math=True, size=32, line_height=1)
    _two_keys(s, 350, 436)
    s.key(350, 504, "dash", "orange curve lifted by ε")
    _count_labels(s)
    return s


# ================================================================ Gaussian noise, linear scale
def _gauss_y(d: float) -> float:
    return BASE - 420 * d


def _gaussian_linear(aria: str, gap_opacity: float, leader: tuple[float, float, float, float]) -> Scene:
    blue = _curve(lambda y: normal_pdf(y, COUNT_D), _gauss_y)
    orange = _curve(lambda y: normal_pdf(y, COUNT_DP), _gauss_y)
    stretched = _curve(lambda y: E * normal_pdf(y, COUNT_DP), _gauss_y)
    # Left of 6.5 the blue bell is above the stretched orange one. That sliver is delta.
    left = [y for y in GRID if y <= 6.5]
    sliver = [(x_count(y), _gauss_y(normal_pdf(y, COUNT_D))) for y in left] + [
        (x_count(y), _gauss_y(E * normal_pdf(y, COUNT_DP))) for y in reversed(left)
    ]
    s = _plot(aria)
    _axis(s)
    _guides(s, 366)
    s.area(blue, BLUE, 0.12, BASE)
    s.area(orange, ORANGE, 0.12, BASE)
    s.polygon(sliver, DEEP, gap_opacity)
    s.line(orange, ORANGE)
    s.line(blue, BLUE)
    s.line(stretched, ORANGE, dash="dash")
    _h_bracket(s, X7, X8, 492)
    s.segments([leader], INK, 2, round_cap=True)
    s.label(64, 0, "how likely each published count is")
    _two_keys(s, 64, 52)
    s.key(64, 120, "dash", "orange curve × 2.7")
    return s


def gaussian() -> Scene:
    s = _gaussian_linear(
        "Two bell curves centred on 7 and 8, and a dashed copy of the orange bell multiplied by 2.7. "
        "Left of 6.5 the blue bell rises above the dashed curve",
        0.35,
        (300, 362, 338, 498),
    )
    s.label(64, 328, "the blue curve sticks out here", 360, "r", strong=True)
    s.label((X7 + X8) / 2 - 40, 502, "Δ", 80, "c", strong=True, math=True, size=32, line_height=1)
    _count_labels(s)
    return s


def approx_dp() -> Scene:
    s = _gaussian_linear(
        "The same two bells and the dashed curve. The area of the blue bell above the dashed curve "
        "is filled: it is δ, about 0.13",
        0.85,
        (300, 372, 338, 498),
    )
    s.label(64, 310, f"**δ = {DELTA_1:.2f}**\nthe area left uncovered", 360, "r")
    s.label((X7 + X8) / 2 - 40, 502, "Δ", 80, "c", strong=True, math=True, size=32, line_height=1)
    _count_labels(s)
    return s


# ================================================================ Gaussian noise, log scale
def gaussian_log() -> Scene:
    def to_y(v: float) -> float:
        return 48 + (0.6 - v) * 46

    def log_orange(y: float) -> float:
        return math.log(normal_pdf(y, COUNT_DP))

    blue = _curve(lambda y: math.log(normal_pdf(y, COUNT_D)), to_y)
    orange = _curve(log_orange, to_y)
    lifted = _curve(lambda y: log_orange(y) + EPS, to_y)
    left = [y for y in GRID if y <= 6.5]
    wedge = [(x_count(y), min(BASE, to_y(math.log(normal_pdf(y, COUNT_D))))) for y in left] + [
        (x_count(y), min(BASE, to_y(log_orange(y) + EPS))) for y in reversed(left)
    ]
    # Brackets of equal height along the curves: the lift is eps everywhere, measured straight up.
    peak_x = 620.0
    peak_y = (peak_x - 64) * 9 / 960 + 3
    marks = (4.6, 5.6, 9.4, 10.4, 11.2)
    s = _plot(
        "On a log scale the two bells are parabolas. Left of 6.5 the blue parabola is above the "
        "orange one lifted by ε, and the gap keeps widening"
    )
    s.polygon(wedge, DEEP, 0.3)
    _axis(s, vertical=True)
    s.segments(
        [(X7, BASE, X7, to_y(math.log(normal_pdf(7, 7)))), (X8, BASE, X8, to_y(math.log(normal_pdf(8, 8))))],
        AXIS,
        1.5,
        dash="guide",
    )
    s.line(clip(orange, TOP, BASE), ORANGE)
    s.line(clip(blue, TOP, BASE), BLUE)
    s.line(clip(lifted, TOP, BASE), ORANGE, dash="dash")
    s.segments([(170, 122, 236, 296)], INK, 2, round_cap=True)
    brackets: list[tuple[float, float, float, float]] = []
    for v in (*marks, peak_y):
        brackets += _v_bracket(x_count(v), to_y(log_orange(v) + EPS) - 5, to_y(log_orange(v)) + 5)
    s.segments(brackets, INK, 3, round_cap=True)
    s.label(64, 0, "how likely each published count is, on a log scale")
    s.label(76, 56, "**not covered**\nand the gap keeps growing", 340)
    mid = (to_y(log_orange(peak_y)) + to_y(log_orange(peak_y) + EPS)) / 2
    s.label(peak_x + 14, round(mid - 15), "ε", 40, strong=True, math=True, size=32, line_height=1)
    _two_keys(s, 400, 400)
    s.key(400, 468, "dash", "orange curve lifted by ε")
    for v in marks:
        top = to_y(log_orange(v) + EPS) - 30 if v > 8 else to_y(log_orange(v)) + 4
        s.label(round(x_count(v) + 12), round(top), "ε", 30, strong=True, math=True)
    _count_labels(s)
    return s


# ================================================================ the privacy loss distribution
def _x_loss(loss: float) -> float:
    return 64 + (loss + 3) * 128


def _loss_y(d: float) -> float:
    return BASE - 1000 * d


def _loss_pdf(loss: float) -> float:
    """Privacy loss of the Gaussian mechanism with sigma equal to the sensitivity: N(0.5, 1)."""
    return normal_pdf(loss, 0.5, 1.0)


def _loss_bell() -> list[Point]:
    return [(_x_loss(v), _loss_y(_loss_pdf(v))) for v in linspace(-3, 4.5, 150)]


def _beyond(eps: float, uncovered: bool) -> list[Point]:
    """The tail of the loss bell beyond a wall at eps, or only its uncovered part.

    A loss L beyond the wall is covered up to a factor e^(eps - L), so 1 - e^(eps - L) of its
    probability is left over. Summed over the tail, that is delta.
    """
    points: list[Point] = [(_x_loss(eps), BASE)]
    for v in linspace(eps, 4.5, 60):
        share = 1 - math.exp(eps - v) if uncovered else 1.0
        points.append((_x_loss(v), _loss_y(_loss_pdf(v) * share)))
    points.append((_x_loss(4.5), BASE))
    return points


def _loss_axis(scene: Scene) -> None:
    _axis(scene)
    scene.segments([(_x_loss(0), BASE, _x_loss(0), BASE + 10)], AXIS, 1.5)


def loss_distribution() -> Scene:
    bell = _loss_bell()
    s = _plot(
        "A bell curve of privacy loss values centred at 0.5. A wall stands at ε = 1. The tail beyond "
        f"it holds {TAIL_1 * 100:.0f}% of the mass, and a darker part of that tail, {DELTA_1:.2f}, is δ"
    )
    _loss_axis(s)
    s.area(bell, VIOLET, 0.12, BASE)
    s.polygon(_beyond(EPS, uncovered=False), VIOLET, 0.22)
    s.polygon(_beyond(EPS, uncovered=True), DEEP, 0.85)
    s.line(bell, VIOLET)
    s.segments([(_x_loss(1), BASE, _x_loss(1), 130)], INK, 3, round_cap=True)
    s.segments([(800, 424, 728, 500)], INK, 2, round_cap=True)
    s.label(64, 0, "how often each loss occurs")
    s.label(96, 300, "most published counts:\na small loss", 300)
    s.label(_x_loss(1) + 20, 130, f"**loss above ε**\nfor {TAIL_1 * 100:.0f}% of published counts", 380)
    s.label(760, 330, f"**δ = {DELTA_1:.2f}**\nthe uncovered part\nof that tail", 264)
    s.label(64, 560, "privacy loss *L*", 240)
    s.label(_x_loss(0) - 40, 560, "0", 80, "c", math=True)
    s.label(_x_loss(1) - 60, 560, "ε = 1", 120, "c", strong=True, math=True)
    return s


def many_pairs() -> Scene:
    bell = _loss_bell()
    walls = [(0.5, 70.0, 0.28), (1.0, 146.0, 0.5), (2.0, 326.0, 0.9)]
    pairs = ", ".join(f"{gaussian_delta(e, 1.0):.2f}" for e, _, _ in walls)
    s = _plot(
        f"The same bell with three walls, at ε = 0.5, 1 and 2. The uncovered part beyond each wall is δ = {pairs}"
    )
    _loss_axis(s)
    s.area(bell, VIOLET, 0.12, BASE)
    for eps, _, opacity in walls:
        s.polygon(_beyond(eps, uncovered=True), DEEP, opacity)
    s.line(bell, VIOLET)
    for eps, top, _ in walls:
        s.segments([(_x_loss(eps), BASE, _x_loss(eps), top)], INK, 3, round_cap=True)
    s.label(64, 0, "how often each loss occurs")
    for eps, top, _ in walls:
        s.label(_x_loss(eps) + 16, top - 6, f"**ε = {eps:g}**\nδ = {gaussian_delta(eps, 1.0):.2f}", 200)
    s.label(64, 560, "privacy loss *L*", 240)
    for v in (0, 0.5, 1, 2):
        s.label(_x_loss(v) - 40, 560, f"{v:g}", 80, "c", math=True)
    return s


# ================================================================ two releases
def compose_pure() -> Scene:
    """Three Laplace curves on a log scale: f(D), one release on D' and the worst case of two."""

    def to_y(v: float) -> float:
        return 48 + (1.5 - v) * 64

    def tent(centre: float, lift: float = 0.0) -> list[Point]:
        return [(x_count(y), to_y(math.log(laplace_pdf(y, centre)) + lift)) for y in (3, centre, 12)]

    xs = x_count(4.6)
    v_blue = math.log(laplace_pdf(4.6, COUNT_D))
    ya, yb, yc = to_y(v_blue), to_y(v_blue - EPS), to_y(v_blue - 2 * EPS)
    xr = 728.0
    yr = (xr - 64) * 9 / 960 + 3
    y3, y3_lifted = to_y(math.log(laplace_pdf(yr, 9))), to_y(math.log(laplace_pdf(yr, 9)) + 2 * EPS)
    s = _plot(
        "Three straight-line curves on a log scale, centred at f(D), f(D) + Δ and f(D) + 2Δ. Left of "
        "f(D) the gaps stack: ε down to the first orange curve and ε more down to the second, so the "
        "second must be lifted by 2ε to cover the blue curve"
    )
    _axis(s, vertical=True)
    _guides(s, to_y(math.log(0.5)), (X7, X8, X9))
    s.line(clip(tent(8), TOP, BASE), ORANGE, dash="dot", round_cap=True)
    s.line(clip(tent(9), TOP, BASE), ORANGE)
    s.line(clip(tent(7), TOP, BASE), BLUE)
    s.line(clip(tent(9, 2 * EPS), TOP, BASE), ORANGE, dash="dash")
    s.segments(_v_bracket(xs, ya, yb) + _v_bracket(xs, yb, yc) + _v_bracket(xr, y3_lifted, y3), INK, 3, round_cap=True)
    s.label(64, 0, "how likely each published value is, on a log scale")
    s.label(round(xs + 14), round((ya + yb) / 2 - 22), "ε", 40, strong=True, math=True, size=32, line_height=1)
    s.label(round(xs + 14), round((yb + yc) / 2 - 22), "ε", 40, strong=True, math=True, size=32, line_height=1)
    s.label(round(xr + 14), round((y3 + y3_lifted) / 2 - 10), "2ε", 60, strong=True, math=True, size=32, line_height=1)
    s.key(404, 400, "d", "on *D*")
    s.key(404, 434, "dot", "on *D′*, one release")
    s.key(404, 468, "solid", "on *D′*, two releases: as if Δ + Δ")
    s.key(404, 502, "dash", "that curve lifted by 2ε")
    s.label(X7 - 50, 560, "*f*(*D*)", 100, "c", math=True)
    s.label(X8 - 50, 560, "+ Δ", 100, "c", math=True)
    s.label(X9 - 50, 560, "+ 2Δ", 100, "c", math=True)
    s.label(804, 560, "published value", 220, "r")
    return s


def compose_approx() -> Scene:
    """The sum of two Gaussian releases: shifted by twice the sensitivity, with twice the variance."""
    unit = 960 / 11
    root2 = math.sqrt(2)

    def x(t: float) -> float:
        return 64 + (t + 4.5) * unit

    def to_y(d: float) -> float:
        return BASE - 513 * d

    grid = sorted(set(linspace(-4.5, 6.5, 220) + [-1.0]))

    def bell(centre: float, sd: float, factor: float = 1.0) -> list[Point]:
        return [(x(t), to_y(factor * normal_pdf(t, centre, sd))) for t in grid]

    one_blue, one_orange = bell(0, 1), bell(1, 1)
    two_blue, two_orange = bell(0, root2), bell(2, root2)
    stretched = bell(2, root2, E * E)
    left = [t for t in grid if t <= -1.0]
    sliver = [(x(t), to_y(normal_pdf(t, 0, root2))) for t in left] + [
        (x(t), to_y(E * E * normal_pdf(t, 2, root2))) for t in reversed(left)
    ]
    xa, xc = x(0), x(2)
    s = _plot(
        "Dotted: the two bells of one release, Δ apart. Solid: the bells of the sum of two releases, "
        "2Δ apart and wider, with variance 2σ². A dashed copy of the solid orange bell multiplied by "
        f"7.4 covers the solid blue bell except for a small filled area on the left, {DELTA_2:.2f}"
    )
    _axis(s)
    s.segments([(v, BASE, v, BASE + 10) for v in (xa, x(1), xc)], AXIS, 1.5)
    s.area(two_blue, BLUE, 0.12, BASE)
    s.area(two_orange, ORANGE, 0.12, BASE)
    s.polygon(sliver, DEEP, 0.85)
    s.line(one_blue, BLUE, dash="dot", round_cap=True)
    s.line(one_orange, ORANGE, dash="dot", round_cap=True)
    s.line(two_orange, ORANGE)
    s.line(two_blue, BLUE)
    s.line(clip(stretched, TOP, BASE), ORANGE, dash="dash")
    s.segments([(xa, 500, xc, 500), (xa, 492, xa, 508), (xc, 492, xc, 508)], INK, 3, round_cap=True)
    s.segments([(236, 432, 296, 502)], INK, 2, round_cap=True)
    s.label(64, 0, "how likely each total is")
    s.key(64, 52, "d", "without Alice (*D*)")
    s.key(64, 86, "dp", "with Alice (*D′*)")
    s.key(64, 120, "dot-ink", "one release")
    s.key(64, 154, "solid-ink", "two releases, added up")
    s.key(64, 188, "dash", "orange × 7.4, for ε + ε = 2")
    s.label(96, 372, f"**δ = {DELTA_2:.2f}**\nleft uncovered", 260)
    s.label(700, 326, "**wider**\nvariance 2*σ*²", 150)
    s.label((xa + xc) / 2 - 40, 508, "2Δ", 80, "c", strong=True, math=True, size=32, line_height=1)
    s.label(xa - 40, 560, "0", 80, "c", math=True)
    s.label(x(1) - 40, 560, "Δ", 80, "c", math=True)
    s.label(xc - 40, 560, "2Δ", 80, "c", math=True)
    s.label(664, 560, "noise plus Alice’s contribution", 360, "r")
    return s


# ================================================================ concentrated definitions
CD_BASE = 540.0


def _cd_y(d: float) -> float:
    return CD_BASE - 551 * d


def cdp() -> Scene:
    """An arbitrary privacy loss next to the Gaussian yardstick that bounds it."""

    def x(loss: float) -> float:
        return 64 + (loss + 1.75) * 240

    mu, tau = 0.125, 0.5
    start, span = -1.15, 2.6

    def actual(loss: float) -> float:
        u = (loss - start) / span
        return 60 * u * u * (1 - u) ** 3 / span if 0 < u < 1 else 0.0

    s = _plot(
        "A filled privacy loss distribution sits beside a dashed Gaussian bell with centre μ and "
        "width τ. The filled shape is centred no further right and spreads no wider than the dashed bell"
    )
    s.line([(64, CD_BASE), (1024, CD_BASE)], AXIS, 1.5)
    s.segments([(x(0), CD_BASE, x(0), CD_BASE + 10)], AXIS, 1.5)
    s.segments([(x(mu), CD_BASE, x(mu), _cd_y(normal_pdf(mu, mu, tau)))], AXIS, 1.5, dash="guide")
    s.filled_line([(x(v), _cd_y(actual(v))) for v in linspace(start, start + span, 40)], VIOLET, 0.28)
    s.line([(x(v), _cd_y(normal_pdf(v, mu, tau))) for v in linspace(-1.75, 2.25, 64)], INK, dash="dash")
    y_tau = _cd_y(normal_pdf(mu + tau, mu, tau))
    s.segments(
        [
            (x(mu), y_tau, x(mu + tau), y_tau),
            (x(mu), y_tau - 10, x(mu), y_tau + 10),
            (x(mu + tau), y_tau - 10, x(mu + tau), y_tau + 10),
        ],
        INK,
        3,
        round_cap=True,
    )
    s.label(64, 0, "how often each loss occurs")
    s.key(64, 200, "l", "actual privacy loss")
    s.label(640, 110, "Gaussian yardstick", 380, strong=True)
    s.label(640, 144, "mean *μ*, standard deviation *τ*", 380)
    s.label(518, 222, "*τ*", 80, "c", strong=True, math=True, size=32)
    s.label(64, 552, "privacy loss *L*", 240)
    s.label(474, 548, "*μ*", 80, "c", strong=True, math=True, size=32)
    return s


def _rho_bells(aria: str) -> Scene:
    """Privacy loss bells N(rho, 2 rho) for rho = 2, 0.5 and 0.125."""

    def x(loss: float) -> float:
        return 64 + (loss + 4) * 80

    s = _plot(aria)
    s.line([(64, CD_BASE), (1024, CD_BASE)], AXIS, 1.5)
    s.segments([(x(v), CD_BASE, x(v), CD_BASE + 10) for v in (0, 2, 4, 6)], AXIS, 1.5)
    for rho, color in ((2.0, "#35268F"), (0.5, VIOLET), (0.125, "#9184E4")):
        sd = math.sqrt(2 * rho)
        low, high = max(-4.0, rho - 4.2 * sd), min(8.0, rho + 4.2 * sd)
        s.filled_line([(x(v), _cd_y(normal_pdf(v, rho, sd))) for v in linspace(low, high, 48)], color, 0.10)
    for v in (0, 2, 4, 6):
        s.label(x(v) - 40, 552, f"{v}", 80, "c", math=True)
    return s


def zcdp() -> Scene:
    s = _rho_bells("Three bells for ρ = 0.125, 0.5 and 2. As ρ grows, the bell moves right and widens")
    s.label(64, 0, "how often each loss occurs")
    s.label(424, 92, "*ρ* = 0.125", 200, strong=True, math=True)
    s.label(504, 296, "*ρ* = 0.5", 200, strong=True, math=True)
    s.label(724, 416, "*ρ* = 2", 200, strong=True, math=True)
    s.label(64, 552, "privacy loss *L*", 240)
    return s


def composition() -> Scene:
    s = _rho_bells(
        "The same three bells, now the total privacy loss after 1, 4 and 16 releases. The bell moves "
        "right and widens as releases accumulate"
    )
    s.label(64, 0, "how often each total loss occurs")
    s.label(424, 88, "**1 release**\ntotal *ρ* = 0.125", 260)
    s.label(504, 276, "**4 releases**\ntotal *ρ* = 0.5", 260)
    s.label(724, 396, "**16 releases**\ntotal *ρ* = 2", 260)
    s.label(64, 552, "total privacy loss", 240)
    return s


# ================================================================ the cost of many releases
COST_RELEASES = 200
COST_RATIO = 1 / 50  # sigma is 50 times the sensitivity
COST_DELTA = 1e-6


def cost_totals() -> tuple[float, float, float]:
    """Total eps after all releases under the basic rule, the advanced rule and zero-concentrated accounting."""
    args = (COST_RELEASES, COST_RATIO, COST_DELTA)
    return basic_composition_epsilon(*args), advanced_composition_epsilon(*args), zcdp_epsilon(*args)


def cost() -> Scene:
    def x(k: float) -> float:
        return 80 + k * 820 / 200

    def to_y(eps: float) -> float:
        return 560 - eps * 25

    ks = [1, 2, 3, 4, 6, 8, 10, 13, 16, 20, 25, 30, 35, 40, *range(50, 201, 10)]
    basic, advanced, zc = cost_totals()
    s = _plot(
        "Line chart of total ε against the number of releases, from 1 to 200. Basic composition rises "
        f"in a straight line to {basic:.1f}, advanced composition bends to {advanced:.1f}, "
        f"zero-concentrated accounting stays low and reaches {zc:.1f}"
    )
    s.segments([(80, to_y(e), 900, to_y(e)) for e in (5, 10, 15, 20)], HAIRLINE, 1.5)
    s.line([(80, 560), (900, 560)], AXIS, 1.5)
    s.segments([(x(k), 560, x(k), 570) for k in (0, 50, 100, 150, 200)], AXIS, 1.5)
    rules = (
        (basic_composition_epsilon, GREY, 3.0, "solid", 7.0, basic),
        (advanced_composition_epsilon, GREY, 3.0, "dash", 7.0, advanced),
        (zcdp_epsilon, VIOLET, 4.0, "solid", 8.0, zc),
    )
    for rule, color, width, dash, _, _ in rules:
        s.line([(x(k), to_y(rule(k, COST_RATIO, COST_DELTA))) for k in ks], color, width, dash=dash)  # type: ignore[arg-type]
    for _, color, _, _, radius, total in rules:
        s.circle(x(200), to_y(total), radius, color, PAPER, 2)
    s.label(80, 8, "total ε")
    for e in (0, 5, 10, 15, 20):
        s.label(0, to_y(e) - 15, f"{e}", 64, "r")
    s.label(420, 146, "basic rule", 300, "r", strong=True)
    s.label(620, 396, "advanced rule", 280, strong=True)
    s.label(620, 480, "zero-concentrated", 280, strong=True)
    for total in (basic, advanced, zc):
        s.label(918, round(to_y(total) - 14.6), f"{total:.1f}", 110, strong=True)
    for k in (50, 100, 150, 200):
        s.label(x(k) - 40, 574, f"{k}", 80, "c")
    s.label(500, 608, "number of releases *k*", 400, "r")
    return s


# ================================================================ small pictures
MINI_W, MINI_H = 344, 150


def _mini(aria: str) -> Scene:
    s = Scene(MINI_W, MINI_H, aria)
    s.line([(0, 141), (MINI_W, 141)], AXIS, 1.5)
    return s


def _mini_x(loss: float) -> float:
    return (loss + 1.75) * 86


def _mini_y(d: float) -> float:
    return 140 - d * 150


def _mini_bell(steps: int = 40) -> list[Point]:
    return [(_mini_x(v), _mini_y(normal_pdf(v, 0.125, 0.5))) for v in linspace(-1.75, 2.25, steps)]


def _bounded_loss() -> list[Point]:
    """A loss that never leaves [-eps, eps]: the picture of pure differential privacy."""
    curve = [(_mini_x(v), _mini_y(normal_pdf(v, 0.1, 0.3) * 0.6)) for v in linspace(-0.95, 0.95, 24)]
    return [(_mini_x(-0.95), 140.0), *curve, (_mini_x(0.95), 140.0)]


def recap_pure() -> Scene:
    s = _mini("A privacy loss distribution that lies entirely between two walls at −ε and +ε")
    s.filled_line(_bounded_loss(), VIOLET, 0.2, closed=True)
    s.segments([(64.5, 141, 64.5, 40), (236.5, 141, 236.5, 40)], INK, 3, round_cap=True)
    s.label(34, 4, "−ε", 60, "c", strong=True, math=True)
    s.label(206, 4, "+ε", 60, "c", strong=True, math=True)
    return s


def recap_approx() -> Scene:
    def x(loss: float) -> float:
        return (loss + 3) * MINI_W / 7.5

    def to_y(d: float) -> float:
        return 140 - 300 * d

    tail = linspace(1, 4.5, 30)
    s = _mini("A bell of privacy loss with a wall at ε. Part of the tail beyond the wall is filled: δ")
    s.filled_line([(x(v), to_y(_loss_pdf(v))) for v in linspace(-3, 4.5, 60)], VIOLET, 0.2)
    s.polygon([(x(1), 140), *[(x(v), to_y(_loss_pdf(v))) for v in tail], (MINI_W, 140)], VIOLET, 0.22)
    s.polygon(
        [(x(1), 140), *[(x(v), to_y(_loss_pdf(v) * (1 - math.exp(1 - v)))) for v in tail], (MINI_W, 140)],
        DEEP,
        0.85,
    )
    s.segments([(x(1), 141, x(1), 34)], INK, 3, round_cap=True)
    s.label(round(x(1) - 30), 0, "ε", 60, "c", strong=True, math=True)
    s.label(round(x(2.6)), 76, "δ", 60, strong=True, math=True)
    return s


def recap_concentrated() -> Scene:
    s = _mini("A filled privacy loss distribution next to a dashed Gaussian bell that is at least as wide")
    s.filled_line(_bounded_loss(), VIOLET, 0.2, closed=True)
    s.line(_mini_bell(), INK, dash="dash")
    s.label(236, 30, "*μ*, *τ*", 100, strong=True, math=True)
    return s


def recap_zcdp() -> Scene:
    s = _mini("A single bell of privacy loss, fixed by one number ρ")
    s.filled_line(_mini_bell(), VIOLET, 0.2)
    s.label(236, 30, "*ρ*", 100, strong=True, math=True)
    return s


def promise_outputs() -> Scene:
    """Two bells almost on top of each other: the outputs on D and on D'."""
    s = Scene(380, 150, "Two bell curves, blue for D and orange for D′, almost on top of each other")
    bell = _mini_bell()
    s.filled_line(bell, BLUE, 0.12)
    s.filled_line([(px + 30, py) for px, py in bell], ORANGE, 0.12)
    s.line([(0, 141), (380, 141)], AXIS, 1.5)
    return s


def cover_art() -> Scene:
    """Two wide bells along the bottom of the cover."""
    s = Scene(1920, 1080, "Two overlapping bell curves, one blue and one orange, a short distance apart")
    for centre, color in ((860.0, "#5B9BEA"), (1060.0, "#F0895A")):
        points = [(px, 1080 - 430 * math.exp(-((px - centre) ** 2) / (2 * 260**2))) for px in linspace(0, 1920, 48)]
        s.filled_line(points, color, 0.14, width=4)
    return s


# Plots that can be exported on their own, by name.
STANDALONE: dict[str, Callable[[], Scene]] = {
    "sensitivity": sensitivity,
    "pure-dp": pure_dp,
    "log-scale": log_scale,
    "gaussian": gaussian,
    "gaussian-log": gaussian_log,
    "approx-dp": approx_dp,
    "loss-distribution": loss_distribution,
    "many-pairs": many_pairs,
    "compose-pure": compose_pure,
    "compose-approx": compose_approx,
    "cdp": cdp,
    "zcdp": zcdp,
    "composition": composition,
    "cost": cost,
}
