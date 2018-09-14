# coding=UTF-8
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


from __future__ import print_function, division, absolute_import, unicode_literals
import collections
import logging
import unittest
import tempfile
import os
import shutil

from defcon import Font
from fontTools.misc.loggingTools import CapturingLogHandler
from glyphsLib import builder
from glyphsLib.classes import (
    GSFont,
    GSFontMaster,
    GSGlyph,
    GSLayer,
    GSPath,
    GSNode,
    GSAlignmentZone,
    GSGuideLine,
)
from glyphsLib.types import Point

from glyphsLib.builder import to_ufos, to_glyphs
from glyphsLib.builder.builders import UFOBuilder, GlyphsBuilder
from glyphsLib.builder.paths import to_ufo_paths
from glyphsLib.builder.names import build_stylemap_names
from glyphsLib.builder.filters import parse_glyphs_filter
from glyphsLib.builder.constants import (
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


class BuildStyleMapNamesTest(unittest.TestCase):
    def test_regular(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Regular",
            is_bold=False,
            is_italic=False,
            linked_style=None,
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("regular", map_style)

    def test_regular_isBold(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Regular",
            is_bold=True,
            is_italic=False,
            linked_style=None,
        )
        self.assertEqual("NotoSans Regular", map_family)
        self.assertEqual("bold", map_style)

    def test_regular_isItalic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Regular",
            is_bold=False,
            is_italic=True,
            linked_style=None,
        )
        self.assertEqual("NotoSans Regular", map_family)
        self.assertEqual("italic", map_style)

    def test_non_regular(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="ExtraBold",
            is_bold=False,
            is_italic=False,
            linked_style=None,
        )
        self.assertEqual("NotoSans ExtraBold", map_family)
        self.assertEqual("regular", map_style)

    def test_bold_no_style_link(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold",
            is_bold=False,  # not style-linked, despite the name
            is_italic=False,
            linked_style=None,
        )
        self.assertEqual("NotoSans Bold", map_family)
        self.assertEqual("regular", map_style)

    def test_italic_no_style_link(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Italic",
            is_bold=False,
            is_italic=False,  # not style-linked, despite the name
            linked_style=None,
        )
        self.assertEqual("NotoSans Italic", map_family)
        self.assertEqual("regular", map_style)

    def test_bold_italic_no_style_link(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold Italic",
            is_bold=False,  # not style-linked, despite the name
            is_italic=False,  # not style-linked, despite the name
            linked_style=None,
        )
        self.assertEqual("NotoSans Bold Italic", map_family)
        self.assertEqual("regular", map_style)

    def test_bold(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold",
            is_bold=True,
            is_italic=False,
            linked_style=None,
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold", map_style)

    def test_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Italic",
            is_bold=False,
            is_italic=True,
            linked_style=None,
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("italic", map_style)

    def test_bold_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold Italic",
            is_bold=True,
            is_italic=True,
            linked_style=None,
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold italic", map_style)

    def test_incomplete_bold_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold",  # will be stripped...
            is_bold=True,
            is_italic=True,
            linked_style=None,
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold italic", map_style)

        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Italic",  # will be stripped...
            is_bold=True,
            is_italic=True,
            linked_style=None,
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold italic", map_style)

    def test_italicbold_isBoldItalic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Italic Bold",  # reversed
            is_bold=True,
            is_italic=True,
            linked_style=None,
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold italic", map_style)

    def test_linked_style_regular(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Condensed",
            is_bold=False,
            is_italic=False,
            linked_style="Cd",
        )
        self.assertEqual("NotoSans Cd", map_family)
        self.assertEqual("regular", map_style)

    def test_linked_style_bold(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Condensed Bold",
            is_bold=True,
            is_italic=False,
            linked_style="Cd",
        )
        self.assertEqual("NotoSans Cd", map_family)
        self.assertEqual("bold", map_style)

    def test_linked_style_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Condensed Italic",
            is_bold=False,
            is_italic=True,
            linked_style="Cd",
        )
        self.assertEqual("NotoSans Cd", map_family)
        self.assertEqual("italic", map_style)

    def test_linked_style_bold_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Condensed Bold Italic",
            is_bold=True,
            is_italic=True,
            linked_style="Cd",
        )
        self.assertEqual("NotoSans Cd", map_family)
        self.assertEqual("bold italic", map_style)


