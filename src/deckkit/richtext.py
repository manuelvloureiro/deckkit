"""A small inline markup for slide text, and its conversion to runs.

The markup keeps the text of the deck independent of the output format:

    *x*      italic, for mathematical variables
    **x**    strong
    ^{x}     superscript
    _{x}     subscript
    newline  line break

Every renderer consumes the parsed runs, so the same sentence becomes HTML in one output and
PowerPoint text runs in the other.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

NBSP = " "


@dataclass(frozen=True)
class Run:
    """A stretch of text with one formatting. `shift` is 1 for superscript and -1 for subscript."""

    text: str
    italic: bool = False
    bold: bool = False
    shift: int = 0


def parse(markup: str) -> list[Run]:
    """Split one line of markup into runs."""
    runs: list[Run] = []
    buffer: list[str] = []
    italic = bold = False
    shift = 0

    def flush() -> None:
        if buffer:
            runs.append(Run("".join(buffer), italic, bold, shift))
            buffer.clear()

    i = 0
    while i < len(markup):
        two = markup[i : i + 2]
        if two == "**":
            flush()
            bold = not bold
            i += 2
        elif markup[i] == "*":
            flush()
            italic = not italic
            i += 1
        elif two in ("^{", "_{"):
            flush()
            shift = 1 if two == "^{" else -1
            i += 2
        elif markup[i] == "}" and shift:
            flush()
            shift = 0
            i += 1
        else:
            buffer.append(markup[i])
            i += 1
    flush()
    return runs


def parse_lines(markup: str) -> list[list[Run]]:
    """Runs of each line of a text with explicit line breaks."""
    return [parse(line) for line in markup.split("\n")]


def plain(markup: str) -> str:
    """The text without any formatting, line breaks as spaces."""
    return " ".join("".join(run.text for run in line) for line in parse_lines(markup))


def upper(runs: list[Run]) -> list[Run]:
    return [replace(run, text=run.text.upper()) for run in runs]


def escape(text: str) -> str:
    """Escape text for HTML or SVG. A non-breaking space is written as a numeric entity."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(NBSP, "&#160;")


def _run_html(run: Run) -> str:
    out = escape(run.text)
    if run.italic:
        out = f"<i>{out}</i>"
    if run.bold:
        out = f'<b class="strong">{out}</b>'
    return out


def to_html(markup: str) -> str:
    """Inline HTML for flowing text: italics, strong and line breaks. Shifts are not allowed here."""
    lines: list[str] = []
    for line in parse_lines(markup):
        if any(run.shift for run in line):
            raise ValueError(f"superscripts and subscripts belong in an equation: {markup!r}")
        lines.append("".join(_run_html(run) for run in line))
    return "<br>".join(lines)


def equation_html(markup: str) -> str:
    """The pieces of an equation row.

    The Slides page format has no superscript element, so an equation is a flex row of paragraphs
    in which the raised and lowered pieces carry their own class.
    """
    pieces: list[tuple[int, list[Run]]] = []
    for run in parse(markup):
        if pieces and pieces[-1][0] == run.shift:
            pieces[-1][1].append(run)
        else:
            pieces.append((run.shift, [run]))
    out: list[str] = []
    for index, (shift, runs) in enumerate(pieces):
        body = "".join(_run_html(run) for run in runs)
        if index and body.startswith(" "):
            body = "&#160;" + body[1:]
        cls = {1: ' class="sup"', -1: ' class="sub"', 0: ""}[shift]
        out.append(f"<p{cls}>{body}</p>")
    return "".join(out)
