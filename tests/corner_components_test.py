import glyphsLib
from glyphsLib.filters.cornerComponents import CornerComponentsFilter
import py
import pytest


datadir = py.path.local(py.path.local(__file__).dirname).join("data")

ufo = glyphsLib.load_to_ufos(datadir.join("CornerComponents.glyphs"))[0]
CornerComponentsFilter()(ufo)

test_glyphs = [glyph[:-12] for glyph in ufo.keys() if glyph.endswith(".expectation")]


@pytest.mark.parametrize("glyph", test_glyphs)
def test_corner_components(glyph):
    test_glyph = ufo[glyph]
    expectation = ufo[glyph + ".expectation"]
    for test_contour, expectation_contour in zip(
        test_glyph.contours, expectation.contours
    ):
        assert test_contour == expectation_contour, glyph
