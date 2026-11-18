import json
import re
from pathlib import Path

from deckkit.model import CardsSlide, Cover, Deck, DiagramSlide, PlotSlide
from deckkit.render_html import slide_html, write_artifact, write_standalone
from deckkit.scene import Scene


def scenes(deck: Deck) -> list[Scene]:
    found: list[Scene] = []
    for slide in deck.slides:
        if isinstance(slide, PlotSlide):
            found.append(slide.scene)
        elif isinstance(slide, Cover) and slide.art:
            found.append(slide.art)
        elif isinstance(slide, CardsSlide):
            found += [card.scene for card in slide.cards if card.scene]
        elif isinstance(slide, DiagramSlide):
            found += [node.scene for node in slide.nodes if node.scene]
    return found


def test_artifact_folder(deck: Deck, tmp_path: Path) -> None:
    write_artifact(deck, tmp_path)
    index = json.loads((tmp_path / "project" / "deck.json").read_text("utf-8"))
    assert index["order"] == [slide.id for slide in deck.slides]
    assert len(set(index["order"])) == len(deck.slides)
    for slide_id in index["order"]:
        html = (tmp_path / "project" / "slides" / f"{slide_id}.html").read_text("utf-8")
        assert html.startswith(f'<section id="{slide_id}"')
        # What the Slides page format does not accept.
        assert not re.search(r"<text|<sup|<sub|z-index", html)
    assert all(section["start"] in index["order"] for section in index["sections"].values())


def test_at_most_24_pinned_labels_per_plot(deck: Deck) -> None:
    assert max(len(scene.labels) for scene in scenes(deck)) <= 24


def test_standalone_file_draws_arrows_itself(deck: Deck, tmp_path: Path) -> None:
    html = write_standalone(deck, tmp_path / "deck.html").read_text("utf-8")
    assert html.count("<section ") == len(deck.slides)
    assert "x-connector" not in html
    for slide in deck.slides:
        if isinstance(slide, DiagramSlide):
            assert "marker-end" in html
            assert "<x-connector" in slide_html(slide)
