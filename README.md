# dp-deck

A 20-minute slide deck for newcomers to differential privacy and privacy accounting: ε-DP, (ε, δ)-DP, concentrated and zero-concentrated DP. The deck is generated from code. Every curve is computed from its formula, and one description of the slides is rendered as PowerPoint or as HTML.

## Quick start

```bash
uv sync            # install the dependencies
make fonts         # download IBM Plex Sans and Source Serif 4 into fonts/
make               # build/dp-deck.pptx
```

`make help` lists every target. The same commands are available as `uv run dpdeck …`; `uv run dpdeck build --help` shows the options.

| Command | Output |
| --- | --- |
| `make` or `make pptx` | `build/dp-deck.pptx`, plots as native PowerPoint shapes |
| `make pptx-images` | the same file with every plot exported as a transparent image |
| `make html` | `build/dp-deck.html`, one file that opens in any browser (arrow keys move through it) |
| `make artifact` | `build/artifact/project/`, the folder a Claude Slides artifact is published from |
| `make plots` | `build/plots/*.svg` and `*.png`, each plot on its own with a transparent background |
| `make preview` | `build/preview/slide-NN.png`, the PowerPoint file rendered by LibreOffice |

## The PowerPoint output

**Native where PowerPoint can draw it.** A plot becomes a group of ordinary shapes: freeforms for curves and filled areas, lines for axes and brackets, ovals, text boxes. Translucent fills, dashes, arrowheads, superscripts and the fade between slides are all native too, so everything can be edited in PowerPoint. Tables are PowerPoint tables and every slide has a real title.

**An image for what PowerPoint cannot draw.** A shape with no PowerPoint equivalent, such as a gradient or a blur, goes into a plot as `scene.raw(svg)`. In the PowerPoint output that shape, and only that shape, is rendered to a PNG and placed in the plot at its place in the stacking order. The image has no background, so the slide colour and the shapes underneath show through. The deck as it stands needs no image. Three modes choose the behaviour:

| `--plots` | What happens |
| --- | --- |
| `auto` (default) | native shapes, images only for raw SVG |
| `image` | all the shapes of every plot become one image per plot; labels stay native text |
| `native` | the build fails if a shape would need an image |

Exporting an image needs `rsvg-convert` (Debian package `librsvg2-bin`) or the Python package `cairosvg`. `--scale` sets the resolution, 3 by default, which is three times the 1920 px slide.

**Plots stay aligned from slide to slide.** The deck makes its points by keeping curves in place while the slide changes. Two rules guarantee it in PowerPoint. Every plot is drawn on one fixed frame, 1040 × 640 px, placed at the same position. And nothing is cropped to its content: a native plot is a group whose first member is an invisible rectangle of the full frame, and an exported image always covers the full frame. So the group or the image has the same position and size on every slide, whatever it shows. `tests/test_pptx.py` checks both.

**Fonts.** The deck is set in IBM Plex Sans and Source Serif 4, both under the SIL Open Font License. `make fonts` downloads them into `fonts/`, which is enough to build and preview. To present, install them on the machine that runs PowerPoint, or build with fonts it has: `uv run dpdeck build --font-sans Arial --font-serif Georgia`. PowerPoint has no layout engine to ask, so the build measures every paragraph with the font files to decide where the next block goes; with other fonts on the presenting machine, a paragraph can take one line more or less than planned.

**What differs from the HTML deck.** Headings use the Bold weight, where the HTML deck uses SemiBold. Dashed and dotted lines use PowerPoint's preset patterns, which are close to the HTML ones and not identical.

## How it is organised

```
src/dpdeck/
  dpmath.py       densities, the exact δ of the Gaussian mechanism, the composition rules
  plots.py        every plot, built from dpmath as a Scene
  scene.py        a Scene: shapes and labels on a fixed canvas, with no output format in it
  content.py      the 22 slides and their text
  model.py        the kinds of slide and of text block
  richtext.py     the inline markup of slide text (*x* italic, **x** strong, ^{x}, _{x})
  theme.py        colours, type sizes, page geometry
  fonts.py        finding the fonts and measuring text
  render_pptx.py  PowerPoint output
  render_html.py  HTML output, single file and artifact folder
  render_svg.py   standalone SVG and PNG, used by `plots` and by the image fallback
  assets/         deck.css for the HTML outputs, and the viewer of the single file
```

The flow is `dpmath → plots → content`, then one renderer per format. Nothing in `plots.py` or `content.py` knows which format it will become.

## Changing the deck

- **A sentence or an equation**: edit `content.py`.
- **A parameter of the example** (ε, the counts, σ): the constants at the top of `plots.py`. Numbers quoted in the text, such as δ = 0.13, are computed, so they follow.
- **A plot**: its function in `plots.py`. Keep to the shared axis (`x_count`, `BASE`) when the plot should line up with its neighbours.
- **A new slide**: add it to `content.py`, using one of the slide types in `model.py`. A new type needs a branch in `render_html.py` and in `render_pptx.py`.
- **A colour or a type size**: `theme.py` for PowerPoint and images, `assets/deck.css` for HTML. They hold the same values and are changed together.

## Checks

```bash
make check    # ruff, pyright and the tests
make preview  # then look at build/preview/sheet-*.png
```

The tests cover the numbers quoted on the slides, the markup, the constraints of the Slides page format, and the PowerPoint output: titles, the shared plot frame, transparent images, and the image fallback.

## Known limits

The PowerPoint file has been checked by rendering it with LibreOffice, not with PowerPoint itself. Text positions follow the HTML deck to within a pixel or two in LibreOffice; PowerPoint may place lines slightly differently.
