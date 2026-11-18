"""Command line: build the deck, export the plots, fetch the fonts, preview the PowerPoint file."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from dpdeck import fonts as fontlib
from dpdeck import plots
from dpdeck.content import build_deck
from dpdeck.fonts import Measurer
from dpdeck.render_html import write_artifact, write_standalone
from dpdeck.render_pptx import PptxRenderer
from dpdeck.render_svg import raster, scene_svg
from dpdeck.theme import Fonts

NAME = "dp-deck"
FORMATS = ("pptx", "html", "artifact")


def _measurer(args: argparse.Namespace, out: Path) -> tuple[Measurer, dict[str, str]]:
    env = fontlib.fontconfig_env(args.fonts_dir, out / ".cache")
    chosen = Fonts(sans=args.font_sans or Fonts.sans, serif=args.font_serif or Fonts.serif)
    return Measurer(chosen, env), env


def build(args: argparse.Namespace) -> int:
    deck = build_deck()
    out: Path = args.out
    formats = FORMATS if args.format == "all" else (args.format,)
    for fmt in formats:
        if fmt == "pptx":
            measurer, env = _measurer(args, out)
            renderer = PptxRenderer(measurer, plots=args.plots, scale=args.scale, env=env)
            path = renderer.write(deck, out / f"{NAME}.pptx")
            exported = f", {renderer.images} exported as images" if renderer.images else ""
            print(f"{path}  ({len(deck.slides)} slides{exported})")
        elif fmt == "html":
            print(write_standalone(deck, out / f"{NAME}.html"))
        else:
            print(write_artifact(deck, out / "artifact"))
    return 0


def export_plots(args: argparse.Namespace) -> int:
    out: Path = args.out
    measurer, env = _measurer(args, out)
    out.mkdir(parents=True, exist_ok=True)
    for name, make in plots.STANDALONE.items():
        svg = scene_svg(make(), measurer)
        if args.format == "svg":
            (out / f"{name}.svg").write_text(svg, "utf-8")
        else:
            (out / f"{name}.png").write_bytes(raster(svg, args.scale, env))
    print(f"{out}  ({len(plots.STANDALONE)} plots, {args.format}, transparent background)")
    return 0


def fetch_fonts(args: argparse.Namespace) -> int:
    fetched = fontlib.download(args.fonts_dir)
    print(f"{args.fonts_dir}  ({len(fetched)} files downloaded)")
    return 0


def preview(args: argparse.Namespace) -> int:
    """Render the PowerPoint file to one PNG per slide with LibreOffice."""
    source: Path = args.file
    out: Path = args.out
    if not source.exists():
        print(f"{source} does not exist: run `dpdeck build` first", file=sys.stderr)
        return 1
    for tool in ("soffice", "pdftoppm"):
        if not shutil.which(tool):
            print(f"preview needs {tool} on the PATH", file=sys.stderr)
            return 1
    cache = source.parent / ".cache"
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


def _add_font_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--fonts-dir", type=Path, default=Path("fonts"), help="folder with the deck's font files")
    parser.add_argument("--font-sans", help=f"sans family to use instead of {Fonts.sans}")
    parser.add_argument("--font-serif", help=f"serif family to use instead of {Fonts.serif}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="dpdeck", description=__doc__)
    commands = root.add_subparsers(dest="command")

    b = commands.add_parser("build", help="build the deck (the default command)")
    b.add_argument("-f", "--format", choices=(*FORMATS, "all"), default="pptx")
    b.add_argument("-o", "--out", type=Path, default=Path("build"))
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

    p = commands.add_parser("plots", help="export every plot on its own, on a transparent background")
    p.add_argument("-f", "--format", choices=("svg", "png"), default="svg")
    p.add_argument("-o", "--out", type=Path, default=Path("build/plots"))
    p.add_argument("--scale", type=float, default=3.0)
    _add_font_options(p)
    p.set_defaults(run=export_plots)

    f = commands.add_parser("fonts", help="download the deck's fonts into fonts/")
    f.add_argument("--fonts-dir", type=Path, default=Path("fonts"))
    f.set_defaults(run=fetch_fonts)

    v = commands.add_parser("preview", help="render the PowerPoint file to PNG with LibreOffice")
    v.add_argument("file", type=Path, nargs="?", default=Path("build") / f"{NAME}.pptx")
    v.add_argument("-o", "--out", type=Path, default=Path("build/preview"))
    v.add_argument("--dpi", type=int, default=144, help="144 gives 1920 px wide images")
    v.add_argument("--sheets", action="store_true", help="also write contact sheets of four slides")
    v.add_argument("--fonts-dir", type=Path, default=Path("fonts"))
    v.set_defaults(run=preview)
    return root


def main(argv: list[str] | None = None) -> int:
    args_in = list(sys.argv[1:] if argv is None else argv)
    if not args_in or args_in[0].startswith("-") and args_in[0] not in ("-h", "--help"):
        args_in.insert(0, "build")
    args = parser().parse_args(args_in)
    return int(args.run(args))


if __name__ == "__main__":
    raise SystemExit(main())
