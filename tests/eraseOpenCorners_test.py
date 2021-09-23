import pytest
from defcon import Font

from glyphsLib.filters.eraseOpenCorners import EraseOpenCornersFilter


@pytest.fixture(
    params=[
        {
            "glyphs": [
                {"name": "space", "width": 500},
                {
                    "name": "hasCornerGlyph",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((20, 0),)),
                        ("lineTo", ((179, 0),)),
                        ("lineTo", ((60, 353),)),
                        ("lineTo", ((198, 360),)),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "curvyCornerGlyph",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((400, 0),)),
                        ("curveTo", ((400, 100), (450, 300), (300, 300))),
                        ("lineTo", ((200, 100),)),
                        ("curveTo", ((250, 100), (450, 150), (450, 50))),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "doubleCornerGlyph",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((100, 0),)),
                        ("lineTo", ((400, 0),)),
                        ("lineTo", ((400, 500),)),
                        ("lineTo", ((500, 400),)),
                        ("lineTo", ((0, 400),)),
                        ("lineTo", ((100, 500),)),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "doubleCornerGlyphTrickyBitInMiddle",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((100, 500),)),
                        ("lineTo", ((100, 0),)),
                        ("lineTo", ((400, 0),)),
                        ("lineTo", ((400, 500),)),
                        ("lineTo", ((500, 400),)),
                        ("lineTo", ((0, 400),)),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "curveCorner",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((316, 437),)),
                        (
                            "curveTo",
                            (
                                (388.67761, 437.0),
                                (446.1305580343, 401.4757887467),
                                (475, 344),
                            ),
                        ),
                        ("lineTo", ((588, 407),)),
                        ("lineTo", ((567, 260),)),
                        ("curveTo", ((567, 414), (464, 510), (316, 510))),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "curveCornerPlusSquare",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((316, 437),)),
                        (
                            "curveTo",
                            (
                                (388.67761, 437.0),
                                (446.1305580343, 401.4757887467),
                                (475, 344),
                            ),
                        ),
                        ("lineTo", ((588, 407),)),
                        ("lineTo", ((567, 260),)),
                        ("curveTo", ((567, 414), (464, 510), (316, 510))),
                        ("closePath", ()),
                        ("moveTo", ((100, 100),)),
                        ("lineTo", ((100, 200),)),
                        ("lineTo", ((200, 200),)),
                        ("lineTo", ((200, 100),)),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "squarePlusCurveCorner",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((100, 100),)),
                        ("lineTo", ((100, 200),)),
                        ("lineTo", ((200, 200),)),
                        ("lineTo", ((200, 100),)),
                        ("closePath", ()),
                        ("moveTo", ((316, 437),)),
                        (
                            "curveTo",
                            (
                                (388.67761, 437.0),
                                (446.1305580343, 401.4757887467),
                                (475, 344),
                            ),
                        ),
                        ("lineTo", ((588, 407),)),
                        ("lineTo", ((567, 260),)),
                        ("curveTo", ((567, 414), (464, 510), (316, 510))),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "dotabove-ar",
                    "width": 116,
                    "outline": [
                        ("moveTo", ((58, -58),)),
                        ("curveTo", ((90, -58), (116, -32), (116, 0))),
                        ("curveTo", ((116, 32), (90, 58), (58, 58))),
                        ("curveTo", ((26, 58), (0, 32), (0, 0))),
                        ("curveTo", ((0, -32), (26, -58), (58, -58))),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "sofiaSans",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((190, 327),)),
                        ("lineTo", ((199, 497),)),
                        ("lineTo", ((199, 488),)),
                        ("lineTo", ((32, 503),)),
                        ("closePath", ()),
                    ],
                },
                {
                    "name": "largeCrossing",
                    "width": 600,
                    "outline": [
                        ("moveTo", ((378, 615),)),
                        ("lineTo", ((344, 706),)),
                        ("lineTo", ((444, 660),)),
                        ("lineTo", ((281, 699),)),
                        ("closePath", ()),
                    ],
                },
            ]
        }
    ]
)
def font(request):
    font = Font()
    for param in request.param["glyphs"]:
        glyph = font.newGlyph(param["name"])
        glyph.width = param.get("width", 0)
        pen = glyph.getPen()
        for operator, operands in param.get("outline", []):
            getattr(pen, operator)(*operands)

        glyph = font.newGlyph(param["name"] + ".reversed")
        glyph.width = param.get("width", 0)
        pen = glyph.getPen()
        for operator, operands in param.get("outline", []):
            getattr(pen, operator)(*operands)
        for c in glyph:
            c.reverse()
    return font


