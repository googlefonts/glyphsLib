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
import datetime
import copy
import unittest
import pytest

from glyphsLib.classes import (
    GSFont,
    GSFontMaster,
    GSInstance,
    GSCustomParameter,
    GSGlyph,
    GSLayer,
    GSAnchor,
    GSComponent,
    GSAlignmentZone,
    GSClass,
    GSFeature,
    GSAnnotation,
    GSFeaturePrefix,
    GSGuideLine,
    GSHint,
    GSNode,
    GSPath,
    GSSmartComponentAxis,
    GSBackgroundImage,
    segment,
    LayerComponentsProxy,
    LayerGuideLinesProxy,
    STEM,
    TEXT,
    ARROW,
    CIRCLE,
    PLUS,
    MINUS,
    LINE,
    CURVE,
    OFFCURVE,
)
from glyphsLib.types import Point, Transform, Rect


TESTFILE_PATH = os.path.join(
    os.path.dirname(__file__), os.path.join("data", "GlyphsUnitTestSans.glyphs")
)


def generate_minimal_font():
    font = GSFont()
    font.appVersion = 895
    font.date = datetime.datetime.today()
    font.familyName = "MyFont"

    master = GSFontMaster()
    master.ascender = 0
    master.capHeight = 0
    master.descender = 0
    master.id = "id"
    master.xHeight = 0
    font.masters.append(master)

    font.upm = 1000
    font.versionMajor = 1
    font.versionMinor = 0

    return font


def generate_instance_from_dict(instance_dict):
    instance = GSInstance()
    instance.name = instance_dict["name"]
    for custom_parameter in instance_dict.get("customParameters", []):
        cp = GSCustomParameter()
        cp.name = custom_parameter["name"]
        cp.value = custom_parameter["value"]
        instance.customParameters.append(cp)
    return instance


def add_glyph(font, glyphname):
    glyph = GSGlyph()
    glyph.name = glyphname
    font.glyphs.append(glyph)
    layer = GSLayer()
    layer.layerId = font.masters[0].id
    layer.associatedMasterId = font.masters[0].id
    layer.width = 0
    glyph.layers.append(layer)
    return glyph


def add_anchor(font, glyphname, anchorname, x, y):
    for glyph in font.glyphs:
        if glyph.name == glyphname:
            for master in font.masters:
                layer = glyph.layers[master.id]
                layer.anchors = getattr(layer, "anchors", [])
                anchor = GSAnchor()
                anchor.name = anchorname
                anchor.position = (x, y)
                layer.anchors.append(anchor)


def add_component(font, glyphname, componentname, transform):
    for glyph in font.glyphs:
        if glyph.name == glyphname:
            for layer in glyph.layers.values():
                component = GSComponent()
                component.name = componentname
                component.transform = transform
                layer.components.append(component)


class GlyphLayersTest(unittest.TestCase):
    def test_check_master_layer(self):
        font = generate_minimal_font()
        glyph = add_glyph(font, "A")
        self.assertIsNotNone(glyph)
        master = font.masters[0]
        self.assertIsNotNone(master)
        layer = glyph.layers[master.id]
        self.assertIsNotNone(layer)

        layer = glyph.layers["XYZ123"]
        self.assertIsNone(layer)

    def test_append_layer_same_id(self):
        font = generate_minimal_font()
        font.masters[0].id = "abc"
        master2 = GSFontMaster()
        master2.ascender = 0
        master2.capHeight = 0
        master2.descender = 0
        master2.xHeight = 0
        master2.id = "abc"
        font.masters.append(master2)
        assert len({m.id for m in font.masters}) == 2


class GSFontTest(unittest.TestCase):
    def test_init(self):
        font = GSFont()
        self.assertEqual(font.familyName, "Unnamed font")
        self.assertEqual(font.versionMajor, 1)
        self.assertEqual(font.versionMinor, 0)
        self.assertEqual(font.appVersion, "895")

        self.assertEqual(len(font.glyphs), 0)
        self.assertEqual(len(font.masters), 0)
        self.assertEqual(list(font.masters), list(()))
        self.assertEqual(len(font.instances), 0)
        self.assertEqual(font.instances, [])
        self.assertEqual(len(font.customParameters), 0)

    def test_repr(self):
        font = GSFont()
        self.assertEqual(repr(font), '<GSFont "Unnamed font">')

    def test_update_custom_parameter(self):
        font = GSFont()
        font.customParameters["Filter"] = "RemoveOverlap"
        self.assertEqual(font.customParameters["Filter"], "RemoveOverlap")
        font.customParameters["Filter"] = "AddExtremes"
        self.assertEqual(font.customParameters["Filter"], "AddExtremes")

    def test_font_master_proxy(self):
        font = GSFont()
        master = GSFontMaster()
        font.masters.append(master)
        self.assertEqual(master.font, font)


class GSObjectsTestCase(unittest.TestCase):
    def setUp(self):
        self.font = GSFont(TESTFILE_PATH)

    def assertString(self, value):
        self.assertIsInstance(value, str)
        old_value = value
        value = "eee"
        self.assertEqual(value, "eee")
        value = old_value
        self.assertEqual(value, old_value)

    def assertUnicode(self, value):
        self.assertIsInstance(value, str)
        old_value = value
        value = "ə"
        self.assertEqual(value, "ə")
        value = old_value
        self.assertEqual(value, old_value)

    def assertInteger(self, value):
        self.assertIsInstance(value, int)
        old_value = value
        value = 5
        self.assertEqual(value, 5)
        value = old_value
        self.assertEqual(value, old_value)

    def assertFloat(self, value):
        self.assertIsInstance(value, float)
        old_value = value
        value = 0.5
        self.assertEqual(value, 0.5)
        value = old_value
        self.assertEqual(value, old_value)

    def assertBool(self, value):
        self.assertIsInstance(value, bool)
        old_value = value
        value = not value
        self.assertEqual(value, not old_value)
        value = old_value
        self.assertEqual(value, old_value)

    def assertDict(self, dictObject):
        self.assertIsInstance(dictObject, dict)
        var1 = "abc"
        var2 = "def"
        dictObject["uniTestValue"] = var1
        self.assertEqual(dictObject["uniTestValue"], var1)
        dictObject["uniTestValue"] = var2
        self.assertEqual(dictObject["uniTestValue"], var2)


class GSFontFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()

    def test_pathlike_path(self):
        from pathlib import Path

        font = GSFont(TESTFILE_PATH)
        self.assertEqual(font.filepath, TESTFILE_PATH)

        font = GSFont(Path(TESTFILE_PATH))
        self.assertEqual(font.filepath, TESTFILE_PATH)

    def test_masters(self):
        font = self.font
        amount = len(font.masters)
        self.assertEqual(len(list(font.masters)), 3)

        new_master = GSFontMaster()
        font.masters.append(new_master)
        self.assertEqual(new_master, font.masters[-1])
        del font.masters[-1]

        new_master1 = GSFontMaster()
        new_master2 = GSFontMaster()
        font.masters.extend([new_master1, new_master2])
        self.assertEqual(new_master1, font.masters[-2])
        self.assertEqual(new_master2, font.masters[-1])

        font.masters.remove(font.masters[-1])
        font.masters.remove(font.masters[-1])

        new_master = GSFontMaster()
        font.masters.insert(0, new_master)
        self.assertEqual(new_master, font.masters[0])
        font.masters.remove(font.masters[0])
        self.assertEqual(amount, len(font.masters))

    def test_instances(self):
        font = self.font
        amount = len(font.instances)
        self.assertEqual(len(list(font.instances)), 8)
        new_instance = GSInstance()
        font.instances.append(new_instance)
        self.assertEqual(new_instance, font.instances[-1])
        del font.instances[-1]
        new_instance1 = GSInstance()
        new_instance2 = GSInstance()
        font.instances.extend([new_instance1, new_instance2])
        self.assertEqual(new_instance1, font.instances[-2])
        self.assertEqual(new_instance2, font.instances[-1])
        font.instances.remove(font.instances[-1])
        font.instances.remove(font.instances[-1])
        new_instance = GSInstance()
        font.instances.insert(0, new_instance)
        self.assertEqual(new_instance, font.instances[0])
        font.instances.remove(font.instances[0])
        self.assertEqual(amount, len(font.instances))

    def test_glyphs(self):
        font = self.font
        self.assertGreaterEqual(len(list(font.glyphs)), 1)
        by_index = font.glyphs[3]
        by_name = font.glyphs["adieresis"]
        by_unicode_char = font.glyphs["ä"]
        by_unicode_value = font.glyphs["00E4"]
        by_unicode_value_lowercased = font.glyphs["00e4"]
        self.assertEqual(by_index, by_name)
        self.assertEqual(by_unicode_char, by_name)
        self.assertEqual(by_unicode_value, by_name)
        self.assertEqual(by_unicode_value_lowercased, by_name)

    def test_classes(self):
        font = self.font
        font.classes = []
        amount = len(font.classes)
        font.classes.append(GSClass("uppercaseLetters", "A"))
        self.assertIsNotNone(font.classes[-1].__repr__())
        self.assertEqual(len(font.classes), 1)
        self.assertIn('<GSClass "uppercaseLetters">', str(font.classes))
        self.assertIn("A", font.classes["uppercaseLetters"].code)
        del font.classes["uppercaseLetters"]
        newClass1 = GSClass("uppercaseLetters1", "A")
        newClass2 = GSClass("uppercaseLetters2", "A")
        font.classes.extend([newClass1, newClass2])
        self.assertEqual(newClass1, font.classes[-2])
        self.assertEqual(newClass2, font.classes[-1])
        newClass = GSClass("uppercaseLetters3", "A")
        newClass = copy.copy(newClass)
        font.classes.insert(0, newClass)
        self.assertEqual(newClass, font.classes[0])
        font.classes.remove(font.classes[-1])
        font.classes.remove(font.classes[-1])
        font.classes.remove(font.classes[0])
        self.assertEqual(len(font.classes), amount)

    def test_features(self):
        font = self.font
        font.features = []
        amount = len(font.features)
        font.features.append(GSFeature("liga", "sub f i by fi;"))
        # TODO
        # self.assertIsNotNone(font.features['liga'].__repr__())
        self.assertEqual(len(font.features), 1)
        # TODO
        # self.assertIn('<GSFeature "liga">', str(font.features))
        # self.assertIn('sub f i by fi;', font.features['liga'].code)
        # del(font.features['liga'])
        del font.features[-1]
        newFeature1 = GSFeature("liga", "sub f i by fi;")
        newFeature2 = GSFeature("liga", "sub f l by fl;")
        font.features.extend([newFeature1, newFeature2])
        self.assertEqual(newFeature1, font.features[-2])
        self.assertEqual(newFeature2, font.features[-1])
        newFeature = GSFeature("liga", "sub f i by fi;")
        newFeature = copy.copy(newFeature)
        font.features.insert(0, newFeature)
        self.assertEqual(newFeature, font.features[0])
        font.features.remove(font.features[-1])
        font.features.remove(font.features[-1])
        font.features.remove(font.features[0])
        self.assertEqual(len(font.features), amount)

    def test_featurePrefixes(self):
        font = self.font
        font.featurePrefixes = []
        amount = len(font.featurePrefixes)
        font.featurePrefixes.append(
            GSFeaturePrefix("LanguageSystems", "languagesystem DFLT dflt;")
        )
        self.assertIsNotNone(font.featurePrefixes[-1].__repr__())
        self.assertEqual(len(font.featurePrefixes), 1)
        self.assertIn('<GSFeaturePrefix "LanguageSystems">', str(font.featurePrefixes))
        self.assertIn("languagesystem DFLT dflt;", font.featurePrefixes[-1].code)
        # TODO
        # del(font.featurePrefixes['LanguageSystems'])
        del font.featurePrefixes[-1]
        newFeaturePrefix1 = GSFeaturePrefix(
            "LanguageSystems1", "languagesystem DFLT dflt;"
        )
        newFeaturePrefix2 = GSFeaturePrefix(
            "LanguageSystems2", "languagesystem DFLT dflt;"
        )
        font.featurePrefixes.extend([newFeaturePrefix1, newFeaturePrefix2])
        self.assertEqual(newFeaturePrefix1, font.featurePrefixes[-2])
        self.assertEqual(newFeaturePrefix2, font.featurePrefixes[-1])
        newFeaturePrefix = GSFeaturePrefix(
            "LanguageSystems3", "languagesystem DFLT dflt;"
        )
        newFeaturePrefix = copy.copy(newFeaturePrefix)
        font.featurePrefixes.insert(0, newFeaturePrefix)
        self.assertEqual(newFeaturePrefix, font.featurePrefixes[0])
        font.featurePrefixes.remove(font.featurePrefixes[-1])
        font.featurePrefixes.remove(font.featurePrefixes[-1])
        font.featurePrefixes.remove(font.featurePrefixes[0])
        self.assertEqual(len(font.featurePrefixes), amount)

    def test_ints(self):
        attributes = ["versionMajor", "versionMajor", "upm", "grid", "gridSubDivisions"]
        font = self.font
        for attr in attributes:
            self.assertInteger(getattr(font, attr))

    def test_strings(self):
        attributes = [
            "copyright",
            "designer",
            "designerURL",
            "manufacturer",
            "manufacturerURL",
            "familyName",
        ]
        font = self.font
        for attr in attributes:
            self.assertUnicode(getattr(font, attr))

    def test_note(self):
        font = self.font
        self.assertUnicode(font.note)

    # date
    def test_date(self):
        font = self.font
        self.assertIsInstance(font.date, datetime.datetime)

    def test_kerning(self):
        font = self.font
        self.assertDict(font.kerning)

    def test_userData(self):
        font = self.font
        self.assertEqual(
            font.userData["AsteriskParameters"],
            {"253E7231-480D-4F8E-8754-50FC8575C08E": ["754", "30", 7, 51, "80", "50"]},
        )
        # self.assertIsInstance(font.userData, dict)
        # TODO
        self.assertIsNone(font.userData["TestData"])
        font.userData["TestData"] = 42
        self.assertEqual(font.userData["TestData"], 42)
        self.assertTrue("TestData" in font.userData)
        del font.userData["TestData"]
        self.assertIsNone(font.userData["TestData"])

    def test_disableNiceNames(self):
        font = self.font
        self.assertIsInstance(font.disablesNiceNames, bool)

    def test_customParameters(self):
        font = self.font
        font.customParameters["trademark"] = "ThisFont is a trademark by MyFoundry.com"
        self.assertIn(
            font.customParameters["trademark"],
            "ThisFont is a trademark by MyFoundry.com",
        )
        amount = len(list(font.customParameters))
        newParameter = GSCustomParameter("hello1", "world1")
        font.customParameters.append(newParameter)
        self.assertEqual(newParameter, list(font.customParameters)[-1])
        del font.customParameters[-1]
        newParameter1 = GSCustomParameter("hello2", "world2")
        newParameter2 = GSCustomParameter("hello3", "world3")
        newParameter2 = copy.copy(newParameter2)
        font.customParameters.extend([newParameter1, newParameter2])
        self.assertEqual(newParameter1, list(font.customParameters)[-2])
        self.assertEqual(newParameter2, list(font.customParameters)[-1])
        font.customParameters.remove(list(font.customParameters)[-1])
        font.customParameters.remove(list(font.customParameters)[-1])
        newParameter = GSCustomParameter("hello1", "world1")
        font.customParameters.insert(0, newParameter)
        self.assertEqual(newParameter, list(font.customParameters)[0])
        font.customParameters.remove(list(font.customParameters)[0])
        self.assertEqual(amount, len(list(font.customParameters)))
        del font.customParameters["trademark"]

    # TODO: selection, selectedLayers, currentText, tabs, currentTab

    # TODO: selectedFontMaster, masterIndex

    def test_filepath(self):
        font = self.font
        self.assertIsNotNone(font.filepath)

    # TODO: tool, tools
    # TODO: save(), close()
    # TODO: setKerningForPair(), kerningForPair(), removeKerningForPair()
    # TODO: updateFeatures()
    # TODO: copy(font)


class GSFontMasterFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.font = GSFont(TESTFILE_PATH)
        self.master = self.font.masters[0]

    def test_attributes(self):
        master = self.master
        self.assertIsNotNone(master.__repr__())
        self.assertIsNotNone(master.id)
        self.assertIsNotNone(master.name)
        self.assertIsNotNone(master.weight)
        self.assertIsNotNone(master.width)
        # weightValue
        obj = master.weightValue
        old_obj = obj
        self.assertIsInstance(obj, int)
        master.weightValue = 0.5
        self.assertEqual(master.weightValue, 0.5)
        self.assertIsInstance(master.weightValue, float)
        master.weightValue = old_obj
        self.assertIsInstance(master.widthValue, int)
        self.assertIsInstance(master.customValue, int)
        self.assertIsInstance(master.ascender, int)
        self.assertIsInstance(master.capHeight, int)
        self.assertIsInstance(master.xHeight, int)
        self.assertIsInstance(master.descender, int)
        self.assertIsInstance(master.italicAngle, int)
        for attr in [
            "weightValue",
            "widthValue",
            "customValue",
            "ascender",
            "capHeight",
            "xHeight",
            "descender",
            "italicAngle",
        ]:
            value = getattr(master, attr)
            self.assertIsInstance(value, int)
            setattr(master, attr, 0.5)
            self.assertEqual(getattr(master, attr), 0.5)
            setattr(master, attr, value)
        self.assertIsInstance(master.customName, str)

        # verticalStems
        oldStems = master.verticalStems
        master.verticalStems = [10, 15, 20]
        self.assertEqual(len(master.verticalStems), 3)
        master.verticalStems = oldStems

        # horizontalStems
        oldStems = master.horizontalStems
        master.horizontalStems = [10, 15, 20]
        self.assertEqual(len(master.horizontalStems), 3)
        master.horizontalStems = oldStems

        # alignmentZones
        self.assertIsInstance(master.alignmentZones, list)

        # TODO blueValues
        # self.assertIsInstance(master.blueValues, list)

        # TODO otherBlues
        # self.assertIsInstance(master.otherBlues, list)

        # guides
        self.assertIsInstance(master.guides, list)
        master.guides = []
        self.assertEqual(len(master.guides), 0)
        newGuide = GSGuideLine()
        newGuide.position = Point("{100, 100}")
        newGuide.angle = -10.0
        master.guides.append(newGuide)
        self.assertIsNotNone(master.guides[0].__repr__())
        self.assertEqual(len(master.guides), 1)
        del master.guides[0]
        self.assertEqual(len(master.guides), 0)

        # guides
        self.assertIsInstance(master.guides, list)
        master.guides = []
        self.assertEqual(len(master.guides), 0)
        newGuide = GSGuideLine()
        newGuide.position = Point("{100, 100}")
        newGuide.angle = -10.0
        master.guides.append(newGuide)
        self.assertIsNotNone(master.guides[0].__repr__())
        self.assertEqual(len(master.guides), 1)
        del master.guides[0]
        self.assertEqual(len(master.guides), 0)

        # userData
        self.assertIsNotNone(master.userData)
        master.userData["TestData"] = 42
        self.assertEqual(master.userData["TestData"], 42)
        del master.userData["TestData"]
        # TODO
        # self.assertIsNone(master.userData["TestData"])

        # customParameters
        master.customParameters[
            "trademark"
        ] = "ThisFont is a trademark by MyFoundry.com"
        self.assertGreaterEqual(len(master.customParameters), 1)
        del master.customParameters["trademark"]

        # font
        self.assertEqual(self.font, self.master.font)

    def test_name(self):
        master = self.master
        self.assertEqual("Light", master.name)

        master.width = "Condensed"
        self.assertEqual(master.name, "Condensed Light")
        master.width = ""

        master.customParameters["Master Name"] = "My custom master name"
        self.assertEqual("My custom master name", master.name)
        del master.customParameters["Master Name"]
        self.assertEqual("Light", master.name)

        master.italicAngle = 11
        self.assertEqual("Light Italic", master.name)
        master.italicAngle = 0

        master.italicAngle = 11
        master.width = "Condensed"
        self.assertEqual("Condensed Light Italic", master.name)
        master.width = ""
        master.italicAngle = 0

        master.customName = "Rounded"
        self.assertEqual("Light Rounded", master.name)
        master.customName = "Rounded Stretched Filled Rotated"
        self.assertEqual("Light Rounded Stretched Filled Rotated", master.name)
        master.customName = ""
        self.assertEqual("Light", master.name)

        # Test the name of a master set to "Regular" in the UI dropdown
        # but with a customName
        thin = GSFontMaster()
        thin.customName = "Thin"
        self.assertEqual("Thin", thin.name)

        # Test that we don't get an extra "Regular" in the name of "Italic"
        # https://github.com/googlefonts/glyphsLib/issues/380
        master = GSFontMaster()
        master.weight = "Regular"
        master.width = "Regular"
        master.italicAngle = 10.0
        self.assertEqual("Italic", master.name)

        # Test that we don't get an extra "Italic" in the name of masters
        # whose customName already contain the string "Italic"
        master = GSFontMaster()
        master.weight = "Regular"
        master.width = "Regular"
        master.customName = "Italic"
        master.italicAngle = 10.0
        self.assertEqual("Italic", master.name)

    def test_name_assignment(self):
        test_data = [
            # <name>, <expected weight>, <expected width>, <expected custom>
            # Regular
            ("Regular", "", "", ""),
            # Weights from the dropdown
            ("Light", "Light", "", ""),
            ("SemiLight", "SemiLight", "", ""),
            ("SemiBold", "SemiBold", "", ""),
            ("Bold", "Bold", "", ""),
            # Widths from the dropdown
            ("Condensed", "", "Condensed", ""),
            ("SemiCondensed", "", "SemiCondensed", ""),
            ("SemiExtended", "", "SemiExtended", ""),
            ("Extended", "", "Extended", ""),
            # Mixed weight and width from dropdowns
            ("Light Condensed", "Light", "Condensed", ""),
            ("Bold SemiExtended", "Bold", "SemiExtended", ""),
            # With italic -- in Glyphs 1114  works like a custom part
            ("Light Italic", "Light", "", "Italic"),
            ("SemiLight Italic", "SemiLight", "", "Italic"),
            ("SemiBold Italic", "SemiBold", "", "Italic"),
            ("Bold Italic", "Bold", "", "Italic"),
            ("Condensed Italic", "", "Condensed", "Italic"),
            ("SemiCondensed Italic", "", "SemiCondensed", "Italic"),
            ("SemiExtended Italic", "", "SemiExtended", "Italic"),
            ("Extended Italic", "", "Extended", "Italic"),
            ("Light Condensed Italic", "Light", "Condensed", "Italic"),
            ("Bold SemiExtended Italic", "Bold", "SemiExtended", "Italic"),
            # With custom parts
            ("Thin", "", "", "Thin"),
            ("SemiLight Ultra Expanded", "SemiLight", "", "Ultra Expanded"),
            ("Bold Compressed", "Bold", "", "Compressed"),
            ("Fat Condensed", "", "Condensed", "Fat"),
            ("Ultra Light Extended", "Light", "Extended", "Ultra"),
            ("Hyper Light Condensed Dunhill", "Light", "Condensed", "Hyper  Dunhill"),
            ("Bold SemiExtended Rugged", "Bold", "SemiExtended", "Rugged"),
            ("Thin Italic", "", "", "Thin Italic"),
            (
                "SemiLight Ultra Expanded Italic",
                "SemiLight",
                "",
                "Ultra Expanded Italic",
            ),
            ("Bold Compressed Italic", "Bold", "", "Compressed Italic"),
            ("Fat Condensed Italic", "", "Condensed", "Fat Italic"),
            ("Ultra Light Extended Italic", "Light", "Extended", "Ultra  Italic"),
            (
                "Hyper Light Condensed Dunhill Italic",
                "Light",
                "Condensed",
                "Hyper  Dunhill Italic",
            ),
            (
                "Bold SemiExtended Rugged Italic",
                "Bold",
                "SemiExtended",
                "Rugged Italic",
            ),
            ("Green Light Red Extended Blue", "Light", "Extended", "Green Red Blue"),
            (
                "Green SemiExtended Red SemiBold Blue",
                "SemiBold",
                "SemiExtended",
                "Green Red Blue",
            ),
        ]
        master = GSFontMaster()
        for name, weight, width, custom in test_data:
            master.name = name
            self.assertEqual(master.name, name)
            self.assertEqual(master.weight, weight or "Regular")
            self.assertEqual(master.width, width or "Regular")
            self.assertEqual(master.customName, custom)

    def test_default_values(self):
        master = GSFontMaster()
        self.assertEqual(master.weightValue, 100.0)
        self.assertEqual(master.widthValue, 100.0)
        self.assertEqual(master.customValue, 0.0)
        self.assertEqual(master.customValue1, 0.0)
        self.assertEqual(master.customValue2, 0.0)
        self.assertEqual(master.customValue3, 0.0)


class GSAlignmentZoneFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.master = self.font.masters[0]

    def test_attributes(self):
        master = self.master
        for i, zone in enumerate(
            [(800, 10), (700, 10), (470, 10), (0, -10), (-200, -10)]
        ):
            pos, size = zone
            self.assertEqual(master.alignmentZones[i].position, pos)
            self.assertEqual(master.alignmentZones[i].size, size)
        master.alignmentZones = []
        self.assertEqual(len(master.alignmentZones), 0)
        master.alignmentZones.append(GSAlignmentZone(100, 10))
        self.assertIsNotNone(master.alignmentZones[-1].__repr__())
        zone = copy.copy(master.alignmentZones[-1])
        self.assertEqual(len(master.alignmentZones), 1)
        self.assertEqual(master.alignmentZones[-1].position, 100)
        self.assertEqual(master.alignmentZones[-1].size, 10)
        del master.alignmentZones[-1]
        self.assertEqual(len(master.alignmentZones), 0)


class GSInstanceFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.instance = self.font.instances[0]

    def test_attributes(self):
        instance = self.instance
        self.assertIsNotNone(instance.__repr__())

        # TODO: active
        # self.assertIsInstance(instance.active, bool)

        # name
        self.assertIsInstance(instance.name, str)

        # weight
        self.assertIsInstance(instance.weight, str)

        # width
        self.assertIsInstance(instance.width, str)

        # weightValue
        # widthValue
        # customValue
        for attr in ["weightValue", "widthValue", "customValue"]:
            value = getattr(instance, attr)
            self.assertIsInstance(value, int)
            setattr(instance, attr, 0.5)
            self.assertEqual(getattr(instance, attr), 0.5)
            setattr(instance, attr, value)
        # isItalic
        # isBold
        for attr in ["isItalic", "isBold"]:
            value = getattr(instance, attr)
            self.assertIsInstance(value, bool)
            setattr(instance, attr, not value)
            self.assertEqual(getattr(instance, attr), not value)
            setattr(instance, attr, value)

        # linkStyle
        self.assertIsInstance(instance.linkStyle, str)

        # familyName
        # preferredFamily
        # preferredSubfamilyName
        # windowsFamily
        # windowsStyle
        # windowsLinkedToStyle
        # fontName
        # fullName
        for attr in [
            "familyName",
            "preferredFamily",
            "preferredSubfamilyName",
            "windowsFamily",
            "windowsStyle",
            "windowsLinkedToStyle",
            "fontName",
            "fullName",
        ]:
            # self.assertIsInstance(getattr(instance, attr), str)
            if not hasattr(instance, attr):
                print("instance does not have %s" % attr)
                if hasattr(instance, "parent") and hasattr(instance.parent, attr):
                    value = getattr(instance.parent)
                    print(value, type(value))

        # customParameters
        instance.customParameters[
            "trademark"
        ] = "ThisFont is a trademark by MyFoundry.com"
        self.assertGreaterEqual(len(instance.customParameters), 1)
        del instance.customParameters["trademark"]

        # instanceInterpolations
        self.assertIsInstance(dict(instance.instanceInterpolations), dict)

        # manualInterpolation
        self.assertIsInstance(instance.manualInterpolation, bool)
        value = instance.manualInterpolation
        instance.manualInterpolation = not instance.manualInterpolation
        self.assertEqual(instance.manualInterpolation, not value)
        instance.manualInterpolation = value

        # interpolatedFont
        # TODO
        # self.assertIsInstance(instance.interpolatedFont, type(Glyphs.font))

        # TODO generate()

    def test_default_values(self):
        instance = GSInstance()
        self.assertEqual(instance.weightValue, 100.0)
        self.assertEqual(instance.widthValue, 100.0)
        self.assertEqual(instance.customValue, 0.0)
        self.assertEqual(instance.customValue1, 0.0)
        self.assertEqual(instance.customValue2, 0.0)
        self.assertEqual(instance.customValue3, 0.0)


class GSGlyphFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.glyph = self.font.glyphs["a"]

    # TODO duplicate
    # def test_duplicate(self):
    #     font = self.font
    #     glyph1 = self.glyph
    #     glyph2 = glyph1.duplicate()
    #     glyph3 = glyph1.duplicate('a.test')

    def test_parent(self):
        font = self.font
        glyph = self.glyph
        self.assertEqual(glyph.parent, font)

    def test_layers(self):
        glyph = self.glyph
        self.assertIsNotNone(glyph.layers)
        amount = len(glyph.layers)
        newLayer = GSLayer()
        newLayer.name = "1"
        glyph.layers.append(newLayer)
        self.assertIn('<GSLayer "1" (a)>', str(glyph.layers[-1]))
        self.assertEqual(newLayer, glyph.layers[-1])
        del glyph.layers[-1]
        newLayer1 = GSLayer()
        newLayer1.name = "2"
        newLayer2 = GSLayer()
        newLayer2.name = "3"
        glyph.layers.extend([newLayer1, newLayer2])
        self.assertEqual(newLayer1, glyph.layers[-2])
        self.assertEqual(newLayer2, glyph.layers[-1])
        newLayer = GSLayer()
        newLayer.name = "4"
        # indices here don't make sense because layer get appended using a UUID
        glyph.layers.insert(0, newLayer)
        # so the latest layer got appended at the end also
        self.assertEqual(newLayer, glyph.layers[-1])
        glyph.layers.remove(glyph.layers[-1])
        glyph.layers.remove(glyph.layers[-1])
        glyph.layers.remove(glyph.layers[-1])
        self.assertEqual(amount, len(glyph.layers))
        self.assertEqual(
            '[<GSLayer "Light" (a)>, <GSLayer "Regular" (a)>, '
            '<GSLayer "Bold" (a)>, <GSLayer "{155, 100}" (a)>]',
            repr(list(glyph.layers)),
        )
        self.assertEqual(
            '[<GSLayer "Bold" (a)>, <GSLayer "Regular" (a)>, '
            '<GSLayer "Light" (a)>, <GSLayer "{155, 100}" (a)>]',
            repr(list(glyph.layers.values())),
        )

    def test_layers_missing_master(self):
        """
        font.glyph['a'] has its layers in a different order
        than the font.masters and an extra layer.
        Adding a master but not adding it as a layer to the glyph should not
        affect glyph.layers unexpectedly.
        """
        glyph = self.glyph
        num_layers = len(glyph.layers)
        self.assertEqual(
            {l.layerId for l in glyph.layers},
            {l.layerId for l in glyph.layers.values()},
        )
        self.assertNotEqual(
            [l.layerId for l in glyph.layers],
            [l.layerId for l in glyph.layers.values()],
        )
        new_fontMaster = GSFontMaster()
        self.font.masters.insert(0, new_fontMaster)
        self.assertEqual(num_layers, len(glyph.layers))
        self.assertEqual(
            {l.layerId for l in glyph.layers},
            {l.layerId for l in glyph.layers.values()},
        )
        self.assertNotEqual(
            [l.layerId for l in glyph.layers],
            [l.layerId for l in glyph.layers.values()],
        )

    def test_name(self):
        glyph = self.glyph
        self.assertIsInstance(glyph.name, str)
        value = glyph.name
        glyph.name = "Ə"
        self.assertEqual(glyph.name, "Ə")
        glyph.name = value

    def test_unicode(self):
        glyph = self.glyph
        self.assertIsInstance(glyph.unicode, str)
        value = glyph.unicode
        # TODO:
        # glyph.unicode = "004a"
        # self.assertEqual(glyph.unicode, "004A")
        glyph.unicode = "004B"
        self.assertEqual(glyph.unicode, "004B")
        glyph.unicode = value

    def test_string(self):
        glyph = self.font.glyphs["adieresis"]
        self.assertEqual(glyph.string, "ä")

    def test_id(self):
        # TODO
        pass

    # TODO
    # category
    # storeCategory
    # subCategory
    # storeSubCategory
    # script
    # storeScript
    # productionName
    # storeProductionName
    # glyphInfo

    def test_horiz_kerningGroup(self):
        for group in ["leftKerningGroup", "rightKerningGroup"]:
            glyph = self.glyph
            self.assertIsInstance(getattr(glyph, group), str)
            value = getattr(glyph, group)
            setattr(glyph, group, "ä")
            self.assertEqual(getattr(glyph, group), "ä")
            setattr(glyph, group, value)

    def test_horiz_metricsKey(self):
        for group in ["leftMetricsKey", "rightMetricsKey"]:
            glyph = self.glyph
            if getattr(glyph, group) is not None:
                self.assertIsInstance(getattr(glyph, group), str)
            value = getattr(glyph, group)
            setattr(glyph, group, "ä")
            self.assertEqual(getattr(glyph, group), "ä")
            setattr(glyph, group, value)

    def test_export(self):
        glyph = self.glyph
        self.assertIsInstance(glyph.export, bool)
        value = glyph.export
        glyph.export = not glyph.export
        self.assertEqual(glyph.export, not value)
        glyph.export = value

    def test_color(self):
        glyph = self.glyph
        if glyph.color is not None:
            self.assertIsInstance(glyph.color, int)
        value = glyph.color
        glyph.color = 5
        self.assertEqual(glyph.color, 5)
        glyph.color = value

    def test_note(self):
        glyph = self.glyph
        if glyph.note is not None:
            self.assertIsInstance(glyph.note, str)
        value = glyph.note
        glyph.note = "ä"
        self.assertEqual(glyph.note, "ä")
        glyph.note = value

    # TODO
    # masterCompatible

    def test_userData(self):
        glyph = self.glyph
        # self.assertIsNone(glyph.userData)
        amount = len(glyph.userData)
        var1 = "abc"
        var2 = "def"
        glyph.userData["unitTestValue"] = var1
        self.assertEqual(glyph.userData["unitTestValue"], var1)
        glyph.userData["unitTestValue"] = var2
        self.assertEqual(glyph.userData["unitTestValue"], var2)
        del glyph.userData["unitTestValue"]
        self.assertIsNone(glyph.userData.get("unitTestValue"))
        self.assertEqual(len(glyph.userData), amount)

    def test_smart_component_axes(self):
        shoulder = self.font.glyphs["_part.shoulder"]
        axes = shoulder.smartComponentAxes
        self.assertIsNotNone(axes)
        crotch_depth, shoulder_width = axes
        self.assertIsInstance(crotch_depth, GSSmartComponentAxis)
        self.assertEqual("crotchDepth", crotch_depth.name)
        self.assertEqual(0, crotch_depth.topValue)
        self.assertEqual(-100, crotch_depth.bottomValue)
        self.assertIsInstance(shoulder_width, GSSmartComponentAxis)
        self.assertEqual("shoulderWidth", shoulder_width.name)
        self.assertEqual(100, shoulder_width.topValue)
        self.assertEqual(0, shoulder_width.bottomValue)

    # TODO
    # lastChange


class GSLayerFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.glyph = self.font.glyphs["a"]
        self.layer = self.glyph.layers[0]

    def test_repr(self):
        layer = self.layer
        self.assertIsNotNone(layer.__repr__())

    def test_parent(self):
        self.assertIs(self.layer.parent, self.glyph)
        self.assertIs(self.layer._background.parent, self.glyph)

    def test_name(self):
        layer = self.layer
        self.assertUnicode(layer.name)

    # TODO
    # def test_associatedMasterId(self):
    #     font = self.font
    #     layer = self.layer
    #     self.assertEqual(layer.associatedMasterId, font.masters[0].id)

    # def test_layerId(self):
    #     font = self.font
    #     layer = self.layer
    #     self.assertEqual(layer.layerId, font.masters[0].id)

    # TODO set layer color in .glyphs file
    # def test_color(self):
    #     layer = self.layer
    #     self.assertInteger(layer.color)

    def test_components(self):
        glyph = self.font.glyphs["adieresis"]
        layer = glyph.layers[0]
        self.assertIsNotNone(layer.components)
        self.assertIsInstance(layer.components, LayerComponentsProxy)
        # self.assertGreaterEqual(len(layer.components), 1)
        self.assertEqual(len(layer.components), 2)
        # for component in layer.components:
        #     self.assertIsInstance(component, GSComponent)
        #     self.assertEqual(component.parent, layer)
        amount = len(layer.components)
        component = GSComponent()
        component.name = "A"
        layer.components.append(component)
        self.assertEqual(component.parent, layer)
        self.assertEqual(len(layer.components), amount + 1)
        del layer.components[-1]
        self.assertEqual(len(layer.components), amount)
        layer.components.extend([component])
        self.assertEqual(len(layer.components), amount + 1)
        layer.components.remove(component)
        self.assertEqual(len(layer.components), amount)

    def test_guides(self):
        layer = self.layer
        self.assertIsInstance(layer.guides, LayerGuideLinesProxy)
        for guide in layer.guides:
            self.assertEqual(guide.parent, layer)
        layer.guides = []
        self.assertEqual(len(layer.guides), 0)
        newGuide = GSGuideLine()
        newGuide.position = Point("{100, 100}")
        newGuide.angle = -10.0
        amount = len(layer.guides)
        layer.guides.append(newGuide)
        self.assertEqual(newGuide.parent, layer)
        self.assertIsNotNone(layer.guides[0].__repr__())
        self.assertEqual(len(layer.guides), amount + 1)
        del layer.guides[0]
        self.assertEqual(len(layer.guides), amount)

    def test_annotations(self):
        layer = self.layer
        # self.assertEqual(layer.annotations, [])
        self.assertEqual(len(layer.annotations), 0)
        newAnnotation = GSAnnotation()
        newAnnotation.type = TEXT
        newAnnotation.text = "This curve is ugly!"
        layer.annotations.append(newAnnotation)
        # TODO position.x, position.y
        # self.assertIsNotNone(layer.annotations[0].__repr__())
        self.assertEqual(len(layer.annotations), 1)
        del layer.annotations[0]
        self.assertEqual(len(layer.annotations), 0)
        newAnnotation1 = GSAnnotation()
        newAnnotation1.type = ARROW
        newAnnotation2 = GSAnnotation()
        newAnnotation2.type = CIRCLE
        newAnnotation3 = GSAnnotation()
        newAnnotation3.type = PLUS
        layer.annotations.extend([newAnnotation1, newAnnotation2, newAnnotation3])
        self.assertEqual(layer.annotations[-3], newAnnotation1)
        self.assertEqual(layer.annotations[-2], newAnnotation2)
        self.assertEqual(layer.annotations[-1], newAnnotation3)
        newAnnotation = GSAnnotation()
        newAnnotation = copy.copy(newAnnotation)
        newAnnotation.type = MINUS
        layer.annotations.insert(0, newAnnotation)
        self.assertEqual(layer.annotations[0], newAnnotation)
        layer.annotations.remove(layer.annotations[0])
        layer.annotations.remove(layer.annotations[-1])
        layer.annotations.remove(layer.annotations[-1])
        layer.annotations.remove(layer.annotations[-1])
        self.assertEqual(len(layer.annotations), 0)

    def test_hints_from_file(self):
        glyph = self.font.glyphs["A"]
        layer = glyph.layers[1]
        self.assertEqual(2, len(layer.hints))
        first, second = layer.hints
        self.assertIsInstance(first, GSHint)
        self.assertTrue(first.horizontal)
        self.assertIsInstance(first.originNode, GSNode)
        first_origin_node = layer.paths[1].nodes[1]
        self.assertEqual(first_origin_node, first.originNode)

        self.assertIsInstance(second, GSHint)
        second_target_node = layer.paths[0].nodes[4]
        self.assertEqual(second_target_node, second.targetNode)

    def test_hints(self):
        layer = self.layer
        # layer.hints = []
        self.assertEqual(len(layer.hints), 0)
        newHint = GSHint()
        newHint = copy.copy(newHint)
        newHint.originNode = layer.paths[0].nodes[0]
        newHint.targetNode = layer.paths[0].nodes[1]
        newHint.type = STEM
        layer.hints.append(newHint)
        self.assertIsNotNone(layer.hints[0].__repr__())
        self.assertEqual(len(layer.hints), 1)
        del layer.hints[0]
        self.assertEqual(len(layer.hints), 0)
        newHint1 = GSHint()
        newHint1.originNode = layer.paths[0].nodes[0]
        newHint1.targetNode = layer.paths[0].nodes[1]
        newHint1.type = STEM
        newHint2 = GSHint()
        newHint2.originNode = layer.paths[0].nodes[0]
        newHint2.targetNode = layer.paths[0].nodes[1]
        newHint2.type = STEM
        layer.hints.extend([newHint1, newHint2])
        newHint = GSHint()
        newHint.originNode = layer.paths[0].nodes[0]
        newHint.targetNode = layer.paths[0].nodes[1]
        self.assertEqual(layer.hints[-2], newHint1)
        self.assertEqual(layer.hints[-1], newHint2)
        layer.hints.insert(0, newHint)
        self.assertEqual(layer.hints[0], newHint)
        layer.hints.remove(layer.hints[0])
        layer.hints.remove(layer.hints[-1])
        layer.hints.remove(layer.hints[-1])
        self.assertEqual(len(layer.hints), 0)

    def test_anchors(self):
        layer = self.layer
        amount = len(layer.anchors)
        self.assertEqual(len(layer.anchors), 3)
        for anchor in layer.anchors:
            self.assertEqual(anchor.parent, layer)
        if layer.anchors["top"]:
            oldPosition = layer.anchors["top"].position
        else:
            oldPosition = None
        layer.anchors["top"] = GSAnchor()
        self.assertGreaterEqual(len(layer.anchors), 1)
        self.assertIsNotNone(layer.anchors["top"].__repr__())
        layer.anchors["top"].position = Point("{100, 100}")
        # anchor = copy.copy(layer.anchors['top'])
        del layer.anchors["top"]
        layer.anchors["top"] = GSAnchor()
        self.assertEqual(amount, len(layer.anchors))
        layer.anchors["top"].position = oldPosition
        self.assertUnicode(layer.anchors["top"].name)
        newAnchor1 = GSAnchor()
        newAnchor1.name = "testPosition1"
        newAnchor2 = GSAnchor()
        newAnchor2.name = "testPosition2"
        layer.anchors.extend([newAnchor1, newAnchor2])
        self.assertEqual(layer.anchors["testPosition1"], newAnchor1)
        self.assertEqual(layer.anchors["testPosition2"], newAnchor2)
        newAnchor3 = GSAnchor()
        newAnchor3.name = "testPosition3"
        layer.anchors.append(newAnchor3)
        self.assertEqual(layer.anchors["testPosition3"], newAnchor3)
        layer.anchors.remove(layer.anchors["testPosition3"])
        layer.anchors.remove(layer.anchors["testPosition2"])
        layer.anchors.remove(layer.anchors["testPosition1"])
        self.assertEqual(amount, len(layer.anchors))

    # TODO layer.paths

    # TODO
    # selection

    # TODO
    # LSB, RSB, TSB, BSB, width

    def test_leftMetricsKey(self):
        self.assertIs(self.layer.leftMetricsKey, None)

    def test_rightMetricsKey(self):
        self.assertIs(self.layer.rightMetricsKey, None)

    def test_widthMetricsKey(self):
        self.assertIs(self.layer.widthMetricsKey, None)

    # TODO: bounds, selectionBounds

    def test_background(self):
        self.assertIn("GSBackgroundLayer", self.layer.background.__repr__())
        self.assertIs(self.layer, self.layer.background.foreground)
        self.assertIs(self.layer.parent, self.layer.background.parent)

    def test_backgroundImage(self):
        # The selected layer (0 of glyph 'a') doesn't have one
        self.assertIsNone(self.layer.backgroundImage)

        glyph = self.font.glyphs["A"]
        layer = glyph.layers[0]
        image = layer.backgroundImage
        self.assertIsInstance(image, GSBackgroundImage)
        # Values from the file
        self.assertEqual("A.jpg", image.path)
        self.assertEqual([0.0, 0.0, 489.0, 637.0], list(image.crop))
        # Default values
        self.assertEqual(50, image.alpha)
        self.assertEqual([1, 0, 0, 1, 0, 0], image.transform.value)
        self.assertEqual(False, image.locked)

        # Test documented behaviour of "alpha"
        image.alpha = 10
        self.assertEqual(10, image.alpha)
        image.alpha = 9
        self.assertEqual(50, image.alpha)
        image.alpha = 100
        self.assertEqual(100, image.alpha)
        image.alpha = 101
        self.assertEqual(50, image.alpha)

    # TODO?
    # bezierPath, openBezierPath, completeBezierPath, completeOpenBezierPath?

    def test_userData(self):
        layer = self.layer
        # self.assertDict(layer.userData)
        layer.userData["Hallo"] = "Welt"
        self.assertEqual(layer.userData["Hallo"], "Welt")
        self.assertTrue("Hallo" in layer.userData)

    def test_smartComponentPoleMapping(self):
        # http://docu.glyphsapp.com/#smartComponentPoleMapping
        # Read some data from the file
        shoulder = self.font.glyphs["_part.shoulder"]
        for layer in shoulder.layers:
            if layer.name == "NarrowShoulder":
                mapping = layer.smartComponentPoleMapping
                self.assertIsNotNone(mapping)
                # crotchDepth is at the top pole
                self.assertEqual(2, mapping["crotchDepth"])
                # shoulderWidth is at the bottom pole
                self.assertEqual(1, mapping["shoulderWidth"])

        # Exercise the getter/setter
        layer = self.layer
        self.assertDict(layer.smartComponentPoleMapping)
        self.assertFalse("crotchDepth" in layer.smartComponentPoleMapping)
        layer.smartComponentPoleMapping["crotchDepth"] = 2
        self.assertTrue("crotchDepth" in layer.smartComponentPoleMapping)
        layer.smartComponentPoleMapping = {"shoulderWidth": 1}
        self.assertFalse("crotchDepth" in layer.smartComponentPoleMapping)
        self.assertEqual(1, layer.smartComponentPoleMapping["shoulderWidth"])

    # TODO: Methods
    # copyDecomposedLayer()
    # decomposeComponents()
    # compareString()
    # connectAllOpenPaths()
    # syncMetrics()
    # correctPathDirection()
    # removeOverlap()
    # roundCoordinates()
    # addNodesAtExtremes()
    # applyTransform()
    # beginChanges()
    # endChanges()
    # cutBetweenPoints()
    # intersectionsBetweenPoints()
    # addMissingAnchors()
    # clearSelection()
    # swapForegroundWithBackground()
    # reinterpolate()
    # clear()


class GSComponentFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.glyph = self.font.glyphs["adieresis"]
        self.layer = self.glyph.layers[0]
        self.component = self.layer.components[0]

    def test_repr(self):
        component = self.component
        self.assertIsNotNone(component.__repr__())
        self.assertEqual(repr(component), '<GSComponent "a" x=0.0 y=0.0>')

    def test_delete_and_add(self):
        layer = self.layer
        self.assertEqual(len(layer.components), 2)
        layer.components = []
        self.assertEqual(len(layer.components), 0)
        layer.components.append(GSComponent("a"))
        self.assertIsNotNone(layer.components[0].__repr__())
        self.assertEqual(len(layer.components), 1)
        layer.components.append(GSComponent("dieresis"))
        self.assertEqual(len(layer.components), 2)
        layer.components = [GSComponent("a"), GSComponent("dieresis")]
        self.assertEqual(len(layer.components), 2)
        layer.components = []
        layer.components.extend([GSComponent("a"), GSComponent("dieresis")])
        self.assertEqual(len(layer.components), 2)
        newComponent = GSComponent("dieresis")
        layer.components.insert(0, newComponent)
        self.assertEqual(newComponent, layer.components[0])
        layer.components.remove(layer.components[0])
        self.assertEqual(len(layer.components), 2)

    def test_position(self):
        self.assertIsInstance(self.component.position, Point)

    def test_componentName(self):
        self.assertUnicode(self.component.componentName)

    def test_component(self):
        self.assertIsInstance(self.component.component, GSGlyph)

    def test_rotation(self):
        self.assertFloat(self.component.rotation)

    def test_transform(self):
        self.assertIsInstance(self.component.transform, Transform)
        self.assertEqual(len(self.component.transform.value), 6)

    def test_bounds(self):
        self.assertIsInstance(self.component.bounds, Rect)
        bounds = self.component.bounds
        self.assertEqual(bounds.origin.x, 80)
        self.assertEqual(bounds.origin.y, -10)
        self.assertEqual(bounds.size.width, 289)
        self.assertEqual(bounds.size.height, 490)

    def test_moreBounds(self):
        self.component.scale = 1.1
        bounds = self.component.bounds
        self.assertEqual(bounds.origin.x, 88)
        self.assertEqual(bounds.origin.y, -11)
        self.assertEqual(round(bounds.size.width * 10), round(317.9 * 10))
        self.assertEqual(round(bounds.size.height * 10), round(539 * 10))

    # def test_automaticAlignment(self):
    #     self.assertBool(self.component.automaticAlignment)

    def test_anchor(self):
        self.assertString(self.component.anchor)

    def test_smartComponentValues(self):
        glyph = self.font.glyphs["h"]
        stem, shoulder = glyph.layers[0].components
        self.assertEqual(100, stem.smartComponentValues["height"])
        self.assertEqual(-80.20097, shoulder.smartComponentValues["crotchDepth"])

        self.assertNotIn("shoulderWidth", shoulder.smartComponentValues)

        self.assertNotIn("somethingElse", shoulder.smartComponentValues)

    # bezierPath?
    # componentLayer()


class GSGuideLineTest(unittest.TestCase):
    def test_repr(self):
        guide = GSGuideLine()
        self.assertEqual(repr(guide), "<GSGuideLine x=0.0 y=0.0 angle=0.0>")


class GSAnchorFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.glyph = self.font.glyphs["a"]
        self.layer = self.glyph.layers[0]
        self.anchor = self.layer.anchors[0]

    def test_repr(self):
        anchor = self.anchor
        self.assertEqual(anchor.__repr__(), '<GSAnchor "bottom" x=218.0 y=0.0>')

    def test_name(self):
        anchor = self.anchor
        self.assertUnicode(anchor.name)

    # TODO
    def test_position(self):
        pass


class GSPathFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.glyph = self.font.glyphs["a"]
        self.layer = self.glyph.layers[0]
        self.path = self.layer.paths[0]

    def test_proxy(self):
        layer = self.layer
        path = self.path
        amount = len(layer.paths)
        pathCopy1 = copy.copy(path)
        layer.paths.append(pathCopy1)
        pathCopy2 = copy.copy(pathCopy1)
        layer.paths.extend([pathCopy2])
        self.assertEqual(layer.paths[-2], pathCopy1)
        self.assertEqual(layer.paths[-1], pathCopy2)
        pathCopy3 = copy.copy(pathCopy2)
        layer.paths.insert(0, pathCopy3)
        self.assertEqual(layer.paths[0], pathCopy3)
        layer.paths.remove(layer.paths[0])
        layer.paths.remove(layer.paths[-1])
        layer.paths.remove(layer.paths[-1])
        self.assertEqual(amount, len(layer.paths))

    def test_parent(self):
        path = self.path
        self.assertEqual(path.parent, self.layer)

    def test_nodes(self):
        path = self.path
        self.assertIsNotNone(path.nodes)
        self.assertEqual(len(path.nodes), 44)
        for node in path.nodes:
            self.assertEqual(node.parent, path)
        amount = len(path.nodes)
        newNode = GSNode(Point("{100, 100}"))
        path.nodes.append(newNode)
        self.assertEqual(newNode, path.nodes[-1])
        del path.nodes[-1]
        newNode = GSNode(Point("{20, 20}"))
        path.nodes.insert(0, newNode)
        self.assertEqual(newNode, path.nodes[0])
        path.nodes.remove(path.nodes[0])
        newNode1 = GSNode(Point("{10, 10}"))
        newNode2 = GSNode(Point("{20, 20}"))
        path.nodes.extend([newNode1, newNode2])
        self.assertEqual(newNode1, path.nodes[-2])
        self.assertEqual(newNode2, path.nodes[-1])
        del path.nodes[-2]
        del path.nodes[-1]
        self.assertEqual(amount, len(path.nodes))

    # TODO: GSPath.closed

    # bezierPath?

    # TODO:
    # addNodesAtExtremes()
    # applyTransform()
    def test_applyTransform_translate(self):
        pathCopy = copy.copy(self.path)
        pathCopy.applyTransform((1, 0, 0, 1, 50, 25))
        expected = ((402, 172), (402, 93), (364, 32), (262, 32))
        for i, pt in enumerate(expected):
            self.assertEqual(pathCopy.nodes[i].position.x, pt[0])
            self.assertEqual(pathCopy.nodes[i].position.y, pt[1])

    def test_applyTransform_translate_scale(self):
        pathCopy = copy.copy(self.path)
        pathCopy.applyTransform((0.9, 0, 0, 1.2, 50, 25))
        expected = ((367, 201), (367, 107), (333, 33), (241, 33))
        for i, pt in enumerate(expected):
            self.assertAlmostEqual(pathCopy.nodes[i].position.x, pt[0], 0)
            self.assertAlmostEqual(pathCopy.nodes[i].position.y, pt[1], 0)

    def test_applyTransform_skew(self):
        pathCopy = copy.copy(self.path)
        pathCopy.applyTransform((1, 0.1, 0.2, 1, 0, 0))
        expected = ((381, 182), (366, 103), (315, 38), (213, 28))
        for i, pt in enumerate(expected):
            self.assertAlmostEqual(pathCopy.nodes[i].position.x, pt[0], 0)
            self.assertAlmostEqual(pathCopy.nodes[i].position.y, pt[1], 0)

    def test_direction(self):
        self.assertEqual(self.path.direction, -1)

    def test_segments(self):
        oldSegments = self.path.segments
        self.assertEqual(len(self.path.segments), 20)
        self.path.reverse()
        self.assertEqual(len(self.path.segments), 20)
        self.assertEqual(oldSegments[0].nodes[0], self.path.segments[0].nodes[0])

    def test_segments_2(self):
        p = GSPath()
        p.nodes = [
            GSNode((204, 354), "curve"),
            GSNode((198, 353), "offcurve"),
            GSNode((193, 352), "offcurve"),
            GSNode((183, 352), "curve"),
            GSNode((154, 352), "offcurve"),
            GSNode((123, 364), "offcurve"),
            GSNode((123, 384), "curve"),
            GSNode((123, 403), "offcurve"),
            GSNode((148, 419), "offcurve"),
            GSNode((167, 419), "curve"),
            GSNode((190, 419), "offcurve"),
            GSNode((204, 397), "offcurve"),
        ]
        self.assertEqual(len(p.segments), 4)

    def test_bounds(self):
        bounds = self.path.bounds
        self.assertEqual(bounds.origin.x, 80)
        self.assertEqual(bounds.origin.y, -10)
        self.assertEqual(bounds.size.width, 289)
        self.assertEqual(bounds.size.height, 490)