class ParseGlyphsFilterTest(unittest.TestCase):
    def test_complete_parameter(self):
        inputstr = (
            "Transformations;LSB:+23;RSB:-22;SlantCorrection:true;"
            "OffsetX:10;OffsetY:-10;Origin:0;exclude:uni0334,uni0335 uni0336"
        )
        expected = {
            "name": "Transformations",
            "kwargs": {
                "LSB": 23,
                "RSB": -22,
                "SlantCorrection": True,
                "OffsetX": 10,
                "OffsetY": -10,
                "Origin": 0,
            },
            "exclude": ["uni0334", "uni0335", "uni0336"],
        }
        result = parse_glyphs_filter(inputstr)
        self.assertEqual(result, expected)

    def test_is_pre(self):
        inputstr = "Dummy"
        expected = {"name": "Dummy", "pre": True}
        result = parse_glyphs_filter(inputstr, is_pre=True)
        self.assertEqual(result, expected)

    def test_positional_parameter(self):
        inputstr = "Roughenizer;34;2;0;0.34"
        expected = {"name": "Roughenizer", "args": [34, 2, 0, 0.34]}
        result = parse_glyphs_filter(inputstr)
        self.assertEqual(result, expected)

    def test_single_name(self):
        inputstr = "AddExtremes"
        expected = {"name": "AddExtremes"}
        result = parse_glyphs_filter(inputstr)
        self.assertEqual(result, expected)

    def test_empty_string(self):
        inputstr = ""
        with CapturingLogHandler(builder.logger, "ERROR") as captor:
            parse_glyphs_filter(inputstr)
        self.assertGreater(
            len(
                [r for r in captor.records if "Failed to parse glyphs filter" in r.msg]
            ),
            0,
            msg="Empty string should trigger an error message",
        )

    def test_no_name(self):
        inputstr = ";OffsetX:2"
        with CapturingLogHandler(builder.logger, "ERROR") as captor:
            parse_glyphs_filter(inputstr)
        self.assertGreater(
            len(
                [r for r in captor.records if "Failed to parse glyphs filter" in r.msg]
            ),
            0,
            msg="Empty string with no filter name should trigger an error message",
        )

    def test_duplicate_exclude_include(self):
        inputstr = "thisisaname;34;-3.4;exclude:uni1111;include:uni0022;exclude:uni2222"
        expected = {"name": "thisisaname", "args": [34, -3.4], "exclude": ["uni2222"]}
        with CapturingLogHandler(builder.logger, "ERROR") as captor:
            result = parse_glyphs_filter(inputstr)

        self.assertGreater(
            len(
                [
                    r
                    for r in captor.records
                    if "can only present as the last argument" in r.msg
                ]
            ),
            0,
            msg=(
                "The parse_glyphs_filter should warn user that the exclude/include "
                "should only be the last argument in the filter string."
            ),
        )
        self.assertEqual(result, expected)

    def test_empty_args_trailing_semicolon(self):
        inputstr = "thisisaname;3;;a:b;;;"
        expected = {"name": "thisisaname", "args": [3], "kwargs": {"a": "b"}}
        result = parse_glyphs_filter(inputstr)
        self.assertEqual(result, expected)