def test_empty_glyph(font):
    glyph = "space"
    for g in [glyph, glyph + ".reversed"]:
        philter = EraseOpenCornersFilter(include=g)
        assert not philter(font)


def test_corner_glyph(font):
    philter = EraseOpenCornersFilter(include={"hasCornerGlyph"})
    assert philter(font)

    newcontour = font["hasCornerGlyph"][0]
    assert len(newcontour) == 3
    assert newcontour[2].x == pytest.approx(114.5417)
    assert newcontour[2].y == pytest.approx(191.2080)

    philter = EraseOpenCornersFilter(include={"hasCornerGlyph.reversed"})
    assert not philter(font)


def test_curve_curve_glyph(font):
    philter = EraseOpenCornersFilter(include={"curvyCornerGlyph"})
    assert philter(font)

    newcontour = font["curvyCornerGlyph"][0]
    assert len(newcontour) == 7
    assert newcontour[0].x == pytest.approx(406.4859)
    assert newcontour[0].y == pytest.approx(104.5666)

    philter = EraseOpenCornersFilter(include={"curvyCornerGlyph.reversed"})
    assert not philter(font)


def test_double_corner_glyph(font):
    philter = EraseOpenCornersFilter(include={"doubleCornerGlyph"})
    assert philter(font)

    newcontour = font["doubleCornerGlyph"][0]
    assert len(newcontour) == 4
    assert newcontour[0].x == 100 and newcontour[0].y == 0
    assert newcontour[1].x == 400 and newcontour[1].y == 0
    assert newcontour[2].x == 400 and newcontour[2].y == 400
    assert newcontour[3].x == 100 and newcontour[3].y == 400

    philter = EraseOpenCornersFilter(include={"doubleCornerGlyph.reversed"})
    assert not philter(font)


# In this, the corner point of the contour is at array index 0, so we
# need to wrap around the array indexes.
def test_double_corner_glyph_wrap(font):
    philter = EraseOpenCornersFilter(include={"doubleCornerGlyphTrickyBitInMiddle"})
    assert philter(font)

    newcontour = font["doubleCornerGlyphTrickyBitInMiddle"][0]
    assert len(newcontour) == 4
    assert newcontour[0].x == 100 and newcontour[0].y == 400
    assert newcontour[1].x == 100 and newcontour[1].y == 0
    assert newcontour[2].x == 400 and newcontour[2].y == 0
    assert newcontour[3].x == 400 and newcontour[3].y == 400


def test_curve_corner(font):
    oldcontour = font["curveCorner"][0]
    assert len(oldcontour) == 9

    philter = EraseOpenCornersFilter(include={"curveCorner"})
    assert philter(font)

    newcontour = font["curveCorner"][0]
    assert len(newcontour) == 8
    assert newcontour[5].x == pytest.approx(501.81019332487494)
    assert newcontour[5].y == pytest.approx(462.5782044264)

    philter = EraseOpenCornersFilter(include={"curveCorner.reversed"})
    assert not philter(font)


