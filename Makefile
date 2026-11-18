.DEFAULT_GOAL := pptx
.PHONY: pptx pptx-images html artifact plots all fonts preview check test lint typecheck clean help

pptx: ## The deck as PowerPoint, plots as native shapes (the default)
	uv run dpdeck build

pptx-images: ## The deck as PowerPoint, every plot exported as a transparent image
	uv run dpdeck build --plots image

html: ## The deck as one HTML file that opens in a browser
	uv run dpdeck build --format html

artifact: ## The project folder of a Claude Slides artifact
	uv run dpdeck build --format artifact

plots: ## Every plot on its own, as SVG and as transparent PNG
	uv run dpdeck plots --format svg
	uv run dpdeck plots --format png

all: ## PowerPoint, HTML and the artifact folder
	uv run dpdeck build --format all

fonts: ## Download IBM Plex Sans and Source Serif 4 into fonts/
	uv run dpdeck fonts

preview: pptx ## Render the PowerPoint file to PNG with LibreOffice, with contact sheets
	uv run dpdeck preview --sheets

check: lint typecheck test ## Everything below

test: ## Run the tests
	uv run pytest -q

lint: ## Ruff: errors and formatting
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck: ## Pyright
	uv run pyright

clean: ## Remove build output
	rm -rf build

help: ## Show this list
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'
