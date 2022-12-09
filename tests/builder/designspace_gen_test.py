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


import os
from fontTools.designspaceLib import DesignSpaceDocument
from xmldiff import main, formatting
from fontTools.varLib import FEAVAR_FEATURETAG_LIB_KEY

import itertools
import pytest

import glyphsLib
from glyphsLib import to_designspace, to_glyphs
from glyphsLib.util import open_ufo


def test_designspace_generation_regular_same_family_name(tmpdir, ufo_module):
    ufo_Lt = ufo_module.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Lt.info.styleName = "Light"
    ufo_Lt.info.openTypeOS2WeightClass = 300

    ufo_Rg = ufo_module.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular"
    ufo_Rg.info.openTypeOS2WeightClass = 400

    ufo_Md = ufo_module.Font()
    ufo_Md.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Md.info.styleName = "Medium"
    ufo_Md.info.openTypeOS2WeightClass = 500

    ufo_Bd = ufo_module.Font()
    ufo_Bd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Bd.info.styleName = "Bold"
    ufo_Bd.info.openTypeOS2WeightClass = 700

    ufo_ExBd = ufo_module.Font()
    ufo_ExBd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_ExBd.info.styleName = "XBold"
    ufo_ExBd.info.openTypeOS2WeightClass = 800

    font = to_glyphs([ufo_Lt, ufo_Rg, ufo_Md, ufo_Bd, ufo_ExBd])
    designspace = to_designspace(font, ufo_module=ufo_module)

    path = os.path.join(str(tmpdir), "actual.designspace")
    designspace.write(path)

    expected_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "DesignspaceGenTestRegular.designspace"
    )

    assert (
        len(main.diff_files(path, expected_path, formatter=formatting.DiffFormatter()))
        == 0
    )


def test_designspace_generation_italic_same_family_name(tmpdir, ufo_module):
    ufo_Lt = ufo_module.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Lt.info.styleName = "Light Italic"
    ufo_Lt.info.openTypeOS2WeightClass = 300
    ufo_Lt.info.italicAngle = -11

    ufo_Rg = ufo_module.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular Italic"
    ufo_Rg.info.openTypeOS2WeightClass = 400
    ufo_Rg.info.italicAngle = -11

    ufo_Md = ufo_module.Font()
    ufo_Md.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Md.info.styleName = "Medium Italic"
    ufo_Md.info.openTypeOS2WeightClass = 500
    ufo_Md.info.italicAngle = -11

    ufo_Bd = ufo_module.Font()
    ufo_Bd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Bd.info.styleName = "Bold Italic"
    ufo_Bd.info.openTypeOS2WeightClass = 700
    ufo_Bd.info.italicAngle = -11

    ufo_ExBd = ufo_module.Font()
    ufo_ExBd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_ExBd.info.styleName = "XBold Italic"
    ufo_ExBd.info.openTypeOS2WeightClass = 800
    ufo_ExBd.info.italicAngle = -11

    font = to_glyphs([ufo_Lt, ufo_Rg, ufo_Md, ufo_Bd, ufo_ExBd])
    designspace = to_designspace(font, ufo_module=ufo_module)

    path = os.path.join(str(tmpdir), "actual.designspace")
    designspace.write(path)

    expected_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "DesignspaceGenTestItalic.designspace"
    )

    assert (
        len(main.diff_files(path, expected_path, formatter=formatting.DiffFormatter()))
        == 0
    )


def test_designspace_generation_regular_different_family_names(tmpdir, ufo_module):
    ufo_Lt = ufo_module.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif Light"
    ufo_Lt.info.styleName = "Regular"
    ufo_Lt.info.openTypeOS2WeightClass = 300

    ufo_Rg = ufo_module.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular"
    ufo_Rg.info.openTypeOS2WeightClass = 400

    # Different family names are not allowed
    # REVIEW: reasonable requirement?
    with pytest.raises(Exception):
        to_glyphs([ufo_Lt, ufo_Rg])


