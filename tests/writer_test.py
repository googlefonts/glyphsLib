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
from collections import OrderedDict

import glyphsLib
from glyphsLib import classes
from glyphsLib.types import glyphs_datetime

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
        """Test the writer on all GSFont attributes"""
        font = classes.GSFont()
        # List of properties from https://docu.glyphsapp.com/#gsfont
        # parent: not handled because it's internal and read-only
        # masters
        m1 = classes.GSFontMaster()
        m1.id = "M1"
        font.masters.insert(0, m1)
        m2 = classes.GSFontMaster()
        m2.id = "M2"
        font.masters.insert(1, m2)
        # instances
        i1 = classes.GSInstance()
        i1.name = "MuchBold"
        font.instances.append(i1)
        # glyphs
        g1 = classes.GSGlyph()
        g1.id = 'G1'
        font.glyphs.append(g1)
        # classes
        c1 = classes.GSClass()
        c1.name = "C1"
        font.classes.append(c1)
        # features
        f1 = classes.GSFeature()
        f1.name = "F1"
        font.features.append(f1)
        # featurePrefixes
        fp1 = classes.GSFeaturePrefix()
        fp1 = "FP1"
        font.featurePrefixes.append(fp1)
        # copyright
        font.copyright = "Copyright Bob"
        # designer
        font.designer = "Bob"
        # designerURL
        font.designerURL = "bob.me"
        # manufacturer
        font.manufacturer = "Manu"
        # manufacturerURL
        font.manufacturerURL = "manu.com"
        # versionMajor
        font.versionMajor = 2
        # versionMinor
        font.versionMinor = 104
        # date
        font.date = glyphs_datetime('2017-10-03 07:35:46 +0000')
        # familyName
        font.familyName = "Sans Rien"
        # upm
        # FIXME: (jany) In this library it is called "unitsPerEm"
        # font.upm = 2000
        font.unitsPerEm = 2000
        # note
        font.note = "Was bored, made this"
        # kerning
        font.kerning = OrderedDict([
            ('M1', OrderedDict([
                ('@MMK_L_G1', OrderedDict([
                    ('@MMK_R_G1', 0.1)
                ]))
            ]))
        ])
        # userData
        font.userData = {
            'a': 'test',
            'b': [1, {'c': 2}]
        }
        # grid
        font.grid = 35
        # gridSubDivisions
        # FIXME: (jany) In this library it is called "gridSubDivision" (no s)
        font.gridSubDivisions = 5
        # gridLength
        font.gridLength = 2
        # keyboardIncrement
        # FIXME: (jany) Not handled by this library, maybe because it's a
        #   UI feature from Glyphs.app. It should be handled though, so that
        #   designers who use the export/import macros don't lose their settings?
        font.keyboardIncrement = 1.2
        # disablesNiceNames
        font.disablesNiceNames = True
        # customParameters
        font.customParameters['ascender'] = 300
        # selection
        # FIXME: (jany) Not handled by this library.
        #   Not sure that it makes sense to handle it, because the selection
        #   sounds like a very impermanent thing that will not be expected to
        #   be restored after an export/import to UFO.
        #   Maybe it would still be nice to have? TODO: ask a designer?
        # font.selection = ?
        # selectedLayers
        # FIXME: (jany) Same as `selection`
        # selectedFontMaster
        # FIXME: (jany) Same as `selection`
        # masterIndex
        # FIXME: (jany) Same as `selection`
        # currentText
        # FIXME: (jany) Same as `selection`
        # tabs
        # FIXME: (jany) Same as `selection`
        # currentTab
        # FIXME: (jany) Same as `selection`
        # filepath
        # FIXME: (jany) not handled because the GSFont should be able
        #   to be written anywhere on the disk once it has been loaded?
        # tool
        # FIXME: (jany) Same as `selection`
        # tools: not handled because it is a read-only list of GUI features
        # .appVersion (extra property that is not in the docs!)
        font.appVersion = 895
        # TODO: (jany) check that node and ascender are correctly stored
        self.assertWritten(font, dedent("""\
            {
            .appVersion = 895;
            classes = (
            {
            name = C1;
            }
            );
            copyright = "Copyright Bob";
            customParameters = (
            {
            name = note;
            value = "Was bored, made this";
            },
            {
            name = ascender;
            value = 300;
            }
            );
            date = "2017-10-03 07:35:46 +0000";
            designer = Bob;
            designerURL = bob.me;
            disablesNiceNames = 1;
            familyName = "Sans Rien";
            featurePrefixes = (
            FP1
            );
            features = (
            {
            name = F1;
            }
            );
            fontMaster = (
            {
            id = M1;
            },
            {
            id = M2;
            }
            );
            glyphs = (
            {
            }
            );
            grid = 35;
            gridLength = 2;
            instances = (
            {
            name = MuchBold;
            }
            );
            kerning = {
            M1 = {
            "@MMK_L_G1" = {
            "@MMK_R_G1" = 0.1;
            };
            };
            };
            manufacturer = Manu;
            manufacturerURL = manu.com;
            userData = {
            a = test;
            b = (
            1,
            {
            c = 2;
            }
            );
            };
            versionMajor = 2;
            versionMinor = 104;
            }
        """))

    # TODO: (jany) same for each GS class

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
