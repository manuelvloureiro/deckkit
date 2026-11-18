"""Finding the deck's fonts and measuring text with them.

PowerPoint has no layout engine to ask, so the PowerPoint output measures every paragraph itself
to know how many lines it takes. The measurements use the real font files when fontconfig can
find them, and average character widths otherwise.

`download` fetches the two families into `fonts/`. Everything that renders text outside
PowerPoint (measuring, exporting images, the LibreOffice preview) is pointed at that folder, so
the fonts do not have to be installed system-wide to build the deck. They do have to be installed
on the machine that presents the PowerPoint file.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont, features

from dpdeck.richtext import NBSP, Run
from dpdeck.theme import Family, Fonts, TextStyle

PLEX = "https://github.com/IBM/plex/raw/master/packages/plex-sans/fonts/complete/ttf/"
SERIF = "https://github.com/adobe-fonts/source-serif/raw/release/TTF/"
DOWNLOADS = {
    "IBMPlexSans-Regular.ttf": PLEX + "IBMPlexSans-Regular.ttf",
    "IBMPlexSans-Italic.ttf": PLEX + "IBMPlexSans-Italic.ttf",
    "IBMPlexSans-Bold.ttf": PLEX + "IBMPlexSans-Bold.ttf",
    "IBMPlexSans-BoldItalic.ttf": PLEX + "IBMPlexSans-BoldItalic.ttf",
    "IBMPlexSans-LICENSE.txt": "https://github.com/IBM/plex/raw/master/LICENSE.txt",
    "SourceSerif4-Regular.ttf": SERIF + "SourceSerif4-Regular.ttf",
    "SourceSerif4-It.ttf": SERIF + "SourceSerif4-It.ttf",
    "SourceSerif4-Bold.ttf": SERIF + "SourceSerif4-Bold.ttf",
    "SourceSerif4-BoldIt.ttf": SERIF + "SourceSerif4-BoldIt.ttf",
    "SourceSerif4-LICENSE.md": "https://github.com/adobe-fonts/source-serif/raw/release/LICENSE.md",
}

# Raised and lowered text is set smaller, as PowerPoint and the HTML deck both do.
SHIFT_SCALE = 0.66
# Average advance of a character in em, used only when no font file is found.
FALLBACK_ADVANCE = {("sans", False): 0.53, ("sans", True): 0.56, ("serif", False): 0.47, ("serif", True): 0.5}
# Ascent and descent in em, used only when no font file is found.
FALLBACK_METRICS = {"sans": (1.025, 0.275), "serif": (1.036, 0.335)}


def download(dest: Path) -> list[Path]:
    """Fetch the font files that are not in `dest` yet. Both families are under the SIL Open Font License."""
    dest.mkdir(parents=True, exist_ok=True)
    fetched: list[Path] = []
    for name, url in DOWNLOADS.items():
        target = dest / name
        if target.exists():
            continue
        request = urllib.request.Request(url, headers={"User-Agent": "dpdeck"})
        with urllib.request.urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())
        fetched.append(target)
    return fetched


def fontconfig_env(fonts_dir: Path, work_dir: Path) -> dict[str, str]:
    """An environment in which fontconfig also sees the fonts in `fonts_dir`.

    The system configuration stays in effect; the folder is added to it.
    """
    env = dict(os.environ)
    if not fonts_dir.is_dir() or not any(fonts_dir.glob("*.ttf")):
        return env
    work_dir.mkdir(parents=True, exist_ok=True)
    conf = work_dir / "fonts.conf"
    conf.write_text(
        '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
        '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
        f"  <dir>{fonts_dir.resolve()}</dir>\n"
        f"  <cachedir>{(work_dir / 'fontcache').resolve()}</cachedir>\n"
        "</fontconfig>\n",
        "utf-8",
    )
    env["FONTCONFIG_FILE"] = str(conf.resolve())
    return env


class Measurer:
    """Widths, line counts and baselines of text set in the deck's fonts."""

    def __init__(self, fonts: Fonts, env: dict[str, str] | None = None) -> None:
        self.fonts = fonts
        self.env = env if env is not None else dict(os.environ)
        self._files: dict[tuple[Family, bool, bool], str | None] = {}
        self._warned: set[str] = set()

    # ------------------------------------------------------------------ font files
    def _file(self, family: Family, bold: bool, italic: bool) -> str | None:
        key = (family, bold, italic)
        if key not in self._files:
            self._files[key] = self._match(self.fonts.name(family), bold, italic)
        return self._files[key]

    def _match(self, name: str, bold: bool, italic: bool) -> str | None:
        if not shutil.which("fc-match"):
            self._warn("fc-match", "fontconfig not found: text is measured with average character widths")
            return None
        pattern = f"{name}:weight={'bold' if bold else 'regular'}:slant={'italic' if italic else 'roman'}"
        try:
            out = subprocess.run(
                ["fc-match", "-f", "%{file}\n%{family}", pattern],
                capture_output=True,
                text=True,
                check=True,
                env=self.env,
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            return None
        file, _, found = out.partition("\n")
        if name.lower() not in [f.strip().lower() for f in found.split(",")]:
            self._warn(
                name,
                f"font '{name}' not found: measuring with '{found.split(',')[0]}' instead. "
                "Run `dpdeck fonts` to download the deck's fonts.",
            )
        return file or None

    def _warn(self, key: str, message: str) -> None:
        if key not in self._warned:
            self._warned.add(key)
            print(f"warning: {message}", file=sys.stderr)

    # ------------------------------------------------------------------ measures
    def run_width(self, run: Run, style: TextStyle) -> float:
        size = style.size * (SHIFT_SCALE if run.shift else 1.0)
        bold = style.bold or run.bold
        text = run.text.upper() if style.upper else run.text
        text = text.replace(NBSP, " ")
        file = self._file(style.family, bold, run.italic)
        if file:
            width = _font(file, 200).getlength(text) * size / 200
        else:
            width = FALLBACK_ADVANCE[(style.family, bold)] * size * len(text)
        return width + style.spacing * len(text)

    def width(self, runs: list[Run], style: TextStyle) -> float:
        """Width in pixels of runs set on one line."""
        return sum(self.run_width(run, style) for run in runs)

    def line_count(self, runs: list[Run], style: TextStyle, max_width: float) -> int:
        """Number of lines the runs take when wrapped at word boundaries into `max_width`."""
        space = self.run_width(Run(" "), style)
        lines, used = 1, 0.0
        for word in _words(runs):
            width = self.width(word, style)
            if used and used + space + width > max_width:
                lines += 1
                used = width
            else:
                used += (space if used else 0.0) + width
        return lines

    def metrics(self, style: TextStyle) -> tuple[float, float]:
        """Ascent and descent in pixels at the style's size."""
        file = self._file(style.family, style.bold, False)
        if file:
            ascent, descent = _font(file, 200).getmetrics()
            return ascent * style.size / 200, descent * style.size / 200
        ascent, descent = FALLBACK_METRICS[style.family]
        return ascent * style.size, descent * style.size

    def baseline(self, style: TextStyle) -> float:
        """Distance from the top of a line box to its baseline, as a browser places it."""
        ascent, descent = self.metrics(style)
        return (style.line - (ascent + descent)) / 2 + ascent


@lru_cache(maxsize=32)
def _font(file: str, size: int) -> ImageFont.FreeTypeFont:
    # With Raqm the text is shaped as a renderer shapes it, kerning and ligatures included.
    engine = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
    return ImageFont.truetype(file, size, layout_engine=engine)


def _words(runs: list[Run]) -> list[list[Run]]:
    """Split runs at spaces. A word can span several runs, as in an italic letter followed by a comma."""
    words: list[list[Run]] = [[]]
    for run in runs:
        parts = run.text.split(" ")
        for index, part in enumerate(parts):
            if index:
                words.append([])
            if part:
                words[-1].append(Run(part, run.italic, run.bold, run.shift))
    return [word for word in words if word]
