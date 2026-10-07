import logging
import math

from fontTools.misc.bezierTools import cubicPointAtT
from fontTools.pens.basePen import BasePen
import glyphsLib
from glyphsLib.builder.constants import HINTS_LIB_KEY, SHAPE_ORDER_LIB_KEY
from glyphsLib.filters.cornerComponents import (
    CornerComponentsFilter,
    split_cubic_at_point,
)
import py
import pytest
import ufoLib2

datadir = py.path.local(py.path.local(__file__).dirname).join("data")

# Each case has a <case>.expectation glyph with Glyphs 3.5's own decomposition
# of its corners, made by tests/tools/corner_components_expectations.py.
ufo = glyphsLib.load_to_ufos(datadir.join("CornerComponents.glyphs"))[0]

# Cases where we don't yet match Glyphs
MISMATCHES = {
    "ad_curved_instroke",
    "align_unaligned_concave",
    "curve_bracketed_instroke_tight",
    "curve_bracketed_outstroke_tight",
    "curve_cupped_instroke_tight",
    "curve_cupped_outstroke_tight",
    "curve_flare_instroke_tight",
    "curve_flare_outstroke_tight",
    "curve_flare_turned_instroke_tight",
    "curve_flare_turned_outstroke_tight",
    "real_aoboshi_g",
    "real_bellota_sha",
    "real_hina_yoko",
    "real_iansui_sturn",
}


def _cases():
    mismatches = set(MISMATCHES)
    cases = []
    for name in sorted(ufo.keys()):
        hints = ufo[name].lib.get(HINTS_LIB_KEY, [])
        if any(hint["type"] == "Corner" for hint in hints):
            marks = pytest.mark.xfail(strict=True) if name in mismatches else ()
            mismatches.discard(name)
            cases.append(pytest.param(name, marks=marks))
    assert not mismatches, f"no such cases: {sorted(mismatches)}"
    return cases


def _nodes(glyph):
    return [[(pt.x, pt.y) for pt in contour if pt.segmentType] for contour in glyph]


def _node_distance(nodes, others):
    pairs = zip(nodes, others)
    return max(
        (max(abs(x0 - x1), abs(y0 - y1)) for (x0, y0), (x1, y1) in pairs), default=0
    )


def _furthest_node(ours, glyphs):
    # The furthest any of our nodes is from Glyphs', matching each of our
    # contours with whichever of Glyphs' contours and start points fits best
    if sorted(map(len, ours)) != sorted(map(len, glyphs)):
        return math.inf
    glyphs = list(glyphs)
    furthest = 0
    for contour in ours:
        distance, i = min(
            (_node_distance(contour, other[k:] + other[:k]), i)
            for i, other in enumerate(glyphs)
            if len(other) == len(contour)
            for k in range(max(1, len(other)))
        )
        furthest = max(furthest, distance)
        del glyphs[i]
    return furthest


class _LinesPen(BasePen):
    """Collect an outline as straight lines, flattening curves."""

    def __init__(self):
        super().__init__(glyphSet=None)
        self.lines = []

    def _moveTo(self, pt):
        self.start = pt

    def _lineTo(self, pt):
        self.lines.append((self._getCurrentPoint(), pt))

    def _curveToOne(self, pt1, pt2, pt3):
        pt0 = self._getCurrentPoint()
        pts = [cubicPointAtT(pt0, pt1, pt2, pt3, i / 24) for i in range(25)]
        self.lines.extend(zip(pts, pts[1:]))

    def _closePath(self):
        self._lineTo(self.start)


def _lines(glyph):
    pen = _LinesPen()
    glyph.draw(pen)
    return pen.lines


