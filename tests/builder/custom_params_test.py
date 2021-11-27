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


from textwrap import dedent
import unittest
import os

from unittest import mock
from unittest.mock import patch

import glyphsLib
import defcon
import ufoLib2
from glyphsLib.builder.builders import UFOBuilder
from glyphsLib.builder import to_ufos
from glyphsLib.builder.custom_params import (
    _set_default_params,
    GLYPHS_UFO_CUSTOM_PARAMS,
)
from glyphsLib.builder.constants import (
    UFO2FT_FILTERS_KEY,
    UFO2FT_USE_PROD_NAMES_KEY,
    FONT_CUSTOM_PARAM_PREFIX,
    MASTER_CUSTOM_PARAM_PREFIX,
    UFO_FILENAME_CUSTOM_PARAM,
    GLYPHLIB_PREFIX,
)
from glyphsLib.builder.masters import UFO_FILENAME_KEY
from glyphsLib.builder.instances import FULL_FILENAME_KEY
from glyphsLib.classes import GSFont, GSFontMaster, GSCustomParameter, GSGlyph, GSLayer
from glyphsLib.types import parse_datetime

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class SetCustomParamsTestBase(object):

    ufo_module = None  # subclasses must override this

    def setUp(self):
        self.ufo = self.ufo_module.Font()
        self.font = GSFont()
        self.master = GSFontMaster()
        self.font.masters.insert(0, self.master)
        self.builder = UFOBuilder(self.font)

    def set_custom_params(self):
        self.builder.to_ufo_custom_params(self.ufo, self.font)
        self.builder.to_ufo_custom_params(self.ufo, self.master)

    def test_normalizes_curved_quotes_in_names(self):
        self.master.customParameters = [
            GSCustomParameter(name="‘bad’", value=1),
            GSCustomParameter(name="“also bad”", value=2),
        ]
        self.set_custom_params()
        self.assertIn(MASTER_CUSTOM_PARAM_PREFIX + "'bad'", self.ufo.lib)
        self.assertIn(MASTER_CUSTOM_PARAM_PREFIX + '"also bad"', self.ufo.lib)

    def test_set_fsSelection_flags_none(self):
        self.ufo.info.openTypeOS2Selection = None
        self.font = glyphsLib.to_glyphs([self.ufo], minimize_ufo_diffs=True)
        self.assertEqual(self.font.customParameters["Use Typo Metrics"], None)
        self.assertEqual(self.font.customParameters["Has WWS Names"], None)
        self.assertEqual(
            self.font.customParameters["openTypeOS2SelectionUnsupportedBits"], None
        )
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Selection, None)

    def test_set_fsSelection_flags_empty(self):
        self.ufo.info.openTypeOS2Selection = []
        self.font = glyphsLib.to_glyphs([self.ufo], minimize_ufo_diffs=True)
        self.assertEqual(self.font.customParameters["Use Typo Metrics"], None)
        self.assertEqual(self.font.customParameters["Has WWS Names"], None)
        self.assertEqual(
            self.font.customParameters["openTypeOS2SelectionUnsupportedBits"], []
        )
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [])

    def test_set_fsSelection_flags_all(self):
        self.ufo.info.openTypeOS2Selection = [1, 2, 3, 4, 7, 8, 9]
        self.font = glyphsLib.to_glyphs([self.ufo], minimize_ufo_diffs=True)
        self.assertEqual(self.font.customParameters["Use Typo Metrics"], True)
        self.assertEqual(self.font.customParameters["Has WWS Names"], True)
        self.assertEqual(
            self.font.customParameters["openTypeOS2SelectionUnsupportedBits"],
            [1, 2, 3, 4, 9],
        )
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [1, 2, 3, 4, 7, 8, 9])

    def test_set_fsSelection_flags(self):
        self.assertEqual(self.ufo.info.openTypeOS2Selection, None)

        self.master.customParameters["Has WWS Names"] = False
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Selection, None)

        self.master.customParameters["Use Typo Metrics"] = True
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [7])

        self.ufo = self.ufo_module.Font()
        self.master.customParameters = [
            GSCustomParameter(name="Use Typo Metrics", value=True),
            GSCustomParameter(name="Has WWS Names", value=True),
        ]
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [7, 8])

    def test_integer_parameters(self):
        """Test casting glyphsapp customParameters whose values are just
        integers into ufo equivalents."""
        integer_params = [
            "underlinePosition",
            "underlineThickness",
            "strikeoutPosition",
            "strikeoutSize",
            "subscriptXSize",
            "subscriptYSize",
            "subscriptXOffset",
            "subscriptYOffset",
            "superscriptXSize",
            "superscriptYSize",
            "superscriptXOffset",
            "superscriptYOffset",
        ]
        params_to_check = [
            (k, v) for (k, v) in GLYPHS_UFO_CUSTOM_PARAMS if k in integer_params
        ]

        for glyphs_key, ufo_key in params_to_check:
            self.master.customParameters[glyphs_key] = 10
            self.set_custom_params()
            self.assertEqual(getattr(self.ufo.info, ufo_key), 10)
            for param in self.master.customParameters:
                if param.name == glyphs_key:
                    param.value = -2
                    break
            self.set_custom_params()
            self.assertEqual(getattr(self.ufo.info, ufo_key), -2)

    @patch("glyphsLib.builder.custom_params.parse_glyphs_filter")
    def test_parse_glyphs_filter(self, mock_parse_glyphs_filter):
        pre_filter = "AddExtremes"
        filter1 = "Transformations;OffsetX:40;OffsetY:60;include:uni0334,uni0335"
        filter2 = "Transformations;OffsetX:10;OffsetY:-10;exclude:uni0334,uni0335"
        self.master.customParameters.extend(
            [
                GSCustomParameter(name="PreFilter", value=pre_filter),
                GSCustomParameter(name="Filter", value=filter1),
                GSCustomParameter(name="Filter", value=filter2),
            ]
        )
        self.set_custom_params()

        self.assertEqual(mock_parse_glyphs_filter.call_count, 3)
        self.assertEqual(
            mock_parse_glyphs_filter.call_args_list[0],
            mock.call(pre_filter, is_pre=True),
        )
        self.assertEqual(
            mock_parse_glyphs_filter.call_args_list[1], mock.call(filter1, is_pre=False)
        )
        self.assertEqual(
            mock_parse_glyphs_filter.call_args_list[2], mock.call(filter2, is_pre=False)
        )

    def test_set_defaults(self):
        _set_default_params(self.ufo)
        self.assertEqual(self.ufo.info.openTypeOS2Type, [3])
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, -100)
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 50)

    def test_set_codePageRanges_empty(self):
        self.font.customParameters["codePageRanges"] = []
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2CodePageRanges, [])
        self.font = glyphsLib.to_glyphs([self.ufo], minimize_ufo_diffs=True)
        self.assertEqual(self.font.customParameters["codePageRanges"], [])

    def test_set_codePageRanges(self):
        self.font.customParameters["codePageRanges"] = [1252, 1250]
        self.font.customParameters["codePageRangesUnsupportedBits"] = [15]
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2CodePageRanges, [0, 1, 15])
        self.font = glyphsLib.to_glyphs([self.ufo], minimize_ufo_diffs=True)
        self.assertEqual(self.font.customParameters["codePageRanges"], [1252, 1250])
        self.assertEqual(
            self.font.customParameters["codePageRangesUnsupportedBits"], [15]
        )

    def test_set_openTypeOS2CodePageRanges(self):
        self.font.customParameters["openTypeOS2CodePageRanges"] = [1252, 1250]
        self.font.customParameters["codePageRangesUnsupportedBits"] = [15]
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2CodePageRanges, [0, 1, 15])
        self.font = glyphsLib.to_glyphs([self.ufo], minimize_ufo_diffs=True)
        self.assertEqual(self.font.customParameters["codePageRanges"], [1252, 1250])
        self.assertEqual(
            self.font.customParameters["codePageRangesUnsupportedBits"], [15]
        )

    def test_gasp_table(self):
        gasp_table = {"65535": "15", "20": "7", "8": "10"}
        self.font.customParameters["GASP Table"] = gasp_table
        self.set_custom_params()

        ufo_range_records = self.ufo.info.openTypeGaspRangeRecords
        self.assertIsNotNone(ufo_range_records)
        self.assertEqual(len(ufo_range_records), 3)
        rec1, rec2, rec3 = ufo_range_records
        self.assertEqual(rec1["rangeMaxPPEM"], 8)
        self.assertEqual(rec1["rangeGaspBehavior"], [1, 3])
        self.assertEqual(rec2["rangeMaxPPEM"], 20)
        self.assertEqual(rec2["rangeGaspBehavior"], [0, 1, 2])
        self.assertEqual(rec3["rangeMaxPPEM"], 65535)
        self.assertEqual(rec3["rangeGaspBehavior"], [0, 1, 2, 3])

    def test_set_disables_nice_names(self):
        self.font.disablesNiceNames = False
        self.set_custom_params()
        self.assertEqual(True, self.ufo.lib[FONT_CUSTOM_PARAM_PREFIX + "useNiceNames"])

    def test_set_disable_last_change(self):
        glyph = GSGlyph()
        glyph.name = "a"
        self.font.glyphs.append(glyph)
        layer = GSLayer()
        layer.layerId = self.font.masters[0].id
        layer.associatedMasterId = self.font.masters[0].id
        layer.width = 100
        glyph.layers.append(layer)
        glyph.lastChange = parse_datetime("2017-10-03 07:35:46 +0000")
        self.font.customParameters["Disable Last Change"] = True
        self.ufo = to_ufos(self.font)[0]
        self.assertEqual(
            True, self.ufo.lib[FONT_CUSTOM_PARAM_PREFIX + "disablesLastChange"]
        )
        self.assertNotIn(GLYPHLIB_PREFIX + "lastChange", self.ufo["a"].lib)

    # https://github.com/googlefonts/glyphsLib/issues/268
    def test_xHeight(self):
        self.ufo.info.xHeight = 300
        self.master.customParameters["xHeight"] = "500"
        self.set_custom_params()
        # Additional xHeight values are Glyphs-specific and stored in lib
        self.assertEqual(self.ufo.lib[MASTER_CUSTOM_PARAM_PREFIX + "xHeight"], "500")
        # The xHeight from the property is not modified
        self.assertEqual(self.ufo.info.xHeight, 300)
        # TODO: (jany) check that the instance custom param wins over the
        #       interpolated value

    def test_replace_feature(self):
        self.ufo.features.text = dedent(
            """
            feature liga {
            # only the first match is replaced
            sub f i by fi;
            } liga;

            feature calt {
            sub e' t' c by ampersand;
            } calt;

            feature liga {
            sub f l by fl;
            } liga;
        """
        )

        repl = "liga; sub f f by ff;"

        self.master.customParameters["Replace Feature"] = repl
        self.set_custom_params()

        self.assertEqual(
            self.ufo.features.text,
            dedent(
                """
            feature liga {
            sub f f by ff;
            } liga;

            feature calt {
            sub e' t' c by ampersand;
            } calt;

            feature liga {
            sub f l by fl;
            } liga;
        """
            ),
        )

        # only replace feature body if tag already present
        original = self.ufo.features.text
        repl = "numr; sub one by one.numr;\nsub two by two.numr;\n"

        self.master.customParameters["Replace Feature"] = repl
        self.set_custom_params()

        self.assertEqual(self.ufo.features.text, original)

    def test_replace_prefix(self):
        self.ufo.features.text = dedent(
            """\
            # Prefix: AAA
            include(../aaa.fea);

            # Prefix: FOO
            # foo

            # Prefix: ZZZ
            include(../zzz.fea);

            # Prefix: BAR
            # bar

            feature liga {
            sub f i by f_i;
            } liga;

            table GDEF {
            GlyphClassDef
                [f i], # Base
                [f_i], # Liga
                , # Mark
                ;
            } GDEF;
            """
        )

        self.master.customParameters.append(
            GSCustomParameter("Replace Prefix", "FOO; include(../foo.fea);")
        )
        self.master.customParameters.append(
            GSCustomParameter("Replace Prefix", "BAR; include(../bar.fea);")
        )
        self.set_custom_params()

        self.assertEqual(
            self.ufo.features.text,
            dedent(
                """\
                # Prefix: AAA
                include(../aaa.fea);

                # Prefix: FOO
                include(../foo.fea);

                # Prefix: ZZZ
                include(../zzz.fea);

                # Prefix: BAR
                include(../bar.fea);

                table GDEF {
                GlyphClassDef
                    [f i], # Base
                    [f_i], # Liga
                    , # Mark
                    ;
                } GDEF;

                feature liga {
                sub f i by f_i;
                } liga;
                """
            ),
        )

    def test_useProductionNames(self):
        for value in (True, False):
            self.master.customParameters["Don't use Production Names"] = value
            self.set_custom_params()

            self.assertIn(UFO2FT_USE_PROD_NAMES_KEY, self.ufo.lib)
            self.assertEqual(self.ufo.lib[UFO2FT_USE_PROD_NAMES_KEY], not value)

    def test_default_fstype(self):
        # No specified fsType => set default value
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Type, [3])

    def test_set_fstype(self):
        # Set another fsType => store that
        self.master.customParameters["fsType"] = [2]
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Type, [2])

    def test_empty_fstype(self):
        # Set empty fsType => store empty
        self.master.customParameters["fsType"] = []
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Type, [])

    def test_version_string(self):
        # TODO: (jany) test the automatic replacement that is described in the
        #   Glyphs Handbook
        self.font.customParameters["versionString"] = "Version 2.040"
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeNameVersion, "Version 2.040")

    def test_ufo2ft_filter_roundtrip(self):
        ufo_filters = [
            {"name": "propagateAnchors", "pre": True, "include": ["a", "b", "c"]}
        ]
        glyphs_filter = "propagateAnchors;include:a,b,c"

        # Test the one-way conversion of (Pre)Filters into ufo2ft filters. See the
        # docstring for FilterParamHandler.
        self.master.customParameters["PreFilter"] = glyphs_filter
        self.set_custom_params()
        self.assertEqual(self.ufo.lib[UFO2FT_FILTERS_KEY], ufo_filters)

        # Test the round-tripping of ufo2ft filters from UFO -> Glyphs master -> UFO.
        # See the docstring for FilterParamHandler.
        font_rt = glyphsLib.to_glyphs([self.ufo])
        self.assertNotIn("PreFilter", font_rt.masters[0].customParameters)
        self.assertEqual(font_rt.masters[0].userData[UFO2FT_FILTERS_KEY], ufo_filters)
        ufo_rt = glyphsLib.to_ufos(font_rt, ufo_module=self.ufo_module)[0]
        self.assertEqual(ufo_rt.lib[UFO2FT_FILTERS_KEY], ufo_filters)

    def test_color_palettes(self):
        glyphs_palettes = [
            ["68,0,59,255", "220,187,72,255", "42,255", "87,255", "0,138,255,255"]
        ]
        ufo_palettes = [
            [
                (0.26666666666666666, 0.0, 0.23137254901960785, 1.0),
                (0.8627450980392157, 0.7333333333333333, 0.2823529411764706, 1.0),
                (0.16470588235294117, 0.16470588235294117, 0.16470588235294117, 1.0),
                (0.3411764705882353, 0.3411764705882353, 0.3411764705882353, 1.0),
                (0.0, 0.5411764705882353, 1.0, 1.0),
            ]
        ]
        self.font.customParameters["Color Palettes"] = glyphs_palettes
        self.set_custom_params()
        self.assertEqual(
            self.ufo.lib["com.github.googlei18n.ufo2ft.colorPalettes"], ufo_palettes
        )

        # Test the round-tripping
        font = glyphsLib.to_glyphs([self.ufo])
        self.assertEqual(font.customParameters["Color Palettes"], glyphs_palettes)


