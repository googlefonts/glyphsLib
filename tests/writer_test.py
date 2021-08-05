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
from io import StringIO
from textwrap import dedent
from collections import OrderedDict
import os

from glyphsLib import classes
from glyphsLib.types import parse_datetime, Point, Rect
from glyphsLib.writer import dump, dumps

from . import test_helpers


class WriterTest(unittest.TestCase, test_helpers.AssertLinesEqual):
    def assertWrites(self, glyphs_object, text, format_version=2):
        """Assert that the given object, when given to the writer,
        produces the given text.
        """
        expected = text.splitlines()
        actual = test_helpers.write_to_lines(glyphs_object, format_version)
        self.assertLinesEqual(
            expected, actual, "The writer has not produced the expected output"
        )

    def assertWritesValue(self, glyphs_value, text, format_version=2):
        """Assert that the writer produces the given text for the given value."""
        expected = (
            dedent(
                """\
        {{
        writtenValue = {0};
        }}
        """
            )
            .format(text)
            .splitlines()
        )
        # We wrap the value in a dict to use the same test helper
        actual = test_helpers.write_to_lines(
            {"writtenValue": glyphs_value}, format_version
        )
        self.assertLinesEqual(
            expected, actual, "The writer has not produced the expected output"
        )

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
        g1.name = "G1"
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
        fp1.name = "FP1"
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
        font.date = parse_datetime("2017-10-03 07:35:46 +0000")
        # familyName
        font.familyName = "Sans Rien"
        # upm
        font.upm = 2000
        # note
        font.note = "Was bored, made this"
        # kerning
        font.kerning = OrderedDict(
            [("M1", OrderedDict([("@MMK_L_G1", OrderedDict([("@MMK_R_G1", 0.1)]))]))]
        )
        # userData
        font.userData = {
            "a": "test",
            "b": [1, {"c": 2}],
            "d": [1, "1"],
            "noodleThickness": "106.0",
        }
        # grid -> gridLength
        font.grid = 35
        # gridSubDivisions
        font.gridSubDivisions = 5
        # keyboardIncrement
        font.keyboardIncrement = 1.2
        # disablesNiceNames
        font.disablesNiceNames = True
        # customParameters
        font.customParameters["ascender"] = 300
        # selection: not written
        # selectedLayers: not written
        # selectedFontMaster: not written
        # masterIndex: not written
        # currentText: not written
        # tabs: not written
        # currentTab: not written
        # filepath: not written
        # tool: not written
        # tools: not handled because it is a read-only list of GUI features
        # .appVersion (extra property that is not in the docs!)
        font.appVersion = "895"
        self.assertWrites(
            font,
            dedent(
                """\
            {
            .appVersion = "895";
            classes = (
            {
            code = "";
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
            {
            code = "";
            name = FP1;
            }
            );
            features = (
            {
            code = "";
            name = F1;
            }
            );
            fontMaster = (
            {
            ascender = 800;
            capHeight = 700;
            descender = -200;
            id = M1;
            xHeight = 500;
            },
            {
            ascender = 800;
            capHeight = 700;
            descender = -200;
            id = M2;
            xHeight = 500;
            }
            );
            glyphs = (
            {
            glyphname = G1;
            }
            );
            gridLength = 35;
            gridSubDivision = 5;
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
            keyboardIncrement = 1.2;
            manufacturer = Manu;
            manufacturerURL = manu.com;
            unitsPerEm = 2000;
            userData = {
            a = test;
            b = (
            1,
            {
            c = 2;
            }
            );
            d = (
            1,
            "1"
            );
            noodleThickness = "106.0";
            };
            versionMajor = 2;
            versionMinor = 104;
            }
        """
            ),
        )

        # Don't write the keyboardIncrement if it's 1 (default)
        font.keyboardIncrement = 1
        written = test_helpers.write_to_lines(font)
        self.assertFalse(any("keyboardIncrement" in line for line in written))

        # Always write versionMajor and versionMinor, even when 0
        font.versionMajor = 0
        font.versionMinor = 0
        written = test_helpers.write_to_lines(font)
        self.assertIn("versionMajor = 0;", written)
        self.assertIn("versionMinor = 0;", written)

    def test_write_font_master_attributes(self):
        """Test the writer on all GSFontMaster attributes"""
        master = classes.GSFontMaster()
        # List of properties from https://docu.glyphsapp.com/#gsfontmaster
        # id
        master.id = "MASTER-ID"
        # name
        master._name = "Name Hairline Megawide"
        master.customParameters["Master Name"] = "Param Hairline Megawide"
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
        master.customName = "Overextended"
        # A value of 0.0 is not written to the file.
        master.customValue = 0.001
        master.customValue1 = 0.1
        master.customValue2 = 0.2
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
        master.alignmentZones = [zone]
        # blueValues: not handled because it is read-only
        # otherBlues: not handled because it is read-only
        # guides
        guide = classes.GSGuide()
        guide.name = "middle"
        master.guides.append(guide)
        # userData
        master.userData["rememberToMakeTea"] = True
        # customParameters
        master.customParameters["underlinePosition"] = -135
        self.assertWrites(
            master,
            dedent(
                """\
            {
            alignmentZones = (
            "{0, -30}"
            );
            ascender = 234.5;
            capHeight = 200.6;
            custom = Overextended;
            customValue = 0.001;
            customValue1 = 0.1;
            customValue2 = 0.2;
            customValue3 = 0.3;
            customParameters = (
            {
            name = "Master Name";
            value = "Param Hairline Megawide";
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
            name = "Name Hairline Megawide";
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
        """
            ),
        )

        # Write the capHeight and xHeight even if they are "0"
        master.xHeight = 0
        master.capHeight = 0
        written = test_helpers.write_to_lines(master)
        self.assertIn("xHeight = 0;", written)
        self.assertIn("capHeight = 0;", written)

    def test_write_alignment_zone(self):
        zone = classes.GSAlignmentZone(23, 40)
        self.assertWritesValue(zone, '"{23, 40}"')

    def test_write_instance(self):
        instance = classes.GSInstance()
        # List of properties from https://docu.glyphsapp.com/#gsinstance
        # active
        instance.active = True
        # name
        instance.name = "SemiBoldCompressed (name)"
        # weight
        instance.weight = "SemiBold (weight)"
        # width
        instance.width = "Compressed (width)"
        # weightValue
        instance.weightValue = 600
        # widthValue
        instance.widthValue = 200
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
        instance.preferredSubfamilyName = (
            "Semi Bold Compressed (preferredSubFamilyName)"
        )
        # windowsFamily
        instance.windowsFamily = "Sans Rien MS (windowsFamily)"
        # windowsStyle: read only
        # windowsLinkedToStyle: read only
        # fontName
        instance.fontName = "SansRien (fontName)"
        # fullName
        instance.fullName = "Sans Rien Semi Bold Compressed (fullName)"
        # customParameters
        instance.customParameters["hheaLineGap"] = 10
        # instanceInterpolations
        instance.instanceInterpolations = {"M1": 0.2, "M2": 0.8}
        # manualInterpolation
        instance.manualInterpolation = True
        # interpolatedFont: read only

        self.assertWrites(
            instance,
            dedent(
                """\
            {
            customParameters = (
            {
            name = familyName;
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
            interpolationWeight = 600;
            interpolationWidth = 200;
            instanceInterpolations = {
            M1 = 0.2;
            M2 = 0.8;
            };
            isBold = 1;
            isItalic = 1;
            linkStyle = "linked style value";
            manualInterpolation = 1;
            name = "SemiBoldCompressed (name)";
            weightClass = "SemiBold (weight)";
            widthClass = "Compressed (width)";
            }
        """
            ),
        )

    def test_write_custom_parameter(self):
        # Name without quotes
        self.assertWritesValue(
            classes.GSCustomParameter("myParam", "myValue"),
            "{\nname = myParam;\nvalue = myValue;\n}",
        )
        # Name with quotes
        self.assertWritesValue(
            classes.GSCustomParameter("my param", "myValue"),
            '{\nname = "my param";\nvalue = myValue;\n}',
        )
        # Value with quotes
        self.assertWritesValue(
            classes.GSCustomParameter("myParam", "my value"),
            '{\nname = myParam;\nvalue = "my value";\n}',
        )
        # Int param (ascender): should convert the value to string
        self.assertWritesValue(
            classes.GSCustomParameter("ascender", 12),
            "{\nname = ascender;\nvalue = 12;\n}",
        )
        # Float param (postscriptBlueScale): should convert the value to string
        self.assertWritesValue(
            classes.GSCustomParameter("postscriptBlueScale", 0.125),
            "{\nname = postscriptBlueScale;\nvalue = 0.125;\n}",
        )
        # Bool param (isFixedPitch): should convert the boolean value to 0/1
        self.assertWritesValue(
            classes.GSCustomParameter("isFixedPitch", True),
            "{\nname = isFixedPitch;\nvalue = 1;\n}",
        )
        # Intlist param: should map list of int to list of strings
        self.assertWritesValue(
            classes.GSCustomParameter("fsType", [1, 2]),
            "{\nname = fsType;\nvalue = (\n1,\n2\n);\n}",
        )

    def test_write_class(self):
        class_ = classes.GSClass()
        class_.name = "e"
        class_.code = "e eacute egrave"
        class_.automatic = True
        self.assertWrites(
            class_,
            dedent(
                """\
            {
            automatic = 1;
            code = "e eacute egrave";
            name = e;
            }
        """
            ),
        )

        # When the code is an empty string, write an empty string
        class_.code = ""
        self.assertWrites(
            class_,
            dedent(
                """\
            {
            automatic = 1;
            code = "";
            name = e;
            }
        """
            ),
        )

    def test_write_feature_prefix(self):
        fp = classes.GSFeaturePrefix()
        fp.name = "Languagesystems"
        fp.code = "languagesystem DFLT dflt;"
        fp.automatic = True
        self.assertWrites(
            fp,
            dedent(
                """\
            {
            automatic = 1;
            code = "languagesystem DFLT dflt;";
            name = Languagesystems;
            }
        """
            ),
        )

    def test_write_feature(self):
        feature = classes.GSFeature()
        feature.name = "sups"
        feature.code = "    sub @standard by @sups;"
        feature.automatic = True
        feature.notes = "notes about sups"
        self.assertWrites(
            feature,
            dedent(
                """\
            {
            automatic = 1;
            code = "    sub @standard by @sups;";
            name = sups;
            notes = "notes about sups";
            }
        """
            ),
        )

    def test_write_glyph(self):
        glyph = classes.GSGlyph()
        # https://docu.glyphsapp.com/#gsglyph
        # parent: not written
        # layers
        # Put the glyph in a font with at least one master for the magic in
        # `glyph.layers.append()` to work.
        font = classes.GSFont()
        master = classes.GSFontMaster()
        master.id = "MASTER-ID"
        font.masters.insert(0, master)
        font.glyphs.append(glyph)
        layer = classes.GSLayer()
        layer.layerId = "LAYER-ID"
        layer.name = "L1"
        glyph.layers.insert(0, layer)
        # name
        glyph.name = "Aacute"
        # unicode
        glyph.unicode = "00C1"
        # string: not written
        # id: not written
        # category
        glyph.category = "Letter"
        # subCategory
        glyph.subCategory = "Uppercase"
        # script
        glyph.script = "latin"
        # productionName
        glyph.productionName = "Aacute.prod"
        # glyphInfo: not written
        # leftKerningGroup
        glyph.leftKerningGroup = "A"
        # rightKerningGroup
        glyph.rightKerningGroup = "A"
        # leftKerningKey: not written
        # rightKerningKey: not written
        # leftMetricsKey
        glyph.leftMetricsKey = "A"
        # rightMetricsKey
        glyph.rightMetricsKey = "A"
        # widthMetricsKey
        glyph.widthMetricsKey = "A"
        # export
        glyph.export = False
        # color
        glyph.color = 11
        # colorObject: not written
        # note
        glyph.note = "Stunning one-bedroom A with renovated acute accent"
        # selected: not written
        # mastersCompatible: not stored
        # userData
        glyph.userData["rememberToMakeCoffe"] = True
        # Check that empty collections are written
        glyph.userData["com.someoneelse.coolsoftware.customdata"] = [
            OrderedDict(
                [("zero", 0), ("emptyList", []), ("emptyDict", {}), ("emptyString", "")]
            ),
            [],
            {},
            "",
            "hey",
            0,
            1,
        ]
        # smartComponentAxes
        axis = classes.GSSmartComponentAxis()
        axis.name = "crotchDepth"
        glyph.smartComponentAxes.append(axis)
        # lastChange
        glyph.lastChange = parse_datetime("2017-10-03 07:35:46 +0000")
        self.assertWrites(
            glyph,
            dedent(
                """\
            {
            color = 11;
            export = 0;
            glyphname = Aacute;
            lastChange = "2017-10-03 07:35:46 +0000";
            layers = (
            {
            associatedMasterId = "MASTER-ID";
            layerId = "LAYER-ID";
            name = L1;
            width = 600;
            }
            );
            leftKerningGroup = A;
            leftMetricsKey = A;
            widthMetricsKey = A;
            note = "Stunning one-bedroom A with renovated acute accent";
            rightKerningGroup = A;
            rightMetricsKey = A;
            unicode = 00C1;
            script = latin;
            category = Letter;
            subCategory = Uppercase;
            userData = {
            com.someoneelse.coolsoftware.customdata = (
            {
            zero = 0;
            emptyList = (
            );
            emptyDict = {
            };
            emptyString = "";
            },
            (
            ),
            {
            },
            "",
            hey,
            0,
            1
            );
            rememberToMakeCoffe = 1;
            };
            partsSettings = (
            {
            name = crotchDepth;
            bottomValue = 0;
            topValue = 0;
            }
            );
            }
        """
            ),
        )

        # Write the script even when it's an empty string
        # Same for category and subCategory
        glyph.script = ""
        glyph.category = ""
        glyph.subCategory = ""
        written = test_helpers.write_to_lines(glyph)
        self.assertIn('script = "";', written)
        self.assertIn('category = "";', written)
        self.assertIn('subCategory = "";', written)

        # Write double unicodes
        glyph.unicodes = ["00C1", "E002"]
        written = test_helpers.write_to_lines(glyph)
        self.assertIn('unicode = "00C1,E002";', written)

    def test_write_layer(self):
        layer = classes.GSLayer()
        # http://docu.glyphsapp.com/#gslayer
        # parent: not written
        # name
        layer.name = "{125, 100}"
        # associatedMasterId
        layer.associatedMasterId = "M1"
        # layerId
        layer.layerId = "L1"
        # color
        layer.color = (1, 2, 3, 4)
        # colorObject: read-only, computed
        # components
        component = classes.GSComponent(glyph="glyphName")
        layer.components.append(component)
        # guides
        guide = classes.GSGuide()
        guide.name = "xheight"
        layer.guides.append(guide)
        # annotations
        annotation = classes.GSAnnotation()
        annotation.type = classes.TEXT
        annotation.text = "Fuck, this curve is ugly!"
        layer.annotations.append(annotation)
        # hints
        hint = classes.GSHint()
        hint.name = "hintName"
        layer.hints.append(hint)
        # anchors
        anchor = classes.GSAnchor()
        anchor.name = "top"
        layer.anchors["top"] = anchor
        # paths
        path = classes.GSPath()
        layer.paths.append(path)
        # selection: read-only
        # LSB, RSB, TSB, BSB: not written
        # width
        layer.width = 890.4
        # leftMetricsKey
        layer.leftMetricsKey = "A"
        # rightMetricsKey
        layer.rightMetricsKey = "A"
        # widthMetricsKey
        layer.widthMetricsKey = "A"
        # bounds: read-only, computed
        # selectionBounds: read-only, computed
        # background
        # XXX bg is unused?
        bg = layer.background  # noqa: F841
        # backgroundImage
        image = classes.GSBackgroundImage("/path/to/file.jpg")
        layer.backgroundImage = image
        # bezierPath: read-only, objective-c
        # openBezierPath: read-only, objective-c
        # completeOpenBezierPath: read-only, objective-c
        # isAligned
        # FIXME: (jany) is this read-only?
        #   is this computed from each component's alignment?
        # layer.isAligned = False
        # userData
        layer.userData["rememberToMakeCoffe"] = True
        # smartComponentPoleMapping
        layer.smartComponentPoleMapping["crotchDepth"] = 2  # Top pole
        layer.smartComponentPoleMapping["shoulderWidth"] = 1  # Bottom pole
        self.assertWrites(
            layer,
            dedent(
                """\
            {
            anchors = (
            {
            name = top;
            position = "{0, 0}";
            }
            );
            annotations = (
            {
            text = "Fuck, this curve is ugly!";
            type = 1;
            }
            );
            associatedMasterId = M1;
            background = {
            };
            backgroundImage = {
            crop = "{{0, 0}, {0, 0}}";
            imagePath = "/path/to/file.jpg";
            };
            color = (1, 2, 3, 4);
            components = (
            {
            name = glyphName;
            }
            );
            guideLines = (
            {
            name = xheight;
            }
            );
            hints = (
            {
            name = hintName;
            }
            );
            layerId = L1;
            leftMetricsKey = A;
            widthMetricsKey = A;
            rightMetricsKey = A;
            name = "{125, 100}";
            paths = (
            {
            closed = 1;
            }
            );
            userData = {
            PartSelection = {
            crotchDepth = 2;
            shoulderWidth = 1;
            };
            rememberToMakeCoffe = 1;
            };
            width = 890.4;
            }
        """
            ),
        )

        # Don't write a blank layer name
        layer.name = ""
        written = test_helpers.write_to_lines(layer)
        self.assertNotIn('name = "";', written)

        # Write the width even if 0
        layer.width = 0
        written = test_helpers.write_to_lines(layer)
        self.assertIn("width = 0;", written)

    def test_write_anchor(self):
        anchor = classes.GSAnchor("top", Point(23, 45.5))
        self.assertWrites(
            anchor,
            dedent(
                """\
            {
            name = top;
            position = "{23, 45.5}";
            }
        """
            ),
        )

        # Write a position of 0, 0
        anchor = classes.GSAnchor("top", Point(0, 0))
        self.assertWrites(
            anchor,
            dedent(
                """\
            {
            name = top;
            position = "{0, 0}";
            }
        """
            ),
        )

    def test_write_component(self):
        component = classes.GSComponent("dieresis")
        # http://docu.glyphsapp.com/#gscomponent
        # position
        component.position = Point(45.5, 250)
        # scale
        component.scale = 2.0
        # rotation
        component.rotation = 90
        # componentName: already set at init
        # component: read-only
        # layer: read-only
        # transform: already set using scale & position
        # bounds: read-only, objective-c
        # automaticAlignment
        component.automaticAlignment = True
        # anchor
        component.anchor = "top"
        # selected: not written
        # smartComponentValues
        component.smartComponentValues = {"crotchDepth": -77}
        # bezierPath: read-only, objective-c
        self.assertWrites(
            component,
            dedent(
                """\
            {
            anchor = top;
            name = dieresis;
            piece = {
            crotchDepth = -77;
            };
            transform = "{0, 2, -2, 0, 45.5, 250}";
            }
        """
            ),
        )

    def test_write_smart_component_axis(self):
        axis = classes.GSSmartComponentAxis()
        # http://docu.glyphsapp.com/#gssmartcomponentaxis
        axis.name = "crotchDepth"
        axis.topName = "High"
        axis.topValue = 0
        axis.bottomName = "Low"
        axis.bottomValue = -100
        self.assertWrites(
            axis,
            dedent(
                """\
            {
            name = crotchDepth;
            bottomName = Low;
            bottomValue = -100;
            topName = High;
            topValue = 0;
            }
        """
            ),
        )

    def test_write_path(self):
        path = classes.GSPath()
        # http://docu.glyphsapp.com/#gspath
        # parent: not written
        # nodes
        node = classes.GSNode()
        path.nodes.append(node)
        # segments: computed, objective-c
        # closed
        path.closed = True
        # direction: computed
        # bounds: computed
        # selected: not written
        # bezierPath: computed
        self.assertWrites(
            path,
            dedent(
                """\
            {
            closed = 1;
            nodes = (
            "0 0 LINE"
            );
            }
        """
            ),
        )

    def test_write_node(self):
        node = classes.GSNode(Point(10, 30), classes.CURVE)
        # http://docu.glyphsapp.com/#gsnode
        # position: already set
        # #type: already set
        # smooth
        node.smooth = True
        # connection: deprecated
        # selected: not written
        # index, nextNode, prevNode: computed
        # name
        node.name = "top-left corner"
        # userData
        node.userData["rememberToDownloadARealRemindersApp"] = True
        self.assertWritesValue(
            node,
            '"10 30 CURVE SMOOTH {name = \\"top-left corner\\";\\n\
rememberToDownloadARealRemindersApp = 1;}"',
        )

        # Write floating point coordinates
        node = classes.GSNode(Point(499.99, 512.01), classes.OFFCURVE)
        self.assertWritesValue(node, '"499.99 512.01 OFFCURVE"')

        # Write userData with special characters
        test_user_data = {
            "\nkey\"';\n\n\n": "\"'value\nseveral lines\n;\n",
            ";": ";\n",
            "escapeception": "\\\"\\'\\n\\\\n",
        }
        node = classes.GSNode(Point(130, 431), classes.LINE)
        for key, value in test_user_data.items():
            node.userData[key] = value
        # This is the output of Glyphs 1089
        expected_output = (
            '"130 431 LINE {\\"\\012key\\\\"\';\\012\\012\\012\\" '
            '= \\"\\\\"\'value\\012several lines\\012;\\012\\"'
            ';\\n\\";\\" = \\";\\012\\";\\n'
            'escapeception = \\"\\\\\\\\"\\\\\'\\\\\\n\\\\\\\\\\n\\";}"'
        )
        self.assertWritesValue(node, expected_output)
        # Check that we can read the userData back
        node = classes.GSNode().read(expected_output[1:-1])
        self.assertEqual(test_user_data, dict(node.userData))

    def test_write_guideline(self):
        line = classes.GSGuide()
        # http://docu.glyphsapp.com/#GSGuideLine
        line.position = Point(56, 45)
        line.angle = 11.0
        line.name = "italic angle"
        # selected: not written
        self.assertWrites(
            line,
            dedent(
                """\
            {
            angle = 11;
            name = "italic angle";
            position = "{56, 45}";
            }
        """
            ),
        )

    def test_write_annotation(self):
        annotation = classes.GSAnnotation()
        # http://docu.glyphsapp.com/#gsannotation
        annotation.position = Point(12, 34)
        annotation.type = classes.TEXT
        annotation.text = "Look here"
        annotation.angle = 123.5
        annotation.width = 135
        self.assertWrites(
            annotation,
            dedent(
                """\
            {
            angle = 123.5;
            position = "{12, 34}";
            text = "Look here";
            type = 1;
            width = 135;
            }
        """
            ),
        )

    def test_write_hint(self):
        hint = classes.GSHint()
        # http://docu.glyphsapp.com/#gshint
        layer = classes.GSLayer()
        path1 = classes.GSPath()
        layer.paths.append(path1)
        node1 = classes.GSNode(Point(100, 100))
        path1.nodes.append(node1)
        hint.originNode = node1

        node2 = classes.GSNode(Point(200, 200))
        path1.nodes.append(node2)
        hint.targetNode = node2

        node3 = classes.GSNode(Point(300, 300))
        path1.nodes.append(node3)
        hint.otherNode1 = node3

        path2 = classes.GSPath()
        layer.paths.append(path2)
        node4 = classes.GSNode(Point(400, 400))
        path2.nodes.append(node4)
        hint.otherNode2 = node4

        hint.type = classes.CORNER
        hint.options = classes.TTROUND | classes.TRIPLE
        hint.horizontal = True
        # selected: not written
        hint.name = "My favourite hint"
        self.assertWrites(
            hint,
            dedent(
                """\
            {
            horizontal = 1;
            origin = "{0, 0}";
            target = "{0, 1}";
            other1 = "{0, 2}";
            other2 = "{1, 0}";
            type = 16;
            name = "My favourite hint";
            options = 128;
            }
        """
            ),
        )

        # FIXME: (jany) What about the undocumented scale & stem?
        #   -> Add a test for that

        # Test with target = "up"
        # FIXME: (jany) what does target = "up" mean?
        #   Is there an official python API to write that?
        # hint.targetNode = 'up'
        # written = test_helpers.write_to_lines(hint)
        # self.assertIn('target = up;', written)

    def test_write_hint_v3(self):
        hint = classes.GSHint()
        # http://docu.glyphsapp.com/#gshint
        layer = classes.GSLayer()
        path1 = classes.GSPath()
        layer.paths.append(path1)
        node1 = classes.GSNode(Point(100, 100))
        path1.nodes.append(node1)
        hint.originNode = node1

        node2 = classes.GSNode(Point(200, 200))
        path1.nodes.append(node2)
        hint.targetNode = node2

        node3 = classes.GSNode(Point(300, 300))
        path1.nodes.append(node3)
        hint.otherNode1 = node3

        path2 = classes.GSPath()
        layer.paths.append(path2)
        node4 = classes.GSNode(Point(400, 400))
        path2.nodes.append(node4)
        hint.otherNode2 = node4

        hint.type = classes.CORNER
        hint.options = classes.TTROUND | classes.TRIPLE
        hint.horizontal = True
        # selected: not written
        hint.name = "My favourite hint"
        self.assertWrites(
            hint,
            dedent(
                """\
             {
             horizontal = 1;
             origin = (0,0);
             target = (0,1);
             other1 = (0,2);
             other2 = (1,0);
             type = 16;
             name = "My favourite hint";
             options = 128;
             }
         """,
            ),
            format_version=3,
        )

        # FIXME: (jany) What about the undocumented scale & stem?
        #   -> Add a test for that

        # Test with target = "up"
        # FIXME: (jany) what does target = "up" mean?
        #   Is there an official python API to write that?
        # hint.targetNode = 'up'
        # written = test_helpers.write_to_lines(hint)
        # self.assertIn('target = up;', written)

    def test_write_background_image(self):
        image = classes.GSBackgroundImage("/tmp/img.jpg")
        # http://docu.glyphsapp.com/#gsbackgroundimage
        # path: already set
        # image: read-only, objective-c
        image.crop = Rect(Point(0, 10), Point(500, 510))
        image.locked = True
        image.alpha = 70
        image.position = Point(40, 90)
        image.scale = (1.1, 1.2)
        image.rotation = 0.3
        # transform: Already set with scale/rotation
        self.assertWrites(
            image,
            dedent(
                """\
            {
            alpha = 70;
            crop = "{{0, 10}, {500, 510}}";
            imagePath = "/tmp/img.jpg";
            locked = 1;
            transform = "{1.09998, 0.00576, -0.00628, 1.19998, 40, 90}";
            }
        """
            ),
        )


class WriterDumpInterfaceTest(unittest.TestCase):
    def test_dump(self):
        obj = classes.GSFont()
        fp = StringIO()

        dump(obj, fp)

        self.assertTrue(fp.getvalue())

    def test_dumps(self):
        obj = classes.GSFont()

        string = dumps(obj)

        self.assertTrue(string)


class WriterRoundtripTest(unittest.TestCase, test_helpers.AssertParseWriteRoundtrip):
    def test_roundtrip_on_file(self):
        filename = os.path.join(
            os.path.dirname(__file__), "data/GlyphsUnitTestSans.glyphs"
        )
        self.assertParseWriteRoundtrip(filename)


if __name__ == "__main__":
    unittest.main()
