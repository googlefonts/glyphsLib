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
import difflib
import sys

from glyphsLib import classes
from glyphsLib.builder import (to_ufos, to_glyphs)

import test_helpers


class ClassRoundtripTest(unittest.TestCase, test_helpers.AssertLinesEqual):
    def assertRoundtrip(self, font):
        expected = test_helpers.write_to_lines(font)
        roundtrip = to_glyphs(to_ufos(font))
        actual = test_helpers.write_to_lines(roundtrip)
        self.assertLinesEqual(
            expected, actual,
            "The font has been modified by the roundtrip")

    def test_empty_font(self):
        empty_font = classes.GSFont()
        empty_font.masters.append(classes.GSFontMaster())
        self.assertRoundtrip(empty_font)


if __name__ == '__main__':
    unittest.main()
