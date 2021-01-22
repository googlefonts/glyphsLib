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


import os
from collections import OrderedDict
import unittest
import datetime

import glyphsLib
from glyphsLib.dictParser import DictParser
from glyphsLib.classes import GSGlyph, GSGuide, GSFontMaster, GSLayer, GSHint
from glyphsLib.types import Point
import openstep_plist

GLYPH_DATA = """\
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
)"""

NESTED_DATA = """
(
{
glyphname = A;
lastChange = "2017-07-17 13:57:06 +0000";
layers = (
{
anchors = (
{
name = bottom;
position = "{377, 0}";
},
{
name = ogonek;
position = "{678, 10}";
},
{
name = top;
position = "{377, 700}";
}
);
layerId = "BFFFD157-90D3-4B85-B99D-9A2F366F03CA";
}
);
leftKerningGroup = A;
rightKerningGroup = A;
unicode = 0041;
script = "";
category = "";
subCategory = "";
}
)
"""

class ParserGlyphTest(unittest.TestCase):

    def test_parse_glyphs(self):
        data = GLYPH_DATA
        data_dict = openstep_plist.loads(data)

        parser = DictParser(GSGlyph)
        result = parser.parse(data_dict)
        glyph = result[0]
        self.assertEqual(glyph.name, "A")
        self.assertEqual(glyph.color, 5)
        self.assertEqual(glyph.lastChange, datetime.datetime(2017, 4, 30, 13, 57, 4))
        self.assertEqual(glyph.leftKerningGroup, "A")
        self.assertEqual(glyph.rightKerningGroup, "A")
        self.assertEqual(glyph.unicode, "0041")

    def test_parse_nested(self):
        data = NESTED_DATA
        data_dict = openstep_plist.loads(data)

        parser = DictParser(GSGlyph)
        result = parser.parse(data_dict)
        glyph = result[0]
        self.assertEqual(glyph.name, "A")
        self.assertEqual(len(glyph.layers), 1)
        self.assertEqual(len(glyph.layers[0].anchors), 3)
        self.assertEqual(glyph.layers[0].anchors[0].position.x, 377)

    def test_guideline(self):
        data = """
{
position = "{-126, 593}";
}
"""
        data_dict = openstep_plist.loads(data)

        parser = DictParser(GSGuide)
        result = parser.parse(data_dict)
        self.assertEqual(result.position.x, -126)
        self.assertEqual(result.position.y, 593)

    def test_gsfontmaster(self):
        data = """
{
alignmentZones = (
"{800, 12}",
"{700, 12}",
"{480, 12}",
"{0, -12}",
"{-200, -12}"
);
ascender = 800;
capHeight = 700;
descender = -200;
guideLines = (
{
position = "{-126, 593}";
},
{
locked = 1;
position = "{-126, 90}";
},
{
position = "{-113, 773}";
},
{
position = "{524, -133}";
},
{
position = "{-126, 321}";
},
{
position = "{-113, 959}";
}
);
horizontalStems = (
80,
88,
91
);
id = "3E7589AA-8194-470F-8E2F-13C1C581BE24";
weightValue = 90;
xHeight = 480;
}
"""
        data_dict = openstep_plist.loads(data)

        parser = DictParser(GSLayer)
        result = parser.parse(data_dict)
        self.assertEqual(result.guides[0].position.x, -126)
        self.assertEqual(result.guides[0].position.y, 593)

    def test_gshint_v2(self):
        data = """
{
horizontal = 1;
origin = "{1, 1}";
target = "{1, 0}";
type = Stem;
}
"""
        data_dict = openstep_plist.loads(data)

        parser = DictParser(GSHint)
        result = parser.parse(data_dict)
        self.assertEqual(result.target.x, 1)
        self.assertEqual(result.target.y, 0)

    def test_gshint_v3(self):
        data = """
{
horizontal = 1;
origin = (1,1);
target = (1,0);
type = Stem;
}
"""
        data_dict = openstep_plist.loads(data)

        parser = DictParser(GSHint)
        result = parser.parse(data_dict)
        self.assertEqual(result.target.x, 1)
        self.assertEqual(result.target.y, 0)

def test_parser_main(capsys):
    """This is both a test for the "main" functionality of glyphsLib.parser
    and for the round-trip of GlyphsUnitTestSans.glyphs.
    """
    filename = os.path.join(os.path.dirname(__file__), "data/GlyphsUnitTestSans.glyphs")
    with open(filename) as f:
        expected = f.read()

    glyphsLib.dictParser.main([filename])
    out, _err = capsys.readouterr()
    assert expected == out, "The roundtrip should output the .glyphs file unmodified."


def test_parser_main_v3(capsys):
    """This is both a test for the "main" functionality of glyphsLib.parser
    and for the round-trip of GlyphsUnitTestSans.glyphs.
    """
    filename = os.path.join(
        os.path.dirname(__file__), "data/GlyphsUnitTestSans3.glyphs"
    )
    with open(filename) as f:
        expected = f.read()

    glyphsLib.dictParser.main([filename])
    out, _err = capsys.readouterr()
    assert expected == out, "The roundtrip should output the .glyphs file unmodified."


def test_parser_main_v3_upstream(capsys):
    filename = os.path.join(os.path.dirname(__file__), "data/GlyphsFileFormatv3.glyphs")
    with open(filename) as f:
        expected = f.read()

    glyphsLib.dictParser.main([filename])
    out, _err = capsys.readouterr()
    assert expected == out, "The roundtrip should output the .glyphs file unmodified."

