#
# Copyright 2016 Google Inc. All Rights Reserved.
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


import collections
import pytest
import tempfile
import os
import shutil

import glyphsLib
import defcon
import ufoLib2
from textwrap import dedent
from glyphsLib.classes import (
    GSComponent,
    GSFeature,
    GSFont,
    GSFontMaster,
    GSGlyph,
    GSLayer,
    GSPath,
    GSNode,
    GSAlignmentZone,
    GSGuide,
)
from glyphsLib.types import Point

from glyphsLib.builder import to_glyphs, to_designspace, to_ufos
from glyphsLib.builder.builders import UFOBuilder, GlyphsBuilder
from glyphsLib.builder.paths import to_ufo_paths
from glyphsLib.builder.constants import (
    COMPONENT_INFO_KEY,
    GLYPHS_PREFIX,
    GLYPHLIB_PREFIX,
    FONT_CUSTOM_PARAM_PREFIX,
)

from ..classes_test import (
    generate_minimal_font,
    generate_instance_from_dict,
    add_glyph,
    add_anchor,
    add_component,
)


pytestmark = pytest.mark.parametrize("ufo_module", [ufoLib2, defcon])


def test_minimal_data(ufo_module):
    """Test the minimal data that must be provided to generate UFOs, and in
    some cases that additional redundant data is not set."""

    font = generate_minimal_font()
    family_name = font.familyName
    ufos = to_ufos(font, ufo_module=ufo_module)
    assert len(ufos) == 1

    ufo = ufos[0]
    assert len(ufo) == 0
    assert ufo.info.familyName == family_name
    # assert (ufo.info.styleName, == Regular'
    assert ufo.info.versionMajor == 1
    assert ufo.info.versionMinor == 0
    assert ufo.info.openTypeNameVersion is None
    # TODO(jamesgk) try to generate minimally-populated UFOs in glyphsLib,
    # assert that more fields are empty here (especially in name table)


def test_warn_no_version(caplog, ufo_module):
    """Test that a warning is printed when app version is missing."""
    font = generate_minimal_font()
    font.appVersion = "0"
    to_ufos(font, ufo_module=ufo_module)
    assert len([r for r in caplog.records if "outdated version" in r.msg]) == 1


def test_load_kerning(ufo_module):
    """Test that kerning conflicts are left untouched.

    Discussion at: https://github.com/googlefonts/glyphsLib/pull/407
    It turns out that Glyphs and the UFO spec agree on how to treat
    ambiguous kerning, so keep it ambiguous, it minimizes diffs.
    """
    font = generate_minimal_font()

    # generate classes 'A': ['A', 'a'] and 'V': ['V', 'v']
    for glyph_name in ("A", "a", "V", "v"):
        glyph = add_glyph(font, glyph_name)
        glyph.rightKerningGroup = glyph_name.upper()
        glyph.leftKerningGroup = glyph_name.upper()

    # classes are referenced in Glyphs kerning using old MMK names
    font.kerning = {
        font.masters[0].id: collections.OrderedDict(
            (
                (
                    "@MMK_L_A",
                    collections.OrderedDict((("@MMK_R_V", -250), ("v", -100))),
                ),
                ("a", collections.OrderedDict((("@MMK_R_V", 100),))),
            )
        )
    }

    ufos = to_ufos(font, ufo_module=ufo_module)
    ufo = ufos[0]

    assert ufo.kerning["public.kern1.A", "public.kern2.V"] == -250
    assert ufo.kerning["public.kern1.A", "v"] == -100
    assert ufo.kerning["a", "public.kern2.V"] == 100


def test_propagate_anchors_on(ufo_module):
    """Test anchor propagation for some relatively complicated cases."""

    font = generate_minimal_font()

    glyphs = (
        ("sad", [], [("bottom", 50, -50), ("top", 50, 150)]),
        ("dotabove", [], [("top", 0, 150), ("_top", 0, 100)]),
        ("dotbelow", [], [("bottom", 0, -50), ("_bottom", 0, 0)]),
        ("dad", [("sad", 0, 0), ("dotabove", 50, 50)], []),
        ("dadDotbelow", [("dad", 0, 0), ("dotbelow", 50, -50)], []),
        ("yod", [], [("bottom", 50, -50)]),
        ("yod_yod", [("yod", 0, 0), ("yod", 100, 0)], []),  # ligature
        ("yodyod", [("yod", 0, 0), ("yod", 100, 0)], []),  # not a ligature
    )
    for name, component_data, anchor_data in glyphs:
        add_glyph(font, name)
        for n, x, y in anchor_data:
            add_anchor(font, name, n, x, y)
        for n, x, y in component_data:
            add_component(font, name, n, (1, 0, 0, 1, x, y))

    ufos = to_ufos(font, propagate_anchors=True, ufo_module=ufo_module)
    ufo = ufos[0]

    glyph = ufo["dadDotbelow"]
    assert len(glyph.anchors) == 2
    # check propagated anchors are appended in a deterministic order
    assert [anchor.name for anchor in glyph.anchors] == ["bottom", "top"]
    for anchor in glyph.anchors:
        assert anchor.x == 50
        if anchor.name == "bottom":
            assert anchor.y == -100
        else:
            assert anchor.name == "top"
            assert anchor.y == 200

    # 'yodyod' isn't explicitly classified as a 'ligature' hence it will NOT
    # inherit two 'bottom_1' and 'bottom_2' anchors from each 'yod' component,
    # but only one 'bottom' anchor from the last component.
    # https://github.com/googlefonts/glyphsLib/issues/368#issuecomment-2103376997
    glyph = ufo["yodyod"]
    assert len(glyph.anchors) == 1
    for anchor in glyph.anchors:
        assert anchor.name == "bottom"
        assert anchor.y == -50
        assert anchor.x == 150

    # 'yod_yod' is a ligature hence will inherit two 'bottom_{1,2}' anchors
    # from each 'yod' component
    glyph = ufo["yod_yod"]
    assert len(glyph.anchors) == 2
    for anchor in glyph.anchors:
        assert anchor.y == -50
        if anchor.name == "bottom_1":
            assert anchor.x == 50
        else:
            assert anchor.name == "bottom_2"
            assert anchor.x == 150


def test_propagate_anchors_off(ufo_module):
    """Test disabling anchor propagation."""

    font = generate_minimal_font()
    font.customParameters["Propagate Anchors"] = 0

    glyphs = (
        ("sad", [], [("bottom", 50, -50), ("top", 50, 150)]),
        ("dotabove", [], [("top", 0, 150), ("_top", 0, 100)]),
        ("dad", [("sad", 0, 0), ("dotabove", 50, 50)], []),
    )
    for name, component_data, anchor_data in glyphs:
        add_glyph(font, name)
        for n, x, y in anchor_data:
            add_anchor(font, name, n, x, y)
        for n, x, y in component_data:
            add_component(font, name, n, (1, 0, 0, 1, x, y))

    ufos = to_ufos(font, propagate_anchors=False, ufo_module=ufo_module)
    ufo = ufos[0]

    assert len(ufo["dad"].anchors) == 0


def test_propagate_anchors_custom_parameter_on(ufo_module):
    """Test anchor propagation with Propagate Anchors set to 1."""

    font = generate_minimal_font()
    font.customParameters["Propagate Anchors"] = 1

    glyphs = (
        ("sad", [], [("bottom", 50, -50), ("top", 50, 150)]),
        ("dotabove", [], [("top", 0, 150), ("_top", 0, 100)]),
        ("dad", [("sad", 0, 0), ("dotabove", 50, 50)], []),
    )
    for name, component_data, anchor_data in glyphs:
        add_glyph(font, name)
        for n, x, y in anchor_data:
            add_anchor(font, name, n, x, y)
        for n, x, y in component_data:
            add_component(font, name, n, (1, 0, 0, 1, x, y))

    ufos = to_ufos(font, ufo_module=ufo_module)
    ufo = ufos[0]

    glyph = ufo["dad"]
    assert len(glyph.anchors) == 2
    # check propagated anchors are appended in a deterministic order
    assert [anchor.name for anchor in glyph.anchors] == ["bottom", "top"]
    for anchor in glyph.anchors:
        assert anchor.x == 50
        if anchor.name == "bottom":
            assert anchor.y == -50
        else:
            assert anchor.name == "top"
            assert anchor.y == 200


def test_propagate_anchors_custom_parameter_off(ufo_module):
    """Test anchor propagation with Propagate Anchors set to 0."""

    font = generate_minimal_font()
    font.customParameters["Propagate Anchors"] = 0

    glyphs = (
        ("sad", [], [("bottom", 50, -50), ("top", 50, 150)]),
        ("dotabove", [], [("top", 0, 150), ("_top", 0, 100)]),
        ("dad", [("sad", 0, 0), ("dotabove", 50, 50)], []),
    )
    for name, component_data, anchor_data in glyphs:
        add_glyph(font, name)
        for n, x, y in anchor_data:
            add_anchor(font, name, n, x, y)
        for n, x, y in component_data:
            add_component(font, name, n, (1, 0, 0, 1, x, y))

    ufos = to_ufos(font, ufo_module=ufo_module)
    ufo = ufos[0]

    assert len(ufo["dad"].anchors) == 0


def test_fail_during_anchor_propagation(ufo_module):
    """Fix https://github.com/googlefonts/glyphsLib/issues/317."""
    font = generate_minimal_font()

    glyphs = (
        # This glyph has components that don't exist in the font
        ("yodyod", [("yod", 0, 0), ("yod", 100, 0)], []),
    )
    for name, component_data, anchor_data in glyphs:
        add_glyph(font, name)
        for n, x, y in anchor_data:
            add_anchor(font, name, n, x, y)
        for n, x, y in component_data:
            add_component(font, name, n, (1, 0, 0, 1, x, y))

    # We just want the call to `to_ufos` to not crash
    assert to_ufos(font, ufo_module=ufo_module)


def test_postscript_name_from_data(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "foo")["production"] = "f_o_o.alt1"
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    postscriptNames = ufo.lib.get("public.postscriptNames")
    assert postscriptNames == {"foo": "f_o_o.alt1"}


def test_postscript_name_from_glyph_name(ufo_module):
    font = generate_minimal_font()
    # in GlyphData (and AGLFN) without a 'production' name
    add_glyph(font, "A")
    # not in GlyphData, no production name
    add_glyph(font, "foobar")
    # in GlyphData with a 'production' name
    add_glyph(font, "C-fraktur")
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    postscriptNames = ufo.lib.get("public.postscriptNames")
    assert postscriptNames == {"C-fraktur": "uni212D"}


def test_category(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "foo")["category"] = "Mark"
    add_glyph(font, "bar")
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    category_key = GLYPHLIB_PREFIX + "category"
    assert ufo["foo"].lib.get(category_key) == "Mark"
    assert category_key not in ufo["bar"].lib


def test_subCategory(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "foo")["subCategory"] = "Nonspacing"
    add_glyph(font, "bar")
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    subCategory_key = GLYPHLIB_PREFIX + "subCategory"
    assert ufo["foo"].lib.get(subCategory_key) == "Nonspacing"
    assert subCategory_key not in ufo["bar"].lib


def test_mark_nonspacing_zero_width(ufo_module):
    font = generate_minimal_font()

    add_glyph(font, "dieresiscomb").layers[0].width = 100

    foo = add_glyph(font, "foo")
    foo.category = "Mark"
    foo.subCategory = "Nonspacing"
    foo.layers[0].width = 200

    bar = add_glyph(font, "bar")
    bar.category = "Mark"
    bar.subCategory = "Nonspacing"
    bar.layers[0].width = 0

    ufo = to_ufos(font, ufo_module=ufo_module)[0]

    originalWidth_key = GLYPHLIB_PREFIX + "originalWidth"
    assert ufo["dieresiscomb"].width == 0
    assert ufo["dieresiscomb"].lib.get(originalWidth_key) == 100
    assert ufo["foo"].width == 0
    assert ufo["foo"].lib.get(originalWidth_key) == 200
    assert ufo["bar"].width == 0
    assert originalWidth_key not in ufo["bar"].lib