class ToUfosTest(unittest.TestCase):
    def test_minimal_data(self):
        """Test the minimal data that must be provided to generate UFOs, and in
        some cases that additional redundant data is not set."""

        font = generate_minimal_font()
        family_name = font.familyName
        ufos = to_ufos(font)
        self.assertEqual(len(ufos), 1)

        ufo = ufos[0]
        self.assertEqual(len(ufo), 0)
        self.assertEqual(ufo.info.familyName, family_name)
        # self.assertEqual(ufo.info.styleName, 'Regular')
        self.assertEqual(ufo.info.versionMajor, 1)
        self.assertEqual(ufo.info.versionMinor, 0)
        self.assertIsNone(ufo.info.openTypeNameVersion)
        # TODO(jamesgk) try to generate minimally-populated UFOs in glyphsLib,
        # assert that more fields are empty here (especially in name table)

    def test_warn_no_version(self):
        """Test that a warning is printed when app version is missing."""

        font = generate_minimal_font()
        font.appVersion = "0"
        with CapturingLogHandler(builder.logger, "WARNING") as captor:
            to_ufos(font)
        self.assertEqual(
            len([r for r in captor.records if "outdated version" in r.msg]), 1
        )

    def test_load_kerning(self):
        """Test that kerning conflicts are left untouched.

        Discussion at: https://github.com/googlei18n/glyphsLib/pull/407
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

        ufos = to_ufos(font)
        ufo = ufos[0]

        self.assertEqual(ufo.kerning["public.kern1.A", "public.kern2.V"], -250)
        self.assertEqual(ufo.kerning["public.kern1.A", "v"], -100)
        self.assertEqual(ufo.kerning["a", "public.kern2.V"], 100)

    def test_propagate_anchors(self):
        """Test anchor propagation for some relatively complicated cases."""

        font = generate_minimal_font()

        glyphs = (
            ("sad", [], [("bottom", 50, -50), ("top", 50, 150)]),
            ("dotabove", [], [("top", 0, 150), ("_top", 0, 100)]),
            ("dotbelow", [], [("bottom", 0, -50), ("_bottom", 0, 0)]),
            ("dad", [("sad", 0, 0), ("dotabove", 50, 50)], []),
            ("dadDotbelow", [("dad", 0, 0), ("dotbelow", 50, -50)], []),
            ("yod", [], [("bottom", 50, -50)]),
            ("yodyod", [("yod", 0, 0), ("yod", 100, 0)], []),
        )
        for name, component_data, anchor_data in glyphs:
            glyph = add_glyph(font, name)
            for n, x, y in anchor_data:
                add_anchor(font, name, n, x, y)
            for n, x, y in component_data:
                add_component(font, name, n, (1, 0, 0, 1, x, y))

        ufos = to_ufos(font)
        ufo = ufos[0]

        glyph = ufo["dadDotbelow"]
        self.assertEqual(len(glyph.anchors), 2)
        # check propagated anchors are appended in a deterministic order
        self.assertEqual([anchor.name for anchor in glyph.anchors], ["bottom", "top"])
        for anchor in glyph.anchors:
            self.assertEqual(anchor.x, 50)
            if anchor.name == "bottom":
                self.assertEqual(anchor.y, -100)
            else:
                self.assertEqual(anchor.name, "top")
                self.assertEqual(anchor.y, 200)

        glyph = ufo["yodyod"]
        self.assertEqual(len(glyph.anchors), 2)
        for anchor in glyph.anchors:
            self.assertEqual(anchor.y, -50)
            if anchor.name == "bottom_1":
                self.assertEqual(anchor.x, 50)
            else:
                self.assertEqual(anchor.name, "bottom_2")
                self.assertEqual(anchor.x, 150)

    def test_fail_during_anchor_propagation(self):
        """Fix https://github.com/googlei18n/glyphsLib/issues/317."""
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
        assert to_ufos(font)

    def test_postscript_name_from_data(self):
        font = generate_minimal_font()
        add_glyph(font, "foo")["production"] = "f_o_o.alt1"
        ufo = to_ufos(font)[0]
        postscriptNames = ufo.lib.get("public.postscriptNames")
        self.assertEqual(postscriptNames, {"foo": "f_o_o.alt1"})

    def test_postscript_name_from_glyph_name(self):
        font = generate_minimal_font()
        # in GlyphData (and AGLFN) without a 'production' name
        add_glyph(font, "A")
        # not in GlyphData, no production name
        add_glyph(font, "foobar")
        # in GlyphData with a 'production' name
        add_glyph(font, "C-fraktur")
        ufo = to_ufos(font)[0]
        postscriptNames = ufo.lib.get("public.postscriptNames")
        self.assertEqual(postscriptNames, {"C-fraktur": "uni212D"})

    def test_category(self):
        font = generate_minimal_font()
        add_glyph(font, "foo")["category"] = "Mark"
        add_glyph(font, "bar")
        ufo = to_ufos(font)[0]
        category_key = GLYPHLIB_PREFIX + "category"
        self.assertEqual(ufo["foo"].lib.get(category_key), "Mark")
        self.assertFalse(category_key in ufo["bar"].lib)

    def test_subCategory(self):
        font = generate_minimal_font()
        add_glyph(font, "foo")["subCategory"] = "Nonspacing"
        add_glyph(font, "bar")
        ufo = to_ufos(font)[0]
        subCategory_key = GLYPHLIB_PREFIX + "subCategory"
        self.assertEqual(ufo["foo"].lib.get(subCategory_key), "Nonspacing")
        self.assertFalse(subCategory_key in ufo["bar"].lib)

    def test_mark_nonspacing_zero_width(self):
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

        ufo = to_ufos(font)[0]

        originalWidth_key = GLYPHLIB_PREFIX + "originalWidth"
        self.assertEqual(ufo["dieresiscomb"].width, 0)
        self.assertEqual(ufo["dieresiscomb"].lib.get(originalWidth_key), 100)
        self.assertEqual(ufo["foo"].width, 0)
        self.assertEqual(ufo["foo"].lib.get(originalWidth_key), 200)
        self.assertEqual(ufo["bar"].width, 0)
        self.assertFalse(originalWidth_key in ufo["bar"].lib)

    def test_GDEF(self):
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
        ufo = to_ufos(font)[0]
        self.assertEqual(
            ufo.features.text.splitlines(),
            [
                "table GDEF {",
                "  # automatic",
                "  GlyphClassDef",
                "    [A], # Base",
                "    [fi t_e_s_t.alt], # Liga",
                "    [wigglylinebelowcomb wigglylinebelowcomb.alt], # Mark",
                "    ;",
                "  LigatureCaretByPos fi 150;",
                "  LigatureCaretByPos t_e_s_t.alt 200 400 600;",
                "} GDEF;",
            ],
        )

    def test_GDEF_base_with_attaching_anchor(self):
        font = generate_minimal_font()
        add_glyph(font, "A.alt")
        add_anchor(font, "A.alt", "top", 400, 1000)
        self.assertIn("[A.alt], # Base", to_ufos(font)[0].features.text)

    def test_GDEF_base_with_nonattaching_anchor(self):
        font = generate_minimal_font()
        add_glyph(font, "A.alt")
        add_anchor(font, "A.alt", "_top", 400, 1000)
        self.assertEqual("", to_ufos(font)[0].features.text)

    def test_GDEF_ligature_with_attaching_anchor(self):
        font = generate_minimal_font()
        add_glyph(font, "fi")
        add_anchor(font, "fi", "top", 400, 1000)
        self.assertIn("[fi], # Liga", to_ufos(font)[0].features.text)

    def test_GDEF_ligature_with_nonattaching_anchor(self):
        font = generate_minimal_font()
        add_glyph(font, "fi")
        add_anchor(font, "fi", "_top", 400, 1000)
        self.assertEqual("", to_ufos(font)[0].features.text)

    def test_GDEF_mark(self):
        font = generate_minimal_font()
        add_glyph(font, "eeMatra-gurmukhi")
        self.assertIn("[eeMatra-gurmukhi], # Mark", to_ufos(font)[0].features.text)

    def test_GDEF_fractional_caret_position(self):
        # Some Glyphs sources happen to contain fractional caret positions.
        # In the Adobe feature file syntax (and binary OpenType GDEF tables),
        # caret positions must be integers.
        font = generate_minimal_font()
        add_glyph(font, "fi")
        add_anchor(font, "fi", "caret_1", 499.9876, 0)
        self.assertIn("LigatureCaretByPos fi 500;", to_ufos(font)[0].features.text)

    def test_GDEF_custom_category_subCategory(self):
        font = generate_minimal_font()
        add_glyph(font, "foo")["subCategory"] = "Ligature"
        add_anchor(font, "foo", "top", 400, 1000)
        bar = add_glyph(font, "bar")
        bar["category"], bar["subCategory"] = "Mark", "Nonspacing"
        baz = add_glyph(font, "baz")
        baz["category"], baz["subCategory"] = "Mark", "Spacing Combining"
        features = to_ufos(font)[0].features.text
        self.assertIn("[foo], # Liga", features)
        self.assertIn("[bar baz], # Mark", features)

    def test_set_blue_values(self):
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
        ufo = to_ufos(font)[0]

        self.assertEqual(ufo.info.postscriptBlueValues, expected_blue_values)
        self.assertEqual(ufo.info.postscriptOtherBlues, expected_other_blues)

    def test_missing_date(self):
        font = generate_minimal_font()
        font.date = None
        ufo = to_ufos(font)[0]
        self.assertIsNone(ufo.info.openTypeHeadCreated)

    def test_variation_font_origin(self):
        font = generate_minimal_font()
        name = "Variation Font Origin"
        value = "Light"
        font.customParameters[name] = value

        ufos, instances = to_ufos(font, include_instances=True)

        key = FONT_CUSTOM_PARAM_PREFIX + name
        for ufo in ufos:
            self.assertIn(key, ufo.lib)
            self.assertEqual(ufo.lib[key], value)
        self.assertIn(name, instances)
        self.assertEqual(instances[name], value)

    def test_family_name_none(self):
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
        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0].name, "Regular1")
        self.assertEqual(instances[1].name, "Regular2")
        self.assertEqual(len(instances[0].customParameters), 0)
        self.assertEqual(len(instances[1].customParameters), 1)
        self.assertEqual(instances[1].customParameters[0].value, "CustomFamily")

        # the masters' family name is unchanged
        for ufo in ufos:
            self.assertEqual(ufo.info.familyName, "MyFont")

    def test_family_name_same_as_default(self):
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
        ufos, instance_data = to_ufos(
            font, include_instances=True, family_name="MyFont"
        )
        instances = instance_data["data"]

        # only instances which don't have 'familyName' custom parameter
        # are included in returned list
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].name, "Regular1")
        self.assertEqual(len(instances[0].customParameters), 0)

        # the masters' family name is unchanged
        for ufo in ufos:
            self.assertEqual(ufo.info.familyName, "MyFont")

    def test_family_name_custom(self):
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
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].name, "Regular2")
        self.assertEqual(len(instances[0].customParameters), 1)
        self.assertEqual(instances[0].customParameters[0].value, "CustomFamily")

        # the masters' family is also modified to use custom 'family_name'
        for ufo in ufos:
            self.assertEqual(ufo.info.familyName, "CustomFamily")

    def test_lib_no_weight(self):
        font = generate_minimal_font()
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "weight"], "Regular")

    def test_lib_weight(self):
        font = generate_minimal_font()
        font.masters[0].weight = "Bold"
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "weight"], "Bold")

    def test_lib_no_width(self):
        font = generate_minimal_font()
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "width"], "Regular")

    def test_lib_width(self):
        font = generate_minimal_font()
        font.masters[0].width = "Condensed"
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "width"], "Condensed")

    def test_lib_no_custom(self):
        font = generate_minimal_font()
        ufo = to_ufos(font)[0]
        self.assertFalse(GLYPHS_PREFIX + "customName" in ufo.lib)

    def test_lib_custom(self):
        font = generate_minimal_font()
        font.masters[0].customName = "FooBar"
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "customName"], "FooBar")

    def test_coerce_to_bool(self):
        font = generate_minimal_font()
        font.customParameters["Disable Last Change"] = "Truthy"
        ufo = to_ufos(font)[0]
        self.assertEqual(True, ufo.lib[FONT_CUSTOM_PARAM_PREFIX + "disablesLastChange"])

    def _run_guideline_test(self, data_in, expected):
        font = generate_minimal_font()
        glyph = GSGlyph(name="a")
        font.glyphs.append(glyph)
        layer = GSLayer()
        layer.layerId = font.masters[0].id
        layer.width = 0
        for guide_data in data_in:
            pt = Point(
                value=guide_data["position"][0], value2=guide_data["position"][1]
            )
            guide = GSGuideLine()
            guide.position = pt
            guide.angle = guide_data["angle"]
            layer.guides.append(guide)
        glyph.layers.append(layer)
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo["a"].guidelines, expected)

    def test_set_guidelines(self):
        """Test that guidelines are set correctly."""

        self._run_guideline_test(
            [{"position": (1, 2), "angle": 90}],
            [{str("x"): 1, str("y"): 2, str("angle"): 90}],
        )

    def test_set_guidelines_duplicates(self):
        """Test that duplicate guidelines are accepted."""

        self._run_guideline_test(
            [{"position": (1, 2), "angle": 90}, {"position": (1, 2), "angle": 90}],
            [
                {str("x"): 1, str("y"): 2, str("angle"): 90},
                {str("x"): 1, str("y"): 2, str("angle"): 90},
            ],
        )

    # TODO test more than just name
    def test_supplementary_layers(self):
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
        ufo = to_ufos(font)[0]
        self.assertEqual([l.name for l in ufo.layers], ["public.default", "SubLayer"])

    def test_glyph_lib_Export(self):
        font = generate_minimal_font()
        glyph = add_glyph(font, "a")

        self.assertEqual(glyph.export, True)

        ufo = to_ufos(font)[0]

        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo["a"].lib)

        glyph.export = False
        ufo = to_ufos(font)[0]

        self.assertEqual(ufo["a"].lib[GLYPHLIB_PREFIX + "Export"], False)

    def test_glyph_lib_metricsKeys(self):
        font = generate_minimal_font()
        glyph = add_glyph(font, "x")
        glyph.leftMetricsKey = "y"
        glyph.rightMetricsKey = "z"
        assert glyph.widthMetricsKey is None

        ufo = to_ufos(font)[0]

        self.assertEqual(ufo["x"].lib[GLYPHLIB_PREFIX + "glyph.leftMetricsKey"], "y")
        self.assertEqual(ufo["x"].lib[GLYPHLIB_PREFIX + "glyph.rightMetricsKey"], "z")
        self.assertNotIn(GLYPHLIB_PREFIX + "glyph.widthMetricsKey", ufo["x"].lib)

    def test_glyph_lib_component_alignment_and_locked_and_smart_values(self):
        font = generate_minimal_font()
        add_glyph(font, "a")
        add_glyph(font, "b")
        composite_glyph = add_glyph(font, "c")
        add_component(font, "c", "a", (1, 0, 0, 1, 0, 0))
        add_component(font, "c", "b", (1, 0, 0, 1, 0, 100))
        comp1 = composite_glyph.layers[0].components[0]
        comp2 = composite_glyph.layers[0].components[1]

        self.assertEqual(comp1.alignment, 0)
        self.assertEqual(comp1.locked, False)
        self.assertEqual(comp1.smartComponentValues, {})

        ufo = to_ufos(font)[0]

        # all components have deault values, no lib key is written
        self.assertNotIn(GLYPHS_PREFIX + "componentsAlignment", ufo["c"].lib)
        self.assertNotIn(GLYPHS_PREFIX + "componentsLocked", ufo["c"].lib)
        self.assertNotIn(GLYPHS_PREFIX + "componentsSmartComponentValues", ufo["c"].lib)

        comp2.alignment = -1
        comp1.locked = True
        comp1.smartComponentValues["height"] = 0
        ufo = to_ufos(font)[0]

        # if any component has a non-default alignment/locked values, write
        # list of values for all of them
        self.assertIn(GLYPHS_PREFIX + "componentsAlignment", ufo["c"].lib)
        self.assertEqual(ufo["c"].lib[GLYPHS_PREFIX + "componentsAlignment"], [0, -1])
        self.assertIn(GLYPHS_PREFIX + "componentsLocked", ufo["c"].lib)
        self.assertEqual(
            ufo["c"].lib[GLYPHS_PREFIX + "componentsLocked"], [True, False]
        )
        self.assertIn(GLYPHS_PREFIX + "componentsSmartComponentValues", ufo["c"].lib)
        self.assertEqual(
            ufo["c"].lib[GLYPHS_PREFIX + "componentsSmartComponentValues"],
            [{"height": 0}, {}],
        )

    def test_master_with_light_weight_but_thin_name(self):
        font = generate_minimal_font()
        master = font.masters[0]
        name = "Thin"  # In Glyphs.app, show "Thin" in the sidebar
        weight = "Light"  # In Glyphs.app, have the light "n" icon
        width = None  # No data => should be equivalent to Regular
        custom_name = "Thin"
        master.set_all_name_components(name, weight, width, custom_name)
        assert master.name == "Thin"
        assert master.weight == "Light"

        ufo, = to_ufos(font)
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

    def test_italic_angle(self):
        font = generate_minimal_font()
        ufo, = to_ufos(font)

        ufo.info.italicAngle = 1
        ufo_rt, = to_ufos(to_glyphs([ufo]))
        assert ufo_rt.info.italicAngle == 1

        ufo.info.italicAngle = 1.5
        ufo_rt, = to_ufos(to_glyphs([ufo]))
        assert ufo_rt.info.italicAngle == 1.5

        ufo.info.italicAngle = 0
        font_rt = to_glyphs([ufo])
        assert font_rt.masters[0].italicAngle == 0
        ufo_rt, = to_ufos(font_rt)
        assert ufo_rt.info.italicAngle == 0

    def test_unique_masterid(self):
        font = generate_minimal_font()
        master2 = GSFontMaster()
        master2.ascender = 0
        master2.capHeight = 0
        master2.descender = 0
        master2.xHeight = 0
        font.masters.append(master2)
        ufos = to_ufos(font, minimize_glyphs_diffs=True)

        try:
            to_glyphs(ufos)
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))

        ufos[1].lib["com.schriftgestaltung.fontMasterID"] = (
            ufos[0].lib["com.schriftgestaltung.fontMasterID"].lower()
        )

        with self.assertRaises(ValueError):
            to_glyphs(ufos)