def test_curve_corner_plus_square(font):
    oldcontour = font["curveCornerPlusSquare"][0]
    assert len(oldcontour) == 9

    philter = EraseOpenCornersFilter(include={"curveCornerPlusSquare"})
    assert philter(font)
    assert len(font["curveCornerPlusSquare"][1]) == 4
    newcontour = font["curveCornerPlusSquare"][0]
    assert len(newcontour) == 8
    assert newcontour[5].x == pytest.approx(501.81019332487494)
    assert newcontour[5].y == pytest.approx(462.5782044264)

    philter = EraseOpenCornersFilter(include={"curveCornerPlusSquare.reversed"})
    assert not philter(font)


def test_square_plus_curve_corner(font):
    oldcontour = font["squarePlusCurveCorner"][1]
    assert len(oldcontour) == 9

    philter = EraseOpenCornersFilter(include={"squarePlusCurveCorner"})
    assert philter(font)
    assert len(font["squarePlusCurveCorner"][0]) == 4
    newcontour = font["squarePlusCurveCorner"][1]
    assert len(newcontour) == 8
    assert newcontour[5].x == pytest.approx(501.81019332487494)
    assert newcontour[5].y == pytest.approx(462.5782044264)

    philter = EraseOpenCornersFilter(include={"squarePlusCurveCorner.reversed"})
    assert not philter(font)


def test_circle_no_overlap(font):
    oldcontour = font["dotabove-ar"][0]
    assert len(oldcontour) == 12

    philter = EraseOpenCornersFilter(include={"dotabove-ar"})
    assert not philter(font)
    newcontour = font["dotabove-ar"][0]
    assert len(newcontour) == 12
    assert oldcontour == newcontour


def test_self_loop(font):
    oldcontour = font["sofiaSans"][0]
    assert len(oldcontour) == 4

    philter = EraseOpenCornersFilter(include={"sofiaSans"})
    assert philter(font)
    newcontour = font["sofiaSans"][0]
    assert len(newcontour) == 3


def test_large_crossing(font):
    oldcontour = font["largeCrossing"][0]
    assert len(oldcontour) == 4
    philter = EraseOpenCornersFilter(include={"largeCrossing"})
    assert philter(font)
    newcontour = font["largeCrossing"][0]
    assert len(newcontour) == 3


def structure(contour):
    return [x.segmentType for x in contour]


def test_compatibility():
    font1 = Font("tests/data/EraseOpenCornersIncompatibilityTest-One.ufo")
    font2 = Font("tests/data/EraseOpenCornersIncompatibilityTest-Two.ufo")
    philter = EraseOpenCornersFilter(include={"incompatible"})
    assert philter(font1)
    assert philter(font2)
    newcontour1 = font1["incompatible"][0]
    newcontour2 = font2["incompatible"][0]
    assert len(newcontour1) == len(newcontour2)
    assert structure(newcontour1) == structure(newcontour2)


def test_compatibility2():
    font1 = Font("tests/data/EraseOpenCornersIncompatibilityTest-One.ufo")
    font2 = Font("tests/data/EraseOpenCornersIncompatibilityTest-Two.ufo")
    philter = EraseOpenCornersFilter(include={"incompatible2"})
    assert philter(font1)
    newcontour1 = font1["incompatible2"][0]
    assert philter(font2)
    newcontour2 = font2["incompatible2"][0]
    assert len(newcontour1) == len(newcontour2)
    assert structure(newcontour1) == structure(newcontour2)


def test_compatibility3():
    font1 = Font("tests/data/EraseOpenCornersIncompatibilityTest-One.ufo")
    font2 = Font("tests/data/EraseOpenCornersIncompatibilityTest-Two.ufo")
    philter = EraseOpenCornersFilter(include={"incompatible3"})

    assert philter(font1)
    newcontour1 = font1["incompatible3"][0]
    assert philter(font2)
    newcontour2 = font2["incompatible3"][0]
    assert len(newcontour1) == len(newcontour2)
    assert structure(newcontour1) == structure(newcontour2)