def test_GDEF(ufo_module):
    font = generate_minimal_font()
    for glyph in (
        "space",
        "A",
        "A.alt",
        "wigglylinebelowcomb",
        "wigglylinebelowcomb.alt",
        "fi",
        "fi.alt",
        "t_e_s_t",
        "t_e_s_t.alt",
    ):
        add_glyph(font, glyph)
    add_anchor(font, "A", "bottom", 300, -10)
    add_anchor(font, "wigglylinebelowcomb", "_bottom", 100, 40)
    add_anchor(font, "fi", "caret_1", 150, 0)
    add_anchor(font, "t_e_s_t.alt", "caret_1", 200, 0)
    add_anchor(font, "t_e_s_t.alt", "caret_2", 400, 0)
    add_anchor(font, "t_e_s_t.alt", "caret_3", 600, 0)
    ufo = to_ufos(font, ufo_module=ufo_module)[0]

    assert ufo.lib["public.openTypeCategories"] == {
        "A": "base",
        "fi": "ligature",
        "t_e_s_t.alt": "ligature",
        "wigglylinebelowcomb": "mark",
        "wigglylinebelowcomb.alt": "mark",
    }


def test_GDEF_base_with_attaching_anchor(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "A.alt")
    add_anchor(font, "A.alt", "top", 400, 1000)
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib["public.openTypeCategories"] == {"A.alt": "base"}


def test_GDEF_base_with_nonattaching_anchor(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "A.alt")
    add_anchor(font, "A.alt", "_top", 400, 1000)
    assert to_ufos(font, ufo_module=ufo_module)[0].features.text == ""
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert "public.openTypeCategories" not in ufo.lib


def test_GDEF_ligature_with_attaching_anchor(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "fi")
    add_anchor(font, "fi", "top", 400, 1000)
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib["public.openTypeCategories"] == {"fi": "ligature"}


def test_GDEF_ligature_with_nonattaching_anchor(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "fi")
    add_anchor(font, "fi", "_top", 400, 1000)
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.features.text == ""
    assert "public.openTypeCategories" not in ufo.lib


def test_GDEF_mark(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "eeMatra-gurmukhi")
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib["public.openTypeCategories"] == {"eeMatra-gurmukhi": "mark"}


def test_GDEF_custom_category_subCategory(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "foo")["subCategory"] = "Ligature"
    add_anchor(font, "foo", "top", 400, 1000)
    bar = add_glyph(font, "bar")
    bar["category"], bar["subCategory"] = "Mark", "Nonspacing"
    baz = add_glyph(font, "baz")
    baz["category"], baz["subCategory"] = "Mark", "Spacing Combining"
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib["public.openTypeCategories"] == {
        "foo": "ligature",
        "bar": "mark",
        "baz": "mark",
    }


def test_GDEF_roundtrip(ufo_module):
    font = generate_minimal_font()

    ds = to_designspace(font, ufo_module=ufo_module)
    ufo = ds.sources[0].font
    assert "public.openTypeCategories" not in ufo.lib

    ufo.newGlyph("base")
    ufo.newGlyph("mark")
    ufo.newGlyph("ligature")
    ufo.newGlyph("mystery")
    categories = {
        "base": "base",
        "mark": "mark",
        "ligature": "ligature",
        "asdf": "component",
    }
    ufo.lib["public.openTypeCategories"] = categories

    font2 = to_glyphs(ds)
    assert (
        font2.userData["com.schriftgestaltung.Glyphs.originalOpenTypeCategory"]
        == categories
    )

    add_anchor(font2, "mystery", "top", 400, 1000)
    ds2 = to_designspace(font2, ufo_module=ufo_module)
    ufo2 = ds2.sources[0].font
    assert ufo2.lib["public.openTypeCategories"] == {
        **categories,
        "mystery": "base",
    }


def test_GDEF_roundtrip_empty(ufo_module):
    font = generate_minimal_font()

    ds = to_designspace(font, ufo_module=ufo_module)
    ufo = ds.sources[0].font
    assert "public.openTypeCategories" not in ufo.lib

    font2 = to_glyphs(ds, ufo_module=ufo_module)
    assert (
        font2.userData["com.schriftgestaltung.Glyphs.originalOpenTypeCategory"] is None
    )

    ds2 = to_designspace(font2, ufo_module=ufo_module)
    ufo2 = ds2.sources[0].font
    assert "public.openTypeCategories" not in ufo2.lib


def test_set_blue_values(ufo_module):
    """Test that blue values are set correctly from alignment zones."""

    data_in = [
        GSAlignmentZone(pos=500, size=15),
        GSAlignmentZone(pos=400, size=-15),
        GSAlignmentZone(pos=0, size=-15),
        GSAlignmentZone(pos=-200, size=15),
        GSAlignmentZone(pos=-300, size=-15),
    ]
    expected_blue_values = [-200, -185, -15, 0, 500, 515]
    expected_other_blues = [-315, -300, 385, 400]

    font = generate_minimal_font()
    font.masters[0].alignmentZones = data_in
    ufo = to_ufos(font, ufo_module=ufo_module)[0]

    assert ufo.info.postscriptBlueValues == expected_blue_values
    assert ufo.info.postscriptOtherBlues == expected_other_blues


def test_set_blue_values_empty(ufo_module):
    font = generate_minimal_font()
    font.masters[0].alignmentZones = []
    ufo = to_ufos(font, ufo_module=ufo_module)[0]

    if ufo_module is ufoLib2:
        assert ufo.info.postscriptBlueValues is None
        assert ufo.info.postscriptOtherBlues is None
    else:
        assert ufo.info.postscriptBlueValues == []
        assert ufo.info.postscriptOtherBlues == []


def test_missing_date(ufo_module):
    font = generate_minimal_font()
    font.date = None
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.info.openTypeHeadCreated is None


def test_variation_font_origin(ufo_module):
    font = generate_minimal_font()
    name = "Variation Font Origin"
    value = "Light"
    font.customParameters[name] = value

    ufos, instances = to_ufos(font, include_instances=True, ufo_module=ufo_module)

    key = FONT_CUSTOM_PARAM_PREFIX + name
    for ufo in ufos:
        assert key in ufo.lib
        assert ufo.lib[key] == value
    assert name in instances
    assert instances[name] == value


def test_family_name_none(ufo_module):
    font = generate_minimal_font()
    instances_list = [
        {"name": "Regular1"},
        {
            "name": "Regular2",
            "customParameters": [{"name": "familyName", "value": "CustomFamily"}],
        },
    ]
    font.instances = [generate_instance_from_dict(i) for i in instances_list]

    # 'family_name' defaults to None
    ufos, instance_data = to_ufos(font, include_instances=True)
    instances = instance_data["data"]

    # all instances are included, both with/without 'familyName' parameter
    assert len(instances) == 2
    assert instances[0].name == "Regular1"
    assert instances[1].name == "Regular2"
    assert len(instances[0].customParameters) == 0
    assert len(instances[1].customParameters) == 1
    assert instances[1].customParameters[0].value == "CustomFamily"

    # the masters' family name is unchanged
    for ufo in ufos:
        assert ufo.info.familyName == "MyFont"


def test_family_name_same_as_default(ufo_module):
    font = generate_minimal_font()
    instances_list = [
        {"name": "Regular1"},
        {
            "name": "Regular2",
            "customParameters": [{"name": "familyName", "value": "CustomFamily"}],
        },
    ]
    font.instances = [generate_instance_from_dict(i) for i in instances_list]
    # 'MyFont' is the source family name, as returned from
    # 'generate_minimal_data'
    ufos, instance_data = to_ufos(font, include_instances=True, family_name="MyFont")
    instances = instance_data["data"]

    # only instances which don't have 'familyName' custom parameter
    # are included in returned list
    assert len(instances) == 1
    assert instances[0].name == "Regular1"
    assert len(instances[0].customParameters) == 0

    # the masters' family name is unchanged
    for ufo in ufos:
        assert ufo.info.familyName == "MyFont"


def test_family_name_custom(ufo_module):
    font = generate_minimal_font()
    instances_list = [
        {"name": "Regular1"},
        {
            "name": "Regular2",
            "customParameters": [{"name": "familyName", "value": "CustomFamily"}],
        },
    ]
    font.instances = [generate_instance_from_dict(i) for i in instances_list]
    ufos, instance_data = to_ufos(
        font, include_instances=True, family_name="CustomFamily"
    )
    instances = instance_data["data"]

    # only instances with familyName='CustomFamily' are included
    assert len(instances) == 1
    assert instances[0].name == "Regular2"
    assert len(instances[0].customParameters) == 1
    assert instances[0].customParameters[0].value == "CustomFamily"

    # the masters' family is also modified to use custom 'family_name'
    for ufo in ufos:
        assert ufo.info.familyName == "CustomFamily"


def test_lib_no_weight(ufo_module):
    font = generate_minimal_font()
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib[GLYPHS_PREFIX + "weight"] == "Regular"


def test_lib_weight(ufo_module):
    font = generate_minimal_font()
    font.masters[0].weight = "Bold"
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib[GLYPHS_PREFIX + "weight"] == "Bold"


def test_lib_no_width(ufo_module):
    font = generate_minimal_font()
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib[GLYPHS_PREFIX + "width"] == "Regular"


def test_lib_width(ufo_module):
    font = generate_minimal_font()
    font.masters[0].width = "Condensed"
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib[GLYPHS_PREFIX + "width"] == "Condensed"


def test_lib_no_custom(ufo_module):
    font = generate_minimal_font()
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert GLYPHS_PREFIX + "customName" not in ufo.lib


def test_lib_custom(ufo_module):
    font = generate_minimal_font()
    font.masters[0].customName = "FooBar"
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib[GLYPHS_PREFIX + "customName"] == "FooBar"


def test_coerce_to_bool(ufo_module):
    font = generate_minimal_font()
    font.customParameters["Disable Last Change"] = "Truthy"
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo.lib[FONT_CUSTOM_PARAM_PREFIX + "disablesLastChange"]


def _run_guideline_test(data_in, expected, ufo_module):
    font = generate_minimal_font()
    glyph = GSGlyph(name="a")
    font.glyphs.append(glyph)
    layer = GSLayer()
    layer.layerId = font.masters[0].id
    layer.width = 0
    for guide_data in data_in:
        pt = Point(value=guide_data["position"][0], value2=guide_data["position"][1])
        guide = GSGuide()
        guide.position = pt
        guide.angle = guide_data["angle"]
        layer.guides.append(guide)
    glyph.layers.append(layer)
    ufo = to_ufos(font, ufo_module=ufo_module, minimal=False)[0]
    assert [dict(g) for g in ufo["a"].guidelines] == expected


def test_set_guidelines(ufo_module):
    """Test that guidelines are set correctly."""

    _run_guideline_test(
        [{"position": (1, 2), "angle": 90}], [{"x": 1, "y": 2, "angle": 90}], ufo_module
    )


def test_set_guidelines_duplicates(ufo_module):
    """Test that duplicate guidelines are accepted."""

    _run_guideline_test(
        [{"position": (1, 2), "angle": 90}, {"position": (1, 2), "angle": 90}],
        [{"x": 1, "y": 2, "angle": 90}, {"x": 1, "y": 2, "angle": 90}],
        ufo_module,
    )