def _distance_to_line(pt, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length2 = dx * dx + dy * dy
    t = ((pt[0] - start[0]) * dx + (pt[1] - start[1]) * dy) / length2 if length2 else 0
    t = max(0, min(1, t))
    return math.dist(pt, (start[0] + t * dx, start[1] + t * dy))


def _furthest_point(lines, others, step=3):
    # The furthest any point on lines is from others, checking every few units
    furthest = 0
    for start, end in lines:
        n = max(1, math.ceil(math.dist(start, end) / step))
        for i in range(n):
            pt = (
                start[0] + (end[0] - start[0]) * i / n,
                start[1] + (end[1] - start[1]) * i / n,
            )
            furthest = max(furthest, min(_distance_to_line(pt, *o) for o in others))
    return furthest


@pytest.mark.parametrize("glyph", _cases())
def test_corner_components(glyph):
    # We and Glyphs round to whole units at different points, so allow a
    # unit's difference. Handles are only compared through the outline: one a
    # few units off can move the curve by less than one.
    expectation = glyph + ".expectation"
    assert (
        expectation in ufo
    ), f"{glyph} has no expectation; run tests/tools/corner_components_expectations.py"
    assert CornerComponentsFilter(include={glyph})(ufo)
    node = _furthest_node(_nodes(ufo[glyph]), _nodes(ufo[expectation]))
    assert node <= 1, f"a node is {node} units from Glyphs'"
    ours, glyphs = _lines(ufo[glyph]), _lines(ufo[expectation])
    outline = max(_furthest_point(ours, glyphs), _furthest_point(glyphs, ours))
    assert outline <= 1, f"the outline is {outline:.1f} units from Glyphs'"


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


def _apply_corner(corner_nodes, host_nodes, node_index, **hint):
    font = ufoLib2.Font()
    for name, nodes in (("_corner.test", corner_nodes), ("host", host_nodes)):
        pen = font.newGlyph(name).getPointPen()
        pen.beginPath()
        for pt, segment_type in nodes:
            pen.addPoint(pt, segment_type)
        pen.endPath()
    font["host"].lib[HINTS_LIB_KEY] = [
        {"type": "Corner", "name": "_corner.test", "origin": [0, node_index], **hint}
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
            [(310, 0, "line"), (311, 15, "line"), (303, 40, "line")],
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


@pytest.mark.parametrize(
    "node_index, expected",
    [
        (1, [(500, 100), (440, 100), (440, 30), (500, 30), (500, 130)]),
        (0, [(440, 100), (440, 30), (500, 30), (500, 130), (500, 100)]),
    ],
    ids=["empty-instroke", "empty-outstroke"],
)
def test_corner_next_to_a_duplicate_node(node_index, expected):
    # Glyphs 3.5's output for a corner on either of two nodes in the same
    # place. It keeps the other node, and aims along the stroke between them,
    # which has no length, as if it ran straight up.
    corner = [
        ((0, 60), "move"),
        ((-70, 60), "line"),
        ((-70, 0), "line"),
        ((30, 0), "line"),
    ]
    host = [
        (pt, "line")
        for pt in ((100, 100), (500, 100), (500, 100), (500, 500), (100, 500))
    ]
    points = _apply_corner(corner, host, node_index)
    on_curves = [(x, y) for x, y, segment_type in points if segment_type]
    assert on_curves[1:-2] == expected


@pytest.mark.parametrize(
    "shape_order, shape_index",
    [(None, 1), ("PC", 2), ("CP", 0)],
    ids=["no-such-path", "no-such-shape", "component"],
)
def test_corner_on_shape_that_is_not_a_path_is_ignored(
    caplog, shape_order, shape_index
):
    # Glyphs ignores these. Aoboshi One's uni5B57 has two corners on a path
    # that isn't there any more.
    font = ufoLib2.Font()
    pen = font.newGlyph("_corner.test").getPointPen()
    pen.beginPath()
    for pt, segment_type in (
        ((0, 50), "move"),
        ((-50, 50), "line"),
        ((-50, 0), "line"),
    ):
        pen.addPoint(pt, segment_type)
    pen.endPath()
    host = font.newGlyph("host")
    pen = host.getPointPen()
    pen.beginPath()
    for pt in ((100, 500), (100, 100), (500, 100)):
        pen.addPoint(pt, "line")
    pen.endPath()
    if shape_order:
        pen.addComponent("_corner.test", (1, 0, 0, 1, 0, 0))
        host.lib[SHAPE_ORDER_LIB_KEY] = shape_order
    host.lib[HINTS_LIB_KEY] = [
        {"type": "Corner", "name": "_corner.test", "origin": [shape_index, 0]}
    ]
    with caplog.at_level(logging.WARNING):
        CornerComponentsFilter(include={"host"})(font)
    assert [(pt.x, pt.y) for pt in host[0]] == [(100, 500), (100, 100), (500, 100)]
    assert "is not a path" in caplog.text


def test_corner_on_off_curve_point_is_ignored(caplog):
    # Glyphs ignores these, as in Iansui's uni7BE1 and Hina Mincho's uni654D
    corner = [((0, 60), "move"), ((-70, 60), "line"), ((-70, 0), "line")]
    host = [
        ((450, 120), "line"),
        ((450, 550), "line"),
        ((150, 550), "line"),
        ((150, 400), None),
        ((150, 250), None),
        ((150, 120), "curve"),
    ]
    with caplog.at_level(logging.WARNING):
        points = _apply_corner(corner, host, 2)
    assert points == [(x, y, segment_type) for (x, y), segment_type in host]
    assert "off-curve point" in caplog.text
