import json
import re
from pathlib import Path

from dpdeck.content import build_deck
from dpdeck.model import CardsSlide, DiagramSlide, PlotSlide
from dpdeck.render_html import slide_html, write_artifact, write_standalone
from dpdeck.scene import Scene


def scenes() -> list[Scene]:
    found: list[Scene] = []
    for slide in build_deck().slides:
        if isinstance(slide, PlotSlide):
            found.append(slide.scene)
        elif isinstance(slide, CardsSlide):
            found += [card.scene for card in slide.cards if card.scene]
        elif isinstance(slide, DiagramSlide):
            found += [node.scene for node in slide.nodes if node.scene]
    return found


def test_artifact_folder(tmp_path: Path) -> None:
    deck = build_deck()
    write_artifact(deck, tmp_path)
    index = json.loads((tmp_path / "project" / "deck.json").read_text("utf-8"))
    assert index["order"] == [slide.id for slide in deck.slides]
    assert len(index["order"]) == 22
    for slide_id in index["order"]:
        html = (tmp_path / "project" / "slides" / f"{slide_id}.html").read_text("utf-8")
        assert html.startswith(f'<section id="{slide_id}"')
        # What the Slides page format does not accept.
        assert not re.search(r"<text|<sup|<sub|z-index", html)
    assert all(section["start"] in index["order"] for section in index["sections"].values())


def test_at_most_24_pinned_labels_per_plot() -> None:
    assert max(len(scene.labels) for scene in scenes()) <= 24


def test_standalone_file_draws_arrows_itself(tmp_path: Path) -> None:
    html = write_standalone(build_deck(), tmp_path / "deck.html").read_text("utf-8")
    assert html.count("<section ") == 22
    assert "x-connector" not in html and "marker-end" in html
    assert "<x-connector" in slide_html(build_deck().slides[3])