# TODO test more than just name
def test_supplementary_layers(ufo_module):
    """Test sub layers."""
    font = generate_minimal_font()
    glyph = GSGlyph(name="a")
    font.glyphs.append(glyph)
    layer = GSLayer()
    layer.layerId = font.masters[0].id
    layer.width = 0
    glyph.layers.append(layer)
    sublayer = GSLayer()
    sublayer.associatedMasterId = font.masters[0].id
    sublayer.width = 0
    sublayer.name = "SubLayer"
    glyph.layers.append(sublayer)
    ufo = to_ufos(font, minimal=False, ufo_module=ufo_module)[0]
    assert [l.name for l in ufo.layers] == ["public.default", "SubLayer"]


def test_duplicate_supplementary_layers(ufo_module, caplog):
    """Test glyph layers with same name."""
    font = generate_minimal_font()
    glyph = GSGlyph(name="a")
    font.glyphs.append(glyph)
    layer = GSLayer()
    layer.layerId = font.masters[0].id
    layer.width = 0
    glyph.layers.append(layer)
    sublayer = GSLayer()
    sublayer.associatedMasterId = font.masters[0].id
    sublayer.width = 0
    sublayer.name = "SubLayer"
    glyph.layers.append(sublayer)
    sublayer = GSLayer()
    sublayer.associatedMasterId = font.masters[0].id
    sublayer.width = 0
    sublayer.name = "SubLayer"
    glyph.layers.append(sublayer)
    ufo = to_ufos(font, minimal=False, ufo_module=ufo_module)[0]

    assert [l.name for l in ufo.layers] == ["public.default", "SubLayer", "SubLayer #1"]
    assert any("Duplicate glyph layer name" in x.message for x in caplog.records)


def test_glyph_lib_Export(ufo_module):
    font = generate_minimal_font()
    glyph = add_glyph(font, "a")
    assert glyph.export

    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    ds = to_designspace(font, ufo_module=ufo_module)

    assert GLYPHLIB_PREFIX + "Export" not in ufo["a"].lib
    assert "public.skipExportGlyphs" not in ufo.lib
    assert "public.skipExportGlyphs" not in ds.lib

    font2 = to_glyphs(ds)
    assert font2.glyphs["a"].export

    font2.glyphs["a"].export = False

    # Test write_skipexportglyphs=True
    ufo = to_ufos(font2, ufo_module=ufo_module, write_skipexportglyphs=True)[0]
    ds = to_designspace(font2, ufo_module=ufo_module, write_skipexportglyphs=True)

    assert GLYPHLIB_PREFIX + "Export" not in ufo["a"].lib
    assert ufo.lib["public.skipExportGlyphs"] == ["a"]
    assert ds.lib["public.skipExportGlyphs"] == ["a"]

    font3 = to_glyphs(ds)
    assert not font3.glyphs["a"].export

    # Test write_skipexportglyphs=False
    ufo = to_ufos(font2, ufo_module=ufo_module, write_skipexportglyphs=False)[0]
    ds = to_designspace(font2, ufo_module=ufo_module, write_skipexportglyphs=False)

    assert not ufo["a"].lib[GLYPHLIB_PREFIX + "Export"]
    assert "public.skipExportGlyphs" not in ufo.lib
    assert "public.skipExportGlyphs" not in ds.lib

    font3 = to_glyphs(ds)
    assert not font3.glyphs["a"].export


def test_glyph_lib_Export_mixed_to_public_skipExportGlyphs(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "a")
    add_glyph(font, "b")
    add_glyph(font, "c")
    add_glyph(font, "d")
    ds = to_designspace(font, ufo_module=ufo_module, write_skipexportglyphs=True)
    ufo = ds.sources[0].font

    ufo["a"].lib[GLYPHLIB_PREFIX + "Export"] = False
    ufo.lib["public.skipExportGlyphs"] = ["b"]
    ds.lib["public.skipExportGlyphs"] = ["c"]

    font2 = to_glyphs(ds)

    ds2 = to_designspace(font2, ufo_module=ufo_module, write_skipexportglyphs=True)
    ufo2 = ds2.sources[0].font

    assert GLYPHLIB_PREFIX + "Export" not in ufo2["a"].lib
    assert GLYPHLIB_PREFIX + "Export" not in ufo2["b"].lib
    assert GLYPHLIB_PREFIX + "Export" not in ufo2["c"].lib
    assert GLYPHLIB_PREFIX + "Export" not in ufo2["d"].lib
    assert ufo2.lib["public.skipExportGlyphs"] == ["a", "c"]
    assert ds2.lib["public.skipExportGlyphs"] == ["a", "c"]

    font3 = to_glyphs(ds2)
    assert not font3.glyphs["a"].export
    assert font3.glyphs["b"].export
    assert not font3.glyphs["c"].export
    assert font3.glyphs["d"].export

    ufos3 = to_ufos(font3, ufo_module=ufo_module, write_skipexportglyphs=True)
    ufo3 = ufos3[0]
    assert GLYPHLIB_PREFIX + "Export" not in ufo3["a"].lib
    assert GLYPHLIB_PREFIX + "Export" not in ufo3["b"].lib
    assert GLYPHLIB_PREFIX + "Export" not in ufo3["c"].lib
    assert GLYPHLIB_PREFIX + "Export" not in ufo3["d"].lib
    assert ufo3.lib["public.skipExportGlyphs"] == ["a", "c"]


def test_glyph_lib_Export_mixed_to_lib_key(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "a")
    add_glyph(font, "b")
    add_glyph(font, "c")
    add_glyph(font, "d")
    ds = to_designspace(font, ufo_module=ufo_module, write_skipexportglyphs=False)
    ufo = ds.sources[0].font

    ufo["a"].lib[GLYPHLIB_PREFIX + "Export"] = False
    ufo.lib["public.skipExportGlyphs"] = ["b"]
    ds.lib["public.skipExportGlyphs"] = ["c"]

    font2 = to_glyphs(ds)

    ds2 = to_designspace(font2, ufo_module=ufo_module, write_skipexportglyphs=False)
    ufo2 = ds2.sources[0].font

    assert not ufo2["a"].lib[GLYPHLIB_PREFIX + "Export"]
    assert GLYPHLIB_PREFIX + "Export" not in ufo2["b"].lib
    assert not ufo2["c"].lib[GLYPHLIB_PREFIX + "Export"]
    assert GLYPHLIB_PREFIX + "Export" not in ufo2["d"].lib
    assert "public.skipExportGlyphs" not in ufo2.lib
    assert "public.skipExportGlyphs" not in ds2.lib

    font3 = to_glyphs(ds2)
    assert not font3.glyphs["a"].export
    assert font3.glyphs["b"].export
    assert not font3.glyphs["c"].export
    assert font3.glyphs["d"].export

    ufos3 = to_ufos(font3, write_skipexportglyphs=False)
    ufo3 = ufos3[0]
    assert not ufo3["a"].lib[GLYPHLIB_PREFIX + "Export"]
    assert GLYPHLIB_PREFIX + "Export" not in ufo3["b"].lib
    assert not ufo3["c"].lib[GLYPHLIB_PREFIX + "Export"]
    assert GLYPHLIB_PREFIX + "Export" not in ufo3["d"].lib
    assert "public.skipExportGlyphs" not in ufo3.lib

    font4 = to_glyphs(ufos3)
    assert not font4.glyphs["a"].export
    assert font4.glyphs["b"].export
    assert not font4.glyphs["c"].export
    assert font4.glyphs["d"].export


def test_glyph_lib_Export_GDEF(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "a")
    add_glyph(font, "d")
    add_anchor(font, "d", "top", 100, 100)

    ds = to_designspace(font, ufo_module=ufo_module, write_skipexportglyphs=True)
    ufo = ds.sources[0].font
    assert ufo.lib["public.openTypeCategories"] == {"d": "base"}

    font.glyphs["d"].export = False
    ds2 = to_designspace(font, ufo_module=ufo_module, write_skipexportglyphs=True)
    ufo2 = ds2.sources[0].font
    # Unexported glyphs still get their category, because it doesn't hurt to
    # do it.
    assert ufo2.lib["public.openTypeCategories"] == {"d": "base"}


def test_glyph_lib_Export_feature_names_from_notes(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "a")
    add_glyph(font, "a.ss01")
    ss01 = GSFeature(name="ss01", code="sub a by a.ss01;")
    font.features.append(ss01)

    # Name should be exported when in first line
    for note in (
        'Name: Single\\storey "ä"',
        'Name: Single\\storey "ä"\nFoo',
    ):
        font.features[0].notes = note
        ufos = to_ufos(font, ufo_module=ufo_module)
        ufo = ufos[0]
        assert r'name "Single\005cstorey \0022ä\0022";' in ufo.features.text
        assert note not in ufo.features.text

    # Name should not be exported when not in first line
    for note in (
        'A Comment\nName: Single\\storey "ä"\nFoo',
        'A Comment\nName: Single\\storey "ä"',
    ):
        font.features[0].notes = note
        ufos = to_ufos(font, ufo_module=ufo_module)
        ufo = ufos[0]
        assert r'name "Single\005cstorey \0022ä\0022";' not in ufo.features.text


def test_glyph_lib_Export_feature_names_long_from_notes(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "a")
    add_glyph(font, "a.ss01")
    ss01 = GSFeature(name="ss01", code="sub a by a.ss01;")
    font.features.append(ss01)
    for note in (
        (
            'featureNames {\n  name 3 1 0x401 "Alternate {ä};";\n'
            '  name 3 1 0x409 "Alternate {};";\n};\n'
        ),
        (
            'Name: "bla"\nfeatureNames {\n  name 3 1 0x401 "Alternate {ä};";\n'
            '  name 3 1 0x409 "Alternate {};";\n};\nHello\n'
        ),
    ):
        font.features[0].notes = note
        ufos = to_ufos(font, ufo_module=ufo_module)
        ufo = ufos[0]
        assert (
            'featureNames {\n  name 3 1 0x401 "Alternate {ä};";\n'
            '  name 3 1 0x409 "Alternate {};";\n};'
        ) in ufo.features.text


def test_glyph_lib_Export_feature_names_long_escaped_from_notes(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "a")
    add_glyph(font, "a.ss01")
    ss01 = GSFeature(name="ss01", code="sub a by a.ss01;")
    font.features.append(ss01)
    for note in (
        (
            'featureNames {\n  name "Round dots";\n  name 3 1 0x0C01 '
            '"\\062d\\0631\\0648\\0641 \\0645\\0647\\0645\\0644\\0629 '
            '(\\0628\\0644\\0627 \\0646\\0642\\0627\\0637)";\n};\n'
        ),
        (
            'Name: "bla"\nfeatureNames {\n  name "Round dots";\n  name 3 1 '
            '0x0C01 "\\062d\\0631\\0648\\0641 \\0645\\0647\\0645\\0644\\0629 '
            '(\\0628\\0644\\0627 \\0646\\0642\\0627\\0637)";\n};\nHello\n'
        ),
    ):
        font.features[0].notes = note
        ufos = to_ufos(font, ufo_module=ufo_module)
        ufo = ufos[0]
        assert (
            'featureNames {\n  name "Round dots";\n  name 3 1 0x0C01 '
            '"\\062d\\0631\\0648\\0641 \\0645\\0647\\0645\\0644\\0629 '
            '(\\0628\\0644\\0627 \\0646\\0642\\0627\\0637)";\n};\n'
        ) in ufo.features.text


