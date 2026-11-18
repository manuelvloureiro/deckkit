"""Colours, type and page geometry shared by every renderer.

Lengths are in the pixels of a 1920 x 1080 slide. The HTML output takes the same values from
`assets/deck.css`; when a size or colour changes, change it in both places.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SLIDE_W, SLIDE_H = 1920, 1080
MARGIN = 128
GAP = 40

# The plot frame. Every plot is drawn on this canvas and placed at the same position, so a curve
# that keeps its coordinates stays on the same pixels from one slide to the next.
PLOT_W, PLOT_H = 1040, 640

INK = "#14213D"
BODY = "#465063"
MUTED = "#5F677A"
PAPER = "#F6F4EE"
PAPER_2 = "#ECE8DC"
CARD = "#FFFDF8"
HAIRLINE = "#D9D4C5"
ACCENT = "#5443C7"

BLUE = "#2A78D6"  # the release on D
ORANGE = "#EB6834"  # the release on D'
VIOLET = "#6250D6"  # privacy loss
DEEP = "#4A3AB8"  # delta: the uncovered part
AXIS = "#8A8F98"
GREY = "#7B8494"

Family = Literal["sans", "serif"]


@dataclass(frozen=True)
class TextStyle:
    """How one kind of text is set."""

    family: Family
    size: float
    line_height: float
    color: str
    bold: bool = False
    spacing: float = 0.0
    upper: bool = False

    @property
    def line(self) -> float:
        """Height of one line in pixels."""
        return self.size * self.line_height


STYLES: dict[str, TextStyle] = {
    "eyebrow": TextStyle("sans", 24, 1.2, ACCENT, bold=True, spacing=3, upper=True),
    "h1": TextStyle("serif", 112, 1.05, INK, bold=True, spacing=-2),
    "h2": TextStyle("serif", 64, 1.1, INK, bold=True, spacing=-0.5),
    "h2-xl": TextStyle("serif", 112, 1.05, INK, bold=True, spacing=-2),
    "h3": TextStyle("serif", 32, 1.25, INK, bold=True),
    "say": TextStyle("sans", 32, 1.4, BODY),
    "lead": TextStyle("serif", 44, 1.3, INK),
    "note": TextStyle("sans", 24, 1.35, MUTED),
    "lbl": TextStyle("sans", 24, 1.2, BODY),
    "key": TextStyle("sans", 24, 1.2, INK),
    "eq": TextStyle("serif", 44, 1.3, INK),
    "eq-s": TextStyle("serif", 32, 1.3, INK),
    "eq-l": TextStyle("serif", 64, 1.2, INK),
    "tag": TextStyle("sans", 24, 1.2, MUTED, bold=True),
    "num": TextStyle("serif", 44, 1.3, INK, bold=True),
    "mid": TextStyle("serif", 64, 1.1, INK, bold=True),
    "step": TextStyle("serif", 64, 1.1, ACCENT, bold=True),
    "table": TextStyle("sans", 28, 1.4, INK),
}

# Slide backgrounds and the text colours that go with the dark ones.
BACKGROUNDS = {"paper": PAPER, "paper-2": PAPER_2, "cover": INK, "accent": DEEP}
COVER_TEXT = {"eyebrow": "#B4A9F5", "h1": PAPER, "lead": "#C5CCDA"}
ACCENT_TEXT = {"eyebrow": "#D6D0FA", "h2-xl": CARD, "lead": "#EDEBFB"}


@dataclass(frozen=True)
class Fonts:
    """The two type families of the deck. Replace them when the presenting machine lacks these."""

    sans: str = "IBM Plex Sans"
    serif: str = "Source Serif 4"

    def name(self, family: Family) -> str:
        return self.sans if family == "sans" else self.serif
