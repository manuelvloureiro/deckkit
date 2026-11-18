"""Finding and loading a deck.

A deck is a Python package, or a single module, that defines `build_deck()` returning a
`deckkit.model.Deck`. Decks live in one folder, `decks/` by default, and are named on the command
line by their folder name, with hyphens or underscores, or by a path to them.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

from deckkit.model import Deck


class DeckError(Exception):
    """A deck that cannot be found or loaded. The message is meant for the person at the terminal."""


@dataclass(frozen=True)
class LoadedDeck:
    name: str  # used for file names: the folder name with hyphens
    path: Path
    deck: Deck


def _is_deck(path: Path) -> bool:
    if path.is_dir():
        return (path / "__init__.py").is_file()
    return path.suffix == ".py" and not path.name.startswith("_")


def available(decks_dir: Path) -> list[str]:
    """Names of the decks in a folder."""
    if not decks_dir.is_dir():
        return []
    return sorted(path.stem.replace("_", "-") for path in decks_dir.iterdir() if _is_deck(path))


def find(spec: str, decks_dir: Path) -> Path:
    """The package folder or module file of a deck given by name or by path."""
    module = spec.replace("-", "_")
    for candidate in (Path(spec), decks_dir / module, decks_dir / f"{module}.py"):
        if candidate.exists() and _is_deck(candidate):
            return candidate.resolve()
    names = ", ".join(available(decks_dir)) or "none"
    raise DeckError(f"no deck '{spec}' in {decks_dir}/ (decks there: {names})")


def load(spec: str, decks_dir: Path = Path("decks")) -> LoadedDeck:
    path = find(spec, decks_dir)
    module_name = path.stem
    if not module_name.isidentifier():
        raise DeckError(f"'{path.name}' cannot be imported: name the deck with letters, digits and underscores")
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    module = importlib.import_module(module_name)
    origin = Path(module.__file__ or "").resolve()
    if path not in (origin, origin.parent):
        raise DeckError(f"the deck name '{module_name}' is already taken by the module at {origin}: rename the deck")
    build = getattr(module, "build_deck", None)
    if not callable(build):
        raise DeckError(f"{path} must define build_deck(), returning a deckkit.model.Deck")
    deck = build()
    if not isinstance(deck, Deck):
        raise DeckError(f"build_deck() of {path} returned {type(deck).__name__}, not a Deck")
    return LoadedDeck(module_name.replace("_", "-"), path, deck)