class GSNodeFromFileTest(GSObjectsTestCase):
    def setUp(self):
        super().setUp()
        self.glyph = self.font.glyphs["a"]
        self.layer = self.glyph.layers[0]
        self.path = self.layer.paths[0]
        self.node = self.path.nodes[0]

    def test_repr(self):
        self.assertIsNotNone(self.node.__repr__())

    def test_position(self):
        self.assertIsInstance(self.node.position, Point)

    def test_type(self):
        self.assertTrue(self.node.type in [LINE, CURVE, OFFCURVE])

    def test_smooth(self):
        self.assertBool(self.node.smooth)

    def test_index(self):
        self.assertInteger(self.node.index)
        self.assertEqual(self.path.nodes[0].index, 0)
        self.assertEqual(self.path.nodes[-1].index, 43)

    def test_nextNode(self):
        self.assertEqual(type(self.path.nodes[-1].nextNode), GSNode)
        self.assertEqual(self.path.nodes[-1].nextNode, self.path.nodes[0])

    def test_prevNode(self):
        self.assertEqual(type(self.path.nodes[0].prevNode), GSNode)
        self.assertEqual(self.path.nodes[0].prevNode, self.path.nodes[-1])

    def test_name(self):
        self.assertEqual(self.node.name, "Hello")

    def test_userData(self):
        self.assertEqual("1", self.node.userData["rememberToMakeCoffee"])

    def test_makeNodeFirst(self):
        oldAmount = len(self.path.nodes)
        oldSecondNode = self.path.nodes[3]
        self.path.nodes[3].makeNodeFirst()
        self.assertEqual(oldAmount, len(self.path.nodes))
        self.assertEqual(oldSecondNode, self.path.nodes[0])

    def test_toggleConnection(self):
        oldConnection = self.node.smooth
        self.node.toggleConnection()
        self.assertEqual(oldConnection, not self.node.smooth)


class GSCustomParameterTest(unittest.TestCase):
    def test_plistValue_string(self):
        test_string = "Some Value"
        param = GSCustomParameter("New Parameter", test_string)
        self.assertEqual(
            param.plistValue(), '{\nname = "New Parameter";\nvalue = "Some Value";\n}'
        )

    def test_plistValue_list(self):
        test_list = [1, 2.5, {"key1": "value1"}]
        param = GSCustomParameter("New Parameter", test_list)
        self.assertEqual(
            param.plistValue(),
            '{\nname = "New Parameter";\nvalue = (\n1,\n2.5,'
            "\n{\nkey1 = value1;\n}\n);\n}",
        )

    def test_plistValue_dict(self):
        test_dict = {"key1": "value1", "key2": "value2"}
        param = GSCustomParameter("New Parameter", test_dict)
        self.assertEqual(
            param.plistValue(),
            '{\nname = "New Parameter";\nvalue = {\nkey1 = value1;'
            "\nkey2 = value2;\n};\n}",
        )


class GSBackgroundLayerTest(unittest.TestCase):
    """Goal: forbid in glyphsLib all the GSLayer.background APIs that don't
    work in Glyphs.app, so that the code we write for glyphsLib is sure to
    work in Glyphs.app
    """

    def setUp(self):
        self.layer = GSLayer()
        self.bg = self.layer.background

    def test_get_GSLayer_background(self):
        """It should always return a GSLayer (actually a GSBackgroundLayer but
        it's a subclass of GSLayer so it's ok)
        """
        self.assertIsInstance(self.bg, GSLayer)
        bg2 = self.layer.background
        self.assertEqual(self.bg, bg2)

    def test_set_GSLayer_background(self):
        """It should raise because it behaves strangely in Glyphs.app.
        The only way to modify a background layer in glyphsLib is to get it
        from a GSLayer object.
        """
        with pytest.raises(AttributeError):
            self.layer.background = GSLayer()

    def test_get_GSLayer_foreground(self):
        """It should raise AttributeError, as in Glyphs.app"""
        with pytest.raises(AttributeError):
            self.layer.foreground

    def test_set_GSLayer_foreground(self):
        with pytest.raises(AttributeError):
            self.layer.foreground = GSLayer()

    def test_get_GSBackgroundLayer_background(self):
        """It should always return None, as in Glyphs.app"""
        self.assertIsNone(self.bg.background)

    def test_set_GSBackgroundLayer_background(self):
        """It should raise because it should not be possible."""
        with pytest.raises(AttributeError):
            self.bg.background = GSLayer()

    def test_get_GSBackgroundLayer_foreground(self):
        """It should return the foreground layer.

        WARNING: currently in Glyphs.app it is not implemented properly and it
        returns some Objective C function.
        """
        self.assertEqual(self.layer, self.bg.foreground)

    def test_set_GSBackgroundLayer_foreground(self):
        """It should raise AttributeError, because it would be too complex to
        implement properly and anyway in Glyphs.app it returns some Objective C
        function.
        """
        with pytest.raises(AttributeError):
            self.bg.foreground = GSLayer()


class segmentTest(unittest.TestCase):
    def test_bbox_bug(self):
        seg = segment(
            [Point(529, 223), Point(447, 456), Point(285, 177), Point(521, 367)]
        )
        bbox = seg.bbox()
        self.assertAlmostEqual(bbox[0], 398.1222655016518)
        self.assertAlmostEqual(bbox[1], 223)
        self.assertAlmostEqual(bbox[2], 529)
        self.assertAlmostEqual(bbox[3], 367)


class FontGlyphsProxyTest(unittest.TestCase):
    def setUp(self):
        self.font = GSFont(TESTFILE_PATH)

    def test_remove_glyphs(self):
        assert self.font.glyphs[0].name == "A"
        del self.font.glyphs[0]
        assert self.font.glyphs[0].name != "A"

        assert self.font.glyphs["Adieresis"].name == "Adieresis"
        del self.font.glyphs["Adieresis"]
        assert self.font.glyphs["Adieresis"] is None

        with pytest.raises(KeyError):
            del self.font.glyphs["xxxzzz"]

        with pytest.raises(KeyError):
            del self.font.glyphs[self.font]


class FontClassesProxyTest(unittest.TestCase):
    def setUp(self):
        self.font = GSFont(TESTFILE_PATH)

    def test_indxing_by_name(self):
        assert "Languagesystems" in self.font.featurePrefixes
        assert "c2sc_source" in self.font.classes
        assert "aalt" in self.font.features

        assert "XXXX" not in self.font.featurePrefixes
        assert "XXXX" not in self.font.classes
        assert "XXXX" not in self.font.features

        assert self.font.featurePrefixes["Languagesystems"] in self.font.featurePrefixes
        assert self.font.classes["c2sc_source"] in self.font.classes
        assert self.font.features["aalt"] in self.font.features


if __name__ == "__main__":
    unittest.main()