class SetCustomParamsTestUfoLib2(SetCustomParamsTestBase, unittest.TestCase):
    ufo_module = ufoLib2


class SetCustomParamsTestDefcon(SetCustomParamsTestBase, unittest.TestCase):
    ufo_module = defcon


def test_ufo_filename_custom_param(ufo_module):
    """Test that new-style UFO_FILENAME_CUSTOM_PARAM is written instead of
    (UFO_FILENAME_KEY|FULL_FILENAME_KEY)."""
    font = glyphsLib.GSFont(os.path.join(DATA, "UFOFilenameTest.glyphs"))
    ds = glyphsLib.to_designspace(
        font, minimize_glyphs_diffs=True, ufo_module=ufo_module
    )
    assert ds.sources[0].filename == "MyFontMaster.ufo"
    assert ds.instances[0].filename == "../build/instance_ufos/MyFont.ufo"
    assert "com.schriftgestaltung.customParameters" not in ds.instances[0].lib

    font_rt = glyphsLib.to_glyphs(ds, minimize_ufo_diffs=True)
    assert (
        font_rt.masters[0].customParameters[UFO_FILENAME_CUSTOM_PARAM]
        == "MyFontMaster.ufo"
    )
    assert UFO_FILENAME_KEY not in font_rt.masters[0].userData
    assert (
        font_rt.instances[0].customParameters[UFO_FILENAME_CUSTOM_PARAM]
        == "../build/instance_ufos/MyFont.ufo"
    )
    assert FULL_FILENAME_KEY not in font_rt.instances[0].customParameters

    ds_rt = glyphsLib.to_designspace(
        font_rt, minimize_glyphs_diffs=True, ufo_module=ufo_module
    )
    assert ds_rt.sources[0].filename == "MyFontMaster.ufo"
    assert ds_rt.instances[0].filename == "../build/instance_ufos/MyFont.ufo"


