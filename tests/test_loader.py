from pathlib import Path

import pytest

from deckkit.cli import main
from deckkit.loader import DeckError, available, load
from deckkit.model import Deck, PlotSlide, Statement

DECKS_DIR = Path(__file__).parent.parent / "decks"


def test_decks_are_found_by_name_with_hyphens_or_underscores() -> None:
    assert {"differential-privacy", "starter"} <= set(available(DECKS_DIR))
    by_hyphen = load("differential-privacy", DECKS_DIR)
    by_underscore = load("differential_privacy", DECKS_DIR)
    assert by_hyphen.name == by_underscore.name == "differential-privacy"
    assert isinstance(by_hyphen.deck, Deck)


def test_a_deck_can_be_one_file_anywhere(tmp_path: Path) -> None:
    source = tmp_path / "one_file_deck.py"
    source.write_text(
        "from deckkit.model import Deck, Statement\n"
        "def build_deck():\n"
        "    return Deck('One file', (Statement('s', 'eyebrow', 'title', 'lead'),))\n",
        "utf-8",
    )
    loaded = load(str(source))
    assert loaded.name == "one-file-deck"
    assert isinstance(loaded.deck.slides[0], Statement)


def test_unknown_deck_names_the_ones_that_exist() -> None:
    with pytest.raises(DeckError, match="starter"):
        load("no-such-deck", DECKS_DIR)


def test_plots_are_the_plot_slides() -> None:
    deck = load("starter", DECKS_DIR).deck
    assert list(deck.plots) == [slide.id for slide in deck.slides if isinstance(slide, PlotSlide)]


def test_build_writes_into_a_folder_named_after_the_deck(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["build", "starter", "--decks-dir", str(DECKS_DIR), "--out", str(tmp_path), "--format", "all"]
    assert main(args) == 0
    assert (tmp_path / "starter" / "starter.pptx").stat().st_size > 10_000
    assert (tmp_path / "starter" / "starter.html").exists()
    assert (tmp_path / "starter" / "artifact" / "project" / "deck.json").exists()
    assert main(["build", "no-such-deck", "--decks-dir", str(DECKS_DIR), "--out", str(tmp_path)]) == 1
    assert "no deck 'no-such-deck'" in capsys.readouterr().err