class _PointDataPen(object):
    def __init__(self):
        self.contours = []

    def addPoint(self, pt, segmentType=None, smooth=False, **kwargs):
        self.contours[-1].append((pt[0], pt[1], segmentType, smooth))

    def beginPath(self):
        self.contours.append([])

    def endPath(self):
        if not self.contours[-1]:
            self.contours.pop()

    def addComponent(self, *args, **kwargs):
        pass


class _Glyph(object):
    def __init__(self):
        self.pen = _PointDataPen()

    def getPointPen(self):
        return self.pen


class _UFOBuilder(object):
    def to_ufo_node_user_data(self, *args):
        pass


class DrawPathsTest(unittest.TestCase):
    def test_to_ufo_draw_paths_empty_nodes(self):
        layer = GSLayer()
        layer.paths.append(GSPath())

        glyph = _Glyph()
        to_ufo_paths(_UFOBuilder(), glyph, layer)

        self.assertEqual(glyph.pen.contours, [])

    def test_to_ufo_draw_paths_open(self):
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

        self.assertEqual(
            glyph.pen.contours,
            [
                [
                    (0, 0, "move", False),
                    (1, 1, None, False),
                    (2, 2, None, False),
                    (3, 3, "curve", True),
                ]
            ],
        )

    def test_to_ufo_draw_paths_closed(self):
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
        self.assertEqual((first_x, first_y), (5, 5))

        first_segment_type = points[0][2]
        self.assertEqual(first_segment_type, "curve")

    def test_to_ufo_draw_paths_qcurve(self):
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
        self.assertEqual((first_x, first_y), (223, 334))

        first_segment_type = points[0][2]
        self.assertEqual(first_segment_type, "qcurve")