def test_glyph_lib_Export_feature_names_from_labels(ufo_module):
    font = generate_minimal_font(format_version=3)
    add_glyph(font, "a")
    add_glyph(font, "a.ss01")
    ss01 = GSFeature(name="ss01", code="sub a by a.ss01;")
    font.features.append(ss01)

    # Name should be exported when in first line
    for lang, name in (
        ("dflt", 'Single\\storey "a"'),
        ("ENG", 'Single\\storey "ä"'),
        ("ARA", 'Sɨngłe\\storey "ä"'),
    ):
        font.features[0].labels.append(dict(language=lang, value=name))
    ufos = to_ufos(font, ufo_module=ufo_module)
    assert ufos[0].features.text == dedent(
        """\
        feature ss01 {
        featureNames {
          name "Single\\005cstorey \\0022a\\0022";
          name 3 1 0x409 "Single\\005cstorey \\0022ä\\0022";
          name 3 1 0xC01 "Sɨngłe\\005cstorey \\0022ä\\0022";
        };
        sub a by a.ss01;
        } ss01;
        """
    )


def test_glyph_lib_Export_fake_designspace(ufo_module):
    font = generate_minimal_font()
    master = GSFontMaster()
    master.ascender = 0
    master.capHeight = 0
    master.descender = 0
    master.id = "id"
    master.xHeight = 0
    font.masters.append(master)
    add_glyph(font, "a")
    add_glyph(font, "b")
    ds = to_designspace(font, ufo_module=ufo_module, write_skipexportglyphs=True)

    ufos = [source.font for source in ds.sources]

    font2 = to_glyphs(ufos)
    ds2 = to_designspace(font2, ufo_module=ufo_module, write_skipexportglyphs=True)
    assert "public.skipExportGlyphs" not in ds2.lib

    ufos[0].lib["public.skipExportGlyphs"] = ["a"]

    with pytest.raises(ValueError):
        to_glyphs(ufos)

    ufos[1].lib["public.skipExportGlyphs"] = ["a"]
    font3 = to_glyphs(ufos)
    assert not font3.glyphs["a"].export
    assert font3.glyphs["b"].export


def test_glyph_lib_metricsKeys(ufo_module):
    font = generate_minimal_font()
    glyph = add_glyph(font, "x")
    glyph.leftMetricsKey = "y"
    glyph.rightMetricsKey = "z"
    assert glyph.widthMetricsKey is None

    ufo = to_ufos(font, ufo_module=ufo_module)[0]

    assert ufo["x"].lib[GLYPHLIB_PREFIX + "glyph.leftMetricsKey"] == "y"
    assert ufo["x"].lib[GLYPHLIB_PREFIX + "glyph.rightMetricsKey"] == "z"
    assert GLYPHLIB_PREFIX + "glyph.widthMetricsKey" not in ufo["x"].lib


def test_glyph_lib_component_alignment_and_locked_and_smart_values(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "a")
    add_glyph(font, "b")
    composite_glyph = add_glyph(font, "c")
    add_component(font, "c", "a", (1, 0, 0, 1, 0, 0))
    add_component(font, "c", "b", (1, 0, 0, 1, 0, 100))
    comp1 = composite_glyph.layers[0].components[0]
    comp2 = composite_glyph.layers[0].components[1]

    assert comp1.alignment == 0
    assert not comp1.locked
    assert comp1.smartComponentValues == {}

    ufo = to_ufos(font, ufo_module=ufo_module)[0]

    # all components have deault values, no lib key is written
    assert GLYPHS_PREFIX + "componentsAlignment" not in ufo["c"].lib
    assert GLYPHS_PREFIX + "componentsLocked" not in ufo["c"].lib
    assert GLYPHS_PREFIX + "componentsSmartComponentValues" not in ufo["c"].lib
    assert COMPONENT_INFO_KEY not in ufo["c"].lib

    comp2.alignment = -1
    comp1.locked = True
    comp1.smartComponentValues["height"] = 0
    ufo = to_ufos(font, ufo_module=ufo_module)[0]

    # if any component has a non-default alignment/locked values, write
    # list of values for all of them
    assert GLYPHS_PREFIX + "componentsAlignment" not in ufo["c"].lib
    assert ufo["c"].lib[COMPONENT_INFO_KEY] == [
        {"index": 1, "name": "b", "alignment": -1}
    ]
    assert GLYPHS_PREFIX + "componentsLocked" in ufo["c"].lib
    assert ufo["c"].lib[GLYPHS_PREFIX + "componentsLocked"] == [True, False]
    assert GLYPHS_PREFIX + "componentsSmartComponentValues" in ufo["c"].lib
    assert ufo["c"].lib[GLYPHS_PREFIX + "componentsSmartComponentValues"] == [
        {"height": 0},
        {},
    ]


def test_glyph_lib_color_mapping(ufo_module):
    font = generate_minimal_font()
    glyph = add_glyph(font, "a")
    add_glyph(font, "b")

    color0 = GSLayer()
    color1 = GSLayer()
    color3 = GSLayer()
    color0.name = "Color 0"
    color1.name = "Color 1"
    color3.name = "Color 3"

    glyph.layers.append(color1)
    glyph.layers.append(color0)
    glyph.layers.append(color3)

    ds = to_designspace(font, ufo_module=ufo_module)
    ufo = ds.sources[0].font

    assert ufo["a"].lib["com.github.googlei18n.ufo2ft.colorLayerMapping"] == [
        ("color.1", 1),
        ("color.0", 0),
        ("color.3", 3),
    ]
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["b"].lib


def test_glyph_lib_color_mapping_foreground_color(ufo_module):
    font = generate_minimal_font()
    glyph = add_glyph(font, "a")
    color = GSLayer()
    color.name = "Color *"

    glyph.layers.append(color)

    ds = to_designspace(font, ufo_module=ufo_module)
    ufo = ds.sources[0].font

    assert ufo["a"].lib["com.github.googlei18n.ufo2ft.colorLayerMapping"] == [
        ("color.65535", 65535),
    ]


def test_glyph_lib_color_mapping_invalid_index(ufo_module):
    font = generate_minimal_font()
    glyph = add_glyph(font, "a")
    color = GSLayer()
    color.name = "Color f"
    glyph.layers.append(color)

    color = GSLayer()
    color.name = "Color 0"
    glyph.layers.append(color)

    ds = to_designspace(font, ufo_module=ufo_module)
    ufo = ds.sources[0].font

    assert ufo["a"].lib["com.github.googlei18n.ufo2ft.colorLayerMapping"] == [
        ("color.0", 0),
    ]


def test_glyph_color_layers_components(ufo_module):
    font = generate_minimal_font()
    glypha = add_glyph(font, "a")
    glyphc = add_glyph(font, "c")
    glyphd = add_glyph(font, "d")

    glypha.layers[0].name = "Color 0"
    glyphd.layers.append(GSLayer())
    glyphd.layers[1].name = "Color 0"

    color0 = GSLayer()
    color1 = GSLayer()
    color3 = GSLayer()
    color0.name = "Color 0"
    color1.name = "Color 1"
    color3.name = "Color 3"
    color0.components.append(GSComponent(glyph=glypha))
    color0.components.append(GSComponent(glyph=glyphd))
    color0.components.append(GSComponent(glyph=glyphc))
    color3.components.append(GSComponent(glyph=glyphc))
    color1.components.append(GSComponent(glyph=glypha))

    glypha.layers.append(color1)
    glypha.layers.append(color0)
    glypha.layers.append(color3)

    ds = to_designspace(font, ufo_module=ufo_module)
    ufo = ds.sources[0].font

    assert len(ufo.layers["color.0"]["a"].components) == 3
    assert len(ufo.layers["color.0"]["a"]) == 0
    assert [c.baseGlyph for c in ufo.layers["color.0"]["a"].components] == [
        "a.color1",
        "d.color0",
        "c",
    ]

    assert len(ufo.layers["color.1"]["a"].components) == 1
    assert len(ufo.layers["color.1"]["a"]) == 0

    assert len(ufo.layers["color.3"]["a"].components) == 1
    assert len(ufo.layers["color.3"]["a"]) == 0


def test_glyph_color_palette_layers_no_unicode_mapping(ufo_module):
    font = generate_minimal_font()
    glypha = add_glyph(font, "a")

    glypha.unicode = "0061"

    color0 = GSLayer()
    color1 = GSLayer()
    color0.name = "Color 0"
    color1.name = "Color 1"

    glypha.layers.append(color0)
    glypha.layers.append(color1)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font

    assert ufo["a"].unicode == 97
    assert ufo["a.color0"].unicode is None
    assert ufo["a.color1"].unicode is None


def test_glyph_color_layers_components_2(ufo_module):
    filename = os.path.join(
        os.path.dirname(__file__), "..", "data", "ColorComponents.glyphs"
    )
    with open(filename) as f:
        font = glyphsLib.load(f)

    ds = glyphsLib.to_designspace(font, minimize_glyphs_diffs=True)
    bold_layer0 = ds.sources[1].font.layers["color.0"]
    bold_layer1 = ds.sources[1].font.layers["color.1"]
    assert [c.baseGlyph for c in bold_layer0["Aacute"].components] == [
        "A.color0",
        "acutecomb.color0",
    ]
    assert [c.baseGlyph for c in bold_layer1["Aacute"].components] == [
        "A.color1",
        "acutecomb.color1",
    ]


def test_glyph_color_palette_layers_explode(ufo_module):
    font = generate_minimal_font()
    glypha = add_glyph(font, "a")
    glyphb = add_glyph(font, "b")
    glyphc = add_glyph(font, "c")
    glyphd = add_glyph(font, "d")
    for i, g in enumerate([glypha, glyphb, glyphc, glyphd]):
        path = GSPath()
        path.nodes = [
            GSNode(position=(i + 0, i + 0), nodetype="line"),
            GSNode(position=(i + 1, i + 1), nodetype="line"),
            GSNode(position=(i + 2, i + 2), nodetype="line"),
            GSNode(position=(i + 3, i + 3), nodetype="line"),
        ]
        g.layers[0].paths.append(path)

    compc = GSComponent(glyph=glyphc)
    compd = GSComponent(glyph=glyphd)

    color0 = GSLayer()
    color1 = GSLayer()
    color3 = GSLayer()
    color0.name = "Color 0"
    color1.name = "Color 1"
    color3.name = "Color 3"
    color0.components.append(compd)
    color0.components.append(compc)
    color3.components.append(compc)
    color1.paths.append(path)

    glypha.layers.append(color1)
    glypha.layers.append(color0)
    glypha.layers.append(color3)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": [("a.color0", 1), ("a.color1", 0), ("a.color2", 3)]
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib
    assert len(ufo["a.color0"].components) == 0
    assert len(ufo["a.color0"]) == 1

    assert len(ufo["a.color1"].components) == 2
    assert len(ufo["a.color1"]) == 0

    assert len(ufo["a.color2"].components) == 1
    assert len(ufo["a.color2"]) == 0


def test_glyph_color_palette_layers_explode_no_export(ufo_module):
    font = generate_minimal_font()
    glypha = add_glyph(font, "a")
    glyphb = add_glyph(font, "b")

    color0 = GSLayer()
    color1 = GSLayer()
    color0.name = "Color 0"
    color1.name = "Color 1"

    glypha.export = False
    glypha.layers.append(color0)
    glyphb.layers.append(color1)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font

    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "b": [("b.color0", 1)]
    }


