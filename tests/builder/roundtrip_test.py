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

import pytest
import unittest
import os

import glyphsLib
import glyphsLib.builder.constants
from glyphsLib import classes

from .. import test_helpers


class UFORoundtripTest(test_helpers.AssertUFORoundtrip):
    def test_empty_font(self):
        empty_font = classes.GSFont()
        empty_font.masters.append(classes.GSFontMaster())
        self.assertUFORoundtrip(empty_font)

    def test_GlyphsUnitTestSans(self):
        filename = os.path.join(
            os.path.dirname(__file__), "../data/GlyphsUnitTestSans.glyphs"
        )
        with open(filename) as f:
            font = glyphsLib.load(f)
        self.assertUFORoundtrip(font)

    @pytest.mark.xfail(reason="Master naming and instance data modification issues.")
    def test_BraceTestFont(self):
        filename = os.path.join(
            os.path.dirname(__file__), "../data/BraceTestFont.glyphs"
        )
        with open(filename) as f:
            font = glyphsLib.load(f)
        self.assertUFORoundtrip(font)

    def test_BraceTestFont_no_editor_state(self):
        filename = os.path.join(
            os.path.dirname(__file__), "../data/BraceTestFont.glyphs"
        )
        with open(filename) as f:
            font = glyphsLib.load(f)

        designspace = glyphsLib.to_designspace(font)
        for source in designspace.sources:
            assert source.font.lib[
                glyphsLib.builder.constants.FONT_CUSTOM_PARAM_PREFIX + "DisplayStrings"
            ] == ["a", "b"]

        designspace = glyphsLib.to_designspace(font, store_editor_state=False)
        for source in designspace.sources:
            assert (
                glyphsLib.builder.constants.FONT_CUSTOM_PARAM_PREFIX + "DisplayStrings"
                not in source.font.lib
            )


if __name__ == "__main__":
    unittest.main()