class GlyphPropertiesTest(unittest.TestCase):
    def test_glyph_color(self):
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
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo["a"].lib.get("public.markColor"), "0.957,0,0.541,0.004")
        self.assertEqual(ufo["b"].lib.get("public.markColor"), "0.97,1,0,1")
        self.assertEqual(ufo["c"].lib.get("public.markColor"), None)
        self.assertEqual(ufo["d"].lib.get("public.markColor"), None)


class SkipDanglingAndNamelessLayers(unittest.TestCase):
    def setUp(self):
        self.font = generate_minimal_font()
        add_glyph(self.font, "a")
        self.logger = logging.getLogger("glyphsLib.builder.builders.UFOBuilder")

    def test_normal_layer(self):
        with CapturingLogHandler(self.logger, level="WARNING") as captor:
            to_ufos(self.font)

        # no warnings are emitted
        self.assertRaises(
            AssertionError, captor.assertRegex, "is dangling and will be skipped"
        )
        self.assertRaises(AssertionError, captor.assertRegex, "layer without a name")

    def test_nameless_layer(self):
        self.font.glyphs[0].layers[0].associatedMasterId = "xxx"

        with CapturingLogHandler(self.logger, level="WARNING") as captor:
            to_ufos(self.font, minimize_glyphs_diffs=True)

        captor.assertRegex("layer without a name")

        # no warning if minimize_glyphs_diff=False
        with CapturingLogHandler(self.logger, level="WARNING") as captor:
            to_ufos(self.font, minimize_glyphs_diffs=False)

        self.assertFalse(captor.records)

    def test_dangling_layer(self):
        self.font.glyphs[0].layers[0].layerId = "yyy"
        self.font.glyphs[0].layers[0].associatedMasterId = "xxx"

        with CapturingLogHandler(self.logger, level="WARNING") as captor:
            to_ufos(self.font, minimize_glyphs_diffs=True)

        captor.assertRegex("is dangling and will be skipped")


