# deckkit

Slide decks written in Python. A deck is a folder of code: its plots are computed from their formulas, its slides are data, and one description is rendered as PowerPoint or as HTML. The repository holds the tool and the decks made with it.

## Quick start

```bash
uv sync               # install the dependencies
make fonts            # download IBM Plex Sans and Source Serif 4 into fonts/
make DECK=starter     # build/starter/starter.pptx
```

`DECK` names a folder of `decks/`; `make list` shows them. Without it, `make` builds `differential-privacy`. `make help` lists every target. The same commands are available as `uv run deckkit …`; `uv run deckkit build --help` shows the options.

| Command | Output, in `build/<deck>/` |
| --- | --- |
| `make` or `make pptx` | `<deck>.pptx`, plots as native PowerPoint shapes |
| `make pptx-images` | the same file with every plot exported as a transparent image |
| `make html` | `<deck>.html`, one file that opens in any browser (arrow keys move through it) |
| `make artifact` | `artifact/project/`, the folder a Claude Slides artifact is published from |
| `make plots` | `plots/*.svg` and `*.png`, the plot of each plot slide on its own, with a transparent background |
| `make preview` | `preview/slide-NN.png`, the PowerPoint file rendered by LibreOffice |

## The decks

| Deck | What it is |
| --- | --- |
| `starter` | Six slides that use the common kinds of slide and two plots on one frame. Copy it to start a deck. |
| `differential-privacy` | A 20-minute introduction to differential privacy and privacy accounting for newcomers: ε-DP, (ε, δ)-DP, concentrated and zero-concentrated DP. 22 slides. |

## Writing a deck

A deck is a Python package in `decks/`, or a single `.py` file, that defines `build_deck()` and returns a `deckkit.model.Deck`. To start one:

```bash
cp -r decks/starter decks/my_talk     # letters, digits and underscores
make DECK=my-talk                     # hyphens or underscores both work
```

A deck is made of three things.

- **Slides** are instances of the classes in `deckkit.model`: a cover, a statement, a plot with its explanation, a row of cards, tables, a diagram of boxes and arrows.
- **Plots** are `Scene` objects, from `deckkit.scene`: lines, filled areas, circles, labels and legend entries on a canvas of fixed size. The deck computes the points; `decks/starter` draws a bell curve in a dozen lines.
- **Text** takes a small inline markup: `*x*` for italics, `**x**` for strong, and in equations `^{x}` and `_{x}` for raised and lowered pieces.

A deck with much mathematics can split into modules, as `decks/differential_privacy` does: `dpmath.py` for the formulas, `plots.py` for the pictures, `content.py` for the slides. A deck outside this repository works too: give its path in place of its name.

## The PowerPoint output

**Native where PowerPoint can draw it.** A plot becomes a group of ordinary shapes: freeforms for curves and filled areas, lines for axes and brackets, ovals, text boxes. Translucent fills, dashes, arrowheads, superscripts and the fade between slides are all native too, so everything can be edited in PowerPoint. Tables are PowerPoint tables and every slide has a real title.

**An image for what PowerPoint cannot draw.** A shape with no PowerPoint equivalent, such as a gradient or a blur, goes into a plot as `scene.raw(svg)`. In the PowerPoint output that shape, and only that shape, is rendered to a PNG and placed in the plot at its place in the stacking order. The image has no background, so the slide colour and the shapes underneath show through. Neither deck in this repository needs one. Three modes choose the behaviour:

| `--plots` | What happens |
| --- | --- |
| `auto` (default) | native shapes, images only for raw SVG |
| `image` | all the shapes of every plot become one image per plot; labels stay native text |
| `native` | the build fails if a shape would need an image |

Exporting an image needs `rsvg-convert` (Debian package `librsvg2-bin`) or the Python package `cairosvg`. `--scale` sets the resolution, 3 by default, which is three times the 1920 px slide.

**Plots stay aligned from slide to slide.** A deck can make a point by keeping a curve in place while the slide changes, provided the plot does not shift. Two rules guarantee that in PowerPoint. Every plot is drawn on one fixed frame, 1040 × 640 px, placed at the same position. And nothing is cropped to its content: a native plot is a group whose first member is an invisible rectangle of the full frame, and an exported image always covers the full frame. So the group or the image has the same position and size on every slide, whatever it shows. `tests/test_pptx.py` checks both.

**Fonts.** Decks are set in IBM Plex Sans and Source Serif 4, both under the SIL Open Font License. `make fonts` downloads them into `fonts/`, which is enough to build and preview. To present, install them on the machine that runs PowerPoint, or build with fonts it has: `uv run deckkit build starter --font-sans Arial --font-serif Georgia`. PowerPoint has no layout engine to ask, so the build measures every paragraph with the font files to decide where the next block goes; with other fonts on the presenting machine, a paragraph can take one line more or less than planned.

**What differs from the HTML deck.** Headings use the Bold weight, where the HTML deck uses SemiBold. Dashed and dotted lines use PowerPoint's preset patterns, which are close to the HTML ones and not identical.

## How it is organised

```
src/deckkit/      the tool
  model.py        the kinds of slide and of text block
  scene.py        a Scene: shapes and labels on a fixed canvas, with no output format in it
  richtext.py     the inline markup of slide text
  theme.py        colours, type sizes, page geometry
  fonts.py        finding the fonts and measuring text
  loader.py       finding a deck by name or path
  render_pptx.py  PowerPoint output
  render_html.py  HTML output, single file and artifact folder
  render_svg.py   standalone SVG and PNG, used by `plots` and by the image fallback
  cli.py          the command line
  assets/         deck.css for the HTML outputs, and the viewer of the single file
decks/            one folder per deck
  starter/
  differential_privacy/
tests/
```

A deck builds slides and scenes; one renderer per format turns them into output. Nothing in a deck knows which format it will become.

## Changing things

- **A sentence, an equation or a plot of a deck**: in that deck's folder. In `differential_privacy`, the parameters of the example (ε, the counts, σ) are constants at the top of `plots.py`, and the numbers quoted in the text, such as δ = 0.13, are computed from them.
- **Plots that line up**: draw them on scenes of the same size, `PLOT_W` × `PLOT_H` for a plot slide, with the same axis coordinates.
- **A new kind of slide**: a class in `model.py`, and a branch in `render_html.py` and in `render_pptx.py`.
- **A colour or a type size**: `theme.py` for PowerPoint and images, `assets/deck.css` for HTML. They hold the same values and are changed together. All decks share this one look.

## Checks

```bash
make check    # ruff, pyright and the tests
make preview  # then look at build/preview/sheet-*.png
```

Most tests run on every deck in `decks/`: the constraints of the Slides page format, and in the PowerPoint output the titles, the shared plot frame and the transparent images. The others cover the markup, the image fallback, the loader, and the numbers quoted in the differential privacy deck.

## Known limits

- The PowerPoint output has been checked by rendering it with LibreOffice, not with PowerPoint itself. Text positions follow the HTML deck to within a pixel or two in LibreOffice; PowerPoint may place lines slightly differently.
- There is one look: the colours and type of `theme.py`. A deck chooses its content, not its theme.
- A table cell holds one line of text.
