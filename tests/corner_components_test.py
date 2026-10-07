import glyphsLib
from glyphsLib.builder.constants import HINTS_LIB_KEY
from glyphsLib.filters.cornerComponents import (
    CornerComponentsFilter,
    split_cubic_at_point,
)
import py
import pytest
import ufoLib2

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


def _apply_corner(corner_nodes, host_nodes, node_index):
    font = ufoLib2.Font()
    for name, nodes in (("_corner.test", corner_nodes), ("host", host_nodes)):
        pen = font.newGlyph(name).getPointPen()
        pen.beginPath()
        for pt, segment_type in nodes:
            pen.addPoint(pt, segment_type)
        pen.endPath()
    font["host"].lib[HINTS_LIB_KEY] = [
        {"type": "Corner", "name": "_corner.test", "origin": [0, node_index]}
    ]
    assert CornerComponentsFilter(include={"host"})(font)
    return [(pt.x, pt.y, pt.segmentType) for pt in font["host"][0]]


@pytest.mark.parametrize(
    "outstroke, expected",
    [
        (
            [],
            [(310, 0, "line"), (309, 15, "line"), (300, 40, "line")],
        ),
        (
            [((310, 100), None), ((310, 200), None)],
            [(310, 0, "line"), (311, 14, "line"), (303, 40, "line")],
        ),
    ],
    ids=["line", "curve"],
)
def test_corner_ending_behind_origin(outstroke, expected):
    # Drawn a quarter turn from the usual orientation, like the serif in
    # Alkatra, so the last point has a small negative x. On a curved
    # outstroke no t matched the negative distance and the filter crashed;
    # on a straight one the corner was turned the wrong way round.
    corner = [
        ((40, 0), "move"),
        ((-10, 0), "line"),
        ((-10, -15), "line"),
        ((-2, -40), "line"),
    ]
    host = [
        ((100, 0), "line"),
        ((300, 0), "line"),
        *outstroke,
        ((300, 300), "curve" if outstroke else "line"),
        ((100, 300), "line"),
    ]
    points = _apply_corner(corner, host, 0)
    assert len(points) == len(host) + len(corner) - 1
    assert points[2:5] == expected


@pytest.mark.parametrize(
    "instroke",
    [[], [((100, 200), None), ((100, 100), None)]],
    ids=["line", "curve"],
)
def test_corner_leaving_along_instroke(instroke):
    # The corner's first handle runs along the stem, so when the stem is a
    # (straight) curve, the first segment never crosses it and there is no
    # intersection to fit the corner to.
    corner = [
        ((0, 30), "move"),
        ((0, 15), None),
        ((-10, 0), None),
        ((-20, 0), "curve"),
        ((10, 0), "line"),
    ]
    host = [
        ((300, 0), "line"),
        ((300, 300), "line"),
        ((100, 300), "line"),
        *instroke,
        ((100, 0), "curve" if instroke else "line"),
    ]
    points = _apply_corner(corner, host, len(host) - 2)
    assert len(points) == len(host) + len(corner) - 1
    assert points[-5:] == [
        (100, 30, "curve" if instroke else "line"),
        (100, 15, None),
        (90, 0, None),
        (80, 0, "curve"),
        (110, 0, "line"),
    ]


# A format 2 glyph with a component and two paths, written the way Glyphs
# writes it, components first. The corner's origin counts paths only.
FORMAT2_MIXED_GLYPH = """{
familyName = CornerComponentsFormat2;
fontMaster = (
{
id = m01;
}
);
glyphs = (
{
export = 0;
glyphname = _corner.one;
layers = (
{
layerId = m01;
paths = (
{
closed = 0;
nodes = (
"0 50 LINE",
"-50 50 LINE",
"-50 0 LINE",
"25 0 LINE"
);
}
);
width = 250;
}
);
},
{
glyphname = square;
layers = (
{
layerId = m01;
paths = (
{
closed = 1;
nodes = (
"450 0 LINE",
"550 0 LINE",
"550 100 LINE",
"450 100 LINE"
);
}
);
width = 600;
}
);
},
{
glyphname = mixed;
layers = (
{
components = (
{
name = square;
}
);
hints = (
{
name = _corner.one;
origin = "{PATH_INDEX, 0}";
type = Corner;
}
);
layerId = m01;
paths = (
{
closed = 1;
nodes = (
"200 100 LINE",
"414 100 LINE",
"100 300 LINE"
);
},
{
closed = 1;
nodes = (
"200 500 LINE",
"414 500 LINE",
"100 700 LINE"
);
}
);
width = 600;
}
);
}
);
unitsPerEm = 1000;
}"""


@pytest.mark.parametrize("path_index", [0, 1])
def test_corner_components_format2_mixed_glyph(path_index):
    source = FORMAT2_MIXED_GLYPH.replace("PATH_INDEX", str(path_index))
    ufo = glyphsLib.to_ufos(glyphsLib.loads(source))[0]
    assert CornerComponentsFilter(include={"mixed"})(ufo)

    # The corner from aa_simple_angleinstroke in CornerComponents.glyphs; the
    # second path is the same triangle moved up by 400 units. (A UFO contour
    # starts at the last node of the Glyphs path.)
    plain = [
        [(100, 300), (200, 100), (414, 100)],
        [(100, 700), (200, 500), (414, 500)],
    ]
    cornered = [
        [(100, 300), (175, 150), (150, 150), (150, 100), (225, 100), (414, 100)],
        [(100, 700), (175, 550), (150, 550), (150, 500), (225, 500), (414, 500)],
    ]
    expected = list(plain)
    expected[path_index] = cornered[path_index]

    glyph = ufo["mixed"]
    assert [[(pt.x, pt.y) for pt in contour] for contour in glyph] == expected
    assert [component.baseGlyph for component in glyph.components] == ["square"]
