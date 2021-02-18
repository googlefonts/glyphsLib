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
                        ("lineTo", ((198, 360),)),
                        ("lineTo", ((60, 353),)),
                        ("lineTo", ((179, 0),)),
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
    return font


def test_empty_glyph(font):
    philter = EraseOpenCornersFilter(include={"space"})
    assert not philter(font)


def test_corner_glyph(font):
    philter = EraseOpenCornersFilter(include={"hasCornerGlyph"})
    assert philter(font)

    newcontour = font["hasCornerGlyph"][0]
    assert len(newcontour) == 3
    assert newcontour[1].x == pytest.approx(114.5417)
    assert newcontour[1].y == pytest.approx(191.2080)


def test_curve_curve_glyph(font):
    philter = EraseOpenCornersFilter(include={"curvyCornerGlyph"})
    assert philter(font)

    newcontour = font["curvyCornerGlyph"][0]
    assert len(newcontour) == 7
    assert newcontour[0].x == pytest.approx(406.4859)
    assert newcontour[0].y == pytest.approx(104.5666)


def test_double_corner_glyph(font):
    philter = EraseOpenCornersFilter(include={"doubleCornerGlyph"})
    assert philter(font)

    newcontour = font["doubleCornerGlyph"][0]
    assert len(newcontour) == 4
    assert newcontour[0].x == 100 and newcontour[0].y == 0
    assert newcontour[1].x == 400 and newcontour[1].y == 0
    assert newcontour[2].x == 400 and newcontour[2].y == 400
    assert newcontour[3].x == 100 and newcontour[3].y == 400


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
