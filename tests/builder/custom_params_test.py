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

from textwrap import dedent
import unittest

# unittest.mock is only available for python 3.3+
try:
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    from mock import patch
    import mock

import glyphsLib
from defcon import Font
from glyphsLib.builder.builders import UFOBuilder
from glyphsLib.builder.custom_params import _set_default_params
from glyphsLib.builder.constants import (
    UFO2FT_USE_PROD_NAMES_KEY,
    FONT_CUSTOM_PARAM_PREFIX,
    MASTER_CUSTOM_PARAM_PREFIX,
)
from glyphsLib.classes import GSFont, GSFontMaster, GSCustomParameter


class SetCustomParamsTest(unittest.TestCase):
    def setUp(self):
        self.ufo = Font()
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

        self.ufo = Font()
        self.master.customParameters = [
            GSCustomParameter(name="Use Typo Metrics", value=True),
            GSCustomParameter(name="Has WWS Names", value=True),
        ]
        self.set_custom_params()
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [7, 8])

    def test_underlinePosition(self):
        self.master.customParameters["underlinePosition"] = -2
        self.set_custom_params()
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, -2)

        # self.master.customParameters['underlinePosition'] = 1
        for param in self.master.customParameters:
            if param.name == "underlinePosition":
                param.value = 1
                break
        self.set_custom_params()
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, 1)

    def test_underlineThickness(self):
        self.master.customParameters["underlineThickness"] = 100
        self.set_custom_params()
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 100)

        # self.master.customParameters['underlineThickness'] = 0
        for param in self.master.customParameters:
            if param.name == "underlineThickness":
                param.value = 0
                break
        self.set_custom_params()
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 0)

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
        self.font.customParameters["Disable Last Change"] = True
        self.set_custom_params()
        self.assertEqual(
            True, self.ufo.lib[FONT_CUSTOM_PARAM_PREFIX + "disablesLastChange"]
        )

    # https://github.com/googlei18n/glyphsLib/issues/268
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