def test_ufo_filename_custom_param_plus_legacy(ufo_module):
    """Test that new-style UFO_FILENAME_CUSTOM_PARAM overrides legacy
    (UFO_FILENAME_KEY|FULL_FILENAME_KEY)."""
    font = glyphsLib.GSFont(os.path.join(DATA, "UFOFilenameTest.glyphs"))
    font.masters[0].customParameters[UFO_FILENAME_CUSTOM_PARAM] = "aaa.ufo"
    font.instances[0].customParameters[UFO_FILENAME_CUSTOM_PARAM] = "bbb.ufo"

    ds = glyphsLib.to_designspace(
        font, minimize_glyphs_diffs=True, ufo_module=ufo_module
    )
    assert ds.sources[0].filename == "aaa.ufo"
    assert ds.instances[0].filename == "bbb.ufo"


def test_ufo_filename_custom_param_instance_empty(ufo_module):
    font = glyphsLib.GSFont(os.path.join(DATA, "UFOFilenameTest.glyphs"))
    font.masters[0].customParameters[UFO_FILENAME_CUSTOM_PARAM] = "aaa.ufo"
    del font.instances[0].customParameters[UFO_FILENAME_CUSTOM_PARAM]
    del font.instances[0].customParameters[FULL_FILENAME_KEY]

    ds = glyphsLib.to_designspace(
        font, minimize_glyphs_diffs=True, ufo_module=ufo_module
    )
    assert ds.sources[0].filename == "aaa.ufo"
    # Instance filename should be whatever the default is.
    assert ds.instances[0].filename == "instance_ufos/NewFont-Regular.ufo"
