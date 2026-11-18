"""Command line: build a deck, export its plots, fetch the fonts, preview the PowerPoint file."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

from deckkit import fonts as fontlib
from deckkit.fonts import Measurer
from deckkit.loader import DeckError, LoadedDeck, available, load
from deckkit.render_html import write_artifact, write_standalone
from deckkit.render_pptx import PptxRenderer
from deckkit.render_svg import raster, scene_svg
from deckkit.theme import Fonts

FORMATS = ("pptx", "html", "artifact")


def _measurer(args: argparse.Namespace) -> tuple[Measurer, dict[str, str]]:
    env = fontlib.fontconfig_env(args.fonts_dir, args.out / ".cache")
    chosen = Fonts(sans=args.font_sans or Fonts.sans, serif=args.font_serif or Fonts.serif)
    return Measurer(chosen, env), env


def _load(args: argparse.Namespace) -> tuple[LoadedDeck, Path]:
    """The deck named on the command line and its output folder, `<out>/<deck>/`."""
    loaded = load(args.deck, args.decks_dir)
    return loaded, args.out / loaded.name


def build(args: argparse.Namespace) -> int:
    loaded, out = _load(args)
    deck = loaded.deck
    formats = FORMATS if args.format == "all" else (args.format,)
    for fmt in formats:
        if fmt == "pptx":
            measurer, env = _measurer(args)
            renderer = PptxRenderer(measurer, plots=args.plots, scale=args.scale, env=env)
            path = renderer.write(deck, out / f"{loaded.name}.pptx")
            exported = f", {renderer.images} exported as images" if renderer.images else ""
            print(f"{path}  ({len(deck.slides)} slides{exported})")
        elif fmt == "html":
            print(write_standalone(deck, out / f"{loaded.name}.html"))
        else:
            print(write_artifact(deck, out / "artifact"))
    return 0


def export_plots(args: argparse.Namespace) -> int:
    loaded, deck_out = _load(args)
    out = deck_out / "plots"
    plots = loaded.deck.plots
    measurer, env = _measurer(args)
    out.mkdir(parents=True, exist_ok=True)
    for name, scene in plots.items():
        svg = scene_svg(scene, measurer)
        if args.format == "svg":
            (out / f"{name}.svg").write_text(svg, "utf-8")
        else:
            (out / f"{name}.png").write_bytes(raster(svg, args.scale, env))
    print(f"{out}  ({len(plots)} plots, {args.format}, transparent background)")
    return 0


def list_decks(args: argparse.Namespace) -> int:
    for name in available(args.decks_dir):
        deck = load(name, args.decks_dir).deck
        print(f"{name:<24} {len(deck.slides):>3} slides  {deck.title}")
    return 0


def fetch_fonts(args: argparse.Namespace) -> int:
    fetched = fontlib.download(args.fonts_dir)
    print(f"{args.fonts_dir}  ({len(fetched)} files downloaded)")
    return 0


def preview(args: argparse.Namespace) -> int:
    """Render the PowerPoint file to one PNG per slide with LibreOffice."""
    loaded, deck_out = _load(args)
    source = deck_out / f"{loaded.name}.pptx"
    out = deck_out / "preview"
    if not source.exists():
        print(f"{source} does not exist: run `deckkit build {loaded.name}` first", file=sys.stderr)
        return 1
    for tool in ("soffice", "pdftoppm"):
        if not shutil.which(tool):
            print(f"preview needs {tool} on the PATH", file=sys.stderr)
            return 1
    cache = args.out / ".cache"
    env = fontlib.fontconfig_env(args.fonts_dir, cache)
    out.mkdir(parents=True, exist_ok=True)
    profile = (cache / "libreoffice").resolve()
    subprocess.run(
        [
            "soffice",
            f"-env:UserInstallation=file://{profile}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out),
            str(source),
        ],
        check=True,
        env=env,
        capture_output=True,
    )
    pdf = out / f"{source.stem}.pdf"
    for old in out.glob("slide-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", str(args.dpi), str(pdf), str(out / "slide")], check=True)
    slides = sorted(out.glob("slide-*.png"))
    if args.sheets:
        _contact_sheets(slides, out)
    print(f"{out}  ({len(slides)} slides)")
    return 0


def _contact_sheets(slides: list[Path], out: Path) -> None:
    """Four slides to a 1920 x 1080 sheet, to look over the whole deck quickly."""
    for old in out.glob("sheet-*.png"):
        old.unlink()
    for start in range(0, len(slides), 4):
        sheet = Image.new("RGB", (1920, 1080), "white")
        for index, path in enumerate(slides[start : start + 4]):
            thumb = Image.open(path).convert("RGB").resize((956, 538))
            sheet.paste(thumb, ((index % 2) * 964, (index // 2) * 542))
        sheet.save(out / f"sheet-{start // 4 + 1}.png")


def _deck_command(commands: Any, name: str, text: str) -> argparse.ArgumentParser:
    """A command that works on one deck and writes into `<out>/<deck>/`."""
    command: argparse.ArgumentParser = commands.add_parser(name, help=text)
    command.add_argument("deck", help="name of a deck in the decks folder, or a path to one")
    command.add_argument("--decks-dir", type=Path, default=Path("decks"), help="folder that holds the decks")
    command.add_argument("-o", "--out", type=Path, default=Path("build"), help="output folder; a deck gets a subfolder")
    command.add_argument("--fonts-dir", type=Path, default=Path("fonts"), help="folder with the font files")
    return command


def _add_font_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--font-sans", help=f"sans family to use instead of {Fonts.sans}")
    parser.add_argument("--font-serif", help=f"serif family to use instead of {Fonts.serif}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="deckkit", description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    b = _deck_command(commands, "build", "build a deck, as PowerPoint unless told otherwise")
    b.add_argument("-f", "--format", choices=(*FORMATS, "all"), default="pptx")
    b.add_argument(
        "--plots",
        choices=("auto", "native", "image"),
        default="auto",
        help="PowerPoint only. auto: native shapes, images for what PowerPoint cannot draw. "
        "native: fail instead of exporting an image. image: export the shapes of every plot as images",
    )
    b.add_argument("--scale", type=float, default=3.0, help="resolution of exported images, as a multiple of 1920 px")
    _add_font_options(b)
    b.set_defaults(run=build)

    p = _deck_command(commands, "plots", "export every plot of a deck on its own, on a transparent background")
    p.add_argument("-f", "--format", choices=("svg", "png"), default="svg")
    p.add_argument("--scale", type=float, default=3.0)
    _add_font_options(p)
    p.set_defaults(run=export_plots)

    v = _deck_command(commands, "preview", "render a deck's PowerPoint file to PNG with LibreOffice")
    v.add_argument("--dpi", type=int, default=144, help="144 gives 1920 px wide images")
    v.add_argument("--sheets", action="store_true", help="also write contact sheets of four slides")
    v.set_defaults(run=preview)

    ls = commands.add_parser("list", help="list the decks")
    ls.add_argument("--decks-dir", type=Path, default=Path("decks"))
    ls.set_defaults(run=list_decks)

    f = commands.add_parser("fonts", help="download the fonts into fonts/")
    f.add_argument("--fonts-dir", type=Path, default=Path("fonts"))
    f.set_defaults(run=fetch_fonts)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return int(args.run(args))
    except DeckError as error:
        print(f"deckkit: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
