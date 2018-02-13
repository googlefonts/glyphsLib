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

import unittest
import os

import glyphsLib
from glyphsLib import classes

import test_helpers


class UFORoundtripTest(unittest.TestCase, test_helpers.AssertUFORoundtrip):
    def test_empty_font(self):
        empty_font = classes.GSFont()
        empty_font.masters.append(classes.GSFontMaster())
        self.assertUFORoundtrip(empty_font)

    def test_GlyphsUnitTestSans(self):
        self.skipTest("TODO")
        filename = os.path.join(os.path.dirname(__file__),
                                'data/GlyphsUnitTestSans.glyphs')
        with open(filename) as f:
            font = glyphsLib.classes.GSFont(f)
        self.assertUFORoundtrip(font)


if __name__ == '__main__':
    unittest.main()
