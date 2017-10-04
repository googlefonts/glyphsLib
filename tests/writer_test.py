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

    def assertWrites(self, glyphs_object, text):
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

    def assertWritesValue(self, glyphs_value, text):
        """Assert that the writer produces the given text for the given value."""
        expected = dedent("""\
        {{
        writtenValue = {0};
        }}
        """).format(text).splitlines()
        # We wrap the value in a dict to use the same test helper
        actual = test_helpers.write_to_lines({'writtenValue': glyphs_value})
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
        self.assertWrites(font, dedent("""\
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

    def test_write_font_master_attributes(self):
        """Test the writer on all GSFontMaster attributes"""
        master = classes.GSFontMaster()
        # List of properties from https://docu.glyphsapp.com/#gsfontmaster
        # id
        master.id = "MASTER-ID"
        # name
        master.name = "Hairline Megawide"
        # weight
        master.weight = "Thin"
        # width
        master.width = "Wide"
        # weightValue
        master.weightValue = 0.01
        # widthValue
        master.widthValue = 0.99
        # customValue
        # customName
        # FIXME: (jany) Why is it called "custom" here instead of "customName"?
        master.custom = "cuteness"
        # FIXME: (jany) A value of 0.0 is not written to the file.
        master.customValue = 0.001
        # FIXME: (jany) Why are there 3 more customValues?
        master.custom1 = "color"
        master.customValue1 = 0.1
        master.custom2 = "depth"
        master.customValue2 = 0.2
        master.custom3 = "surealism"
        master.customValue3 = 0.3
        # ascender
        master.ascender = 234.5
        # capHeight
        master.capHeight = 200.6
        # xHeight
        master.xHeight = 59.1
        # descender
        master.descender = -89.2
        # italicAngle
        master.italicAngle = 12.2
        # verticalStems
        master.verticalStems = [1, 2, 3]
        # horizontalStems
        master.horizontalStems = [4, 5, 6]
        # alignmentZones
        zone = classes.GSAlignmentZone(0, -30)
        master.alignmentZones = [
            zone
        ]
        # blueValues: not handled because it is read-only
        # otherBlues: not handled because it is read-only
        # guides
        # FIXME: (jany) Here it is called "guideLines" instead of "guides"
        guide = classes.GSGuideLine()
        guide.name = "middle"
        master.guideLines.append(guide)
        # userData
        master.userData['rememberToMakeTea'] = True
        # customParameters
        master.customParameters['underlinePosition'] = -135
        self.assertWrites(master, dedent("""\
            {
            alignmentZones = (
            "{0, -30}"
            );
            ascender = 234.5;
            capHeight = 200.6;
            custom = cuteness;
            customValue = 0.001;
            custom1 = color;
            customValue1 = 0.1;
            custom2 = depth;
            customValue2 = 0.2;
            custom3 = surealism;
            customValue3 = 0.3;
            customParameters = (
            {
            name = "Master Name";
            value = "Hairline Megawide";
            },
            {
            name = underlinePosition;
            value = -135;
            }
            );
            descender = -89.2;
            guideLines = (
            {
            name = middle;
            }
            );
            horizontalStems = (
            4,
            5,
            6
            );
            id = "MASTER-ID";
            italicAngle = 12.2;
            userData = {
            rememberToMakeTea = 1;
            };
            verticalStems = (
            1,
            2,
            3
            );
            weight = Thin;
            weightValue = 0.01;
            width = Wide;
            widthValue = 0.99;
            xHeight = 59.1;
            }
        """))

    def test_write_alignment_zone(self):
        zone = classes.GSAlignmentZone(23, 40)
        self.assertWritesValue(zone, '"{23, 40}"')

    def test_write_instance(self):
        instance = classes.GSInstance()
        # List of properties from https://docu.glyphsapp.com/#gsinstance
        # active
        # FIXME: (jany) does not seem to be handled by this library? No doc?
        instance.active = True
        # name
        instance.name = "SemiBoldCompressed (name)"
        # weight
        instance.weight = "SemiBold (weight)"
        # width
        instance.width = "Compressed (width)"
        # weightValue
        instance.weightValue = 0.6
        # widthValue
        instance.widthValue = 0.2
        # customValue
        instance.customValue = 0.4
        # isItalic
        instance.isItalic = True
        # isBold
        instance.isBold = True
        # linkStyle
        instance.linkStyle = "linked style value"
        # familyName
        instance.familyName = "Sans Rien (familyName)"
        # preferredFamily
        instance.preferredFamily = "Sans Rien (preferredFamily)"
        # preferredSubfamilyName
        instance.preferredSubfamilyName = "Semi Bold Compressed (preferredSubFamilyName)"
        # windowsFamily
        instance.windowsFamily = "Sans Rien MS (windowsFamily)"
        # windowsStyle: read only
        # windowsLinkedToStyle: read only
        # fontName
        instance.fontName = "SansRien (fontName)"
        # fullName
        instance.fullName = "Sans Rien Semi Bold Compressed (fullName)"
        # customParameters
        instance.customParameters['hheaLineGap'] = 10
        # instanceInterpolations
        instance.instanceInterpolations = {
            'M1': 0.2,
            'M2': 0.8
        }
        # manualInterpolation
        instance.manualInterpolation = True
        # interpolatedFont: read only

        # FIXME: (jany) the weight and width are not in the output
        #   cofusion with weightClass/widthClass?
        self.assertWrites(instance, dedent("""\
            {
            customParameters = (
            {
            name = famiyName;
            value = "Sans Rien (familyName)";
            },
            {
            name = preferredFamily;
            value = "Sans Rien (preferredFamily)";
            },
            {
            name = preferredSubfamilyName;
            value = "Semi Bold Compressed (preferredSubFamilyName)";
            },
            {
            name = styleMapFamilyName;
            value = "Sans Rien MS (windowsFamily)";
            },
            {
            name = postscriptFontName;
            value = "SansRien (fontName)";
            },
            {
            name = postscriptFullName;
            value = "Sans Rien Semi Bold Compressed (fullName)";
            },
            {
            name = hheaLineGap;
            value = 10;
            }
            );
            interpolationCustom = 0.4;
            interpolationWeight = 0.6;
            interpolationWidth = 0.2;
            instanceInterpolations = {
            M1 = 0.2;
            M2 = 0.8;
            };
            isBold = 1;
            isItalic = 1;
            linkStyle = "linked style value";
            manualInterpolation = 1;
            name = "SemiBoldCompressed (name)";
            }
        """))

# Might be impractical because of formatting (whitespace changes)?
# Maybe it's OK because random glyphs files from github seem to be
# formatted exactly like what this writer outputs
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
