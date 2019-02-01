# coding=UTF-8
#
# Copyright 2017 Google Inc. All Rights Reserved.
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

from __future__ import print_function, division, absolute_import, unicode_literals
import os
from xmldiff import main, formatting

import pytest
import defcon

import glyphsLib
from glyphsLib import to_designspace, to_glyphs


def test_designspace_generation_regular_same_family_name(tmpdir):
    ufo_Lt = defcon.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Lt.info.styleName = "Light"
    ufo_Lt.info.openTypeOS2WeightClass = 300

    ufo_Rg = defcon.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular"
    ufo_Rg.info.openTypeOS2WeightClass = 400

    ufo_Md = defcon.Font()
    ufo_Md.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Md.info.styleName = "Medium"
    ufo_Md.info.openTypeOS2WeightClass = 500

    ufo_Bd = defcon.Font()
    ufo_Bd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Bd.info.styleName = "Bold"
    ufo_Bd.info.openTypeOS2WeightClass = 700

    ufo_ExBd = defcon.Font()
    ufo_ExBd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_ExBd.info.styleName = "XBold"
    ufo_ExBd.info.openTypeOS2WeightClass = 800

    font = to_glyphs([ufo_Lt, ufo_Rg, ufo_Md, ufo_Bd, ufo_ExBd])
    designspace = to_designspace(font)

    path = os.path.join(str(tmpdir), "actual.designspace")
    designspace.write(path)

    expected_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "DesignspaceGenTestRegular.designspace"
    )

    assert (
        len(main.diff_files(path, expected_path, formatter=formatting.DiffFormatter()))
        == 0
    )


def test_designspace_generation_italic_same_family_name(tmpdir):
    ufo_Lt = defcon.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Lt.info.styleName = "Light Italic"
    ufo_Lt.info.openTypeOS2WeightClass = 300
    ufo_Lt.info.italicAngle = -11

    ufo_Rg = defcon.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular Italic"
    ufo_Rg.info.openTypeOS2WeightClass = 400
    ufo_Rg.info.italicAngle = -11

    ufo_Md = defcon.Font()
    ufo_Md.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Md.info.styleName = "Medium Italic"
    ufo_Md.info.openTypeOS2WeightClass = 500
    ufo_Md.info.italicAngle = -11

    ufo_Bd = defcon.Font()
    ufo_Bd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Bd.info.styleName = "Bold Italic"
    ufo_Bd.info.openTypeOS2WeightClass = 700
    ufo_Bd.info.italicAngle = -11

    ufo_ExBd = defcon.Font()
    ufo_ExBd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_ExBd.info.styleName = "XBold Italic"
    ufo_ExBd.info.openTypeOS2WeightClass = 800
    ufo_ExBd.info.italicAngle = -11

    font = to_glyphs([ufo_Lt, ufo_Rg, ufo_Md, ufo_Bd, ufo_ExBd])
    designspace = to_designspace(font)

    path = os.path.join(str(tmpdir), "actual.designspace")
    designspace.write(path)

    expected_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "DesignspaceGenTestItalic.designspace"
    )

    assert (
        len(main.diff_files(path, expected_path, formatter=formatting.DiffFormatter()))
        == 0
    )


def test_designspace_generation_regular_different_family_names(tmpdir):
    ufo_Lt = defcon.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif Light"
    ufo_Lt.info.styleName = "Regular"
    ufo_Lt.info.openTypeOS2WeightClass = 300

    ufo_Rg = defcon.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular"
    ufo_Rg.info.openTypeOS2WeightClass = 400

    # Different family names are not allowed
    # REVIEW: reasonable requirement?
    with pytest.raises(Exception):
        to_glyphs([ufo_Lt, ufo_Rg])


def test_designspace_generation_same_weight_name(tmpdir):
    ufo_Bd = defcon.Font()
    ufo_Bd.info.familyName = "Test"
    ufo_Bd.info.styleName = "Bold"

    ufo_ExBd = defcon.Font()
    ufo_ExBd.info.familyName = "Test"
    ufo_ExBd.info.styleName = "Bold"

    ufo_XExBd = defcon.Font()
    ufo_XExBd.info.familyName = "Test"
    ufo_XExBd.info.styleName = "Bold"

    font = to_glyphs([ufo_Bd, ufo_ExBd, ufo_XExBd])
    designspace = to_designspace(font)

    assert designspace.sources[0].filename != designspace.sources[1].filename
    assert designspace.sources[1].filename != designspace.sources[2].filename
    assert designspace.sources[0].filename != designspace.sources[2].filename