def test_glyph_color_palette_layers_explode_v3(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")
    glyphb = add_glyph(font, "b")
    glyphc = add_glyph(font, "c")
    glyphd = add_glyph(font, "d")
    for i, g in enumerate([glypha, glyphb, glyphc, glyphd]):
        path = GSPath()
        path.nodes = [
            GSNode(position=(i + 0, i + 0), nodetype="line"),
            GSNode(position=(i + 1, i + 1), nodetype="line"),
            GSNode(position=(i + 2, i + 2), nodetype="line"),
            GSNode(position=(i + 3, i + 3), nodetype="line"),
        ]
        g.layers[0].paths.append(path)

    compc = GSComponent(glyph=glyphc)
    compd = GSComponent(glyph=glyphd)

    color0 = GSLayer()
    color1 = GSLayer()
    color3 = GSLayer()
    color0.attributes["colorPalette"] = 0
    color1.attributes["colorPalette"] = 1
    color3.attributes["colorPalette"] = 3
    color0.components.append(compd)
    color0.components.append(compc)
    color3.components.append(compc)
    color1.paths.append(path)

    glypha.layers.append(color1)
    glypha.layers.append(color0)
    glypha.layers.append(color3)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": [("a.color0", 1), ("a.color1", 0), ("a.color2", 3)]
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib
    assert len(ufo["a.color0"].components) == 0
    assert len(ufo["a.color0"]) == 1

    assert len(ufo["a.color1"].components) == 2
    assert len(ufo["a.color1"]) == 0

    assert len(ufo["a.color2"].components) == 1
    assert len(ufo["a.color2"]) == 0


def test_glyph_color_layers_no_unicode_mapping(ufo_module):
    font = generate_minimal_font()
    glypha = add_glyph(font, "a")

    glypha.unicode = "0061"

    color0 = GSLayer()
    color1 = GSLayer()
    color2 = GSLayer()
    color0.attributes["color"] = 1
    color1.attributes["color"] = 1
    color2.attributes["color"] = 1
    glypha.layers.append(color0)
    glypha.layers.append(color1)
    glypha.layers.append(color2)

    for i, layer in enumerate(glypha.layers):
        path = GSPath()
        path.nodes = [
            GSNode(position=(i + 0, i + 0), nodetype="line"),
            GSNode(position=(i + 100, i + 100), nodetype="line"),
            GSNode(position=(i + 200, i + 200), nodetype="line"),
            GSNode(position=(i + 300, i + 300), nodetype="line"),
        ]
        if i == 1:
            path.attributes["fillColor"] = [255, 124, 0, 225]
        elif i == 2:
            path.attributes["gradient"] = {
                "colors": [[[0, 0, 0, 255], 0], [[185, 0, 0, 255], 1]],
                "end": [0.2, 0.3],
                "start": [0.4, 0.09],
            }
        elif i == 3:
            path.attributes["gradient"] = {
                "colors": [[[185, 0, 0, 255], 0], [[0, 0, 0, 255], 1]],
                "end": [0.2, 0.3],
                "start": [0.4, 0.09],
                "type": "circle",
            }
        layer.paths.append(path)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font

    assert ufo["a"].unicode == 97
    assert ufo["a.color0"].unicode is None
    assert ufo["a.color1"].unicode is None


def test_glyph_color_layers_explode(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")

    color0 = GSLayer()
    color1 = GSLayer()
    color2 = GSLayer()
    color0.attributes["color"] = 1
    color1.attributes["color"] = 1
    color2.attributes["color"] = 1
    glypha.layers.append(color0)
    glypha.layers.append(color1)
    glypha.layers.append(color2)

    for i, layer in enumerate(glypha.layers):
        path = GSPath()
        path.nodes = [
            GSNode(position=(i + 0, i + 0), nodetype="line"),
            GSNode(position=(i + 100, i + 100), nodetype="line"),
            GSNode(position=(i + 200, i + 200), nodetype="line"),
            GSNode(position=(i + 300, i + 300), nodetype="line"),
        ]
        if i == 1:
            path.attributes["fillColor"] = [255, 124, 0, 225]
        elif i == 2:
            path.attributes["gradient"] = {
                "colors": [[[0, 0, 0, 255], 0], [[185, 0, 0, 255], 1]],
                "end": [0.2, 0.3],
                "start": [0.4, 0.09],
            }
        elif i == 3:
            path.attributes["gradient"] = {
                "colors": [[[185, 0, 0, 255], 0], [[0, 0, 0, 255], 1]],
                "end": [0.2, 0.3],
                "start": [0.4, 0.09],
                "type": "circle",
            }
        layer.paths.append(path)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"] == [
        [
            (1.0, 0.48627450980392156, 0.0, 0.8823529411764706),
            (0.0, 0.0, 0.0, 1.0),
            (0.7254901960784313, 0.0, 0.0, 1.0),
        ]
    ]
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "a.color0",
                    "Paint": {
                        "Alpha": 0.8823529411764706,
                        "Format": 2,
                        "PaletteIndex": 0,
                    },
                },
                {
                    "Format": 10,
                    "Glyph": "a.color1",
                    "Paint": {
                        "ColorLine": {
                            "ColorStop": [
                                {"Alpha": 1.0, "PaletteIndex": 1, "StopOffset": 0},
                                {"Alpha": 1.0, "PaletteIndex": 2, "StopOffset": 1},
                            ],
                            "Extend": "pad",
                        },
                        "Format": 4,
                        "x0": 122.0,
                        "x1": 62.0,
                        "x2": 185.0,
                        "y0": 29.0,
                        "y1": 92.0,
                        "y2": 89.0,
                    },
                },
                {
                    "Format": 10,
                    "Glyph": "a.color2",
                    "Paint": {
                        "ColorLine": {
                            "ColorStop": [
                                {"Alpha": 1.0, "PaletteIndex": 2, "StopOffset": 0},
                                {"Alpha": 1.0, "PaletteIndex": 1, "StopOffset": 1},
                            ],
                            "Extend": "pad",
                        },
                        "Format": 6,
                        "r0": 0,
                        "r1": 327.0,
                        "x0": 123.0,
                        "x1": 123.0,
                        "y0": 30.0,
                        "y1": 30.0,
                    },
                },
            ],
        }
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib


def test_glyph_color_layers_strokecolor(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")

    color = GSLayer()
    color.attributes["color"] = 1
    glypha.layers.append(color)

    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="line"),
        GSNode(position=(100, 100), nodetype="line"),
        GSNode(position=(200, 200), nodetype="line"),
        GSNode(position=(300, 300), nodetype="line"),
    ]
    path.attributes["strokeColor"] = [255, 124, 0, 225]
    color.paths.append(path)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"] == [
        [(1.0, 0.48627450980392156, 0.0, 0.8823529411764706)]
    ]
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "a.color0",
                    "Paint": {
                        "Alpha": 0.8823529411764706,
                        "Format": 2,
                        "PaletteIndex": 0,
                    },
                },
            ],
        }
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib
    assert len(ufo["a.color0"]) == 2
    pen = _PointDataPen()
    ufo["a.color0"].drawPoints(pen)
    assert pen.contours == [
        [
            (299.6464538574219, 300.3535461425781, "line", False),
            (-0.3535533845424652, 0.3535533845424652, "line", False),
            (0.3535533845424652, -0.3535533845424652, "line", False),
            (100.35355377197266, 99.64644622802734, "line", False),
            (200.35354614257812, 199.64645385742188, "line", False),
            (300.3535461425781, 299.6464538574219, "line", False),
        ],
        [
            (300.3535461425781, 299.6464538574219, "line", False),
            (300.0, 300.0, "line", False),
            (299.6464538574219, 300.3535461425781, "line", False),
            (199.64645385742188, 200.35354614257812, "line", False),
            (99.64644622802734, 100.35355377197266, "line", False),
            (-0.3535533845424652, 0.3535533845424652, "line", False),
            (0.0, 0.0, "line", False),
            (0.3535533845424652, -0.3535533845424652, "line", False),
        ],
    ]


def test_glyph_color_layers_strokewidth(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")

    color = GSLayer()
    color.attributes["color"] = 1
    glypha.layers.append(color)

    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="line"),
        GSNode(position=(100, 100), nodetype="line"),
        GSNode(position=(200, 200), nodetype="line"),
        GSNode(position=(300, 300), nodetype="line"),
    ]
    path.attributes["strokeWidth"] = 10
    color.paths.append(path)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert "com.github.googlei18n.ufo2ft.colorPalettes" not in ufo.lib
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "a.color0",
                    "Paint": {"Alpha": 1, "Format": 2, "PaletteIndex": 0xFFFF},
                },
            ],
        }
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib
    assert len(ufo["a.color0"]) == 2
    pen = _PointDataPen()
    ufo["a.color0"].drawPoints(pen)
    assert pen.contours == [
        [
            (296.4644775390625, 303.5355224609375, "line", False),
            (-3.535533905029297, 3.535533905029297, "line", False),
            (3.535533905029297, -3.535533905029297, "line", False),
            (103.53553771972656, 96.46446228027344, "line", False),
            (203.53553771972656, 196.46446228027344, "line", False),
            (303.5355224609375, 296.4644775390625, "line", False),
        ],
        [
            (303.5355224609375, 296.4644775390625, "line", False),
            (300.0, 300.0, "line", False),
            (296.4644775390625, 303.5355224609375, "line", False),
            (196.46446228027344, 203.53553771972656, "line", False),
            (96.46446228027344, 103.53553771972656, "line", False),
            (-3.535533905029297, 3.535533905029297, "line", False),
            (0.0, 0.0, "line", False),
            (3.535533905029297, -3.535533905029297, "line", False),
        ],
    ]


def test_glyph_color_layers_stroke_no_attributes(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")

    color = GSLayer()
    color.attributes["color"] = 1
    glypha.layers.append(color)

    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="line"),
        GSNode(position=(100, 100), nodetype="line"),
        GSNode(position=(200, 200), nodetype="line"),
        GSNode(position=(300, 300), nodetype="line"),
    ]
    color.paths.append(path)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert "com.github.googlei18n.ufo2ft.colorPalettes" not in ufo.lib
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "a.color0",
                    "Paint": {"Alpha": 1, "Format": 2, "PaletteIndex": 0xFFFF},
                },
            ],
        }
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib
    assert len(ufo["a.color0"]) == 2
    pen = _PointDataPen()
    ufo["a.color0"].drawPoints(pen)
    assert pen.contours == [
        [
            (299.6464538574219, 300.3535461425781, "line", False),
            (-0.3535533845424652, 0.3535533845424652, "line", False),
            (0.3535533845424652, -0.3535533845424652, "line", False),
            (100.35355377197266, 99.64644622802734, "line", False),
            (200.35354614257812, 199.64645385742188, "line", False),
            (300.3535461425781, 299.6464538574219, "line", False),
        ],
        [
            (300.3535461425781, 299.6464538574219, "line", False),
            (300.0, 300.0, "line", False),
            (299.6464538574219, 300.3535461425781, "line", False),
            (199.64645385742188, 200.35354614257812, "line", False),
            (99.64644622802734, 100.35355377197266, "line", False),
            (-0.3535533845424652, 0.3535533845424652, "line", False),
            (0.0, 0.0, "line", False),
            (0.3535533845424652, -0.3535533845424652, "line", False),
        ],
    ]


def test_glyph_color_layers_component(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")
    glyphb = add_glyph(font, "b")

    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="line"),
        GSNode(position=(100, 100), nodetype="line"),
        GSNode(position=(200, 200), nodetype="line"),
        GSNode(position=(300, 300), nodetype="line"),
    ]
    glyphb.layers[0].paths.append(path)
    comp = GSComponent(glyph=glyphb)

    color = GSLayer()
    color.attributes["color"] = 1
    color.components.append(comp)
    glypha.layers.append(color)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert "com.github.googlei18n.ufo2ft.colorPalettes" not in ufo.lib
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "a.color0",
                    "Paint": {"Alpha": 1, "Format": 2, "PaletteIndex": 0xFFFF},
                },
            ],
        }
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib
    assert len(ufo["a.color0"]) == 2
    pen = _PointDataPen()
    ufo["a.color0"].drawPoints(pen)
    assert pen.contours == [
        [
            (299.6464538574219, 300.3535461425781, "line", False),
            (-0.3535533845424652, 0.3535533845424652, "line", False),
            (0.3535533845424652, -0.3535533845424652, "line", False),
            (100.35355377197266, 99.64644622802734, "line", False),
            (200.35354614257812, 199.64645385742188, "line", False),
            (300.3535461425781, 299.6464538574219, "line", False),
        ],
        [
            (300.3535461425781, 299.6464538574219, "line", False),
            (300.0, 300.0, "line", False),
            (299.6464538574219, 300.3535461425781, "line", False),
            (199.64645385742188, 200.35354614257812, "line", False),
            (99.64644622802734, 100.35355377197266, "line", False),
            (-0.3535533845424652, 0.3535533845424652, "line", False),
            (0.0, 0.0, "line", False),
            (0.3535533845424652, -0.3535533845424652, "line", False),
        ],
    ]


