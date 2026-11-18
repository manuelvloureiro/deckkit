from pathlib import Path

import pytest

from deckkit.loader import available, load
from deckkit.model import Deck

DECKS_DIR = Path(__file__).parent.parent / "decks"


@pytest.fixture(params=available(DECKS_DIR))
def deck(request: pytest.FixtureRequest) -> Deck:
    """Every deck of the repository in turn."""
    return load(request.param, DECKS_DIR).deck
