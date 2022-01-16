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
import logging
import unittest
import tempfile
import os
import shutil

import glyphsLib
import defcon
import ufoLib2
from textwrap import dedent
from fontTools.misc.loggingTools import CapturingLogHandler
from glyphsLib import builder
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

from glyphsLib.builder import to_glyphs
from glyphsLib.builder.builders import UFOBuilder, GlyphsBuilder
from glyphsLib.builder.paths import to_ufo_paths
from glyphsLib.builder.names import build_stylemap_names
from glyphsLib.builder.filters import parse_glyphs_filter
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
from ..test_helpers import ParametrizedUfoModuleTestMixin


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


class ToUfosTestBase(ParametrizedUfoModuleTestMixin):
    def test_minimal_data(self):
        """Test the minimal data that must be provided to generate UFOs, and in
        some cases that additional redundant data is not set."""

        font = generate_minimal_font()
        family_name = font.familyName
        ufos = self.to_ufos(font)
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
            self.to_ufos(font)
        self.assertEqual(
            len([r for r in captor.records if "outdated version" in r.msg]), 1
        )

    def test_load_kerning(self):
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

        ufos = self.to_ufos(font)
        ufo = ufos[0]

        self.assertEqual(ufo.kerning["public.kern1.A", "public.kern2.V"], -250)
        self.assertEqual(ufo.kerning["public.kern1.A", "v"], -100)
        self.assertEqual(ufo.kerning["a", "public.kern2.V"], 100)

    def test_propagate_anchors_on(self):
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
            add_glyph(font, name)
            for n, x, y in anchor_data:
                add_anchor(font, name, n, x, y)
            for n, x, y in component_data:
                add_component(font, name, n, (1, 0, 0, 1, x, y))

        ufos = self.to_ufos(font, propagate_anchors=True)
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

    def test_propagate_anchors_off(self):
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

        ufos = self.to_ufos(font, propagate_anchors=False)
        ufo = ufos[0]

        self.assertEqual(len(ufo["dad"].anchors), 0)

    def test_propagate_anchors_custom_parameter_on(self):
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

        ufos = self.to_ufos(font)
        ufo = ufos[0]

        glyph = ufo["dad"]
        self.assertEqual(len(glyph.anchors), 2)
        # check propagated anchors are appended in a deterministic order
        self.assertEqual([anchor.name for anchor in glyph.anchors], ["bottom", "top"])
        for anchor in glyph.anchors:
            self.assertEqual(anchor.x, 50)
            if anchor.name == "bottom":
                self.assertEqual(anchor.y, -50)
            else:
                self.assertEqual(anchor.name, "top")
                self.assertEqual(anchor.y, 200)

    def test_propagate_anchors_custom_parameter_off(self):
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

        ufos = self.to_ufos(font)
        ufo = ufos[0]

        self.assertEqual(len(ufo["dad"].anchors), 0)

    def test_fail_during_anchor_propagation(self):
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
        assert self.to_ufos(font)

    def test_postscript_name_from_data(self):
        font = generate_minimal_font()
        add_glyph(font, "foo")["production"] = "f_o_o.alt1"
        ufo = self.to_ufos(font)[0]
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
        ufo = self.to_ufos(font)[0]
        postscriptNames = ufo.lib.get("public.postscriptNames")
        self.assertEqual(postscriptNames, {"C-fraktur": "uni212D"})

    def test_category(self):
        font = generate_minimal_font()
        add_glyph(font, "foo")["category"] = "Mark"
        add_glyph(font, "bar")
        ufo = self.to_ufos(font)[0]
        category_key = GLYPHLIB_PREFIX + "category"
        self.assertEqual(ufo["foo"].lib.get(category_key), "Mark")
        self.assertFalse(category_key in ufo["bar"].lib)

    def test_subCategory(self):
        font = generate_minimal_font()
        add_glyph(font, "foo")["subCategory"] = "Nonspacing"
        add_glyph(font, "bar")
        ufo = self.to_ufos(font)[0]
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

        ufo = self.to_ufos(font)[0]

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
        ufo = self.to_ufos(font)[0]
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
        self.assertIn("[A.alt], # Base", self.to_ufos(font)[0].features.text)

    def test_GDEF_base_with_nonattaching_anchor(self):
        font = generate_minimal_font()
        add_glyph(font, "A.alt")
        add_anchor(font, "A.alt", "_top", 400, 1000)
        self.assertEqual("", self.to_ufos(font)[0].features.text)

    def test_GDEF_ligature_with_attaching_anchor(self):
        font = generate_minimal_font()
        add_glyph(font, "fi")
        add_anchor(font, "fi", "top", 400, 1000)
        self.assertIn("[fi], # Liga", self.to_ufos(font)[0].features.text)

    def test_GDEF_ligature_with_nonattaching_anchor(self):
        font = generate_minimal_font()
        add_glyph(font, "fi")
        add_anchor(font, "fi", "_top", 400, 1000)
        self.assertEqual("", self.to_ufos(font)[0].features.text)

    def test_GDEF_mark(self):
        font = generate_minimal_font()
        add_glyph(font, "eeMatra-gurmukhi")
        self.assertIn("[eeMatra-gurmukhi], # Mark", self.to_ufos(font)[0].features.text)

    def test_GDEF_fractional_caret_position(self):
        # Some Glyphs sources happen to contain fractional caret positions.
        # In the Adobe feature file syntax (and binary OpenType GDEF tables),
        # caret positions must be integers.
        font = generate_minimal_font()
        add_glyph(font, "fi")
        add_anchor(font, "fi", "caret_1", 499.9876, 0)
        self.assertIn("LigatureCaretByPos fi 500;", self.to_ufos(font)[0].features.text)

    def test_GDEF_custom_category_subCategory(self):
        font = generate_minimal_font()
        add_glyph(font, "foo")["subCategory"] = "Ligature"
        add_anchor(font, "foo", "top", 400, 1000)
        bar = add_glyph(font, "bar")
        bar["category"], bar["subCategory"] = "Mark", "Nonspacing"
        baz = add_glyph(font, "baz")
        baz["category"], baz["subCategory"] = "Mark", "Spacing Combining"
        features = self.to_ufos(font)[0].features.text
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
        ufo = self.to_ufos(font)[0]

        self.assertEqual(ufo.info.postscriptBlueValues, expected_blue_values)
        self.assertEqual(ufo.info.postscriptOtherBlues, expected_other_blues)

    def test_set_blue_values_empty(self):
        font = generate_minimal_font()
        font.masters[0].alignmentZones = []
        ufo = self.to_ufos(font)[0]

        if self.ufo_module is ufoLib2:
            self.assertIsNone(ufo.info.postscriptBlueValues)
            self.assertIsNone(ufo.info.postscriptOtherBlues)
        else:
            self.assertEqual(ufo.info.postscriptBlueValues, [])
            self.assertEqual(ufo.info.postscriptOtherBlues, [])

    def test_missing_date(self):
        font = generate_minimal_font()
        font.date = None
        ufo = self.to_ufos(font)[0]
        self.assertIsNone(ufo.info.openTypeHeadCreated)

    def test_variation_font_origin(self):
        font = generate_minimal_font()
        name = "Variation Font Origin"
        value = "Light"
        font.customParameters[name] = value

        ufos, instances = self.to_ufos(font, include_instances=True)

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
        ufos, instance_data = self.to_ufos(font, include_instances=True)
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
        ufos, instance_data = self.to_ufos(
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
        ufos, instance_data = self.to_ufos(
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
        ufo = self.to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "weight"], "Regular")

    def test_lib_weight(self):
        font = generate_minimal_font()
        font.masters[0].weight = "Bold"
        ufo = self.to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "weight"], "Bold")

    def test_lib_no_width(self):
        font = generate_minimal_font()
        ufo = self.to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "width"], "Regular")

    def test_lib_width(self):
        font = generate_minimal_font()
        font.masters[0].width = "Condensed"
        ufo = self.to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "width"], "Condensed")

    def test_lib_no_custom(self):
        font = generate_minimal_font()
        ufo = self.to_ufos(font)[0]
        self.assertFalse(GLYPHS_PREFIX + "customName" in ufo.lib)

    def test_lib_custom(self):
        font = generate_minimal_font()
        font.masters[0].customName = "FooBar"
        ufo = self.to_ufos(font)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + "customName"], "FooBar")

    def test_coerce_to_bool(self):
        font = generate_minimal_font()
        font.customParameters["Disable Last Change"] = "Truthy"
        ufo = self.to_ufos(font)[0]
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
            guide = GSGuide()
            guide.position = pt
            guide.angle = guide_data["angle"]
            layer.guides.append(guide)
        glyph.layers.append(layer)
        ufo = self.to_ufos(font, minimal=False)[0]
        self.assertEqual([dict(g) for g in ufo["a"].guidelines], expected)

    def test_set_guidelines(self):
        """Test that guidelines are set correctly."""

        self._run_guideline_test(
            [{"position": (1, 2), "angle": 90}], [{"x": 1, "y": 2, "angle": 90}]
        )

    def test_set_guidelines_duplicates(self):
        """Test that duplicate guidelines are accepted."""

        self._run_guideline_test(
            [{"position": (1, 2), "angle": 90}, {"position": (1, 2), "angle": 90}],
            [{"x": 1, "y": 2, "angle": 90}, {"x": 1, "y": 2, "angle": 90}],
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
        ufo = self.to_ufos(font, minimal=False)[0]
        self.assertEqual([l.name for l in ufo.layers], ["public.default", "SubLayer"])

    def test_duplicate_supplementary_layers(self):
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
        with CapturingLogHandler(builder.logger, level="WARNING") as captor:
            ufo = self.to_ufos(font, minimal=False)[0]

        self.assertEqual(
            [l.name for l in ufo.layers], ["public.default", "SubLayer", "SubLayer #1"]
        )
        captor.assertRegex("Duplicate glyph layer name")

    def test_glyph_lib_Export(self):
        font = generate_minimal_font()
        glyph = add_glyph(font, "a")
        self.assertEqual(glyph.export, True)

        ufo = self.to_ufos(font)[0]
        ds = self.to_designspace(font)

        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo["a"].lib)
        self.assertNotIn("public.skipExportGlyphs", ufo.lib)
        self.assertNotIn("public.skipExportGlyphs", ds.lib)

        font2 = to_glyphs(ds)
        self.assertEqual(font2.glyphs["a"].export, True)

        font2.glyphs["a"].export = False

        # Test write_skipexportglyphs=True
        ufo = self.to_ufos(font2, write_skipexportglyphs=True)[0]
        ds = self.to_designspace(font2, write_skipexportglyphs=True)

        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo["a"].lib)
        self.assertEqual(ufo.lib["public.skipExportGlyphs"], ["a"])
        self.assertEqual(ds.lib["public.skipExportGlyphs"], ["a"])

        font3 = to_glyphs(ds)
        self.assertEqual(font3.glyphs["a"].export, False)

        # Test write_skipexportglyphs=False
        ufo = self.to_ufos(font2, write_skipexportglyphs=False)[0]
        ds = self.to_designspace(font2, write_skipexportglyphs=False)

        self.assertFalse(ufo["a"].lib[GLYPHLIB_PREFIX + "Export"])
        self.assertNotIn("public.skipExportGlyphs", ufo.lib)
        self.assertNotIn("public.skipExportGlyphs", ds.lib)

        font3 = to_glyphs(ds)
        self.assertEqual(font3.glyphs["a"].export, False)

    def test_glyph_lib_Export_mixed_to_public_skipExportGlyphs(self):
        font = generate_minimal_font()
        add_glyph(font, "a")
        add_glyph(font, "b")
        add_glyph(font, "c")
        add_glyph(font, "d")
        ds = self.to_designspace(font, write_skipexportglyphs=True)
        ufo = ds.sources[0].font

        ufo["a"].lib[GLYPHLIB_PREFIX + "Export"] = False
        ufo.lib["public.skipExportGlyphs"] = ["b"]
        ds.lib["public.skipExportGlyphs"] = ["c"]

        font2 = to_glyphs(ds)

        ds2 = self.to_designspace(font2, write_skipexportglyphs=True)
        ufo2 = ds2.sources[0].font

        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo2["a"].lib)
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo2["b"].lib)
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo2["c"].lib)
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo2["d"].lib)
        self.assertEqual(ufo2.lib["public.skipExportGlyphs"], ["a", "c"])
        self.assertEqual(ds2.lib["public.skipExportGlyphs"], ["a", "c"])

        font3 = to_glyphs(ds2)
        self.assertEqual(font3.glyphs["a"].export, False)
        self.assertEqual(font3.glyphs["b"].export, True)
        self.assertEqual(font3.glyphs["c"].export, False)
        self.assertEqual(font3.glyphs["d"].export, True)

        ufos3 = self.to_ufos(font3, write_skipexportglyphs=True)
        ufo3 = ufos3[0]
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo3["a"].lib)
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo3["b"].lib)
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo3["c"].lib)
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo3["d"].lib)
        self.assertEqual(ufo3.lib["public.skipExportGlyphs"], ["a", "c"])

    def test_glyph_lib_Export_mixed_to_lib_key(self):
        font = generate_minimal_font()
        add_glyph(font, "a")
        add_glyph(font, "b")
        add_glyph(font, "c")
        add_glyph(font, "d")
        ds = self.to_designspace(font, write_skipexportglyphs=False)
        ufo = ds.sources[0].font

        ufo["a"].lib[GLYPHLIB_PREFIX + "Export"] = False
        ufo.lib["public.skipExportGlyphs"] = ["b"]
        ds.lib["public.skipExportGlyphs"] = ["c"]

        font2 = to_glyphs(ds)

        ds2 = self.to_designspace(font2, write_skipexportglyphs=False)
        ufo2 = ds2.sources[0].font

        self.assertFalse(ufo2["a"].lib[GLYPHLIB_PREFIX + "Export"])
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo2["b"].lib)
        self.assertFalse(ufo2["c"].lib[GLYPHLIB_PREFIX + "Export"])
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo2["d"].lib)
        self.assertNotIn("public.skipExportGlyphs", ufo2.lib)
        self.assertNotIn("public.skipExportGlyphs", ds2.lib)

        font3 = to_glyphs(ds2)
        self.assertEqual(font3.glyphs["a"].export, False)
        self.assertEqual(font3.glyphs["b"].export, True)
        self.assertEqual(font3.glyphs["c"].export, False)
        self.assertEqual(font3.glyphs["d"].export, True)

        ufos3 = self.to_ufos(font3, write_skipexportglyphs=False)
        ufo3 = ufos3[0]
        self.assertFalse(ufo3["a"].lib[GLYPHLIB_PREFIX + "Export"])
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo3["b"].lib)
        self.assertFalse(ufo3["c"].lib[GLYPHLIB_PREFIX + "Export"])
        self.assertNotIn(GLYPHLIB_PREFIX + "Export", ufo3["d"].lib)
        self.assertNotIn("public.skipExportGlyphs", ufo3.lib)

        font4 = to_glyphs(ufos3)
        self.assertEqual(font4.glyphs["a"].export, False)
        self.assertEqual(font4.glyphs["b"].export, True)
        self.assertEqual(font4.glyphs["c"].export, False)
        self.assertEqual(font4.glyphs["d"].export, True)

    def test_glyph_lib_Export_GDEF(self):
        font = generate_minimal_font()
        add_glyph(font, "a")
        add_glyph(font, "d")
        add_anchor(font, "d", "top", 100, 100)

        ds = self.to_designspace(font, write_skipexportglyphs=True)
        ufo = ds.sources[0].font
        self.assertIn(
            "GlyphClassDef[d]", ufo.features.text.replace("\n", "").replace(" ", "")
        )

        font.glyphs["d"].export = False
        ds2 = self.to_designspace(font, write_skipexportglyphs=True)
        ufo2 = ds2.sources[0].font
        self.assertEqual(ufo2.features.text, "")

    def test_glyph_lib_Export_feature_names_from_notes(self):
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
            ufos = self.to_ufos(font)
            ufo = ufos[0]
            self.assertIn(r'name "Single\005cstorey \0022ä\0022";', ufo.features.text)
            self.assertNotIn(note, ufo.features.text)

        # Name should not be exported when not in first line
        for note in (
            'A Comment\nName: Single\\storey "ä"\nFoo',
            'A Comment\nName: Single\\storey "ä"',
        ):
            font.features[0].notes = note
            ufos = self.to_ufos(font)
            ufo = ufos[0]
            self.assertNotIn(
                r'name "Single\005cstorey \0022ä\0022";', ufo.features.text
            )

    def test_glyph_lib_Export_feature_names_long_from_notes(self):
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
            ufos = self.to_ufos(font)
            ufo = ufos[0]
            self.assertIn(
                (
                    'featureNames {\n  name 3 1 0x401 "Alternate {ä};";\n'
                    '  name 3 1 0x409 "Alternate {};";\n};'
                ),
                ufo.features.text,
            )

    def test_glyph_lib_Export_feature_names_long_escaped_from_notes(self):
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
            ufos = self.to_ufos(font)
            ufo = ufos[0]
            self.assertIn(
                (
                    'featureNames {\n  name "Round dots";\n  name 3 1 0x0C01 '
                    '"\\062d\\0631\\0648\\0641 \\0645\\0647\\0645\\0644\\0629 '
                    '(\\0628\\0644\\0627 \\0646\\0642\\0627\\0637)";\n};\n'
                ),
                ufo.features.text,
            )

    def test_glyph_lib_Export_feature_names_from_labels(self):
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
        ufos = self.to_ufos(font)
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

    def test_glyph_lib_Export_fake_designspace(self):
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
        ds = self.to_designspace(font, write_skipexportglyphs=True)

        ufos = [source.font for source in ds.sources]

        font2 = to_glyphs(ufos)
        ds2 = self.to_designspace(font2, write_skipexportglyphs=True)
        self.assertNotIn("public.skipExportGlyphs", ds2.lib)

        ufos[0].lib["public.skipExportGlyphs"] = ["a"]

        with self.assertRaises(ValueError):
            to_glyphs(ufos)

        ufos[1].lib["public.skipExportGlyphs"] = ["a"]
        font3 = to_glyphs(ufos)
        self.assertEqual(font3.glyphs["a"].export, False)
        self.assertEqual(font3.glyphs["b"].export, True)

    def test_glyph_lib_metricsKeys(self):
        font = generate_minimal_font()
        glyph = add_glyph(font, "x")
        glyph.leftMetricsKey = "y"
        glyph.rightMetricsKey = "z"
        assert glyph.widthMetricsKey is None

        ufo = self.to_ufos(font)[0]

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

        ufo = self.to_ufos(font)[0]

        # all components have deault values, no lib key is written
        self.assertNotIn(GLYPHS_PREFIX + "componentsAlignment", ufo["c"].lib)
        self.assertNotIn(GLYPHS_PREFIX + "componentsLocked", ufo["c"].lib)
        self.assertNotIn(GLYPHS_PREFIX + "componentsSmartComponentValues", ufo["c"].lib)
        self.assertNotIn(COMPONENT_INFO_KEY, ufo["c"].lib)

        comp2.alignment = -1
        comp1.locked = True
        comp1.smartComponentValues["height"] = 0
        ufo = self.to_ufos(font)[0]

        # if any component has a non-default alignment/locked values, write
        # list of values for all of them
        self.assertNotIn(GLYPHS_PREFIX + "componentsAlignment", ufo["c"].lib)
        self.assertEqual(
            ufo["c"].lib[COMPONENT_INFO_KEY],
            [{"index": 1, "name": "b", "alignment": -1}],
        )
        self.assertIn(GLYPHS_PREFIX + "componentsLocked", ufo["c"].lib)
        self.assertEqual(
            ufo["c"].lib[GLYPHS_PREFIX + "componentsLocked"], [True, False]
        )
        self.assertIn(GLYPHS_PREFIX + "componentsSmartComponentValues", ufo["c"].lib)
        self.assertEqual(
            ufo["c"].lib[GLYPHS_PREFIX + "componentsSmartComponentValues"],
            [{"height": 0}, {}],
        )

    def test_glyph_lib_color_mapping(self):
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

        ds = self.to_designspace(font)
        ufo = ds.sources[0].font

        assert ufo["a"].lib["com.github.googlei18n.ufo2ft.colorLayerMapping"] == [
            ("color.1", 1),
            ("color.0", 0),
            ("color.3", 3),
        ]
        assert "com.github.googlei18n.ufo2ft.colorLayerMapping" not in ufo["b"].lib

    def test_glyph_lib_color_mapping_foreground_color(self):
        font = generate_minimal_font()
        glyph = add_glyph(font, "a")
        color = GSLayer()
        color.name = "Color *"

        glyph.layers.append(color)

        ds = self.to_designspace(font)
        ufo = ds.sources[0].font

        assert ufo["a"].lib["com.github.googlei18n.ufo2ft.colorLayerMapping"] == [
            ("color.65535", 65535),
        ]

    def test_glyph_lib_color_mapping_invalid_index(self):
        font = generate_minimal_font()
        glyph = add_glyph(font, "a")
        color = GSLayer()
        color.name = "Color f"
        glyph.layers.append(color)

        color = GSLayer()
        color.name = "Color 0"
        glyph.layers.append(color)

        ds = self.to_designspace(font)
        ufo = ds.sources[0].font

        assert ufo["a"].lib["com.github.googlei18n.ufo2ft.colorLayerMapping"] == [
            ("color.0", 0),
        ]

    def test_glyph_color_layers_decompose(self):
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

        ds = self.to_designspace(font)
        ufo = ds.sources[0].font

        assert len(ufo.layers["color.0"]["a"].components) == 0
        assert len(ufo.layers["color.0"]["a"]) == 2
        pen1 = _PointDataPen()
        ufo.layers["color.0"]["a"].drawPoints(pen1)
        pen2 = _PointDataPen()
        ufo["d"].drawPoints(pen2)
        ufo["c"].drawPoints(pen2)
        assert pen1.contours == pen2.contours

        assert len(ufo.layers["color.1"]["a"].components) == 0
        assert len(ufo.layers["color.1"]["a"]) == 1
        pen1 = _PointDataPen()
        ufo.layers["color.1"]["a"].drawPoints(pen1)
        pen2 = _PointDataPen()
        ufo["d"].drawPoints(pen2)
        assert pen1.contours == pen2.contours

        assert len(ufo.layers["color.3"]["a"].components) == 0
        assert len(ufo.layers["color.3"]["a"]) == 1
        pen1 = _PointDataPen()
        ufo.layers["color.3"]["a"].drawPoints(pen1)
        pen2 = _PointDataPen()
        ufo["c"].drawPoints(pen2)
        assert pen1.contours == pen2.contours

    def test_glyph_color_palette_layers_explode(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_palette_layers_explode_no_export(self):
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

        ds = self.to_designspace(font, minimal=True)
        ufo = ds.sources[0].font

        assert ufo.lib["com.github.googlei18n.ufo2ft.colorLayers"] == {
            "b": [("b.color0", 1)]
        }

    def test_glyph_color_palette_layers_explode_v3(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_explode(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_strokecolor(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_strokewidth(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_stroke_no_attributes(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_component(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_component_color(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_component_color_translate(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_component_color_transform(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_group_paths(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_group_paths_nonconsecutive(self):
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

        ds = self.to_designspace(font, minimal=True)
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

    def test_glyph_color_layers_master_layer(self):
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

        ds = self.to_designspace(font, minimal=True)
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

        (ufo,) = self.to_ufos(font)
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
        (ufo,) = self.to_ufos(font)

        ufo.info.italicAngle = 1
        (ufo_rt,) = self.to_ufos(to_glyphs([ufo]))
        assert ufo_rt.info.italicAngle == 1

        ufo.info.italicAngle = 1.5
        (ufo_rt,) = self.to_ufos(to_glyphs([ufo]))
        assert ufo_rt.info.italicAngle == 1.5

        ufo.info.italicAngle = 0
        font_rt = to_glyphs([ufo])
        assert font_rt.masters[0].italicAngle == 0
        (ufo_rt,) = self.to_ufos(font_rt)
        assert ufo_rt.info.italicAngle == 0

    def test_unique_masterid(self):
        font = generate_minimal_font()
        master2 = GSFontMaster()
        master2.ascender = 0
        master2.capHeight = 0
        master2.descender = 0
        master2.xHeight = 0
        font.masters.append(master2)
        ufos = self.to_ufos(font, minimize_glyphs_diffs=True)

        try:
            to_glyphs(ufos)
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))

        ufos[1].lib["com.schriftgestaltung.fontMasterID"] = ufos[0].lib[
            "com.schriftgestaltung.fontMasterID"
        ]

        font_rt = to_glyphs(ufos)
        assert len({m.id for m in font_rt.masters}) == 2

    def test_custom_glyph_data(self):
        font = generate_minimal_font()
        for glyph_name in ("A", "foo", "bar", "baz"):
            add_glyph(font, glyph_name)
        font.glyphs["baz"].production = "bazglyph"
        font.glyphs["baz"].category = "Number"
        font.glyphs["baz"].subCategory = "Decimal Digit"
        font.glyphs["baz"].script = "Arabic"
        filename = os.path.join(
            os.path.dirname(__file__), "..", "data", "CustomGlyphData.xml"
        )
        (ufo,) = self.to_ufos(font, minimize_glyphs_diffs=True, glyph_data=[filename])

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


class ToUfosTestUfoLib2(ToUfosTestBase, unittest.TestCase):
    ufo_module = ufoLib2

    def test_load_kerning_bracket(self):
        filename = os.path.join(
            os.path.dirname(__file__), "..", "data", "BracketTestFontKerning.glyphs"
        )
        with open(filename) as f:
            font = glyphsLib.load(f)

        ds = glyphsLib.to_designspace(font, minimize_glyphs_diffs=True)
        bracketed_groups = {
            "public.kern2.foo": ["a", "a.BRACKET.300"],
            "public.kern1.foo": ["x", "x.BRACKET.300", "x.BRACKET.600"],
        }
        self.assertEqual(ds.sources[0].font.groups, bracketed_groups)
        self.assertEqual(ds.sources[1].font.groups, bracketed_groups)
        self.assertEqual(ds.sources[2].font.groups, bracketed_groups)
        self.assertEqual(ds.sources[3].font.groups, bracketed_groups)
        self.assertEqual(
            ds.sources[0].font.kerning,
            {
                ("public.kern1.foo", "public.kern2.foo"): -200,
                ("a", "x"): -100,
                ("a.BRACKET.300", "x"): -100,
                ("a", "x.BRACKET.300"): -100,
                ("a.BRACKET.300", "x.BRACKET.300"): -100,
                ("a", "x.BRACKET.600"): -100,
                ("a.BRACKET.300", "x.BRACKET.600"): -100,
            },
        )
        self.assertEqual(ds.sources[1].font.kerning, {})
        self.assertEqual(
            ds.sources[2].font.kerning, {("public.kern1.foo", "public.kern2.foo"): -300}
        )
        self.assertEqual(ds.sources[3].font.kerning, {})

        font2 = glyphsLib.to_glyphs(ds, minimize_ufo_diffs=True)
        self.assertEqual(
            font2.kerning,
            {
                "1034EC4A-9832-4D17-A75A-2B17BF7C4AA6": {
                    "@MMK_L_foo": {"@MMK_R_foo": -200},
                    "a": {"x": -100},
                },
                "C402BD76-83A2-4350-9191-E5499E97AF5D": {
                    "@MMK_L_foo": {"@MMK_R_foo": -300}
                },
            },
        )

        ds2 = glyphsLib.to_designspace(font, minimize_glyphs_diffs=True)
        bracketed_groups = {
            "public.kern2.foo": ["a", "a.BRACKET.300"],
            "public.kern1.foo": ["x", "x.BRACKET.300", "x.BRACKET.600"],
        }
        self.assertEqual(ds2.sources[0].font.groups, bracketed_groups)
        self.assertEqual(ds2.sources[1].font.groups, bracketed_groups)
        self.assertEqual(ds2.sources[2].font.groups, bracketed_groups)
        self.assertEqual(ds2.sources[3].font.groups, bracketed_groups)
        self.assertEqual(
            ds2.sources[0].font.kerning,
            {
                ("public.kern1.foo", "public.kern2.foo"): -200,
                ("a", "x"): -100,
                ("a.BRACKET.300", "x"): -100,
                ("a", "x.BRACKET.300"): -100,
                ("a.BRACKET.300", "x.BRACKET.300"): -100,
                ("a", "x.BRACKET.600"): -100,
                ("a.BRACKET.300", "x.BRACKET.600"): -100,
            },
        )
        self.assertEqual(ds2.sources[1].font.kerning, {})
        self.assertEqual(
            ds2.sources[2].font.kerning,
            {("public.kern1.foo", "public.kern2.foo"): -300},
        )
        self.assertEqual(ds2.sources[3].font.kerning, {})


class ToUfosTestDefcon(ToUfosTestBase, unittest.TestCase):
    ufo_module = defcon


class _PointDataPen:
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


class _Glyph:
    def __init__(self):
        self.pen = _PointDataPen()

    def getPointPen(self):
        return self.pen


class _UFOBuilder:
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


class GlyphPropertiesTestBase(ParametrizedUfoModuleTestMixin):
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
        ufo = self.to_ufos(font)[0]
        self.assertEqual(ufo["a"].lib.get("public.markColor"), "0.957,0,0.541,0.004")
        self.assertEqual(ufo["b"].lib.get("public.markColor"), "0.97,1,0,1")
        self.assertEqual(ufo["c"].lib.get("public.markColor"), None)
        self.assertEqual(ufo["d"].lib.get("public.markColor"), None)

    def test_anchor_assignment(self):
        filename = os.path.join(
            os.path.dirname(__file__), "..", "data", "AnchorAttachmentTest.glyphs"
        )
        with open(filename) as f:
            font = glyphsLib.load(f)

        self.assertEqual(
            font.glyphs["circumflexcomb_acutecomb"].layers[0].components[1].anchor,
            "top_viet",
        )
        self.assertFalse(
            font.glyphs["circumflexcomb_tildecomb"].layers[0].components[1].anchor
        )

        ds = self.to_designspace(font)
        ufo = ds.sources[0].font
        self.assertEqual(
            ufo["circumflexcomb_acutecomb"].lib[GLYPHLIB_PREFIX + "ComponentInfo"],
            [{"anchor": "top_viet", "index": 1, "name": "acutecomb"}],
        )
        self.assertIsNone(
            ufo["circumflexcomb_tildecomb"].lib.get(GLYPHLIB_PREFIX + "ComponentInfo")
        )

        font2 = to_glyphs(ds)
        self.assertEqual(
            font2.glyphs["circumflexcomb_acutecomb"].layers[0].components[1].anchor,
            "top_viet",
        )
        self.assertFalse(
            font2.glyphs["circumflexcomb_tildecomb"].layers[0].components[1].anchor
        )

        ufo["circumflexcomb_acutecomb"].lib[GLYPHLIB_PREFIX + "ComponentInfo"] = [
            {"anchor": "top_viet", "index": 1, "name": "asadad"}
        ]
        font3 = to_glyphs(ds)
        self.assertFalse(
            font3.glyphs["circumflexcomb_acutecomb"].layers[0].components[1].anchor
        )


class GlyphPropertiesTestUfoLib2(GlyphPropertiesTestBase, unittest.TestCase):
    ufo_module = ufoLib2


class GlyphPropertiesTestDefcon(GlyphPropertiesTestBase, unittest.TestCase):
    ufo_module = ufoLib2


class SkipDanglingAndNamelessLayersTestBase(ParametrizedUfoModuleTestMixin):
    def setUp(self):
        self.font = generate_minimal_font()
        add_glyph(self.font, "a")
        self.logger = logging.getLogger("glyphsLib.builder.builders.UFOBuilder")

    def test_normal_layer(self):
        with CapturingLogHandler(self.logger, level="WARNING") as captor:
            self.to_ufos(self.font)

        # no warnings are emitted
        self.assertRaises(
            AssertionError, captor.assertRegex, "is dangling and will be skipped"
        )
        self.assertRaises(AssertionError, captor.assertRegex, "layer without a name")

    def test_nameless_layer(self):
        self.font.glyphs[0].layers[0].associatedMasterId = "xxx"

        with CapturingLogHandler(self.logger, level="WARNING") as captor:
            self.to_ufos(self.font, minimize_glyphs_diffs=True)

        captor.assertRegex("layer without a name")

        # no warning if minimize_glyphs_diff=False
        with CapturingLogHandler(self.logger, level="WARNING") as captor:
            self.to_ufos(self.font, minimize_glyphs_diffs=False)

        self.assertFalse(captor.records)

    def test_dangling_layer(self):
        self.font.glyphs[0].layers[0].layerId = "yyy"
        self.font.glyphs[0].layers[0].associatedMasterId = "xxx"

        with CapturingLogHandler(self.logger, level="WARNING") as captor:
            self.to_ufos(self.font, minimize_glyphs_diffs=True)

        captor.assertRegex("is dangling and will be skipped")


class SkipDanglingAndNamelessLayersTestUfoLib2(
    SkipDanglingAndNamelessLayersTestBase, unittest.TestCase
):
    ufo_module = ufoLib2


class SkipDanglingAndNamelessLayersTestDefcon(
    SkipDanglingAndNamelessLayersTestBase, unittest.TestCase
):
    ufo_module = defcon


class GlyphOrderTestBase(object):
    """Check that the glyphOrder data is persisted correctly in all directions.

    When Glyphs 2.6.1 opens a UFO with a public.glyphOrder key and...

    1. ... no com.schriftgestaltung.glyphOrder key, it will copy
       public.glyphOrder verbatim to the font's custom parameter glyphOrder,
       including non-existant glyphs. It will sort the glyphs in the font
       overview ("Predefined Sorting") as specified by the font's custom
       parameter glyphOrder.
    2. ... a com.schriftgestaltung.glyphOrder key set to a list of glyph names,
       it will copy com.schriftgestaltung.glyphOrder verbatim to the font's custom
       parameter glyphOrder, including non-existant glyphs. It will not reorder
       the glyphs and instead display them as specified in public.glyphOrder. If
       the glyphs aren't grouped by category, it may make repeated category groups
       (e.g. Separator: .notdef, Punctuation: period, Separator: nbspace).
    3. ... a com.schriftgestaltung.glyphOrder key set to False, it will not
       copy public.glyphOrder at all and there is no font custom parameter
       glyphOrder. It will also not sort the glyphs in the font overview and
       instead display them as specified in public.glyphOrder. Round-tripping
       back will therefore overwrite public.glyphOrder with the order of the
       .glyphs file.

    When Glyphs 2.6.1 opens a UFO _without_ a public.glyphOrder key and...

    1. ... no com.schriftgestaltung.glyphOrder key, it will sort the glyphs in
       the font overview in the typical Glyphs way and not create a font custom
       parameter glyphOrder.
    2. ... a com.schriftgestaltung.glyphOrder key set to a list of glyph names,
       it will copy com.schriftgestaltung.glyphOrder verbatim to the font's custom
       parameter glyphOrder, including non-existant glyphs and will sort the
       glyphs in the font overview ("Predefined Sorting") as specified by the font's
       custom parameter glyphOrder.
    3. ... a com.schriftgestaltung.glyphOrder key set to False, it will sort
       the glyphs in the typical Glyphs way and not create a font custom parameter
       glyphOrder.

    Our Strategy:

    1. If a UFO's public.glyphOrder key...
        1. exists: write it to the Glyph font-level glyphOrder custom parameter.
        2. does not exist: Do not write a Glyph font-level glyphOrder custom parameter,
           the order of glyphs is then undefined.
    2. If the Glyph font-level glyphOrder custom parameter...
        1. exists: write it to a UFO's public.glyphOrder key.
        2. does not exist: write the order of Glyphs glyphs into a UFO's
           public.glyphOrder key.
        (This means that glyphs2ufo will *always* write a public.glyphOrder)
    3. Ignore the com.schriftgestaltung.glyphOrder key.
    """

    ufo_module = None  # subclasses must override this

    def setUp(self):
        self.font = GSFont()
        self.font.masters.append(GSFontMaster())
        self.font.glyphs.append(GSGlyph("c"))
        self.font.glyphs.append(GSGlyph("a"))
        self.font.glyphs.append(GSGlyph("f"))

        self.ufo = self.ufo_module.Font()
        self.ufo.newGlyph("c")
        self.ufo.newGlyph("a")
        self.ufo.newGlyph("f")
        if "public.glyphOrder" in self.ufo.lib:
            del self.ufo.lib["public.glyphOrder"]  # defcon automatism

    def from_glyphs(self):
        builder = UFOBuilder(self.font, ufo_module=self.ufo_module)
        return next(iter(builder.masters))

    def from_ufo(self):
        builder = GlyphsBuilder([self.ufo])
        return builder.font

    def test_ufo_to_glyphs_with_glyphOrder(self):
        self.ufo.lib["public.glyphOrder"] = ["c", "xxx1", "f", "xxx2"]
        self.ufo.lib[GLYPHS_PREFIX + "glyphOrder"] = ["a", "b", "c", "d"]
        font = self.from_ufo()
        self.assertEqual(
            ["c", "xxx1", "f", "xxx2"], font.customParameters["glyphOrder"]
        )
        # NOTE: Glyphs not present in public.glyphOrder are appended. Appending order
        # is undefined.
        self.assertEqual(["c", "f", "a"], [glyph.name for glyph in font.glyphs])

    def test_ufo_to_glyphs_without_glyphOrder(self):
        self.ufo.lib[GLYPHS_PREFIX + "glyphOrder"] = ["a", "b", "c", "d"]
        font = self.from_ufo()
        self.assertNotIn("glyphOrder", font.customParameters)
        # NOTE: order of glyphs in font.glyphs undefined because order in the UFO
        # undefined.

    def test_glyphs_to_ufo_without_glyphOrder(self):
        ufo = self.from_glyphs()
        self.assertEqual(["c", "a", "f"], ufo.lib["public.glyphOrder"])
        self.assertNotIn(GLYPHS_PREFIX + "glyphOrder", ufo.lib)

    def test_glyphs_to_ufo_with_glyphOrder(self):
        self.font.customParameters["glyphOrder"] = ["c", "xxx1", "a", "f", "xxx2"]
        ufo = self.from_glyphs()
        self.assertEqual(["c", "xxx1", "a", "f", "xxx2"], ufo.lib["public.glyphOrder"])
        self.assertNotIn(GLYPHS_PREFIX + "glyphOrder", ufo.lib)


class GlyphOrderTestUfoLib2(GlyphOrderTestBase, unittest.TestCase):
    ufo_module = ufoLib2


class GlyphOrderTestDefcon(GlyphOrderTestBase, unittest.TestCase):
    ufo_module = defcon


if __name__ == "__main__":
    unittest.main()
