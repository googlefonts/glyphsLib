# Copyright 2024 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

from glyphsLib import to_designspace, to_glyphs
from glyphsLib.builder.stat import is_stat_only_ital
from glyphsLib.classes import (
    GSAxis,
    GSFont,
    GSFontMaster,
    GSGlyph,
    GSInstance,
    GSLayer,
    InstanceType,
)


def _make_font(axes, masters, instances, variable=True):
    font = GSFont()
    font.format_version = 3
    font.familyName = "Test"
    font.axes = [GSAxis(name=name, tag=tag) for tag, name in axes]

    for name, coords in masters:
        master = GSFontMaster()
        master.name = name
        master.axes = list(coords)
        master.ascender, master.capHeight = 800, 700
        master.xHeight, master.descender = 500, -200
        font.masters.append(master)

    glyph = GSGlyph()
    glyph.name = ".notdef"
    for master in font.masters:
        layer = GSLayer()
        layer.layerId = layer.associatedMasterId = master.id
        layer.width = 500
        glyph.layers.append(layer)
    font.glyphs.append(glyph)

    for name, coords, attrs in instances:
        instance = GSInstance()
        instance.name = name
        instance.axes = list(coords)
        for key, value in attrs.items():
            if key == "customParameters":
                for param, param_value in value.items():
                    instance.customParameters[param] = param_value
            else:
                setattr(instance, key, value)
        instance.parent = font
        font.instances.append(instance)

    if variable:
        instance = GSInstance()
        instance.name = "VF"
        instance.type = InstanceType.VARIABLE
        instance.parent = font
        font.instances.append(instance)

    return font


def _labels(axis):
    return [
        (label.name, label.userValue, label.elidable, label.linkedUserValue)
        for label in axis.axisLabels or []
    ]


def _axis(doc, tag):
    return next(a for a in doc.axes if a.tag == tag)


def test_style_linked_bold_links_the_default_weight():
    def build(is_bold):
        return _make_font(
            [("wght", "Weight")],
            [("Regular", [400]), ("Bold", [700])],
            [
                ("Regular", [400], {"weight": "Regular"}),
                (
                    "Bold",
                    [700],
                    (
                        {"weight": "Bold", "isBold": is_bold, "linkStyle": "Regular"}
                        if is_bold
                        else {"weight": "Bold"}
                    ),
                ),
            ],
        )

    assert _labels(_axis(to_designspace(build(True)), "wght")) == [
        ("Regular", 400, True, 700),
        ("Bold", 700, False, None),
    ]
    assert _labels(_axis(to_designspace(build(False)), "wght")) == [
        ("Regular", 400, True, None),
        ("Bold", 700, False, None),
    ]


def test_weight_width_labels():
    font = _make_font(
        [("wght", "Weight"), ("wdth", "Width")],
        [("Regular", [400, 100]), ("Bold", [700, 100]), ("Condensed", [400, 75])],
        [
            ("Regular", [400, 100], {"weight": "Regular", "width": "Medium (normal)"}),
            ("Bold", [700, 100], {"weight": "Bold", "width": "Medium (normal)"}),
            ("Condensed", [400, 75], {"weight": "Regular", "width": "Condensed"}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, None),
        ("Bold", 700, False, None),
    ]
    assert _labels(_axis(doc, "wdth")) == [
        ("Condensed", 75, False, None),
        ("Normal", 100, True, None),
    ]
    # A STAT-only italic axis is always appended.
    ital = _axis(doc, "ital")
    assert is_stat_only_ital(ital)
    assert ital.values == [0]
    assert _labels(ital) == [("Roman", 0, True, 1)]


def test_style_name_used_for_every_differing_axis():
    # An instance differing from the default on more than one axis uses its whole
    # style name for all of them, not just the first.
    font = _make_font(
        [("SPAC", "Spacing"), ("MSHQ", "Mashq")],
        [("Regular", [0, 10]), ("Compact", [-100, 10]), ("High", [0, 20])],
        [("Regular", [0, 10], {}), ("Compact High", [-100, 20], {})],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "SPAC")) == [
        ("Compact High", -100, False, None),
        ("Regular", 0, True, None),
    ]
    assert _labels(_axis(doc, "MSHQ")) == [
        ("Regular", 10, True, None),
        ("Compact High", 20, False, None),
    ]


