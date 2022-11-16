import glyphsLib
from glyphsLib.filters.cornerComponents import CornerComponentsFilter


def test_corner_components(datadir):
    ufo = glyphsLib.load_to_ufos(datadir.join("CornerComponents.glyphs"))[0]
    philter = CornerComponentsFilter()

    assert philter(ufo)

    for glyph in ufo.keys():
        if not glyph.endswith(".expectation"):
            continue
        expectation = ufo[glyph]
        test_glyph = ufo[glyph[:-12]]
        for test_contour, expectation_contour in zip(
            test_glyph.contours, expectation.contours
        ):
            assert test_contour == expectation_contour, glyph
