import pytest

from glyphsLib.classes import GSFont, GSFontMaster, GSGlyph, GSLayer
from glyphsLib.builder.transformations.resolve_reverse_bracket_layers import (
    resolve_reverse_bracket_layers,
)

MIN_100 = [{"min": 100}]
MAX_50 = [{"max": 50}]
BLANK = [{}]


def make_font(layers):
    """Build a font with masters M1, M2 and one glyph with the given layers.

    Each layer is (layerId, associatedMasterId, attributes).
    """
    font = GSFont()
    font.format_version = 3
    for master_id in ("M1", "M2"):
        master = GSFontMaster()
        master.id = master_id
        font.masters.append(master)
    glyph = GSGlyph("a")
    font.glyphs.append(glyph)
    for layer_id, master_id, attributes, *part_selection in layers:
        layer = GSLayer()
        if part_selection:
            layer.partSelection = part_selection[0]
        layer.layerId = layer_id
        layer.associatedMasterId = master_id
        layer.attributes = dict(attributes)
        # remember which layer object ended up where
        layer.userData["origin"] = layer_id
        glyph.layers.append(layer)
    return font


def layer_summary(font):
    return sorted(
        (
            layer.layerId,
            layer.associatedMasterId,
            layer.userData["origin"],
            layer.attributes.get("axisRules"),
        )
        for layer in font.glyphs["a"].layers
    )


def test_swap_in_every_master():
    font = make_font(
        [
            ("M1", "M1", {"axisRules": MIN_100}),
            ("M2", "M2", {"axisRules": MIN_100}),
            ("B1", "M1", {"axisRules": BLANK}),
            ("X1", "M1", {"axisRules": MAX_50}),
            ("B2", "M2", {"axisRules": BLANK}),
        ]
    )
    resolve_reverse_bracket_layers(font)
    assert layer_summary(font) == [
        ("B1", "M1", "M1", MIN_100),
        ("B2", "M2", "M2", MIN_100),
        ("M1", "M1", "B1", None),
        ("M2", "M2", "B2", None),
        ("X1", "M1", "X1", MAX_50),
    ]
    assert font.glyphs["a"].layers["M1"].userData["origin"] == "B1"


def test_swap_multiple_axes():
    font = make_font(
        [
            ("M1", "M1", {"axisRules": [{"min": 100}, {}]}),
            ("B1", "M1", {"axisRules": [{}, {}]}),
            ("M2", "M2", {}),
        ]
    )
    resolve_reverse_bracket_layers(font)
    assert layer_summary(font)[:2] == [
        ("B1", "M1", "M1", [{"min": 100}, {}]),
        ("M1", "M1", "B1", None),
    ]


@pytest.mark.parametrize(
    "layers, expected",
    [
        pytest.param(
            [("M1", "M1", {}), ("B1", "M1", {"axisRules": BLANK})],
            [("B1", "M1", "B1", None), ("M1", "M1", "M1", None)],
            id="master-without-rules",
        ),
        pytest.param(
            [("B1", "M1", {"axisRules": BLANK}), ("M1", "M1", {"axisRules": BLANK})],
            [("B1", "M1", "B1", None), ("M1", "M1", "M1", None)],
            id="blank-alternate-stored-first",
        ),
        pytest.param(
            [
                ("M1", "M1", {"axisRules": MIN_100}),
                ("B1", "M1", {"axisRules": BLANK}),
                ("B2", "M1", {"axisRules": BLANK}),
            ],
            [
                ("B1", "M1", "B1", None),
                ("B2", "M1", "B2", None),
                ("M1", "M1", "M1", MIN_100),
            ],
            id="two-blank-alternates",
        ),
    ],
)
def test_ignore_blank_alternates(layers, expected):
    # the layers are kept, without axis rules
    font = make_font(layers + [("M2", "M2", {})])
    resolve_reverse_bracket_layers(font)
    assert layer_summary(font) == expected + [("M2", "M2", "M2", None)]


@pytest.mark.parametrize(
    "layers",
    [
        pytest.param(
            [
                ("M1", "M1", {"axisRules": MIN_100}),
                ("X1", "M1", {"axisRules": MAX_50}),
            ],
            id="bounded-sibling-only",
        ),
        pytest.param(
            [
                ("M1", "M1", {"axisRules": MIN_100}),
                ("B1", "M1", {"axisRules": BLANK, "coordinates": [75]}),
            ],
            id="blank-sibling-is-brace-layer",
        ),
        pytest.param(
            [
                ("M1", "M1", {"axisRules": MIN_100}),
                ("B1", "M1", {"axisRules": []}),
            ],
            id="sibling-with-empty-rule-list",
        ),
        pytest.param(
            [
                ("M1", "M1", {}),
                ("B1", "M1", {"axisRules": BLANK}, {"Width": 2}),
            ],
            id="blank-sibling-is-smart-component-layer",
        ),
    ],
)
def test_untouched(layers):
    font = make_font(layers + [("M2", "M2", {})])
    before = layer_summary(font)
    resolve_reverse_bracket_layers(font)
    assert layer_summary(font) == before