def test_glyph_color_layers_component_color(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")
    glyphb = add_glyph(font, "b")

    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="line"),
        GSNode(position=(100, 100), nodetype="line"),
        GSNode(position=(200, 200), nodetype="line"),
        GSNode(position=(300, 300), nodetype="line"),
    ]
    path.attributes["gradient"] = {
        "colors": [[[255, 255, 255, 255], 0], [[0, 0, 0, 255], 1]],
        "end": [0.2, 0.3],
        "start": [0.4, 0.09],
        "type": "circle",
    }
    glyphb.layers[0].attributes["color"] = 1
    glyphb.layers[0].paths.append(path)
    comp = GSComponent(glyph=glyphb)

    color = GSLayer()
    color.attributes["color"] = 1
    color.components.append(comp)
    glypha.layers.append(color)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font

    assert "a.color0" not in ufo
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"] == [
        [(1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0)]
    ]
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {"Format": 1, "Layers": [{"Format": 11, "Glyph": "b"}]},
        "b": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "b",
                    "Paint": {
                        "Format": 6,
                        "ColorLine": {
                            "Extend": "pad",
                            "ColorStop": [
                                {"StopOffset": 0, "Alpha": 1.0, "PaletteIndex": 0},
                                {"StopOffset": 1, "Alpha": 1.0, "PaletteIndex": 1},
                            ],
                        },
                        "x0": 120.0,
                        "y0": 27.0,
                        "x1": 120.0,
                        "y1": 27.0,
                        "r0": 0,
                        "r1": 327.0,
                    },
                }
            ],
        },
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib


def test_glyph_color_layers_component_color_translate(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")
    glyphb = add_glyph(font, "b")

    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="line"),
        GSNode(position=(100, 100), nodetype="line"),
        GSNode(position=(200, 200), nodetype="line"),
        GSNode(position=(300, 300), nodetype="line"),
    ]
    path.attributes["gradient"] = {
        "colors": [[[255, 255, 255, 255], 0], [[0, 0, 0, 255], 1]],
        "end": [0.2, 0.3],
        "start": [0.4, 0.09],
        "type": "circle",
    }
    glyphb.layers[0].attributes["color"] = 1
    glyphb.layers[0].paths.append(path)
    comp = GSComponent(glyph=glyphb, offset=(100, 20))

    color = GSLayer()
    color.attributes["color"] = 1
    color.components.append(comp)
    glypha.layers.append(color)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font

    assert "a.color0" not in ufo
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"] == [
        [(1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0)]
    ]
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 14,
                    "Paint": {"Format": 11, "Glyph": "b"},
                    "dx": 100,
                    "dy": 20,
                }
            ],
        },
        "b": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "b",
                    "Paint": {
                        "Format": 6,
                        "ColorLine": {
                            "Extend": "pad",
                            "ColorStop": [
                                {"StopOffset": 0, "Alpha": 1.0, "PaletteIndex": 0},
                                {"StopOffset": 1, "Alpha": 1.0, "PaletteIndex": 1},
                            ],
                        },
                        "x0": 120.0,
                        "y0": 27.0,
                        "x1": 120.0,
                        "y1": 27.0,
                        "r0": 0,
                        "r1": 327.0,
                    },
                }
            ],
        },
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib


def test_glyph_color_layers_component_color_transform(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")
    glyphb = add_glyph(font, "b")

    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="line"),
        GSNode(position=(100, 100), nodetype="line"),
        GSNode(position=(200, 200), nodetype="line"),
        GSNode(position=(300, 300), nodetype="line"),
    ]
    path.attributes["gradient"] = {
        "colors": [[[255, 255, 255, 255], 0], [[0, 0, 0, 255], 1]],
        "end": [0.2, 0.3],
        "start": [0.4, 0.09],
        "type": "circle",
    }
    glyphb.layers[0].attributes["color"] = 1
    glyphb.layers[0].paths.append(path)
    comp = GSComponent(glyph=glyphb, transform=(-1.0, 0.0, 0.0, -1.0, 282, 700))

    color = GSLayer()
    color.attributes["color"] = 1
    color.components.append(comp)
    glypha.layers.append(color)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font

    assert "a.color0" not in ufo
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"] == [
        [(1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0)]
    ]
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 12,
                    "Paint": {"Format": 11, "Glyph": "b"},
                    "Transform": (-1.0, 0.0, 0.0, -1.0, 282, 700),
                }
            ],
        },
        "b": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "b",
                    "Paint": {
                        "Format": 6,
                        "ColorLine": {
                            "Extend": "pad",
                            "ColorStop": [
                                {"StopOffset": 0, "Alpha": 1.0, "PaletteIndex": 0},
                                {"StopOffset": 1, "Alpha": 1.0, "PaletteIndex": 1},
                            ],
                        },
                        "x0": 120.0,
                        "y0": 27.0,
                        "x1": 120.0,
                        "y1": 27.0,
                        "r0": 0,
                        "r1": 327.0,
                    },
                }
            ],
        },
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib


def test_glyph_color_layers_group_paths(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")

    color = GSLayer()
    color.attributes["color"] = 1
    glypha.layers.append(color)

    for i in range(2):
        path = GSPath()
        path.nodes = [
            GSNode(position=(i + 0, i + 0), nodetype="line"),
            GSNode(position=(i + 100, i + 100), nodetype="line"),
            GSNode(position=(i + 200, i + 200), nodetype="line"),
            GSNode(position=(i + 300, i + 300), nodetype="line"),
        ]
        path.attributes["gradient"] = {
            "colors": [[[255, 255, 255, 255], 0], [[0, 0, 0, 255], 1]],
            "end": [0.2, 0.3],
            "start": [0.4, 0.09],
            "type": "circle",
        }
        color.paths.append(path)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"] == [
        [(1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0)]
    ]
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "a.color0",
                    "Paint": {
                        "ColorLine": {
                            "ColorStop": [
                                {"Alpha": 1.0, "PaletteIndex": 0, "StopOffset": 0},
                                {"Alpha": 1.0, "PaletteIndex": 1, "StopOffset": 1},
                            ],
                            "Extend": "pad",
                        },
                        "Format": 6,
                        "r0": 0,
                        "r1": 328.09000000000003,
                        "x0": 120.4,
                        "x1": 120.4,
                        "y0": 27.09,
                        "y1": 27.09,
                    },
                }
            ],
        }
    }

    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib


def test_glyph_color_layers_group_paths_nonconsecutive(ufo_module):
    font = generate_minimal_font(format_version=3)
    glypha = add_glyph(font, "a")

    color = GSLayer()
    color.attributes["color"] = 1
    glypha.layers.append(color)

    for i in range(3):
        path = GSPath()
        path.nodes = [
            GSNode(position=(i + 0, i + 0), nodetype="line"),
            GSNode(position=(i + 100, i + 100), nodetype="line"),
            GSNode(position=(i + 200, i + 200), nodetype="line"),
            GSNode(position=(i + 300, i + 300), nodetype="line"),
        ]
        path.attributes["gradient"] = {
            "colors": [[[255, 255, 255, 255], 0], [[0, 0, 0, 255], 1]],
            "end": [0.2, 0.3],
            "start": [0.4, 0.09],
            "type": "circle",
        }
        if i == 1:
            path.attributes["foo"] = True
        color.paths.append(path)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"] == [
        [(1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0)]
    ]
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "a.color0",
                    "Paint": {
                        "ColorLine": {
                            "ColorStop": [
                                {"Alpha": 1.0, "PaletteIndex": 0, "StopOffset": 0},
                                {"Alpha": 1.0, "PaletteIndex": 1, "StopOffset": 1},
                            ],
                            "Extend": "pad",
                        },
                        "Format": 6,
                        "r0": 0,
                        "r1": 327.0,
                        "x0": 120.0,
                        "x1": 120.0,
                        "y0": 27.0,
                        "y1": 27.0,
                    },
                },
                {
                    "Format": 10,
                    "Glyph": "a.color1",
                    "Paint": {
                        "ColorLine": {
                            "ColorStop": [
                                {"Alpha": 1.0, "PaletteIndex": 0, "StopOffset": 0},
                                {"Alpha": 1.0, "PaletteIndex": 1, "StopOffset": 1},
                            ],
                            "Extend": "pad",
                        },
                        "Format": 6,
                        "r0": 0,
                        "r1": 327.0,
                        "x0": 121.0,
                        "x1": 121.0,
                        "y0": 28.0,
                        "y1": 28.0,
                    },
                },
                {
                    "Format": 10,
                    "Glyph": "a.color2",
                    "Paint": {
                        "ColorLine": {
                            "ColorStop": [
                                {"Alpha": 1.0, "PaletteIndex": 0, "StopOffset": 0},
                                {"Alpha": 1.0, "PaletteIndex": 1, "StopOffset": 1},
                            ],
                            "Extend": "pad",
                        },
                        "Format": 6,
                        "r0": 0,
                        "r1": 327.0,
                        "x0": 122.0,
                        "x1": 122.0,
                        "y0": 29.0,
                        "y1": 29.0,
                    },
                },
            ],
        }
    }

    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib


def test_glyph_color_layers_master_layer(ufo_module):
    font = generate_minimal_font(format_version=3)
    glyph = add_glyph(font, "a")

    layer = glyph.layers[0]
    layer.attributes["color"] = 1

    for i in range(2):
        path = GSPath()
        path.nodes = [
            GSNode(position=(i + 0, i + 0), nodetype="line"),
            GSNode(position=(i + 100, i + 100), nodetype="line"),
            GSNode(position=(i + 200, i + 200), nodetype="line"),
            GSNode(position=(i + 300, i + 300), nodetype="line"),
        ]
        path.attributes["gradient"] = {
            "colors": [[[0 + i, 0, 0, 255], 0], [[185 + i, 0, 0, 255], 1]],
            "end": [0.2 + i, 0.3 + i],
            "start": [0.4 + i, 0.09 + i],
        }
        layer.paths.append(path)

    ds = to_designspace(font, ufo_module=ufo_module, minimal=True)
    ufo = ds.sources[0].font
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"] == [
        [
            (0.0, 0.0, 0.0, 1.0),
            (0.7254901960784313, 0.0, 0.0, 1.0),
            (0.00392156862745098, 0.0, 0.0, 1.0),
            (0.7294117647058823, 0.0, 0.0, 1.0),
        ]
    ]
    assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
        "a": {
            "Format": 1,
            "Layers": [
                {
                    "Format": 10,
                    "Glyph": "a.color0",
                    "Paint": {
                        "ColorLine": {
                            "ColorStop": [
                                {"Alpha": 1.0, "PaletteIndex": 0, "StopOffset": 0},
                                {"Alpha": 1.0, "PaletteIndex": 1, "StopOffset": 1},
                            ],
                            "Extend": "pad",
                        },
                        "Format": 4,
                        "x0": 120.0,
                        "x1": 60.0,
                        "x2": 183.0,
                        "y0": 27.0,
                        "y1": 90.0,
                        "y2": 87.0,
                    },
                },
                {
                    "Format": 10,
                    "Glyph": "a.color1",
                    "Paint": {
                        "ColorLine": {
                            "ColorStop": [
                                {"Alpha": 1.0, "PaletteIndex": 2, "StopOffset": 0},
                                {"Alpha": 1.0, "PaletteIndex": 3, "StopOffset": 1},
                            ],
                            "Extend": "pad",
                        },
                        "Format": 4,
                        "x0": 421.0,
                        "x1": 361.0,
                        "x2": 484.0,
                        "y0": 328.0,
                        "y1": 391.0,
                        "y2": 388.0,
                    },
                },
            ],
        }
    }
    assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["a"].lib


