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


from __future__ import (print_function, division, absolute_import,
                        unicode_literals)

from collections import OrderedDict
import unittest
import datetime

from glyphsLib.parser import Parser
from glyphsLib.classes import GSGlyph, GSLayer
from glyphsLib.types import color, glyphs_datetime
from fontTools.misc.py23 import unicode

GLYPH_DATA = '''\
(
{
glyphname="A";
color=5;
lastChange = "2017-04-30 13:57:04 +0000";
layers = ();
leftKerningGroup = A;
rightKerningGroup = A;
unicode = 0041;
}
)'''


class ParserTest(unittest.TestCase):
    def run_test(self, text, expected):
        parser = Parser()
        self.assertEqual(parser.parse(text), OrderedDict(expected))

    def test_parse(self):
        self.run_test(
            '{myval=1; mylist=(1,2,3);}',
            [('myval', 1), ('mylist', [1, 2, 3])])

    def test_trim_value(self):
        self.run_test(
            '{mystr="a\\"s\\077d\\U2019f";}',
            [('mystr', 'a"s?d’f')])

    def test_trailing_content(self):
        with self.assertRaises(ValueError):
            self.run_test(
                '{myval=1;}trailing',
                [('myval', '1')])

    def test_unexpected_content(self):
        with self.assertRaises(ValueError):
            self.run_test(
                '{myval=@unexpected;}',
                [('myval', '@unexpected')])

    def test_with_utf8(self):
        self.run_test(
            b'{mystr="Don\xe2\x80\x99t crash";}',
            [('mystr', 'Don’t crash')])

    def test_parse_str_infinity(self):
        self.run_test(
            b'{mystr = infinity;}',
            [('mystr', 'infinity')]
        )
        self.run_test(
            b'{mystr = Infinity;}',
            [('mystr', 'Infinity')]
        )
        self.run_test(
            b'{mystr = InFiNItY;}',
            [('mystr', 'InFiNItY')]
        )

    def test_parse_str_inf(self):
        self.run_test(
            b'{mystr = inf;}',
            [('mystr', 'inf')]
        )
        self.run_test(
            b'{mystr = Inf;}',
            [('mystr', 'Inf')]
        )

    def test_parse_str_nan(self):
        self.run_test(
            b'{mystr = nan;}',
            [('mystr', 'nan')]
        )
        self.run_test(
            b'{mystr = NaN;}',
            [('mystr', 'NaN')]
        )

    def test_dont_crash_on_string_that_looks_like_a_dict(self):
        # https://github.com/googlei18n/glyphsLib/issues/238
        self.run_test(
            b'{UUID0 = "{0.5, 0.5}";}',
            [('UUID0', '{0.5, 0.5}')]
        )

    def test_parse_dict_in_dict(self):
        self.run_test(
            b'{outer = {inner = "turtles";};}',
            [('outer', OrderedDict([('inner', 'turtles')]))]
        )


GLYPH_ATTRIBUTES = {
    "bottomKerningGroup": str,
    "bottomMetricsKey": str,
    "category": str,
    "color": color,
    "export": bool,
    # "glyphname": str,
    "lastChange": glyphs_datetime,
    "layers": GSLayer,
    "leftKerningGroup": str,
    "leftMetricsKey": str,
    "name": str,
    "note": unicode,
    "partsSettings": dict,
    "production": str,
    "rightKerningGroup": str,
    "rightMetricsKey": str,
    "script": str,
    "subCategory": str,
    "topKerningGroup": str,
    "topMetricsKey": str,
    "unicode": str,
    "userData": dict,
    "vertWidthMetricsKey": str,
    "widthMetricsKey": str,
}


class ParserGlyphTest(unittest.TestCase):
    def test_parse_empty_glyphs(self):
        # data = '({glyphname="A";})'
        data = '({})'
        parser = Parser(GSGlyph)
        result = parser.parse(data)
        self.assertEqual(len(result), 1)
        glyph = result[0]
        self.assertIsInstance(glyph, GSGlyph)
        defaults_as_none = [
            "category",
            "color",
            "lastChange",
            "leftKerningGroup",
            "leftMetricsKey",
            "name",
            "note",
            "rightKerningGroup",
            "rightMetricsKey",
            "script",
            "subCategory",
            "unicode",
            "widthMetricsKey",
        ]
        for attr in defaults_as_none:
            self.assertIsNone(getattr(glyph, attr))
        self.assertIsNotNone(glyph.userData)
        defaults_as_true = [
            "export",
        ]
        for attr in defaults_as_true:
            self.assertTrue(getattr(glyph, attr))

    def test_parse_glyphs(self):
        data = GLYPH_DATA
        parser = Parser(GSGlyph)
        result = parser.parse(data)
        glyph = result[0]
        self.assertEqual(glyph.name, "A")
        self.assertEqual(glyph.color, 5)
        self.assertEqual(glyph.lastChange,
                         datetime.datetime(2017, 4, 30, 13, 57, 4))
        self.assertEqual(glyph.leftKerningGroup, "A")
        self.assertEqual(glyph.rightKerningGroup, "A")
        self.assertEqual(glyph.unicode, "0041")


if __name__ == '__main__':
    unittest.main()
