import pytest

from dpdeck.richtext import Run, equation_html, parse, plain, to_html
from dpdeck.scene import clip


def test_parse_runs() -> None:
    assert parse("*e*^{*ε* − *L*} and **more**") == [
        Run("e", italic=True),
        Run("ε", italic=True, shift=1),
        Run(" − ", shift=1),
        Run("L", italic=True, shift=1),
        Run(" and "),
        Run("more", bold=True),
    ]
    assert plain("**δ = 0.13**\nthe *area*") == "δ = 0.13 the area"


def test_html() -> None:
    assert to_html("a < *b*\n**c**") == 'a &lt; <i>b</i><br><b class="strong">c</b>'
    with pytest.raises(ValueError):
        to_html("x^{2}")


def test_equation_pieces_keep_the_space_after_a_superscript() -> None:
    assert equation_html("≤ *e*^{*ε*} · *q*_{1}") == (
        '<p>≤ <i>e</i></p><p class="sup"><i>ε</i></p><p>&#160;· <i>q</i></p><p class="sub">1</p>'
    )


def test_clip_cuts_at_the_limits() -> None:
    parts = clip([(0, 0), (10, 10), (20, 0)], 0, 5)
    assert parts == [[(0, 0), (5.0, 5)], [(15.0, 5), (20, 0)]]