def test_master_with_light_weight_but_thin_name(ufo_module):
    font = generate_minimal_font()
    master = font.masters[0]
    name = "Thin"  # In Glyphs.app, show "Thin" in the sidebar
    weight = "Light"  # In Glyphs.app, have the light "n" icon
    width = None  # No data => should be equivalent to Regular
    custom_name = "Thin"
    master.set_all_name_components(name, weight, width, custom_name)
    assert master.name == "Thin"
    assert master.weight == "Light"

    (ufo,) = to_ufos(font, ufo_module=ufo_module)
    font_rt = to_glyphs([ufo])
    master_rt = font_rt.masters[0]

    assert master_rt.name == "Thin"
    assert master_rt.weight == "Light"

    tmpdir = tempfile.mkdtemp()
    try:
        filename = os.path.join(tmpdir, "test.glyphs")
        font_rt.save(filename)
        font_rt_written = GSFont(filename)

        master_rt_written = font_rt_written.masters[0]

        assert master_rt_written.name == "Thin"
        assert master_rt_written.weight == "Light"
    finally:
        shutil.rmtree(tmpdir)


def test_italic_angle(ufo_module):
    font = generate_minimal_font()
    (ufo,) = to_ufos(font, ufo_module=ufo_module)

    ufo.info.italicAngle = 1
    (ufo_rt,) = to_ufos(to_glyphs([ufo]))
    assert ufo_rt.info.italicAngle == 1

    ufo.info.italicAngle = 1.5
    (ufo_rt,) = to_ufos(to_glyphs([ufo]))
    assert ufo_rt.info.italicAngle == 1.5

    ufo.info.italicAngle = 0
    font_rt = to_glyphs([ufo])
    assert font_rt.masters[0].italicAngle == 0
    (ufo_rt,) = to_ufos(font_rt)
    assert ufo_rt.info.italicAngle == 0


def test_unique_masterid(ufo_module):
    font = generate_minimal_font()
    master2 = GSFontMaster()
    master2.ascender = 0
    master2.capHeight = 0
    master2.descender = 0
    master2.xHeight = 0
    font.masters.append(master2)
    ufos = to_ufos(font, minimize_glyphs_diffs=True)

    to_glyphs(ufos)

    ufos[1].lib["com.schriftgestaltung.fontMasterID"] = ufos[0].lib[
        "com.schriftgestaltung.fontMasterID"
    ]

    font_rt = to_glyphs(ufos)
    assert len({m.id for m in font_rt.masters}) == 2


def test_custom_glyph_data(ufo_module):
    font = generate_minimal_font()
    for glyph_name in ("A", "Aitalic-math", "Aitalic-math.ssty1", "foo", "bar", "baz"):
        add_glyph(font, glyph_name)
    # add a composite glyph to trigger propagate_anchors
    add_component(font, "bar", "baz", (1, 0, 0, 1, 0, 0))
    font.glyphs["baz"].production = "bazglyph"
    font.glyphs["baz"].category = "Number"
    font.glyphs["baz"].subCategory = "Decimal Digit"
    font.glyphs["baz"].script = "Arabic"
    filename = os.path.join(
        os.path.dirname(__file__), "..", "data", "CustomGlyphData.xml"
    )
    (ufo,) = to_ufos(font, minimize_glyphs_diffs=True, glyph_data=[filename])

    postscriptNames = ufo.lib.get("public.postscriptNames")
    categoryKey = "com.schriftgestaltung.Glyphs.category"
    subCategoryKey = "com.schriftgestaltung.Glyphs.subCategory"
    scriptKey = "com.schriftgestaltung.Glyphs.script"
    assert postscriptNames is not None
    # default, only in GlyphData.xml
    assert postscriptNames.get("A") is None
    lib = ufo["A"].lib
    assert lib.get(categoryKey) is None
    assert lib.get(subCategoryKey) is None
    assert lib.get(scriptKey) is None

    assert postscriptNames.get("Aitalic-math") == "u1D434"
    assert postscriptNames.get("Aitalic-math.ssty1") == "u1D434.ssty1"

    # from customGlyphData.xml
    lib = ufo["foo"].lib
    assert postscriptNames.get("foo") == "fooprod"
    assert lib.get(categoryKey) == "Letter"
    assert lib.get(subCategoryKey) == "Lowercase"
    assert lib.get(scriptKey) == "Latin"
    # from CustomGlyphData.xml instead of GlyphData.xml
    lib = ufo["bar"].lib
    assert postscriptNames.get("bar") == "barprod"
    assert lib.get(categoryKey) == "Mark"
    assert lib.get(subCategoryKey) == "Nonspacing"
    assert lib.get(scriptKey) == "Latin"
    # from glyph attributes instead of CustomGlyphData.xml
    lib = ufo["baz"].lib
    assert postscriptNames.get("baz") == "bazglyph"
    assert lib.get(categoryKey) == "Number"
    assert lib.get(subCategoryKey) == "Decimal Digit"
    assert lib.get(scriptKey) == "Arabic"


def test_load_kerning_bracket(ufo_module):
    filename = os.path.join(
        os.path.dirname(__file__), "..", "data", "BracketTestFontKerning.glyphs"
    )
    with open(filename) as f:
        font = glyphsLib.load(f)

    ds = glyphsLib.to_designspace(font, minimize_glyphs_diffs=True)
    bracketed_groups = {
        "public.kern2.foo": ["a", "a.BRACKET.varAlt01"],
        "public.kern1.foo": ["x", "x.BRACKET.varAlt01", "x.BRACKET.varAlt02"],
    }
    assert ds.sources[0].font.groups == bracketed_groups
    assert ds.sources[1].font.groups == bracketed_groups
    assert ds.sources[2].font.groups == bracketed_groups
    assert ds.sources[3].font.groups == bracketed_groups
    assert ds.sources[0].font.kerning == {
        ("public.kern1.foo", "public.kern2.foo"): -200,
        ("a", "x"): -100,
        ("a.BRACKET.varAlt01", "x"): -100,
        ("a", "x.BRACKET.varAlt01"): -100,
        ("a.BRACKET.varAlt01", "x.BRACKET.varAlt01"): -100,
        ("a", "x.BRACKET.varAlt02"): -100,
        ("a.BRACKET.varAlt01", "x.BRACKET.varAlt02"): -100,
    }
    assert ds.sources[1].font.kerning == {}
    assert ds.sources[2].font.kerning == {
        ("public.kern1.foo", "public.kern2.foo"): -300
    }
    assert ds.sources[3].font.kerning == {}

    font2 = glyphsLib.to_glyphs(ds, minimize_ufo_diffs=True)
    assert font2.kerning == {
        "1034EC4A-9832-4D17-A75A-2B17BF7C4AA6": {
            "@MMK_L_foo": {"@MMK_R_foo": -200},
            "a": {"x": -100},
        },
        "C402BD76-83A2-4350-9191-E5499E97AF5D": {"@MMK_L_foo": {"@MMK_R_foo": -300}},
    }

    ds2 = glyphsLib.to_designspace(font, minimize_glyphs_diffs=True)
    bracketed_groups = {
        "public.kern2.foo": ["a", "a.BRACKET.varAlt01"],
        "public.kern1.foo": ["x", "x.BRACKET.varAlt01", "x.BRACKET.varAlt02"],
    }
    assert ds2.sources[0].font.groups == bracketed_groups
    assert ds2.sources[1].font.groups == bracketed_groups
    assert ds2.sources[2].font.groups == bracketed_groups
    assert ds2.sources[3].font.groups == bracketed_groups
    assert ds2.sources[0].font.kerning == {
        ("public.kern1.foo", "public.kern2.foo"): -200,
        ("a", "x"): -100,
        ("a.BRACKET.varAlt01", "x"): -100,
        ("a", "x.BRACKET.varAlt01"): -100,
        ("a.BRACKET.varAlt01", "x.BRACKET.varAlt01"): -100,
        ("a", "x.BRACKET.varAlt02"): -100,
        ("a.BRACKET.varAlt01", "x.BRACKET.varAlt02"): -100,
    }
    assert ds2.sources[1].font.kerning == {}
    assert ds2.sources[2].font.kerning == {
        ("public.kern1.foo", "public.kern2.foo"): -300
    }
    assert ds2.sources[3].font.kerning == {}


def test_unicode_variation_sequences(ufo_module):
    font = generate_minimal_font()
    add_glyph(font, "zero")["unicode"] = f"{ord('0'):04x}"
    add_glyph(font, "zero.uv001")
    add_glyph(font, "zero.uv255")
    add_glyph(font, "u1F170")["unicode"] = "1F170"
    add_glyph(font, "u1F170.uv015")
    add_glyph(font, "u2EA41")["unicode"] = "2EA41"
    add_glyph(font, "u2EA41.uv019")
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    unicodeVariationSequences = ufo.lib.get("public.unicodeVariationSequences")
    assert unicodeVariationSequences == {
        "FE00": {"0030": "zero.uv001"},
        "FE0E": {"1F170": "u1F170.uv015"},
        "E0102": {"2EA41": "u2EA41.uv019"},
        "E01EE": {"0030": "zero.uv255"},
    }


class _PointDataPen:
    def __init__(self, **kwargs):
        self.contours = []

    def addPoint(self, pt, segmentType=None, smooth=False, **kwargs):
        self.contours[-1].append((pt[0], pt[1], segmentType, smooth))

    def beginPath(self, **kwargs):
        self.contours.append([])

    def endPath(self, **kwargs):
        if not self.contours[-1]:
            self.contours.pop()

    def addComponent(self, *args, **kwargs):
        pass


class _Glyph:
    def __init__(self):
        self.pen = _PointDataPen()

    def getPointPen(self):
        return self.pen


class _UFOBuilder:
    def to_ufo_node_user_data(self, *args):
        pass


def test_to_ufo_draw_paths_empty_nodes(ufo_module):
    layer = GSLayer()
    layer.paths.append(GSPath())

    glyph = _Glyph()
    to_ufo_paths(_UFOBuilder(), glyph, layer)

    assert glyph.pen.contours == []


def test_to_ufo_draw_paths_open(ufo_module):
    layer = GSLayer()
    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="line"),
        GSNode(position=(1, 1), nodetype="offcurve"),
        GSNode(position=(2, 2), nodetype="offcurve"),
        GSNode(position=(3, 3), nodetype="curve", smooth=True),
    ]
    path.closed = False
    layer.paths.append(path)
    glyph = _Glyph()
    to_ufo_paths(_UFOBuilder(), glyph, layer)

    assert glyph.pen.contours == [
        [
            (0, 0, "move", False),
            (1, 1, None, False),
            (2, 2, None, False),
            (3, 3, "curve", True),
        ]
    ]