def test_multi_word_style_name_is_not_split_across_axes():
    font = _make_font(
        [("wght", "Weight"), ("wdth", "Width")],
        [("Regular", [400, 100]), ("Bold", [700, 100]), ("Condensed", [400, 75])],
        [
            ("Regular", [400, 100], {"weight": "Regular", "width": "Medium (normal)"}),
            ("Bold Condensed", [700, 75], {"weight": "Bold", "width": "Condensed"}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, None),
        ("Bold Condensed", 700, False, None),
    ]
    assert _labels(_axis(doc, "wdth")) == [
        ("Bold Condensed", 75, False, None),
        ("Normal", 100, True, None),
    ]


def test_instance_driven_values_and_custom_axis():
    # A weight instance at a non-master coordinate (Medium at wght=500) still
    # gets a value, and a custom-axis instance name (Compact) attaches to it.
    font = _make_font(
        [("wght", "Weight"), ("SPAC", "Spacing")],
        [("Regular", [400, 0]), ("Bold", [700, 0]), ("Compact", [400, -100])],
        [
            ("Regular", [400, 0], {"weight": "Regular"}),
            ("Medium", [500, 0], {"weight": "Medium"}),
            ("Bold", [700, 0], {"weight": "Bold"}),
            ("Compact", [400, -100], {"weight": "Regular"}),
            ("Bold Compact", [700, -100], {"weight": "Bold"}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, None),
        ("Medium", 500, False, None),
        ("Bold", 700, False, None),
    ]
    assert _labels(_axis(doc, "SPAC")) == [
        ("Compact", -100, False, None),
        ("Regular", 0, True, None),
    ]


def test_non_regular_default_instance_labels_first_axis():
    # A non-Regular default instance labels the first axis; the degenerate axis
    # and the elided fallback stay "Regular".
    font = _make_font(
        [("SPAC", "Spacing"), ("MSHQ", "Mashq")],
        [("Regular", [0, 10]), ("Compact", [-100, 10])],
        [
            ("Book", [0, 10], {}),
            ("Compact", [-100, 10], {}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "SPAC")) == [
        ("Compact", -100, False, None),
        ("Book", 0, False, None),
    ]
    assert _labels(_axis(doc, "MSHQ")) == [("Regular", 10, True, None)]
    assert doc.elidedFallbackName == "Regular"


def test_default_instance_labels_first_varying_axis():
    font = _make_font(
        [("wght", "Weight"), ("wdth", "Width")],
        [("Regular", [400, 100]), ("Bold", [700, 100]), ("Condensed", [400, 75])],
        [
            ("Book", [400, 100], {"weight": "Regular", "width": "Medium (normal)"}),
            ("Condensed", [400, 75], {"weight": "Regular", "width": "Condensed"}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [("Regular", 400, True, None)]
    assert _labels(_axis(doc, "wdth")) == [
        ("Condensed", 75, False, None),
        ("Book", 100, False, None),
    ]


def test_elided_fallback_name_is_always_regular():
    # Even when the default instance is a style-linked Bold.
    font = _make_font(
        [("wght", "Weight")],
        [("Regular", [400]), ("Black", [900])],
        [
            ("Bold", [400], {"isBold": True}),
            ("Black", [900], {}),
        ],
    )
    doc = to_designspace(font)

    assert doc.elidedFallbackName == "Regular"


def test_style_name_is_used_as_is():
    # Style names are used as-is, only the default coordinate is elided.
    font = _make_font(
        [("wght", "Weight")],
        [("Regular", [400]), ("Bold", [700])],
        [
            ("Regular", [400], {"weight": "Regular"}),
            ("Zzz", [600], {"weight": "SemiBold"}),
            ("Bold", [700], {"weight": "Bold"}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, None),
        ("Zzz", 600, False, None),
        ("Bold", 700, False, None),
    ]


def test_no_variable_font_instance_gets_no_stat():
    # Build STAT only for variable fonts.
    font = _make_font(
        [("wght", "Weight")],
        [("Regular", [400]), ("Bold", [700])],
        [
            ("Regular", [400], {"weight": "Regular"}),
            ("Bold", [700], {"weight": "Bold"}),
        ],
        variable=False,
    )
    doc = to_designspace(font)

    assert not any(a.axisLabels for a in doc.axes)
    assert not any(a.tag == "ital" for a in doc.axes)


def test_export_stat_table_off_disables_stat():
    font = _make_font(
        [("wght", "Weight")],
        [("Regular", [400]), ("Bold", [700])],
        [
            ("Regular", [400], {"weight": "Regular"}),
            ("Bold", [700], {"weight": "Bold"}),
        ],
    )
    font.instances[-1].customParameters["Export STAT Table"] = 0

    doc = to_designspace(font)
    assert not any(a.axisLabels for a in doc.axes)
    assert not any(a.tag == "ital" for a in doc.axes)


def test_export_stat_table_off_on_only_one_variable_font_keeps_stat():
    font = _make_font(
        [("wght", "Weight")],
        [("Regular", [400]), ("Bold", [700])],
        [
            ("Regular", [400], {"weight": "Regular"}),
            ("Bold", [700], {"weight": "Bold"}),
        ],
    )
    font.instances[-1].customParameters["Export STAT Table"] = 0
    other = GSInstance()
    other.name = "VF2"
    other.type = InstanceType.VARIABLE
    other.parent = font
    font.instances.append(other)

    doc = to_designspace(font)
    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, None),
        ("Bold", 700, False, None),
    ]


def test_elidable_stat_axis_value_name_param():
    font = _make_font(
        [("wght", "Weight")],
        [("Regular", [400]), ("Bold", [700])],
        [
            ("Regular", [400], {"weight": "Regular"}),
            (
                "Bold",
                [700],
                {
                    "weight": "Bold",
                    "customParameters": {"Elidable STAT Axis Value Name": "wght"},
                },
            ),
        ],
    )
    doc = to_designspace(font)

    # Bold at wght=700 is normally not elidable, the parameter marks it elidable.
    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, None),
        ("Bold", 700, True, None),
    ]


def test_elidable_default_still_links_to_the_style_linked_bold():
    font = _make_font(
        [("wght", "Weight")],
        [("Regular", [400]), ("Bold", [700])],
        [
            (
                "Book",
                [400],
                {
                    "weight": "Regular",
                    "customParameters": {"Elidable STAT Axis Value Name": "wght"},
                },
            ),
            ("Bold", [700], {"weight": "Bold", "isBold": True, "linkStyle": "Regular"}),
        ],
    )
    doc = to_designspace(font)

    # The default value is named “Book”, but the parameter elides it, so Glyphs
    # still pairs it with the bold.
    assert _labels(_axis(doc, "wght")) == [
        ("Book", 400, True, 700),
        ("Bold", 700, False, None),
    ]


def test_style_name_as_stat_entry_manual_mode():
    # The parameter on any instance disables automatic derivation.
    font = _make_font(
        [("wght", "Weight"), ("wdth", "Width")],
        [("Regular", [400, 100]), ("Bold", [700, 100]), ("Condensed", [400, 75])],
        [
            ("Regular", [400, 100], {"weight": "Regular", "width": "Medium (normal)"}),
            (
                "Bold",
                [700, 100],
                {
                    "weight": "Bold",
                    "width": "Medium (normal)",
                    "customParameters": {"Style Name as STAT entry": "wght"},
                },
            ),
            ("Condensed", [400, 75], {"weight": "Regular", "width": "Condensed"}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [("Bold", 700, False, None)]
    assert not _axis(doc, "wdth").axisLabels
    # The STAT-only italic axis is still appended in manual mode.
    assert _labels(_axis(doc, "ital")) == [("Roman", 0, True, 1)]


def test_real_italic_axis_suppresses_stat_only_and_links_upright():
    font = _make_font(
        [("wght", "Weight"), ("ital", "Italic")],
        [
            ("Regular", [400, 0]),
            ("Bold", [700, 0]),
            ("Italic", [400, 1]),
            ("Bold Italic", [700, 1]),
        ],
        [
            ("Regular", [400, 0], {"weight": "Regular"}),
            ("Bold", [700, 0], {"weight": "Bold"}),
            ("Italic", [400, 1], {"weight": "Regular"}),
            ("Bold Italic", [700, 1], {"weight": "Bold"}),
        ],
    )
    doc = to_designspace(font)

    # Exactly one italic axis, the real one.
    itals = [a for a in doc.axes if a.tag == "ital"]
    assert len(itals) == 1
    assert not is_stat_only_ital(itals[0])
    # The upright value links to the italic value.
    assert _labels(itals[0]) == [("Regular", 0, True, 1), ("Italic", 1, False, None)]


def test_italic_family_gets_the_italic_axis_value():
    font = _make_font(
        [("wght", "Weight")],
        [("Italic", [400]), ("Bold Italic", [700])],
        [
            ("Italic", [400], {"weight": "Regular", "isItalic": True}),
            (
                "Bold Italic",
                [700],
                {"weight": "Bold", "isItalic": True, "isBold": True},
            ),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "ital")) == [("Italic", 1, False, None)]
    assert doc.elidedFallbackName == "Regular"


def test_italic_family_detected_from_style_name():
    # No italic flag on either instance.
    font = _make_font(
        [("wght", "Weight")],
        [("Italic", [400]), ("Bold Italic", [700])],
        [
            ("Italic", [400], {"weight": "Regular"}),
            ("Bold Italic", [700], {"weight": "Bold"}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "ital")) == [("Italic", 1, False, None)]


def test_italic_family_labels_drop_the_italic_word():
    font = _make_font(
        [("wght", "Weight")],
        [("Italic", [400]), ("Bold Italic", [700]), ("Black Italic", [900])],
        [
            ("Italic", [400], {"weight": "Regular", "isItalic": True}),
            (
                "Bold Italic",
                [700],
                {"weight": "Bold", "isItalic": True, "isBold": True},
            ),
            ("Black Italic", [900], {"weight": "Black", "isItalic": True}),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, 700),
        ("Bold", 700, False, None),
        ("Black", 900, False, None),
    ]


def test_italic_family_labels_keep_a_named_default():
    # The default instance is "Book Italic", not the bare "Italic".
    font = _make_font(
        [("wght", "Weight")],
        [("Book Italic", [400]), ("Bold Italic", [700])],
        [
            ("Book Italic", [400], {"weight": "Regular", "isItalic": True}),
            (
                "Bold Italic",
                [700],
                {"weight": "Bold", "isItalic": True, "isBold": True},
            ),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [
        ("Book Italic", 400, False, None),
        ("Bold Italic", 700, False, None),
    ]


def test_style_linked_bold_links_from_another_axis_position():
    # The bold sits off the default width.
    font = _make_font(
        [("wght", "Weight"), ("wdth", "Width")],
        [("Regular", [400, 100]), ("Bold", [700, 100]), ("Condensed", [400, 75])],
        [
            ("Regular", [400, 100], {"weight": "Regular"}),
            (
                "Bold Condensed",
                [700, 75],
                {"weight": "Bold", "width": "Condensed", "isBold": True},
            ),
        ],
    )
    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, 700),
        ("Bold Condensed", 700, False, None),
    ]


def test_axis_location_uses_user_space_values():
    # Design coordinates 0..100 map to user 400..700 via “Axis Location”, the STAT
    # values must be in user space to match fvar.
    font = _make_font(
        [("wght", "Weight")],
        [("Regular", [0]), ("Bold", [100])],
        [
            ("Regular", [0], {"weight": "Regular"}),
            ("Bold", [100], {"weight": "Bold"}),
        ],
    )
    locations = {0: 400, 100: 700}
    for owner in list(font.masters) + list(font.instances):
        owner.customParameters["Axis Location"] = [
            {"Axis": "Weight", "Location": locations[owner.axes[0]]}
        ]

    doc = to_designspace(font)

    assert _labels(_axis(doc, "wght")) == [
        ("Regular", 400, True, None),
        ("Bold", 700, False, None),
    ]


@pytest.mark.parametrize("style, italic", [("Regular", False), ("Italic", True)])
def test_stat_only_italic_does_not_roundtrip_to_glyphs(style, italic):
    font = _make_font(
        [("wght", "Weight")],
        [(style, [400]), ("Bold " + style, [700])],
        [
            (style, [400], {"weight": "Regular", "isItalic": italic}),
            ("Bold " + style, [700], {"weight": "Bold", "isItalic": italic}),
        ],
    )
    doc = to_designspace(font)
    assert _axis(doc, "ital").values == [1 if italic else 0]

    roundtripped = to_glyphs(doc)
    assert "ital" not in [a.axisTag for a in roundtripped.axes]
