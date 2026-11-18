import io
import shutil
from typing import Any

import pytest
from PIL import Image
from pptx.enum.shapes import MSO_SHAPE_TYPE

from dpdeck.content import build_deck
from dpdeck.fonts import Measurer
from dpdeck.model import Deck, PlotSlide
from dpdeck.render_pptx import PptxRenderer, slide_titles
from dpdeck.scene import Scene
from dpdeck.theme import BLUE, PLOT_H, PLOT_W, Fonts

needs_rsvg = pytest.mark.skipif(shutil.which("rsvg-convert") is None, reason="rsvg-convert is not installed")


def render(deck: Deck, plots: str = "auto") -> Any:
    renderer = PptxRenderer(Measurer(Fonts()), plots=plots, scale=1.0)  # type: ignore[arg-type]
    return renderer.build(deck), renderer


def plot_groups(presentation: Any, deck: Deck) -> list[Any]:
    """The plot group of every slide that puts its plot at the left edge."""
    groups = []
    for page, slide in zip(presentation.slides, deck.slides, strict=True):
        if isinstance(slide, PlotSlide) and slide.flush:
            groups.append(next(s for s in page.shapes if s.name == f"plot: {slide.id}"))
    return groups


def box(shape: Any) -> tuple[int, int, int, int]:
    return shape.left, shape.top, shape.width, shape.height


def test_every_slide_has_its_title() -> None:
    deck = build_deck()
    presentation, renderer = render(deck)
    assert [page.shapes.title.text_frame.text for page in presentation.slides] == slide_titles(deck)
    assert renderer.images == 0  # nothing in this deck needs an image


def test_plots_share_one_frame() -> None:
    """Native plots have the same position and size on every slide, whatever they draw."""
    deck = build_deck()
    presentation, _ = render(deck)
    groups = plot_groups(presentation, deck)
    assert len(groups) == 13
    assert len({box(group) for group in groups}) == 1
    assert groups[0].width == PLOT_W * 6350 and groups[0].height == PLOT_H * 6350


@needs_rsvg
def test_exported_images_share_the_frame_and_are_transparent() -> None:
    deck = build_deck()
    presentation, renderer = render(deck, "image")
    assert renderer.images > 0
    pictures = [
        next(s for s in group.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE)
        for group in plot_groups(presentation, deck)
    ]
    assert len({box(picture) for picture in pictures}) == 1
    image = Image.open(io.BytesIO(pictures[0].image.blob))
    assert image.size == (PLOT_W, PLOT_H)
    assert image.mode == "RGBA"
    assert image.getchannel("A").getpixel((2, 2)) == 0


def one_plot(raw: bool) -> Deck:
    scene = Scene(PLOT_W, PLOT_H, "a test plot")
    scene.line([(64, 500), (500, 100), (1000, 500)], BLUE)
    if raw:
        scene.raw('<circle cx="500" cy="300" r="80" fill="url(#none)" filter="blur(4px)"/>')
    scene.line([(64, 548), (1024, 548)], BLUE)
    return Deck("test", (PlotSlide("p", "eyebrow", "title", scene, ()),))


@needs_rsvg
def test_only_what_powerpoint_cannot_draw_becomes_an_image() -> None:
    deck = one_plot(raw=True)
    presentation, renderer = render(deck)
    group = plot_groups(presentation, deck)[0]
    kinds = [shape.shape_type for shape in group.shapes]
    assert renderer.images == 1
    assert kinds.count(MSO_SHAPE_TYPE.PICTURE) == 1
    # The image sits between the two native shapes, in the order the scene paints them.
    assert kinds.index(MSO_SHAPE_TYPE.FREEFORM) < kinds.index(MSO_SHAPE_TYPE.PICTURE) < kinds.index(MSO_SHAPE_TYPE.LINE)
    picture = next(s for s in group.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE)
    assert box(picture) == box(group)


def test_native_mode_refuses_images() -> None:
    with pytest.raises(ValueError, match="no PowerPoint equivalent"):
        render(one_plot(raw=True), "native")
    render(one_plot(raw=False), "native")
