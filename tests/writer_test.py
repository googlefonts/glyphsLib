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
import datetime
from textwrap import dedent

import glyphsLib
from glyphsLib import classes

import test_helpers

class WriterTest(unittest.TestCase, test_helpers.AssertLinesEqual):
    def assertWritten(self, glyphs_object, text):
        """Assert that the given object, when given to the writer,
        produces the given text.
        """
        expected = text.splitlines()
        actual = test_helpers.write_to_lines(glyphs_object)
        # print(expected)
        # print(actual)
        self.assertLinesEqual(
            expected, actual,
            "The writer has not produced the expected output")

    def test_write_font_attributes(self):
        font = classes.GSFont()
        font.appVersion = 895
        font.date = datetime.datetime(2017, 10, 3, 7, 35, 46, 897234)
        font.familyName = 'MyFont'
        self.assertWritten(font, dedent("""\
            {
            .appVersion = 895;
            date = "2017-10-03 07:35:46.897234 +0000";
            familyName = MyFont;
            versionMajor = 1;
            versionMinor = 0;
            }
        """))


# Might be impractical because of formatting (whitespace changes)
# class WriterRoundtripTest(unittest.TestCase, test_helpers.AssertLinesEqual):
#     def assertParseWriteRoundtrip(self, filename):
#         with open(filename) as f:
#             expected = f.readlines()
#             font = glyphsLib.load(f)
#         actual = test_helpers.write_to_lines(font)
#         self.assertLinesEqual(
#             expected, actual,
#             "The writer should output exactly what the parser read")

#     def test_roundtrip_on_file(self):
#         self.assertParseWriteRoundtrip('data/GlyphsUnitTestSans.glyphs')


if __name__ == '__main__':
    unittest.main()
