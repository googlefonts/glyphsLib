import math

from fontTools.misc.bezierTools import cubicPointAtT
from fontTools.pens.basePen import BasePen
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

# Each case has a <case>.expectation glyph with Glyphs 3.5's own decomposition
# of its corners, made by tests/tools/corner_components_expectations.py.
ufo = glyphsLib.load_to_ufos(datadir.join("CornerComponents.glyphs"))[0]

# Cases where we don't yet match Glyphs
MISMATCHES = {
    "ad_curved_instroke",
    "ak_right_slanted",
    "al_unaligned",
    "align_instroke_flipxy_acute",
    "align_instroke_squashed",
    "align_middle_squashed",
    "align_unaligned_concave",
    "align_unaligned_flipx_acute",
    "align_unaligned_flipxy_acute",
    "align_unaligned_flipy_acute",
    "anchor_left_instroke",
    "anchor_left_instroke_flipx",
    "anchor_left_instroke_square",
    "anchor_left_middle",
    "anchor_left_middle_flipx",
    "anchor_left_on_path_instroke",
    "anchor_left_on_path_instroke_flipx",
    "anchor_left_on_path_middle",
    "anchor_left_on_path_middle_flipx",
    "anchor_left_on_path_outstroke_flipx",
    "anchor_left_on_path_unaligned_flipx",
    "anchor_left_outstroke_flipx",
    "anchor_left_right_instroke",
    "anchor_left_right_instroke_flipx",
    "anchor_left_right_middle",
    "anchor_left_right_middle_flipx",
    "anchor_left_right_outstroke",
    "anchor_left_right_outstroke_flipx",
    "anchor_left_right_unaligned",
    "anchor_left_right_unaligned_flipx",
    "anchor_left_unaligned_flipx",
    "anchor_origin_instroke",
    "anchor_origin_left",
    "anchor_origin_left_flipx",
    "anchor_right_instroke",
    "anchor_right_instroke_flipx",
    "anchor_right_instroke_square",
    "anchor_right_middle",
    "anchor_right_middle_flipx",
    "anchor_right_outstroke",
    "anchor_right_outstroke_flipx",
    "anchor_right_outstroke_square",
    "anchor_right_unaligned",
    "anchor_right_unaligned_flipx",
    "ap_twoofthem",
    "curve_bracketed_instroke_curvedboth",
    "curve_bracketed_instroke_curvedin",
    "curve_bracketed_instroke_tight",
    "curve_bracketed_outstroke_curvedboth",
    "curve_bracketed_outstroke_curvedin",
    "curve_bracketed_outstroke_tight",
    "curve_cupped_instroke_tight",
    "curve_cupped_outstroke_tight",
    "curve_flare_instroke_curvedboth",
    "curve_flare_instroke_curvedin",
    "curve_flare_instroke_tight",
    "curve_flare_outstroke_curvedboth",
    "curve_flare_outstroke_curvedin",
    "curve_flare_outstroke_tight",
    "curve_flare_turned_instroke_curvedboth",
    "curve_flare_turned_instroke_curvedin",
    "curve_flare_turned_instroke_tight",
    "curve_flare_turned_outstroke_curvedboth",
    "curve_flare_turned_outstroke_curvedin",
    "curve_flare_turned_outstroke_tight",
    "multi_flipx",
    "multi_instroke_acute",
    "orient_tilted_acute",
    "real_aoboshi_g",
    "real_bellota_p",
    "real_bellota_sha",
    "real_hina_yoko",
    "real_iansui_rhook",
    "real_iansui_sturn",
    "real_playfair_de",
    "real_playfair_descender",
    "where_straight_node",
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


def _apply_corners(corner_nodes, host_nodes, hints, anchors=None):
    font = ufoLib2.Font()
    for name, nodes in (("_corner.test", corner_nodes), ("host", host_nodes)):
        pen = font.newGlyph(name).getPointPen()
        pen.beginPath()
        for pt, segment_type in nodes:
            pen.addPoint(pt, segment_type)
        pen.endPath()
    for name, (x, y) in (anchors or {}).items():
        font["_corner.test"].appendAnchor({"name": name, "x": x, "y": y})
    font["host"].lib[HINTS_LIB_KEY] = [
        {"type": "Corner", "name": "_corner.test", **hint} for hint in hints
    ]
    assert CornerComponentsFilter(include={"host"})(font)
    return [(pt.x, pt.y, pt.segmentType) for pt in font["host"][0]]


def _apply_corner(corner_nodes, host_nodes, node_index, anchors=None, **hint):
    hint["origin"] = [0, node_index]
    return _apply_corners(corner_nodes, host_nodes, [hint], anchors)


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


def _path(*nodes):
    # Bare points are line nodes
    return [node if isinstance(node[0], tuple) else (node, "line") for node in nodes]


SERIF = _path((0, 96), (-68, 96), (-68, 0), (9, 0))
SERIF[0] = (SERIF[0][0], "move")


# Corners taken from real fonts, with the on-curve points Glyphs gave them
@pytest.mark.parametrize(
    "corner, anchors, host, node_index, hint, expected",
    [
        pytest.param(
            # The serif slides along the outstroke until its left anchor is
            # on the instroke. (Glyphs 2 decomposing Montagu Slab's K)
            SERIF,
            {"left": (0, 45)},
            _path((257, 198), (800, 682), (629, 682), (184, 283)),
            0,
            {"scale": [0.02, 1]},
            [(692, 586), (751, 586), (751, 682)],
            id="left-anchor",
        ),
        pytest.param(
            # Flipped, the left anchor becomes the right one, and aligned to
            # the instroke, the serif slides along it until that anchor is on
            # the outstroke. (Ditto)
            SERIF,
            {"left": (0, 45)},
            _path((558, 0), (796, 0), (462, 428), (326, 307)),
            0,
            {"options": 1, "scale": [-0.2, 1]},
            [(774, 0), (774, 96), (721, 96)],
            id="right-anchor",
        ),
        pytest.param(
            # The serif turns the other way from the stem, so Glyphs mirrors
            # it. (Glyphs' export of Aoboshi One's L)
            [
                ((0, 30), "move"),
                ((0, 22), None),
                ((15, 19), None),
                ((22, 19), "curve"),
                ((22, 0), "line"),
                ((-28, 0), "line"),
            ],
            None,
            _path((73, 0), (207, 0), (207, 750), (73, 750)),
            3,
            {},
            [(73, 30), (51, 19), (51, 0)],
            id="mirrored",
        ),
        pytest.param(
            # Unaligned, the serif isn't mirrored, though it turns the other
            # way from the inside corner of this L. (Glyphs 3.5)
            [((0, 60), "move"), *_path((-70, 60), (-70, 0), (30, 0))],
            None,
            _path(
                (100, 600), (100, 100), (500, 100), (500, 250), (250, 250), (250, 600)
            ),
            3,
            {"options": 4, "scale": [-1, 1]},
            [(280, 250), (320, 250), (320, 310), (250, 310)],
            id="unaligned-not-mirrored",
        ),
        pytest.param(
            # Aligned to the instroke, a last segment that curves in along the
            # outstroke ends on it, |last node| along. (Aoboshi One's x)
            [
                ((28, 0), "move"),
                ((-42, 0), "line"),
                ((-42, 19), "line"),
                ((-25, 19), None),
                ((0, 32), None),
                ((0, 40), "curve"),
            ],
            None,
            _path((31, 0), (170, 0), (301, 171), (344, 222), (526, 460), (386, 460)),
            4,
            {"options": 1, "scale": [1, 0.97]},
            [(344, 460), (344, 442), (362, 429)],
            id="curved-end-on-outstroke",
        ),
        pytest.param(
            # Drawn a quarter turn round, leaving along the instroke, with a
            # left anchor and a curved outstroke. (Glyphs 3.5's export of
            # Alkatra's l)
            [
                ((175, 491), "move"),
                ((158, 491), None),
                ((57, 473), None),
                ((57, 444), "curve"),
                ((57, 432), None),
                ((65, 422), None),
                ((69, 410), "curve"),
                ((76, 392), None),
                ((81, 361), None),
                ((78, 330), "curve"),
            ],
            {"origin": (95, 491), "left": (175, 491), "right": (75, 304)},
            _path(
                (101, -14),
                (188, -14),
                ((195, 72), None),
                ((201, 177), None),
                ((214, 273), "curve"),
                (58, 233),
            ),
            0,
            {},
            [(108, -14), (225, 36), (212, 70), (201, 150)],
            id="quarter-turn",
        ),
    ],
)
def test_corner_matches_glyphs(corner, anchors, host, node_index, hint, expected):
    points = _apply_corner(corner, host, node_index, anchors, **hint)
    on_curves = [(x, y) for x, y, segment_type in points if segment_type]
    assert any(
        on_curves[i : i + len(expected)] == expected for i in range(len(on_curves))
    ), on_curves


def test_second_corner_on_a_node_is_ignored():
    # The first corner replaces the node, so in Glyphs a second one on the
    # same node does nothing. (Aoboshi One's a.ss01)
    corner = [((0, 50), "move"), ((-50, 50), "line"), ((-50, 0), "line")]
    host = [((100, 500), "line"), ((100, 100), "line"), ((500, 100), "line")]
    hint = {"origin": [0, 0]}
    assert _apply_corners(corner, host, [hint, hint]) == _apply_corner(corner, host, 0)
