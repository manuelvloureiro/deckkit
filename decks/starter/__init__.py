"""A small deck to copy when starting a new one.

It uses the common kinds of slide and has two plots drawn on the same frame, so the first curve
stays in place when the second one appears. Copy the folder, rename it, and change the text.
"""

from __future__ import annotations

import math

from deckkit.model import Card, CardsSlide, Cover, Deck, Def, Eq, Note, PlotSlide, Say, Section, Statement, TableSlide
from deckkit.scene import Mark, Point, Scene
from deckkit.theme import AXIS, BLUE, ORANGE, PLOT_H, PLOT_W

# What each colour means, on every slide.
FIRST, SECOND = Mark(BLUE), Mark(ORANGE)

# The frame shared by the plots: the horizontal axis runs from LEFT to RIGHT at height BASE.
LEFT, RIGHT, BASE = 64.0, 1024.0, 548.0
LOW, HIGH = -4.0, 6.0  # the values shown on the axis


def bell(value: float, mean: float) -> float:
    """Density of a normal distribution with standard deviation 1."""
    return math.exp(-((value - mean) ** 2) / 2) / math.sqrt(2 * math.pi)


def to_x(value: float) -> float:
    return LEFT + (value - LOW) * (RIGHT - LEFT) / (HIGH - LOW)


def to_y(density: float) -> float:
    return BASE - 1100 * density


def curve(mean: float) -> list[Point]:
    values = [LOW + index * (HIGH - LOW) / 200 for index in range(201)]
    return [(to_x(value), to_y(bell(value, mean))) for value in values]


def measurements(second: bool) -> Scene:
    """One bell curve, or two. The first has the same coordinates in both, so it does not move."""
    aria = "A bell curve centred on 0" + (" and a second one centred on 2" if second else "")
    scene = Scene(PLOT_W, PLOT_H, aria)
    scene.line([(LEFT, BASE), (RIGHT, BASE)], AXIS, 1.5)
    if second:
        scene.filled_line(curve(2), ORANGE, 0.14)
    scene.filled_line(curve(0), BLUE, 0.14)
    scene.label(LEFT, 0, "how likely each value is")
    scene.key(LEFT, 52, FIRST, "first measurement")
    if second:
        scene.key(LEFT, 86, SECOND, "second measurement")
    for value in (-2, 0, 2, 4):
        scene.label(to_x(value) - 40, 560, str(value).replace("-", "−"), 80, "c")
    scene.label(RIGHT - 240, 596, "measured value", 240, "r")
    return scene


def cover_art() -> Scene:
    """Two wide bells along the bottom of the cover."""
    scene = Scene(1920, 1080, "Two overlapping bell curves along the bottom of the slide")
    for centre, color in ((860.0, "#5B9BEA"), (1060.0, "#F0895A")):
        points = [(x * 40.0, 1080 - 430 * math.exp(-((x * 40.0 - centre) ** 2) / (2 * 260**2))) for x in range(49)]
        scene.filled_line(points, color, 0.14, width=4)
    return scene


def build_deck() -> Deck:
    slides = (
        Cover(
            "cover",
            "Starter deck",
            "A deck written in Python",
            "One description of the slides, rendered as PowerPoint or HTML",
            cover_art(),
        ),
        Statement(
            "idea",
            "The idea",
            "Compute the pictures",
            "Every curve comes from its formula, so a number that changes moves the plot and the text together.",
        ),
        PlotSlide(
            "one-curve",
            "Plots",
            "A plot and its explanation",
            measurements(second=False),
            (
                Say("A plot slide has the plot on the left and a column of text on the right."),
                Def(
                    "The curve",
                    (
                        Eq("*p*(*x*) = *e*^{−*x*²/2} / √(2π)", "s"),
                        Note("Text takes *italics* and **strong**. An equation also takes raised and lowered pieces."),
                    ),
                ),
            ),
        ),
        PlotSlide(
            "two-curves",
            "Plots",
            "The next slide adds to the picture",
            measurements(second=True),
            (
                Say("Both plots use the same frame, so the blue curve does not move when the orange one appears."),
                Note("In PowerPoint the plot is a group of ordinary shapes: click a curve to edit it."),
            ),
        ),
        CardsSlide(
            "slides",
            "Slides",
            "Other kinds of slide",
            (
                Card("Cards", "A row of short points, numbered or not, with a closing sentence below.", step="1"),
                Card("Tables", "A table across the slide, with an optional card under it.", step="2"),
                Card("Diagrams", "Boxes and arrows, and a definition taken apart term by term.", step="3"),
            ),
            "Each kind of slide is a class in deckkit.model.",
        ),
        TableSlide(
            "outputs",
            "Outputs",
            "One deck, several outputs",
            ("Command", "Output", "Plots are"),
            (30, 36, 34),
            (
                ("make", "PowerPoint file", "native shapes"),
                ("make pptx-images", "PowerPoint file", "transparent images"),
                ("make html", "one HTML file", "inline SVG"),
                ("make plots", "SVG and PNG files", "one file per plot"),
            ),
            Def(None, (Note("Add DECK=starter to a command to build this deck."),)),
        ),
    )
    sections = (
        Section("intro", "cover", "What the deck is for."),
        Section("plots", "one-curve", "Two plots on one frame."),
        Section("slides", "slides", "The other kinds of slide and the outputs."),
    )
    return Deck("Starter deck", slides, sections)