def test_to_ufo_draw_paths_closed(ufo_module):
    layer = GSLayer()
    path = GSPath()
    path.nodes = [
        GSNode(position=(0, 0), nodetype="offcurve"),
        GSNode(position=(1, 1), nodetype="offcurve"),
        GSNode(position=(2, 2), nodetype="curve", smooth=True),
        GSNode(position=(3, 3), nodetype="offcurve"),
        GSNode(position=(4, 4), nodetype="offcurve"),
        GSNode(position=(5, 5), nodetype="curve", smooth=True),
    ]
    path.closed = True
    layer.paths.append(path)

    glyph = _Glyph()
    to_ufo_paths(_UFOBuilder(), glyph, layer)

    points = glyph.pen.contours[0]

    first_x, first_y = points[0][:2]
    assert (first_x, first_y) == (5, 5)

    first_segment_type = points[0][2]
    assert first_segment_type == "curve"


def test_to_ufo_draw_paths_qcurve(ufo_module):
    layer = GSLayer()
    path = GSPath()
    path.nodes = [
        GSNode(position=(143, 695), nodetype="offcurve"),
        GSNode(position=(37, 593), nodetype="offcurve"),
        GSNode(position=(37, 434), nodetype="offcurve"),
        GSNode(position=(143, 334), nodetype="offcurve"),
        GSNode(position=(223, 334), nodetype="qcurve", smooth=True),
    ]
    path.closed = True
    layer.paths.append(path)

    glyph = _Glyph()
    to_ufo_paths(_UFOBuilder(), glyph, layer)

    points = glyph.pen.contours[0]

    first_x, first_y = points[0][:2]
    assert (first_x, first_y) == (223, 334)

    first_segment_type = points[0][2]
    assert first_segment_type == "qcurve"


def test_glyph_color(ufo_module):
    font = generate_minimal_font()
    glyph = GSGlyph(name="a")
    glyph2 = GSGlyph(name="b")
    glyph3 = GSGlyph(name="c")
    glyph4 = GSGlyph(name="d")
    glyph.color = [244, 0, 138, 1]
    glyph2.color = 3
    glyph3.color = 88
    glyph4.color = [800, 0, 138, 255]
    font.glyphs.append(glyph)
    font.glyphs.append(glyph2)
    font.glyphs.append(glyph3)
    font.glyphs.append(glyph4)
    layer = GSLayer()
    layer2 = GSLayer()
    layer3 = GSLayer()
    layer4 = GSLayer()
    layer.layerId = font.masters[0].id
    layer2.layerId = font.masters[0].id
    layer3.layerId = font.masters[0].id
    layer4.layerId = font.masters[0].id
    glyph.layers.append(layer)
    glyph2.layers.append(layer2)
    glyph3.layers.append(layer3)
    glyph4.layers.append(layer4)
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert ufo["a"].lib.get("public.markColor") == "0.957,0,0.541,0.004"
    assert ufo["b"].lib.get("public.markColor") == "0.97,1,0,1"
    assert ufo["c"].lib.get("public.markColor") is None
    assert ufo["d"].lib.get("public.markColor") is None


def test_anchor_assignment(ufo_module):
    filename = os.path.join(
        os.path.dirname(__file__), "..", "data", "AnchorAttachmentTest.glyphs"
    )
    with open(filename) as f:
        font = glyphsLib.load(f)

    assert (
        font.glyphs["circumflexcomb_acutecomb"].layers[0].components[1].anchor
        == "top_viet"
    )
    assert not (font.glyphs["circumflexcomb_tildecomb"].layers[0].components[1].anchor)

    ds = to_designspace(font, ufo_module=ufo_module)
    ufo = ds.sources[0].font
    assert ufo["circumflexcomb_acutecomb"].lib[GLYPHLIB_PREFIX + "ComponentInfo"] == [
        {"anchor": "top_viet", "index": 1, "name": "acutecomb"}
    ]
    assert (
        ufo["circumflexcomb_tildecomb"].lib.get(GLYPHLIB_PREFIX + "ComponentInfo")
        is None
    )

    font2 = to_glyphs(ds)
    assert (
        font2.glyphs["circumflexcomb_acutecomb"].layers[0].components[1].anchor
        == "top_viet"
    )

    assert not (font2.glyphs["circumflexcomb_tildecomb"].layers[0].components[1].anchor)

    ufo["circumflexcomb_acutecomb"].lib[GLYPHLIB_PREFIX + "ComponentInfo"] = [
        {"anchor": "top_viet", "index": 1, "name": "asadad"}
    ]
    font3 = to_glyphs(ds)
    assert not font3.glyphs["circumflexcomb_acutecomb"].layers[0].components[1].anchor


class TestSkipDanglingAndNamelessLayers:
    def setup_method(self, ufo_module):
        self.font = generate_minimal_font()
        add_glyph(self.font, "a")

    def test_normal_layer(self, ufo_module, caplog):
        to_ufos(self.font, ufo_module=ufo_module)

        # no warnings are emitted
        assert not any(
            ["is dangling and will be skipped" in x.message for x in caplog.records]
        )
        assert not any(["layer without a name" in x.message for x in caplog.records])

    def test_nameless_layer_minimal(self, caplog, ufo_module):
        self.font.glyphs[0].layers[0].associatedMasterId = "xxx"
        to_ufos(self.font, ufo_module=ufo_module, minimize_glyphs_diffs=True)
        assert ["layer without a name" in x.message for x in caplog.records]

    def test_nameless_layer(self, caplog, ufo_module):
        self.font.glyphs[0].layers[0].associatedMasterId = "xxx"
        # no warning if minimize_glyphs_diff=False
        to_ufos(self.font, ufo_module=ufo_module, minimize_glyphs_diffs=False)
        assert not any(["layer without a name" in x.message for x in caplog.records])
        assert not caplog.records

    def test_dangling_layer(self, caplog, ufo_module):
        self.font.glyphs[0].layers[0].layerId = "yyy"
        self.font.glyphs[0].layers[0].associatedMasterId = "xxx"

        to_ufos(self.font, ufo_module=ufo_module, minimize_glyphs_diffs=True)
        assert ["is dangling and will be skipped" in x.message for x in caplog.records]


class TestGlyphOrder:
    #     """Check that the glyphOrder data is persisted correctly in all directions.

    #     When Glyphs 2.6.1 opens a UFO with a public.glyphOrder key and...

    #     1. ... no com.schriftgestaltung.glyphOrder key, it will copy
    #        public.glyphOrder verbatim to the font's custom parameter glyphOrder,
    #        including non-existant glyphs. It will sort the glyphs in the font
    #        overview ("Predefined Sorting") as specified by the font's custom
    #        parameter glyphOrder.
    #     2. ... a com.schriftgestaltung.glyphOrder key set to a list of glyph names,
    #        it will copy com.schriftgestaltung.glyphOrder verbatim to the font's custom
    #        parameter glyphOrder, including non-existant glyphs. It will not reorder
    #        the glyphs and instead display them as specified in public.glyphOrder. If
    #        the glyphs aren't grouped by category, it may make repeated category groups
    #        (e.g. Separator: .notdef, Punctuation: period, Separator: nbspace).
    #     3. ... a com.schriftgestaltung.glyphOrder key set to False, it will not
    #        copy public.glyphOrder at all and there is no font custom parameter
    #        glyphOrder. It will also not sort the glyphs in the font overview and
    #        instead display them as specified in public.glyphOrder. Round-tripping
    #        back will therefore overwrite public.glyphOrder with the order of the
    #        .glyphs file.

    #     When Glyphs 2.6.1 opens a UFO _without_ a public.glyphOrder key and...

    #     1. ... no com.schriftgestaltung.glyphOrder key, it will sort the glyphs in
    #        the font overview in the typical Glyphs way and not create a font custom
    #        parameter glyphOrder.
    #     2. ... a com.schriftgestaltung.glyphOrder key set to a list of glyph names,
    #        it will copy com.schriftgestaltung.glyphOrder verbatim to the font's custom
    #        parameter glyphOrder, including non-existant glyphs and will sort the
    #        glyphs in the font overview ("Predefined Sorting") as specified by the
    #        font's custom parameter glyphOrder.
    #     3. ... a com.schriftgestaltung.glyphOrder key set to False, it will sort
    #        the glyphs in the typical Glyphs way and not create a font custom parameter
    #        glyphOrder.

    #     Our Strategy:

    #     1. If a UFO's public.glyphOrder key...
    #         1. exists: write it to the Glyph font-level glyphOrder custom parameter.
    #         2. does not exist: Do not write a Glyph font-level glyphOrder custom
    #            parameter, the order of glyphs is then undefined.
    #     2. If the Glyph font-level glyphOrder custom parameter...
    #         1. exists: write it to a UFO's public.glyphOrder key.
    #         2. does not exist: write the order of Glyphs glyphs into a UFO's
    #            public.glyphOrder key.
    #         (This means that glyphs2ufo will *always* write a public.glyphOrder)
    #     3. Ignore the com.schriftgestaltung.glyphOrder key.
    #     """
    def prepare(self, ufo_module):
        self.font = GSFont()
        self.font.masters.append(GSFontMaster())
        self.font.glyphs.append(GSGlyph("c"))
        self.font.glyphs.append(GSGlyph("a"))
        self.font.glyphs.append(GSGlyph("f"))

        self.ufo = ufo_module.Font()
        self.ufo.newGlyph("c")
        self.ufo.newGlyph("a")
        self.ufo.newGlyph("f")
        if "public.glyphOrder" in self.ufo.lib:
            del self.ufo.lib["public.glyphOrder"]  # defcon automatism

    def from_glyphs(self, ufo_module):
        builder = UFOBuilder(self.font, ufo_module=ufo_module)
        return next(iter(builder.masters))

    def from_ufo(self):
        builder = GlyphsBuilder([self.ufo])
        return builder.font

    def test_ufo_to_glyphs_with_glyphOrder(self, ufo_module):
        self.prepare(ufo_module)
        self.ufo.lib["public.glyphOrder"] = ["c", "xxx1", "f", "xxx2"]
        self.ufo.lib[GLYPHS_PREFIX + "glyphOrder"] = ["a", "b", "c", "d"]
        font = self.from_ufo()
        assert ["c", "xxx1", "f", "xxx2"] == font.customParameters["glyphOrder"]
        # NOTE: Glyphs not present in public.glyphOrder are appended. Appending order
        # is undefined.
        assert ["c", "f", "a"] == [glyph.name for glyph in font.glyphs]

    def test_ufo_to_glyphs_without_glyphOrder(self, ufo_module):
        self.prepare(ufo_module)
        self.ufo.lib[GLYPHS_PREFIX + "glyphOrder"] = ["a", "b", "c", "d"]
        font = self.from_ufo()
        assert "glyphOrder" not in font.customParameters
        # NOTE: order of glyphs in font.glyphs undefined because order in the UFO
        # undefined.

    def test_glyphs_to_ufo_without_glyphOrder(self, ufo_module):
        self.prepare(ufo_module)
        ufo = self.from_glyphs(ufo_module)
        assert ufo.lib["public.glyphOrder"] == ["c", "a", "f"]
        assert GLYPHS_PREFIX + "glyphOrder" not in ufo.lib

    def test_glyphs_to_ufo_with_glyphOrder(self, ufo_module):
        self.prepare(ufo_module)
        self.font.customParameters["glyphOrder"] = ["c", "xxx1", "a", "f", "xxx2"]
        ufo = self.from_glyphs(ufo_module)
        assert ["c", "xxx1", "a", "f", "xxx2"] == ufo.lib["public.glyphOrder"]
        assert GLYPHS_PREFIX + "glyphOrder" not in ufo.lib

    def test_glyphs_to_ufo_with_partial_glyphOrder(self, ufo_module):
        self.prepare(ufo_module)
        self.font.customParameters["glyphOrder"] = ["xxx1", "f", "xxx2"]
        ufo = self.from_glyphs(ufo_module)
        assert ["xxx1", "f", "xxx2", "c", "a"] == ufo.lib["public.glyphOrder"]
        assert GLYPHS_PREFIX + "glyphOrder" not in ufo.lib