def test_designspace_generation_same_weight_name(tmpdir, ufo_module):
    ufo_Bd = ufo_module.Font()
    ufo_Bd.info.familyName = "Test"
    ufo_Bd.info.styleName = "Bold"

    ufo_ExBd = ufo_module.Font()
    ufo_ExBd.info.familyName = "Test"
    ufo_ExBd.info.styleName = "Bold"

    ufo_XExBd = ufo_module.Font()
    ufo_XExBd.info.familyName = "Test"
    ufo_XExBd.info.styleName = "Bold"

    font = to_glyphs([ufo_Bd, ufo_ExBd, ufo_XExBd])
    designspace = to_designspace(font, ufo_module=ufo_module)

    assert designspace.sources[0].filename != designspace.sources[1].filename
    assert designspace.sources[1].filename != designspace.sources[2].filename
    assert designspace.sources[0].filename != designspace.sources[2].filename


@pytest.mark.parametrize("filename", ["BraceTestFont.glyphs", "BraceTestFontV3.glyphs"])
def test_designspace_generation_brace_layers(datadir, filename, ufo_module):
    with open(str(datadir.join(filename))) as f:
        font = glyphsLib.load(f)
    designspace = to_designspace(font, ufo_module=ufo_module, minimal=True)

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
        ("NewFont-Bold.ufo", "Test2 {90.5, 500}", "New Font Bold Test2 {90.5, 500}"),
        ("NewFont-Bold.ufo", "Test1 {90.5, 600}", "New Font Bold Test1 {90.5, 600}"),
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

    # Check that brace layer glyph is created
    assert len(designspace.sources[0].font.layers) == 2


@pytest.mark.parametrize("filename", ["BraceTestFont.glyphs", "BraceTestFontV3.glyphs"])
def test_designspace_generation_instances(datadir, filename, ufo_module):
    with open(str(datadir.join(filename))) as f:
        font = glyphsLib.load(f)
    designspace = to_designspace(font, ufo_module=ufo_module)

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


@pytest.mark.parametrize("filename", ["BraceTestFont.glyphs", "BraceTestFontV3.glyphs"])
def test_designspace_generation_on_disk(datadir, tmpdir, filename, ufo_module):
    glyphsLib.build_masters(str(datadir.join(filename)), str(tmpdir))

    ufo_paths = list(tmpdir.visit(fil="*.ufo"))
    assert len(ufo_paths) == 4  # Source layers should not be written to disk.
    for ufo_path in ufo_paths:
        ufo = open_ufo(ufo_path, ufo_module.Font)

        # Check that all glyphs have contours (brace layers are in "b" only, writing
        # the brace layer to disk would result in empty other glyphs).
        for layer in ufo.layers:
            for glyph in layer:
                if glyph.name == "space":
                    assert not glyph
                else:
                    assert glyph


def test_designspace_generation_bracket_roundtrip(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)
    designspace = to_designspace(font, ufo_module=ufo_module)

    assert designspace.rules[0].name == "BRACKET.Weight_600_1000"
    assert designspace.rules[0].conditionSets == [
        [dict(name="Weight", minimum=600, maximum=1000)]
    ]
    assert sorted(designspace.rules[0].subs) == [
        ("a", "a.BRACKET.varAlt01"),
        ("x", "x.BRACKET.varAlt02"),
    ]

    assert designspace.rules[1].name == "BRACKET.Weight_300_600"
    assert designspace.rules[1].conditionSets == [
        [dict(name="Weight", minimum=300, maximum=600)]
    ]
    assert sorted(designspace.rules[1].subs) == [
        ("a", "a.BRACKET.varAlt01"),
        ("x", "x.BRACKET.varAlt01"),
    ]

    for source in designspace.sources:
        assert "[300]" not in source.font.layers
        assert "Something [300]" not in source.font.layers
        assert "[600]" not in source.font.layers
        assert "Other [600]" not in source.font.layers
        g1 = source.font["x.BRACKET.varAlt01"]
        assert not g1.unicodes
        g2 = source.font["x.BRACKET.varAlt02"]
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