class GlyphOrderTest(unittest.TestCase):
    """Check that the glyphOrder data is persisted correctly in all directions.

    Problem: Glyphs.app (tested 2.4.1 and 2.5.2) does not import and export a
    UFO's public.glyphOrder lib key verbatim. To prevent the glyph order from
    changing when exporting to UFO from within Glyphs.app, working on the UFO
    and re-opening it in Glyphs.app, it will:

    1. if a glyphOrder parameter is present, write it verbatim to the
       `com.schriftgestaltung.glyphOrder` as a list and write a
       cleaned-up version of it (e.g. only existing glyphs plus ones not covered
       in it but present in the font) to `public.glyphOrder`.
    2. if a glyphOrder parameter is not present, write the implicit order of the
       font to `public.glyphOrder` and write the
       `com.schriftgestaltung.glyphOrder` lib key with the value `False`.

    On reading a UFO, Glyphs.app will:

    1. if a `com.schriftgestaltung.glyphOrder` lib key is present and holds a
       list, copy it to the `glyphOrder` parameter.
    2. if a `com.schriftgestaltung.glyphOrder` lib key is present and holds the
       value `False`, not set a `glyphOrder` parameter and use its own ordering
       instead. Side-note: Glyphs.app will get confused if the
       `public.glyphOrder` now contains non-existant glyphs and may crash on
       saving.
    3. if no `com.schriftgestaltung.glyphOrder` lib key is present, copy
       `public.glyphOrder` to the `glyphOrder` parameter.
    4. if no `public.glyphOrder` exist, maybe get confused and crash.

    To work with this instead of against it and reduce Git diff noise on
    round-tripping, do the following:

    1. Glyphs to UFO: If a .glyphs file has...
        1. no `glyphOrder` parameter set, the implicit order of glyphs becomes
           the `public.glyphOrder` lib key and the
           `com.schriftgestaltung.glyphOrder` lib key is set to `False`.
        2. a `glyphOrder` parameter set, it gets copied to the
           `public.glyphOrder` lib key, the `com.schriftgestaltung.glyphOrder`
           lib key is not written.
    2. UFO to Glyphs: If a UFO has...
        1. a `com.schriftgestaltung.glyphOrder` lib key holding a list, it gets
           copied to the `glyphOrder` parameter.
        2. a `com.schriftgestaltung.glyphOrder` lib key holding the value
           `False`, do not set a `glyphOrder` parameter.
        3. a `public.glyphOrder` and no `com.schriftgestaltung.glyphOrder` key,
           copy `public.glyphOrder` to the `glyphOrder` parameter.
        4. no `public.glyphOrder` lib key, do not set the `glyphOrder`
           parameter.

    This covers the case of using Glyphs' UFO exporting mechanism and using
    glyphslib to turn it into a Glyphs file again, as well as using glyphsLib to
    produce UFOs from a .glyphs file and opening them in Glyphs.app again. It
    also preserves existing public.glyphOrder from other tools.

    TODO: these test cases do not exhaustively check for the glyph order in
    GSFont objects, because we don't know Glyphs.app's ordering rules. E.g. a
    test should set a UFOs `public.glyphOrder` to ["d", "c", "b", "a"] and check
    that the resulting GSFont glyph order is ["c", "a", "f"].
    """

    def setUp(self):
        self.font = GSFont()
        self.font.masters.append(GSFontMaster())
        self.font.glyphs.append(GSGlyph("a"))
        self.font.glyphs.append(GSGlyph("c"))
        self.font.glyphs.append(GSGlyph("f"))
        self.ufo = Font()
        self.ufo.newGlyph("a")
        self.ufo.newGlyph("c")
        self.ufo.newGlyph("f")

    def from_glyphs(self):
        builder = UFOBuilder(self.font)
        return next(iter(builder.masters))

    def from_ufo(self):
        builder = GlyphsBuilder([self.ufo])
        return builder.font

    def test_glyphs_to_ufo_no_glyphOrder(self):
        ufo = self.from_glyphs()
        self.assertEqual(["a", "c", "f"], ufo.glyphOrder)
        self.assertFalse(ufo.lib[GLYPHS_PREFIX + "glyphOrder"])

    def test_glyphs_to_ufo_with_glyphOrder(self):
        self.font.customParameters["glyphOrder"] = ["a", "b", "c", "d"]
        ufo = self.from_glyphs()
        self.assertEqual(["a", "b", "c", "d"], ufo.glyphOrder)
        self.assertNotIn(GLYPHS_PREFIX + "glyphOrder", ufo.lib)

    def test_ufo_to_glyphs_with_csgO_list(self):
        self.ufo.lib[GLYPHS_PREFIX + "glyphOrder"] = ["a", "b", "c", "d"]
        font = self.from_ufo()
        self.assertEqual(["a", "b", "c", "d"], font.customParameters["glyphOrder"])
        self.assertEqual(["a", "c", "f"], [glyph.name for glyph in font.glyphs])

    def test_ufo_to_glyphs_with_csgO_false(self):
        self.ufo.lib[GLYPHS_PREFIX + "glyphOrder"] = False
        font = self.from_ufo()
        self.assertNotIn("glyphOrder", font.customParameters)
        self.assertEqual(["a", "c", "f"], [glyph.name for glyph in font.glyphs])

    def test_ufo_to_glyphs_only_pgO(self):
        font = self.from_ufo()
        self.assertEqual(["a", "c", "f"], font.customParameters["glyphOrder"])
        self.assertEqual(["a", "c", "f"], [glyph.name for glyph in font.glyphs])

    def test_ufo_to_glyphs_no_pgO(self):
        del self.ufo.lib["public.glyphOrder"]
        font = self.from_ufo()
        self.assertNotIn("glyphOrder", font.customParameters)
        self.assertEqual(
            [glyph.name for glyph in self.ufo], [glyph.name for glyph in font.glyphs]
        )


if __name__ == "__main__":
    unittest.main()