def test_designspace_generation_brace_layers(datadir):
    with open(str(datadir.join("BraceTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)
    designspace = to_designspace(font)

    axes_order = [
        (a.name, a.minimum, a.default, a.maximum, a.map) for a in designspace.axes
    ]
    assert axes_order == [
        ("Width", 75, 100, 100, [(75, 50.0), (100, 100.0)]),
        ("Weight", 100, 100, 700, [(100, 100.0), (700, 1000.0)]),
    ]

    source_order = [(s.filename, s.layerName, s.name) for s in designspace.sources]
    assert source_order == [
        ("NewFont-Light.ufo", None, "New Font Light"),
        ("NewFont-Light.ufo", "{75}", "New Font Light {75}"),
        ("NewFont-Bold.ufo", None, "New Font Bold"),
        ("NewFont-Bold.ufo", "{75}", "New Font Bold {75}"),
        ("NewFont-Bold.ufo", "Test2 {90, 500}", "New Font Bold Test2 {90, 500}"),
        ("NewFont-Bold.ufo", "Test1 {90, 600}", "New Font Bold Test1 {90, 600}"),
        ("NewFont-CondensedLight.ufo", None, "New Font Condensed Light"),
        ("NewFont-CondensedBold.ufo", None, "New Font Condensed Bold"),
    ]

    # Check that all sources have a font object attached and sources with the same
    # filename have the same font object attached.
    masters = {}
    for source in designspace.sources:
        assert source.font
        if source.filename in masters:
            assert masters[source.filename] is source.font
        masters[source.filename] = source.font


def test_designspace_generation_instances(datadir):
    with open(str(datadir.join("BraceTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)
    designspace = to_designspace(font)

    instances_order = [
        (i.name, i.styleMapStyleName, i.location) for i in designspace.instances
    ]
    assert instances_order == [
        ("New Font Thin", "regular", {"Width": 100.0, "Weight": 100.0}),
        ("New Font Regular", "regular", {"Width": 100.0, "Weight": 500.0}),
        ("New Font Bold", "bold", {"Width": 100.0, "Weight": 1000.0}),
        ("New Font Semi Consensed", "regular", {"Width": 75.0, "Weight": 500.0}),
        ("New Font Thin Condensed", "regular", {"Width": 50.0, "Weight": 100.0}),
        ("New Font Condensed", "regular", {"Width": 50.0, "Weight": 500.0}),
        ("New Font Bold Condensed", "bold", {"Width": 50.0, "Weight": 1000.0}),
    ]


def test_designspace_generation_on_disk(datadir, tmpdir):
    glyphsLib.build_masters(str(datadir.join("BraceTestFont.glyphs")), str(tmpdir))

    ufo_paths = list(tmpdir.visit(fil="*.ufo"))
    assert len(ufo_paths) == 4  # Source layers should not be written to disk.
    for ufo_path in ufo_paths:
        ufo = defcon.Font(str(ufo_path))
        # Check that all glyphs have contours (brace layers are in "b" only, writing
        # the brace layer to disk would result in empty other glyphs).
        for layer in ufo.layers:
            for glyph in layer:
                if glyph.name == "space":
                    assert not glyph
                else:
                    assert glyph


def test_designspace_generation_bracket_roundtrip(datadir):
    with open(str(datadir.join("BracketTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)
    designspace = to_designspace(font)

    assert designspace.rules[0].name == "BRACKET.300.600"
    assert designspace.rules[0].conditionSets == [
        [dict(name="Weight", minimum=300, maximum=600)]
    ]
    assert designspace.rules[0].subs == [("x", "x.BRACKET.300")]

    assert designspace.rules[1].name == "BRACKET.300.1000"
    assert designspace.rules[1].conditionSets == [
        [dict(name="Weight", minimum=300, maximum=1000)]
    ]
    assert designspace.rules[1].subs == [("a", "a.BRACKET.300")]

    assert designspace.rules[2].name == "BRACKET.600.1000"
    assert designspace.rules[2].conditionSets == [
        [dict(name="Weight", minimum=600, maximum=1000)]
    ]
    assert designspace.rules[2].subs == [("x", "x.BRACKET.600")]

    for source in designspace.sources:
        assert "[300]" not in source.font.layers
        assert "Something [300]" not in source.font.layers
        assert "[600]" not in source.font.layers
        assert "Other [600]" not in source.font.layers
        g1 = source.font["x.BRACKET.300"]
        assert not g1.unicodes
        g2 = source.font["x.BRACKET.600"]
        assert not g2.unicodes

    font_rt = to_glyphs(designspace)
    assert "x" in font_rt.glyphs
    g1 = font_rt.glyphs["x"]
    assert len(g1.layers) == 12 and {l.name for l in g1.layers} == {
        "[300]",
        "[600]",
        "Bold",
        "Condensed Bold",
        "Condensed Light",
        "Light",
        "Other [600]",
        "Something [300]",
    }
    g2 = font_rt.glyphs["a"]
    assert len(g2.layers) == 8 and {l.name for l in g2.layers} == {
        "[300]",
        "Bold",
        "Condensed Bold",
        "Condensed Light",
        "Light",
    }
    assert "a.BRACKET.300" not in font_rt.glyphs
    assert "x.BRACKET.300" not in font_rt.glyphs
    assert "x.BRACKET.600" not in font_rt.glyphs


def test_designspace_generation_bracket_unbalanced_brackets(datadir):
    with open(str(datadir.join("BracketTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)

    # Delete the "Other [600]" layer to unbalance bracket layers.
    del font.glyphs["x"].layers["C5C3CA59-C2D0-46F6-B5D3-86541DE36ACB"]
    with pytest.raises(ValueError) as excinfo:
        to_designspace(font)
    assert "bracket layer(s) missing" in str(excinfo)

    # Delete the other [600] layers to rebalance.
    del font.glyphs["x"].layers["E729A72D-C6FF-4DDD-ADA1-BB5B6FD7E3DD"]
    del font.glyphs["x"].layers["F5778F4C-2B04-4030-9D7D-09E3C951C089"]
    del font.glyphs["x"].layers["24328DA8-2CE1-4D0A-9C91-214ED36F6393"]
    assert to_designspace(font)