def test_designspace_generation_bracket_roundtrip_psnames(datadir, ufo_module):
    with open(str(datadir.join("PSNames.glyphs"))) as f:
        font = glyphsLib.load(f)
    designspace: DesignSpaceDocument = to_designspace(font, ufo_module=ufo_module)

    assert designspace.findDefault().font.lib["public.postscriptNames"] == {
        "a-cy": "uni0430",
        "a-cy.BRACKET.varAlt01": "uni0430.BRACKET.varAlt01",
        "a-cy.alt": "uni0430.alt",
    }

    font_rt = to_glyphs(designspace)
    designspace_rt = to_designspace(font_rt, ufo_module=ufo_module)

    assert designspace_rt.findDefault().font.lib["public.postscriptNames"] == {
        "a-cy": "uni0430",
        "a-cy.BRACKET.varAlt01": "uni0430.BRACKET.varAlt01",
        "a-cy.alt": "uni0430.alt",
    }

    font_rt2 = to_glyphs(designspace_rt)
    designspace_rt2 = to_designspace(font_rt2, ufo_module=ufo_module)

    assert designspace_rt2.findDefault().font.lib["public.postscriptNames"] == {
        "a-cy": "uni0430",
        "a-cy.BRACKET.varAlt01": "uni0430.BRACKET.varAlt01",
        "a-cy.alt": "uni0430.alt",
    }


@pytest.mark.xfail
def test_designspace_generation_bracket_roundtrip_no_layername(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)

    # Remove brace layers for clean slate.
    master_ids = {m.id for m in font.masters}
    for g in font.glyphs:
        dl = [l for l in g.layers if l.layerId not in master_ids]
        for l in dl:
            g.layers.remove(l)

    designspace = to_designspace(font, ufo_module=ufo_module)
    for source in designspace.sources:
        source.font.newGlyph("b.BRACKET.100")

    font_rt = to_glyphs(designspace)
    for layer in font_rt.glyphs["b"].layers:
        if layer.layerId not in master_ids:
            assert layer.name == "[100]"


