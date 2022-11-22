import glyphsLib
from glyphsLib.filters.cornerComponents import CornerComponentsFilter
import py
import pytest


datadir = py.path.local(py.path.local(__file__).dirname).join("data")

ufo = glyphsLib.load_to_ufos(datadir.join("CornerComponents.glyphs"))[0]

test_glyphs = [glyph[:-12] for glyph in ufo.keys() if glyph.endswith(".expectation")]


@pytest.mark.parametrize("glyph", sorted(test_glyphs))
def test_corner_components(glyph):
    if "left_anchor" in glyph:
        pytest.xfail("left anchors not quite working yet")
    philter = CornerComponentsFilter(include={glyph})
    assert philter(ufo)
    test_glyph = ufo[glyph]
    expectation = ufo[glyph + ".expectation"]
    assert len(test_glyph) == len(expectation)
    for test_contour, expectation_contour in zip(
        expectation.contours, test_glyph.contours
    ):
        assert test_contour == expectation_contour, glyph
