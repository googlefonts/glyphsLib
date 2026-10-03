import glyphsLib
from glyphsLib.filters.cornerComponents import (
    CornerComponentsFilter,
    split_cubic_at_point,
)
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


def test_split_cubic_at_point_outward_picks_segment_starting_at_point():
    # Outstroke of izhitsa-cy in Libre Franklin Italic. The horizontal ray
    # through the intersection point hits this curve twice, so the split at
    # point[1] yields three segments and its last one starts far from the
    # point; the split at point[0] is the right one. Both candidates end at
    # the original endpoint, so the choice must be made by the start point.
    seg = ((567, 533), (503, 548), (461, 516), (408, 409))
    point = (557.0059633196162, 534.9845238903391)
    result = split_cubic_at_point(seg, point, inward=False)
    assert result[0] == pytest.approx(point, abs=1e-6)
    assert result[-1] == pytest.approx(seg[-1], abs=1e-6)


def test_corner_components_format2_mixed_glyph():
    # A format 2 source whose glyph has both a component and a path, with a
    # corner component on the path. The other fixture in this file is format
    # 3 and has no glyph mixing paths and components, so neither the format 2
    # reading of a corner origin nor the mixed-glyph shapeOrder path was
    # covered before.
    #
    # Only format 3 has an authored shapes array. Here the layer reports its
    # shapes as "CP", which is an artefact of the order glyphsLib assigns
    # paths and components rather than anything in the file, so no shapeOrder
    # may be recorded; the origin "{0, 0}" counts paths and means path 0.
    # Recording it made the filter resolve index 0 to the component and raise
    # "Could not find shape number 0".
    ufo2 = glyphsLib.load_to_ufos(datadir.join("CornerComponentsFormat2.glyphs"))[0]
    glyph = ufo2["mixedcorner"]
    assert "com.schriftgestaltung.Glyphs.shapeOrder" not in glyph.lib
    assert len(glyph.components) == 1
    assert len(glyph.contours) == 1
    assert len(glyph.contours[0]) == 3

    assert CornerComponentsFilter(include={"mixedcorner"})(ufo2)

    # The corner component is applied to the path, not rejected and not
    # applied to the component.
    assert len(ufo2["mixedcorner"].contours[0]) == 6
    assert len(ufo2["mixedcorner"].components) == 1
