# The deck to build: a folder of decks/. `make DECK=starter` builds another one.
DECK ?= differential-privacy

.DEFAULT_GOAL := pptx
.PHONY: pptx pptx-images html artifact plots all list fonts preview check test lint typecheck clean help

pptx: ## The deck as PowerPoint, plots as native shapes (the default)
	uv run deckkit build $(DECK)

pptx-images: ## The deck as PowerPoint, every plot exported as a transparent image
	uv run deckkit build $(DECK) --plots image

html: ## The deck as one HTML file that opens in a browser
	uv run deckkit build $(DECK) --format html

artifact: ## The project folder of a Claude Slides artifact
	uv run deckkit build $(DECK) --format artifact

plots: ## Every plot of the deck on its own, as SVG and as transparent PNG
	uv run deckkit plots $(DECK) --format svg
	uv run deckkit plots $(DECK) --format png

all: ## PowerPoint, HTML and the artifact folder
	uv run deckkit build $(DECK) --format all

preview: pptx ## Render the PowerPoint file to PNG with LibreOffice, with contact sheets
	uv run deckkit preview $(DECK) --sheets

list: ## The decks in decks/
	uv run deckkit list

fonts: ## Download IBM Plex Sans and Source Serif 4 into fonts/
	uv run deckkit fonts

check: lint typecheck test ## Everything below

test: ## Run the tests
	uv run pytest -q

lint: ## Ruff: errors and formatting
	uv run ruff check src decks tests
	uv run ruff format --check src decks tests

typecheck: ## Pyright
	uv run pyright

clean: ## Remove build output
	rm -rf build

help: ## Show this list
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'