def test_designspace_generation_bracket_unbalanced_brackets(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont2.glyphs"))) as f:
        font = glyphsLib.load(f)

    layer_names = {l.name for l in font.glyphs["C"].layers}
    assert layer_names == {"Regular", "Bold", "Bold [600]"}

    designspace = to_designspace(font, ufo_module=ufo_module)

    for source in designspace.sources:
        assert "C.BRACKET.varAlt01" in source.font

    font_rt = to_glyphs(designspace)

    assert "C" in font_rt.glyphs

    assert {l.name for l in font_rt.glyphs["C"].layers} == layer_names
    assert "C.BRACKET.varAlt01" not in font_rt.glyphs


def test_designspace_generation_bracket_composite_glyph(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont2.glyphs"))) as f:
        font = glyphsLib.load(f)

    g = font.glyphs["B"]
    for layer in g.layers:
        assert layer.components[0].name == "A"

    designspace = to_designspace(font, ufo_module=ufo_module)

    for source in designspace.sources:
        ufo = source.font
        assert "B.BRACKET.varAlt01" in ufo
        assert ufo["B"].components[0].baseGlyph == "A"
        assert ufo["B.BRACKET.varAlt01"].components[0].baseGlyph == "A.BRACKET.varAlt01"
        # G has no alternate layers, but it uses a component
        # which does, so it too must develop some.
        assert "G.BRACKET.varAlt01" in ufo

    font_rt = to_glyphs(designspace)

    assert "B" in font_rt.glyphs

    g2 = font_rt.glyphs["B"]
    for layer in g2.layers:
        assert layer.components[0].name == "A"

    assert "B.BRACKET.600" not in font_rt.glyphs


def test_designspace_generation_reverse_bracket_roundtrip(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont2.glyphs"))) as f:
        font = glyphsLib.load(f)

    g = font.glyphs["D"]

    assert {"Regular ]600]", "Bold ]600]"}.intersection(l.name for l in g.layers)

    designspace = to_designspace(font, ufo_module=ufo_module)

    # Bottom box should include substitutions for D (400->600)
    assert designspace.rules[2].name == "BRACKET.Weight_400_570"
    assert designspace.rules[2].conditionSets == [
        [dict(name="Weight", minimum=400, maximum=570)]
    ]
    assert designspace.rules[2].subs == [
        ("D", "D.BRACKET.varAlt01"),
        ("E", "E.BRACKET.varAlt01"),
        ("F", "F.BRACKET.varAlt02"),
    ]

    for source in designspace.sources:
        ufo = source.font
        assert "D.BRACKET.varAlt01" in ufo

    font_rt = to_glyphs(designspace)

    assert "D" in font_rt.glyphs

    g2 = font_rt.glyphs["D"]
    assert {"Regular ]600]", "Bold ]600]"}.intersection(l.name for l in g2.layers)

    assert "D.BRACKET.wght_400_600" not in font_rt.glyphs


def test_designspace_generation_bracket_no_export_glyph(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont2.glyphs"))) as f:
        font = glyphsLib.load(f)

    font.glyphs["E"].export = False

    designspace = to_designspace(
        font, write_skipexportglyphs=True, ufo_module=ufo_module, minimal=False
    )

    assert "E" in designspace.lib.get("public.skipExportGlyphs")

    for source in designspace.sources:
        assert "E.REV_BRACKET.570" not in source.font
        assert "E.BRACKET.630" not in source.font

    for rule in designspace.rules:
        assert "E" not in {g for g in itertools.chain(*rule.subs)}

    font_rt = to_glyphs(designspace)

    assert "E" in font_rt.glyphs
    assert {l.name for l in font_rt.glyphs["E"].layers} == {
        "Regular",
        "Regular [630]",
        "Bold",
        "Bold ]570]",
    }


def test_designspace_generation_bracket_GDEF(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)

    # add some attaching anchors to the "x" glyph and its (bracket) layers to
    # trigger the generation of GDEF table
    for layer in font.glyphs["x"].layers:
        anchor = glyphsLib.classes.GSAnchor()
        anchor.name = "top"
        anchor.position = (0, 0)
        layer.anchors.append(anchor)

    designspace = to_designspace(font, ufo_module=ufo_module, generate_GDEF=True)

    for source in designspace.sources:
        categories = source.font.lib["public.openTypeCategories"]

        assert categories == {
            "x": "base",
            "x.BRACKET.varAlt01": "base",
            "x.BRACKET.varAlt02": "base",
        }


def test_designspace_generation_bracket_glyphs3_simple(datadir, ufo_module):
    with open(str(datadir.join("Alternate-g3-axis1.glyphs"))) as f:
        font = glyphsLib.load(f)

    designspace = to_designspace(font, ufo_module=ufo_module)

    for source in designspace.sources:
        assert "A.BRACKET.varAlt01" in source.font


def test_designspace_generation_bracket_rclt_roundtrip(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)
    font.customParameters["Feature for Feature Variations"] = "rclt"
    designspace = to_designspace(font, ufo_module=ufo_module)
    assert designspace.rulesProcessingLast

    font_rt = to_glyphs(designspace)
    assert font_rt.customParameters["Feature for Feature Variations"] == "rclt"


def test_designspace_generation_bracket_other_roundtrip(datadir, ufo_module):
    with open(str(datadir.join("BracketTestFont.glyphs"))) as f:
        font = glyphsLib.load(f)
    font.customParameters["Feature for Feature Variations"] = "calt"
    designspace = to_designspace(font, ufo_module=ufo_module)
    assert FEAVAR_FEATURETAG_LIB_KEY in designspace.lib
    assert designspace.lib[FEAVAR_FEATURETAG_LIB_KEY] == "calt"

    font_rt = to_glyphs(designspace)
    assert font_rt.customParameters["Feature for Feature Variations"] == "calt"


def test_designspace_generation_multiaxis_bracket(datadir, ufo_module):
    with open(str(datadir.join("Playfair-v.glyphs")), encoding="utf-8") as f:
        font = glyphsLib.load(f)

    # Remove names of bracket layers, make sure the layers get
    # copied anyway
    for l in font.glyphs["v"].layers:
        if l._is_bracket_layer():
            l.name = ""

    designspace = to_designspace(font, ufo_module=ufo_module)
    axes = designspace.axes
    info = font.glyphs["v"].layers[8]._bracket_info(axes)
    assert info == {"opsz": (5, 410), "wdth": (50, 75), "wght": (690, 900)}

    for source in designspace.sources:
        assert "v.BRACKET.varAlt01" in source.font

    assert (
        designspace.rules[0].name
        == "BRACKET.Optical size_5_410.Weight_690_900.Width_50_75"
    )
    assert designspace.rules[0].conditionSets == [
        [
            dict(name="Optical size", minimum=5, maximum=410),
            dict(name="Width", minimum=50, maximum=75),
            dict(name="Weight", minimum=690, maximum=900),
        ]
    ]
    assert designspace.rules[0].subs == [
        ("v", "v.BRACKET.varAlt01"),
    ]
