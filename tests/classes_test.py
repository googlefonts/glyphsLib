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
import re
from typing import Optional

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
    GSGuide,
    GSHint,
    GSNode,
    GSPath,
    GSSmartComponentAxis,
    GSBackgroundImage,
    InstanceType,
    GSPathSegment,
    LayerComponentsProxy,
    LayerGuideLinesProxy,
    GSMetricValue,
    PS_STEM,
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
from glyphsLib.classes import LAYER_ATTRIBUTE_AXIS_RULES

datadir = os.path.join(os.path.dirname(__file__), "data")

TESTFILE_PATHV2 = os.path.join(
    os.path.join(datadir, "GlyphsUnitTestSans2.glyphs")
)
TESTFILE_PATHV3 = os.path.join(
    os.path.join(datadir, "GlyphsUnitTestSans3.glyphs")
)

pytestmark = pytest.mark.parametrize("file_path", [TESTFILE_PATHV2, TESTFILE_PATHV3])


def prune_repr(obj):
    # Remove the space + 0x + hex digits
    return re.sub(r"\s0x[0-9A-Fa-f]+", " 0x00", repr(obj))


def generate_minimal_font(formatVersion=2):
    font = GSFont()
    font.formatVersion = formatVersion
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
    for property in instance_dict.get("properties", []):
        name = property["key"]
        value = property["value"]
        instance.properties.setProperty(name, value)
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
    glyph = font.glyphs[glyphname]
    if glyph:
        for master in font.masters:
            layer = glyph.layers[master.id]
            layer.anchors = getattr(layer, "anchors", [])
            anchor = GSAnchor()
            anchor.name = anchorname
            anchor.position = Point(x, y)
            layer.anchors.append(anchor)


def add_component(font, glyphname, componentname, transform):
    glyph = font.glyphs[glyphname]
    if glyph:
        for layer in glyph.layers.values():
            component = GSComponent(componentname, transform=transform)
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

    def test_iterate_layers_of_orphan_glyph(self):
        # https://github.com/googlefonts/glyphsLib/issues/1013
        glyph = GSGlyph()
        assert glyph.parent is None
        layer = GSLayer()
        glyph.layers.append(layer)
        assert layer.parent is glyph
        # this ought not to raise a `KeyError: 0` exception
        layers = list(glyph.layers)
        assert layers[0] is layer

    def test_layer_nested_bounds(self):
        file = "layer_bounds_with_nested_component.glyphs"
        font = GSFont(os.path.join(datadir, file))

        quotedblright = font.glyphs["quotedblbase"]
        layer = quotedblright.layers[0]
        bounds = layer.bounds
        assert bounds.origin.x == 64
        assert bounds.origin.y == -130
        assert bounds.size.width == 251
        assert bounds.size.height == 237

        quotedblright = font.glyphs["quotedblleft"]
        layer = quotedblright.layers[0]
        bounds = layer.bounds
        assert bounds.origin.x == 79
        assert bounds.origin.y == 463
        assert bounds.size.width == 251
        assert bounds.size.height == 237

        quotedblright = font.glyphs["quotedblright"]
        layer = quotedblright.layers[0]
        bounds = layer.bounds
        assert bounds.origin.x == 73
        assert bounds.origin.y == 463
        assert bounds.size.width == 251
        assert bounds.size.height == 237


# GlyphsBracketLayerTest
def test_bracket_layers(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["cent"]
    for layer in glyph.layers:
        if layer.isMasterLayer:
            continue
        assert layer.attributes[LAYER_ATTRIBUTE_AXIS_RULES] == {"a01": {"min": 120}}
        assert layer.name == "[120‹wg]"


class GSFontTest(unittest.TestCase):
    def test_init(self):
        font = GSFont()
        self.assertEqual(font.familyName, "Unnamed font")
        self.assertEqual(font.versionMajor, 1)
        self.assertEqual(font.versionMinor, 0)
        self.assertEqual(font.appVersion, "3260")

        self.assertEqual(len(font.glyphs), 0)
        self.assertEqual(len(font.masters), 0)
        self.assertEqual(list(font.masters), list(()))
        self.assertEqual(len(font.instances), 0)
        # self.assertEqual(font.instances, []) this is a proxy now
        self.assertEqual(len(font.customParameters), 0)

    def test_repr(self):
        font = GSFont()
        expected = '<GSFont 0x00> "Unnamed font"'
        assert prune_repr(font) == expected

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


class GSInstanceTest(unittest.TestCase):
    def test_variable_instance(self):
        instance = GSInstance()
        instance.name = "Variable"
        instance.type = InstanceType.VARIABLE

        assert len(instance.internalAxesValues) == 0


# GSFontFromFileTest
def test_pathlike_path(file_path):
    from pathlib import Path

    font = GSFont(file_path)
    assert font.filepath == file_path

    font = GSFont(Path(file_path))
    assert font.filepath == file_path


def test_masters(file_path):
    font = GSFont(file_path)
    amount = len(font.masters)
    assert len(list(font.masters)) == 3

    assert font.masters[0].name == "Light"
    assert font.masters[1].name == "Regular"
    assert font.masters[2].name == "Bold"

    new_master = GSFontMaster()
    font.masters.append(new_master)
    assert new_master == font.masters[-1]
    del font.masters[-1]

    new_master1 = GSFontMaster()
    new_master2 = GSFontMaster()
    font.masters.extend([new_master1, new_master2])
    assert new_master1 == font.masters[-2]
    assert new_master2 == font.masters[-1]

    font.masters.remove(font.masters[-1])
    font.masters.remove(font.masters[-1])

    new_master = GSFontMaster()
    font.masters.insert(0, new_master)
    assert new_master == font.masters[0]
    font.masters.remove(font.masters[0])
    assert amount == len(font.masters)


def test_instances(file_path):
    font = GSFont(file_path)
    amount = len(font.instances)
    assert len(list(font.instances)) == 8
    new_instance = GSInstance()
    font.instances.append(new_instance)
    assert new_instance == font.instances[-1]
    del font.instances[-1]
    new_instance1 = GSInstance()
    new_instance2 = GSInstance()
    font.instances.extend([new_instance1, new_instance2])
    assert new_instance1 == font.instances[-2]
    assert new_instance2 == font.instances[-1]
    font.instances.remove(font.instances[-1])
    font.instances.remove(font.instances[-1])
    new_instance = GSInstance()
    font.instances.insert(0, new_instance)
    assert new_instance == font.instances[0]
    font.instances.remove(font.instances[0])
    assert amount == len(font.instances)


def test_glyphs(file_path):
    font = GSFont(file_path)
    assert len(list(font.glyphs)) >= 1
    by_index = font.glyphs[4]
    by_name = font.glyphs["adieresis"]
    by_unicode_char = font.glyphs["ä"]
    by_unicode_value = font.glyphs["00E4"]
    by_unicode_value_lowercased = font.glyphs["00e4"]
    assert by_index == by_name
    assert by_unicode_char == by_name
    assert by_unicode_value == by_name
    assert by_unicode_value_lowercased == by_name


def test_classes(file_path):
    font = GSFont(file_path)
    font.classes = []
    amount = len(font.classes)
    font.classes.append(GSClass("uppercaseLetters", "A"))
    assert font.classes[-1].__repr__() is not None
    assert len(font.classes) == 1
    assert '<GSClass "uppercaseLetters">' in str(font.classes)
    assert "A" in font.classes["uppercaseLetters"].code
    del font.classes["uppercaseLetters"]
    newClass1 = GSClass("uppercaseLetters1", "A")
    newClass2 = GSClass("uppercaseLetters2", "A")
    font.classes.extend([newClass1, newClass2])
    assert newClass1 == font.classes[-2]
    assert newClass2 == font.classes[-1]
    newClass = GSClass("uppercaseLetters3", "A")
    newClass = copy.copy(newClass)
    font.classes.insert(0, newClass)
    assert newClass == font.classes[0]
    font.classes.remove(font.classes[-1])
    font.classes.remove(font.classes[-1])
    font.classes.remove(font.classes[0])
    assert len(font.classes) == amount


def test_features(file_path):
    font = GSFont(file_path)
    font.features = []
    amount = len(font.features)
    font.features.append(GSFeature("liga", "sub f i by fi;"))
    # TODO
    # assert font.features['liga'].__repr__() is not None
    assert len(font.features) == 1
    # TODO
    # assert '<GSFeature "liga">' in str(font.features)
    # assert 'sub f i by fi;' in font.features['liga'].code
    # del(font.features['liga'])
    del font.features[-1]
    newFeature1 = GSFeature("liga", "sub f i by fi;")
    newFeature2 = GSFeature("liga", "sub f l by fl;")
    font.features.extend([newFeature1, newFeature2])
    assert newFeature1 == font.features[-2]
    assert newFeature2 == font.features[-1]
    newFeature = GSFeature("liga", "sub f i by fi;")
    newFeature = copy.copy(newFeature)
    font.features.insert(0, newFeature)
    assert newFeature == font.features[0]
    font.features.remove(font.features[-1])
    font.features.remove(font.features[-1])
    font.features.remove(font.features[0])
    assert len(font.features) == amount


def test_featurePrefixes(file_path):
    font = GSFont(file_path)
    font.featurePrefixes = []
    amount = len(font.featurePrefixes)
    font.featurePrefixes.append(
        GSFeaturePrefix("LanguageSystems", "languagesystem DFLT dflt;")
    )
    assert font.featurePrefixes[-1].__repr__() is not None
    assert len(font.featurePrefixes) == 1
    assert '<GSFeaturePrefix "LanguageSystems">' in str(font.featurePrefixes)
    assert "languagesystem DFLT dflt;" in font.featurePrefixes[-1].code
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
    assert newFeaturePrefix1 == font.featurePrefixes[-2]
    assert newFeaturePrefix2 == font.featurePrefixes[-1]
    newFeaturePrefix = GSFeaturePrefix(
        "LanguageSystems3", "languagesystem DFLT dflt;"
    )
    newFeaturePrefix = copy.copy(newFeaturePrefix)
    font.featurePrefixes.insert(0, newFeaturePrefix)
    assert newFeaturePrefix == font.featurePrefixes[0]
    font.featurePrefixes.remove(font.featurePrefixes[-1])
    font.featurePrefixes.remove(font.featurePrefixes[-1])
    font.featurePrefixes.remove(font.featurePrefixes[0])
    assert len(font.featurePrefixes) == amount


def test_ints(file_path):
    attributes = ["versionMajor", "versionMajor", "upm", "grid", "gridSubDivision"]
    font = GSFont(file_path)
    for attr in attributes:
        assert isinstance(getattr(font, attr), int)


def test_strings(file_path):
    attributes = [
        "copyright",
        "designer",
        "designerURL",
        "manufacturer",
        "manufacturerURL",
        "familyName",
    ]
    font = GSFont(file_path)
    # FIXME: (georg) most of them are not set in the test file and will return None
    for attr in attributes:
        value = getattr(font, attr)
        if value is not None:
            assert isinstance(value, str)


def test_note(file_path):
    font = GSFont(file_path)
    assert isinstance(font.note, str)


# date
def test_date(file_path):
    font = GSFont(file_path)
    assert isinstance(font.date, datetime.datetime)


def test_kerning(file_path):
    font = GSFont(file_path)
    assert isinstance(font.kerning, dict)


def test_userData(file_path):
    font = GSFont(file_path)
    assert font.userData["AsteriskParameters"] == {"253E7231-480D-4F8E-8754-50FC8575C08E": ["754", "30", 7, 51, "80", "50"]}

    # assert isinstance(font.userData, dict)
    # TODO
    assert font.userData["TestData"] is None
    font.userData["TestData"] = 42
    assert font.userData["TestData"] == 42
    assert "TestData" in font.userData
    del font.userData["TestData"]
    assert font.userData["TestData"] is None


def test_disableNiceNames(file_path):
    font = GSFont(file_path)
    assert isinstance(font.disablesNiceNames, bool)


def test_customParameters(file_path):
    font = GSFont(file_path)
    font.customParameters["trademark"] = "ThisFont is a trademark by MyFoundry.com"
    assert font.customParameters["trademark"] in "ThisFont is a trademark by MyFoundry.com"
    amount = len(list(font.customParameters))
    newParameter = GSCustomParameter("hello1", "world1")
    font.customParameters.append(newParameter)
    assert newParameter == list(font.customParameters)[-1]
    del font.customParameters[-1]
    newParameter1 = GSCustomParameter("hello2", "world2")
    newParameter2 = GSCustomParameter("hello3", "world3")
    newParameter2 = copy.copy(newParameter2)
    font.customParameters.extend([newParameter1, newParameter2])
    assert newParameter1 == list(font.customParameters)[-2]
    assert newParameter2 == list(font.customParameters)[-1]
    font.customParameters.remove(list(font.customParameters)[-1])
    font.customParameters.remove(list(font.customParameters)[-1])
    newParameter = GSCustomParameter("hello1", "world1")
    font.customParameters.insert(0, newParameter)
    assert newParameter == list(font.customParameters)[0]
    font.customParameters.remove(list(font.customParameters)[0])
    assert amount == len(list(font.customParameters))
    del font.customParameters["trademark"]

# TODO: selection, selectedLayers, currentText, tabs, currentTab

# TODO: selectedFontMaster, masterIndex


def test_filepath(file_path):
    font = GSFont(file_path)
    assert font.filepath is not None

# TODO: tool, tools
# TODO: save(), close()
# TODO: setKerningForPair(), kerningForPair(), removeKerningForPair()
# TODO: updateFeatures()
# TODO: copy(font)

# GSFontMasterFromFileTest
# def setUp(self):
#     super().setUp()
#     self.master = self.font.masters[0]


def test_attributes(file_path):
    font = GSFont(file_path)
    master = font.masters[0]

    assert master.__repr__() is not None
    assert master.id is not None
    assert master.name is not None
    assert master.internalAxesValues[0] is not None
    assert master.internalAxesValues[1] is None
    # weightValue
    obj = master.internalAxesValues[0]
    old_obj = obj
    assert isinstance(obj, int)
    master.internalAxesValues[0] = 0.5
    assert master.internalAxesValues[0] == 0.5
    assert isinstance(master.internalAxesValues[0], float)
    master.internalAxesValues[0] = old_obj

    metrics = []
    for metric in font.metrics:
        value = master.metricValues[metric.id]
        assert isinstance(value, GSMetricValue)
        metrics.append((value.position, value.overshoot))
    expected = [
        (800, 10),
        (700, 10),
        (470, 10),
        (0, -10),
        (-200, -10),
        (520, 10),
        (0, 0),
    ]
    assert metrics == expected

    stems = []
    for stem in font.stems:
        value = master.stems[stem.id]
        stems.append(value)
    expected = [16, 16, 18, 17, 19]
    assert stems == expected

    # guides
    assert isinstance(master.guides, list)
    master.guides = []
    assert len(master.guides) == 0
    newGuide = GSGuide()
    newGuide.position = Point("{100, 100}")
    newGuide.angle = -10.0
    master.guides.append(newGuide)
    assert master.guides[0].__repr__() is not None
    assert len(master.guides) == 1
    del master.guides[0]
    assert len(master.guides) == 0

    # userData
    assert master.userData is not None
    master.userData["TestData"] = 42
    assert master.userData["TestData"] == 42
    del master.userData["TestData"]
    # TODO
    # self.assertIsNone(master.userData["TestData"])

    # customParameters
    master.customParameters[
        "trademark"
    ] = "ThisFont is a trademark by MyFasoundry.com"
    assert len(master.customParameters) >= 1
    del master.customParameters["trademark"]

    # font
    assert font == master.font


def test_legacyAttributes(file_path):
    font = GSFont(file_path)
    master = font.masters[0]
    assert isinstance(master.ascender, int)
    assert isinstance(master.capHeight, int)
    assert isinstance(master.xHeight, int)
    assert isinstance(master.descender, int)
    assert isinstance(master.italicAngle, int)

    for attr in [
        "ascender",
        "capHeight",
        "xHeight",
        "descender",
        "italicAngle",
    ]:
        value = getattr(master, attr)
        assert isinstance(value, int)
        setattr(master, attr, 0.5)
        assert getattr(master, attr) == 0.5
        setattr(master, attr, value)
    # verticalStems
    assert len(master.verticalStems) == 2
    assert master.verticalStems == [17, 19]

    # horizontalStems
    assert len(master.horizontalStems) == 3
    assert master.horizontalStems == [16, 16, 18]

    # alignmentZones
    assert isinstance(master.alignmentZones, list)
    zones = []
    for zone in master.alignmentZones:
        assert isinstance(zone, GSAlignmentZone)
        zones.append((zone.position, zone.size))
    expected = [(800, 10), (700, 10), (520, 10), (470, 10), (0, -10), (-200, -10)]
    assert zones == expected

    # blueValues
    assert isinstance(master.blueValues, list)
    assert master.blueValues == [-10, 0, 470, 480, 700, 710, 800, 810]

    # otherBlues
    assert isinstance(master.otherBlues, list)
    assert master.otherBlues == [-210, -200]


def test_loadLegacy_name(file_path):
    font = GSFont(file_path)
    master = font.masters[0]
    master.italicAngel = 10
    name = master._joinNames("Bold", "Regular", None)
    assert name == "Bold"


""" .alignmentZones is readonly now.
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
            assert master.alignmentZones[i].position == pos
            assert master.alignmentZones[i].size == size
        master.alignmentZones = []
        assert len(master.alignmentZones) == 0
        master.alignmentZones.append(GSAlignmentZone(100, 10))
        assert master.alignmentZones[-1].__repr__() is not None
        zone = copy.copy(master.alignmentZones[-1])
        assert len(master.alignmentZones) == 1
        assert master.alignmentZones[-1].position == 100
        assert master.alignmentZones[-1].size == 10
        del master.alignmentZones[-1]
        assert len(master.alignmentZones) == 0
"""


# GSInstanceFromFileTest
# def setUp(self):
#     super().setUp()
#     self.instance = self.font.instances[0]

def test_Instance_attributes(file_path):
    font = GSFont(file_path)
    instance = font.instances[0]

    assert instance.__repr__() is not None

    # TODO: active
    # assert isinstance(instance.active, bool)

    # name
    assert isinstance(instance.name, str)

    # weight
    assert isinstance(instance.weightClass, int)

    # width
    assert isinstance(instance.widthClass, int)

    assert instance.internalAxesValues[0] == 17
    instance.internalAxesValues[0] = 17.5
    assert instance.internalAxesValues[0] == 17.5

    # isItalic
    # isBold
    for attr in ["isItalic", "isBold"]:
        value = getattr(instance, attr)
        assert isinstance(value, bool)
        setattr(instance, attr, not value)
        assert getattr(instance, attr) == (not value)
        setattr(instance, attr, value)

    # linkStyle
    assert isinstance(instance.linkStyle, str)

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
        # assert isinstance(getattr(instance, attr), str)
        if not hasattr(instance, attr):
            print("instance does not have %s" % attr)
            if hasattr(instance, "parent") and hasattr(instance.parent, attr):
                value = getattr(instance.parent, attr)  # FIXME: (gs) added "attr"??
                print(value, type(value))

    # customParameters
    instance.customParameters["trademark"] = "ThisFont is a trademark by MyFoundry.com"
    assert len(instance.customParameters) >= 1
    del instance.customParameters["trademark"]

    # instanceInterpolations
    assert isinstance(dict(instance.instanceInterpolations), dict)

    # manualInterpolation
    assert isinstance(instance.manualInterpolation, bool)
    value = instance.manualInterpolation
    instance.manualInterpolation = not instance.manualInterpolation
    assert instance.manualInterpolation == (not value)
    instance.manualInterpolation = value

    # interpolatedFont
    # TODO
    # assert isinstance(instance.interpolatedFont, type(Glyphs.font))

    # TODO generate()


# GSGlyphFromFileTest
# TODO duplicate
# def test_duplicate(self):
#     font = self.font
#     glyph1 = self.glyph
#     glyph2 = glyph1.duplicate()
#     glyph3 = glyph1.duplicate('a.test')

def test_parent(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    assert glyph.parent == font


def test_layers(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    assert glyph.layers is not None
    amount = len(glyph.layers)
    newLayer = GSLayer()
    newLayer.name = "1"
    glyph.layers.append(newLayer)
    assert '<GSLayer 0x00> "1" (a)' in prune_repr(glyph.layers[-1])
    assert newLayer == glyph.layers[-1]
    del glyph.layers[-1]
    newLayer1 = GSLayer()
    newLayer1.name = "2"
    newLayer2 = GSLayer()
    newLayer2.name = "3"
    glyph.layers.extend([newLayer1, newLayer2])
    assert newLayer1 == glyph.layers[-2]
    assert newLayer2 == glyph.layers[-1]
    newLayer = GSLayer()
    newLayer.name = "4"
    # indices here don't make sense because layer get appended using a UUID
    glyph.layers.insert(0, newLayer)
    # so the latest layer got appended at the end also
    assert newLayer == glyph.layers[-1]
    glyph.layers.remove(glyph.layers[-1])
    glyph.layers.remove(glyph.layers[-1])
    glyph.layers.remove(glyph.layers[-1])
    assert amount == len(glyph.layers)
    assert '[<GSLayer 0x00> "Light" (a), <GSLayer 0x00> "Regular" (a), <GSLayer 0x00> "Bold" (a), <GSLayer 0x00> "{155}" (a)]' == prune_repr(list(glyph.layers))
    # values are unordered so we can’t test like this
    # assert '[<GSLayer 0x00> "Light" (a), <GSLayer 0x00> "Regular" (a), <GSLayer 0x00> "Bold" (a), <GSLayer 0x00> "{155}" (a)]' == prune_repr(list(glyph.layers.values()))


def test_layers_missing_master(file_path):
    """
    font.glyph['a'] has its layers in a different order
    than the font.masters and an extra layer.
    Adding a master but not adding it as a layer to the glyph should not
    affect glyph.layers unexpectedly.
    """
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    num_layers = len(glyph.layers)
    assert {layer.layerId for layer in glyph.layers} == {layer.layerId for layer in glyph.layers.values()}

    assert [l.layerId for l in glyph.layers] != [l.layerId for l in glyph.layers.values()]

    new_fontMaster = GSFontMaster()
    font.masters.insert(0, new_fontMaster)
    assert num_layers == len(glyph.layers)
    assert {l.layerId for l in glyph.layers} == {l.layerId for l in glyph.layers.values()}
    assert [l.layerId for l in glyph.layers] != [l.layerId for l in glyph.layers.values()]


def test_name(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    assert isinstance(glyph.name, str)
    value = glyph.name
    glyph.name = "Ə"
    assert glyph.name == "Ə"
    glyph.name = value


def test_unicode(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    assert isinstance(glyph.unicode, str)
    value = glyph.unicode
    # TODO:
    # glyph.unicode = "004a"
    # assert glyph.unicode == "004A"
    glyph.unicode = "004B"
    assert glyph.unicode == "004B"
    glyph.unicode = value


def test_string(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    assert glyph.string == "ä"


def test_id(file_path):
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


def test_horiz_kerningGroup(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    for group in ["leftKerningGroup", "rightKerningGroup"]:
        assert isinstance(getattr(glyph, group), str)
        value = getattr(glyph, group)
        setattr(glyph, group, "ä")
        assert getattr(glyph, group) == "ä"
        setattr(glyph, group, value)


def test_horiz_metricsKey(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    for group in ["leftMetricsKey", "rightMetricsKey"]:
        if getattr(glyph, group) is not None:
            assert isinstance(getattr(glyph, group), str)
        value = getattr(glyph, group)
        setattr(glyph, group, "ä")
        assert getattr(glyph, group) == "ä"
        setattr(glyph, group, value)


def test_export(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    assert isinstance(glyph.export, bool)
    value = glyph.export
    glyph.export = not glyph.export
    assert glyph.export == (not value)
    glyph.export = value


def test_color_glyph(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    if glyph.color is not None:
        assert isinstance(glyph.color, int)
    value = glyph.color
    glyph.color = 5
    assert glyph.color == 5
    glyph.color = value


def test_note_1(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    if glyph.note is not None:
        assert isinstance(glyph.note, str)
    value = glyph.note
    glyph.note = "ä"
    assert glyph.note == "ä"
    glyph.note = value

# TODO
# masterCompatible


def test_userData_1(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    # self.assertIsNone(glyph.userData)
    amount = len(glyph.userData)
    var1 = "abc"
    var2 = "def"
    glyph.userData["unitTestValue"] = var1
    assert glyph.userData["unitTestValue"] == var1
    glyph.userData["unitTestValue"] = var2
    assert glyph.userData["unitTestValue"] == var2
    del glyph.userData["unitTestValue"]
    assert glyph.userData.get("unitTestValue") is None
    assert len(glyph.userData) == amount


def test_smart_component_axes(file_path):
    font = GSFont(file_path)
    shoulder = font.glyphs["_part.shoulder"]
    axes = shoulder.smartComponentAxes
    assert axes is not None
    crotch_depth, shoulder_width = axes
    assert isinstance(crotch_depth, GSSmartComponentAxis)
    assert "crotchDepth" == crotch_depth.name
    assert 0 == crotch_depth.topValue
    assert -100 == crotch_depth.bottomValue
    assert isinstance(shoulder_width, GSSmartComponentAxis)
    assert "shoulderWidth" == shoulder_width.name
    assert 100 == shoulder_width.topValue
    assert 0 == shoulder_width.bottomValue

# TODO
# lastChange


# GSLayerFromFileTest
# def setUp(self):
#     super().setUp()
#     self.glyph = self.font.glyphs["a"]
#     self.layer = self.glyph.layers[0]


def test_repr(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    assert layer.__repr__() is not None


def test_repr_orphan_glyph(file_path):
    # https://github.com/googlefonts/glyphsLib/issues/1014
    layer = GSLayer()
    assert layer.parent is None  # orphan layer

    expected = '<GSLayer 0x00> "" (orphan)'
    assert prune_repr(layer) == expected

    layer.layerId = layer.associatedMasterId = "layer-0"
    assert layer.isMasterLayer
    assert prune_repr(layer) == expected

    parent = GSGlyph("orphan")
    parent.layers.append(layer)
    assert layer.parent == parent  # no longer orphan layer
    assert parent.parent is None  # but still orphan glyph

    # this should not crash with
    #   AttributeError: 'NoneType' object has no attribute 'masterForId'
    assert prune_repr(layer) == expected


def test_parent_layer(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    assert layer.parent is glyph
    assert layer._background.parent is glyph


def test_name_layer(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    assert isinstance(layer.name, str)


def test_associatedMasterId(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    assert layer.associatedMasterId == font.masters[0].id
    assert layer.layerId == font.masters[0].id


def test_color_layer(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    assert layer.color == 7


def test_components(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    assert layer.components is not None
    assert isinstance(layer.components, LayerComponentsProxy)
    # assert len(layer.components) >= 1
    assert len(layer.components) == 2
    # for component in layer.components:
    #     assert isinstance(component, GSComponent)
    #     assert component.parent == layer
    amount = len(layer.components)
    component = GSComponent()
    component.componentName = "A"
    layer.components.append(component)
    assert component.parent == layer
    assert len(layer.components) == (amount + 1)
    del layer.components[-1]
    assert len(layer.components) == amount
    layer.components.extend([component])
    assert len(layer.components) == (amount + 1)
    layer.components.remove(component)
    assert len(layer.components) == amount


def test_guides(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    assert isinstance(layer.guides, LayerGuideLinesProxy)
    for guide in layer.guides:
        assert guide.parent == layer
    layer.guides = []
    assert len(layer.guides) == 0
    newGuide = GSGuide()
    newGuide.position = Point("{100, 100}")
    newGuide.angle = -10.0
    amount = len(layer.guides)
    layer.guides.append(newGuide)
    assert newGuide.parent == layer
    assert layer.guides[0].__repr__() is not None
    assert len(layer.guides) == (amount + 1)
    del layer.guides[0]
    assert len(layer.guides) == amount


def test_annotations(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    # assert layer.annotations == []
    assert len(layer.annotations) == 0
    newAnnotation = GSAnnotation()
    newAnnotation.type = TEXT
    newAnnotation.text = "This curve is ugly!"
    layer.annotations.append(newAnnotation)
    # TODO position.x, position.y
    # assert layer.annotations[0].__repr__() is not None
    assert len(layer.annotations) == 1
    del layer.annotations[0]
    assert len(layer.annotations) == 0
    newAnnotation1 = GSAnnotation()
    newAnnotation1.type = ARROW
    newAnnotation2 = GSAnnotation()
    newAnnotation2.type = CIRCLE
    newAnnotation3 = GSAnnotation()
    newAnnotation3.type = PLUS
    layer.annotations.extend([newAnnotation1, newAnnotation2, newAnnotation3])
    assert layer.annotations[-3] == newAnnotation1
    assert layer.annotations[-2] == newAnnotation2
    assert layer.annotations[-1] == newAnnotation3
    newAnnotation = GSAnnotation()
    newAnnotation = copy.copy(newAnnotation)
    newAnnotation.type = MINUS
    layer.annotations.insert(0, newAnnotation)
    assert layer.annotations[0] == newAnnotation
    layer.annotations.remove(layer.annotations[0])
    layer.annotations.remove(layer.annotations[-1])
    layer.annotations.remove(layer.annotations[-1])
    layer.annotations.remove(layer.annotations[-1])
    assert len(layer.annotations) == 0


def test_hints_from_file(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["A"]
    layer = glyph.layers[1]

    assert len(layer.hints) == 2
    first, second = layer.hints
    assert isinstance(first, GSHint)
    assert first.horizontal
    assert isinstance(first.originNode, GSNode)
    first_origin_node = layer.paths[1].nodes[1]
    assert first_origin_node == first.originNode

    assert isinstance(second, GSHint)
    second_target_node = layer.paths[0].nodes[4]
    assert second_target_node == second.targetNode


def test_hints(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    # layer.hints = []
    assert len(layer.hints) == 0
    newHint = GSHint()
    newHint = copy.copy(newHint)
    newHint.originNode = layer.paths[0].nodes[0]
    newHint.targetNode = layer.paths[0].nodes[1]
    newHint.type = PS_STEM
    layer.hints.append(newHint)
    assert layer.hints[0].__repr__() is not None
    assert len(layer.hints) == 1
    del layer.hints[0]
    assert len(layer.hints) == 0
    newHint1 = GSHint()
    newHint1.originNode = layer.paths[0].nodes[0]
    newHint1.targetNode = layer.paths[0].nodes[1]
    newHint1.type = PS_STEM
    newHint2 = GSHint()
    newHint2.originNode = layer.paths[0].nodes[0]
    newHint2.targetNode = layer.paths[0].nodes[1]
    newHint2.type = PS_STEM
    layer.hints.extend([newHint1, newHint2])
    newHint = GSHint()
    newHint.originNode = layer.paths[0].nodes[0]
    newHint.targetNode = layer.paths[0].nodes[1]
    assert layer.hints[-2] == newHint1
    assert layer.hints[-1] == newHint2
    layer.hints.insert(0, newHint)
    assert layer.hints[0] == newHint
    layer.hints.remove(layer.hints[0])
    layer.hints.remove(layer.hints[-1])
    layer.hints.remove(layer.hints[-1])
    assert len(layer.hints) == 0


def test_anchors(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    amount = len(layer.anchors)
    assert len(layer.anchors) == 3
    for anchor in layer.anchors:
        assert anchor.parent == layer
    if layer.anchors["top"]:
        oldPosition = layer.anchors["top"].position
    else:
        oldPosition = None
    layer.anchors["top"] = GSAnchor()
    assert len(layer.anchors) >= 1
    assert layer.anchors["top"].__repr__() is not None
    layer.anchors["top"].position = Point("{100, 100}")
    # anchor = copy.copy(layer.anchors['top'])
    del layer.anchors["top"]
    layer.anchors["top"] = GSAnchor()
    assert amount == len(layer.anchors)
    layer.anchors["top"].position = oldPosition
    assert isinstance(layer.anchors["top"].name, str)
    newAnchor1 = GSAnchor()
    newAnchor1.name = "testPosition1"
    newAnchor2 = GSAnchor()
    newAnchor2.name = "testPosition2"
    layer.anchors.extend([newAnchor1, newAnchor2])
    assert layer.anchors["testPosition1"] == newAnchor1
    assert layer.anchors["testPosition2"] == newAnchor2
    newAnchor3 = GSAnchor()
    newAnchor3.name = "testPosition3"
    layer.anchors.append(newAnchor3)
    assert layer.anchors["testPosition3"] == newAnchor3
    layer.anchors.remove(layer.anchors["testPosition3"])
    layer.anchors.remove(layer.anchors["testPosition2"])
    layer.anchors.remove(layer.anchors["testPosition1"])
    assert amount == len(layer.anchors)

# TODO layer.paths

# TODO
# selection

# TODO
# LSB, RSB, TSB, BSB, width


def test_metricsKeys(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    assert layer.leftMetricsKey is None
    assert layer.rightMetricsKey is None
    assert layer.widthMetricsKey is None

# TODO: bounds, selectionBounds


def test_background(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    assert "GSBackgroundLayer" in layer.background.__repr__()
    assert layer is layer.background.foreground
    assert layer.parent is layer.background.parent


def test_backgroundImage(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    # The selected layer (0 of glyph 'a') doesn't have one
    assert layer.backgroundImage is None

    glyph = font.glyphs["A"]
    layer = glyph.layers[0]
    image = layer.backgroundImage
    assert isinstance(image, GSBackgroundImage)
    # Values from the file
    assert "A.jpg" == image.path
    assert [0.0, 0.0, 489.0, 637.0] == list(image.crop)
    # Default values
    assert 50 == image.alpha
    assert [1, 0, 0, 1, 0, 0] == image.transform.value
    assert False is image.locked

    # Test documented behaviour of "alpha"
    image.alpha = 10
    assert 10 == image.alpha
    image.alpha = 9
    assert 50 == image.alpha
    image.alpha = 100
    assert 100 == image.alpha
    image.alpha = 101
    assert 50 == image.alpha

# TODO?
# bezierPath, openBezierPath, completeBezierPath, completeOpenBezierPath?


def test_userData_layer(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]

    # self.assertDict(layer.userData)
    layer.userData["Hallo"] = "Welt"
    assert layer.userData["Hallo"] == "Welt"
    assert "Hallo" in layer.userData


def test_smartComponentPoleMapping(file_path):
    # http://docu.glyphsapp.com/#smartComponentPoleMapping
    # Read some data from the file
    font = GSFont(file_path)
    shoulder = font.glyphs["_part.shoulder"]
    for layer in shoulder.layers:
        if layer.name == "NarrowShoulder":
            mapping = layer.smartComponentPoleMapping
            assert mapping is not None
            # crotchDepth is at the top pole
            assert 2 == mapping["crotchDepth"]
            # shoulderWidth is at the bottom pole
            assert 1 == mapping["shoulderWidth"]

    # Exercise the getter/setter
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    assert isinstance(layer.smartComponentPoleMapping, dict)
    assert "crotchDepth" not in layer.smartComponentPoleMapping
    layer.smartComponentPoleMapping["crotchDepth"] = 2
    assert "crotchDepth" in layer.smartComponentPoleMapping
    layer.smartComponentPoleMapping = {"shoulderWidth": 1}
    assert "crotchDepth" not in layer.smartComponentPoleMapping
    assert 1 == layer.smartComponentPoleMapping["shoulderWidth"]

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


# GSComponentFromFileTest
# def setUp(self):
#     super().setUp()
#     self.glyph = self.font.glyphs["adieresis"]
#     self.layer = self.glyph.layers[0]
#     self.component = self.layer.components[0]

def test_repr_component(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    assert component.__repr__() is not None
    assert prune_repr(component) == '<GSComponent 0x00> "a" x=0.0 y=0.0'


def test_delete_and_add(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]

    assert len(layer.components) == 2
    layer.components = []
    assert len(layer.components) == 0
    layer.components.append(GSComponent("a"))
    assert layer.components[0].__repr__() is not None
    assert len(layer.components) == 1
    layer.components.append(GSComponent("dieresis"))
    assert len(layer.components) == 2
    layer.components = [GSComponent("a"), GSComponent("dieresis")]
    assert len(layer.components) == 2
    layer.components = []
    layer.components.extend([GSComponent("a"), GSComponent("dieresis")])
    assert len(layer.components) == 2
    newComponent = GSComponent("dieresis")
    layer.components.insert(0, newComponent)
    assert newComponent == layer.components[0]
    layer.components.remove(layer.components[0])
    assert len(layer.components) == 2


def test_position(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    assert isinstance(component.position, Point)


def test_componentName(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    assert isinstance(component.componentName, str)


def test_component(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    assert isinstance(component.component, GSGlyph)


def test_rotation(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    assert isinstance(component.rotation, (float, int))


def test_transform(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    assert isinstance(component.transform, Transform)
    assert len(component.transform.value) == 6


def test_bounds(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    assert isinstance(component.bounds, Rect)
    bounds = component.bounds
    assert bounds.origin.x == 80
    assert bounds.origin.y == -10
    assert bounds.size.width == 289
    assert bounds.size.height == 490


def test_moreBounds(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    component.scale = 1.1
    bounds = component.bounds
    assert bounds.origin.x == 88
    assert bounds.origin.y == -11
    assert round(bounds.size.width * 10) == round(317.9 * 10)
    assert round(bounds.size.height * 10) == round(539 * 10)

# def test_automaticAlignment(file_path):
#     self.assertBool(self.component.automaticAlignment)


def test_anchor(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["adieresis"]
    layer = glyph.layers[0]
    component = layer.components[0]
    assert isinstance(component.anchor, str)


def test_smartComponentValues(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["h"]
    layer = glyph.layers[0]
    stem, shoulder = layer.components
    assert 100 == stem.smartComponentValues["height"]
    assert -80.20097 == shoulder.smartComponentValues["crotchDepth"]

    assert "shoulderWidth" not in shoulder.smartComponentValues
    assert "somethingElse" not in shoulder.smartComponentValues

# bezierPath?
# componentLayer()


class GSGuideTest(unittest.TestCase):
    def test_repr(self):
        guide = GSGuide()
        assert prune_repr(guide) == "<GSGuide 0x00> x=0.0 y=0.0 angle=0.0"


# GSAnchorFromFileTest
# def setUp(self):
#     super().setUp()
#     self.glyph = self.font.glyphs["a"]
#     self.layer = self.glyph.layers[0]
#     self.anchor = self.layer.anchors[0]

def test_repr_anchor(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    anchor = layer.anchors[0]
    assert prune_repr(anchor) == '<GSAnchor 0x00> "bottom" x=218.0 y=0.0'


def test_name_anchor(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    anchor = layer.anchors[0]

    assert isinstance(anchor.name, str)


def test_position_anchor(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    anchor = layer.anchors[0]
    assert isinstance(anchor.position, Point)
    assert anchor.position == Point(218, 0)


# GSPathFromFileTest
# def setUp(self):
#     super().setUp()
#     self.glyph = self.font.glyphs["a"]
#     self.layer = self.glyph.layers[0]
#     self.path = self.layer.paths[0]

def test_proxy(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    amount = len(layer.paths)
    pathCopy1 = copy.copy(path)
    layer.paths.append(pathCopy1)
    pathCopy2 = copy.copy(pathCopy1)
    layer.paths.extend([pathCopy2])
    assert layer.paths[-2] == pathCopy1
    assert layer.paths[-1] == pathCopy2
    pathCopy3 = copy.copy(pathCopy2)
    layer.paths.insert(0, pathCopy3)
    assert layer.paths[0] == pathCopy3
    layer.paths.remove(layer.paths[0])
    layer.paths.remove(layer.paths[-1])
    layer.paths.remove(layer.paths[-1])
    assert amount == len(layer.paths)


def test_parent_path(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]

    assert path.parent is layer


def test_nodes(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]

    assert path.nodes is not None
    assert len(path.nodes) == 44
    for node in path.nodes:
        assert node.parent is path
    amount = len(path.nodes)
    newNode = GSNode(Point(100, 100))
    path.nodes.append(newNode)
    assert newNode == path.nodes[-1]
    del path.nodes[-1]
    newNode = GSNode(Point(20, 20))
    path.nodes.insert(0, newNode)
    assert newNode == path.nodes[0]
    path.nodes.remove(path.nodes[0])
    newNode1 = GSNode(Point(10, 10))
    newNode2 = GSNode(Point(20, 20))
    path.nodes.extend([newNode1, newNode2])
    assert newNode1 == path.nodes[-2]
    assert newNode2 == path.nodes[-1]
    del path.nodes[-2]
    del path.nodes[-1]
    assert amount == len(path.nodes)


def test_node_position(file_path):
    n = GSNode()
    n.position = Point(10, 10)
    assert n.position.x == 10
    n.position = (20, 20)
    assert n.position.x == 20

# TODO: GSPath.closed

# bezierPath?

# TODO:
# addNodesAtExtremes()
# applyTransform()


def test_applyTransform_translate(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]

    pathCopy = copy.copy(path)
    pathCopy.applyTransform((1, 0, 0, 1, 50, 25))
    expected = ((402, 172), (402, 93), (364, 32), (262, 32))
    for i, pt in enumerate(expected):
        assert pathCopy.nodes[i].position.x == pt[0]
        assert pathCopy.nodes[i].position.y == pt[1]


def test_applyTransform_translate_scale(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]

    pathCopy = copy.copy(path)
    pathCopy.applyTransform((0.9, 0, 0, 1.2, 50, 25))
    expected = ((366.8, 201.4), (366.8, 106.6), (332.6, 33.4), (240.8, 33.4))
    for i, pt in enumerate(expected):
        assert abs(pathCopy.nodes[i].position.x - pt[0]) < 0.01
        assert abs(pathCopy.nodes[i].position.y - pt[1]) < 0.01


def test_applyTransform_skew(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    pathCopy = copy.copy(path)
    pathCopy.applyTransform((1, 0.1, 0.2, 1, 0, 0))
    expected = ((381.4, 182.2), (365.6, 103.2), (315.4, 38.4), (213.4, 28.2))
    for i, pt in enumerate(expected):
        assert abs(pathCopy.nodes[i].position.x - pt[0]) < 0.01
        assert abs(pathCopy.nodes[i].position.y - pt[1]) < 0.01


def test_direction(file_path: str):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    assert glyph is not None
    layer = glyph.layers[0]
    path = layer.paths[0]
    assert path.direction == -1


def test_segments(file_path: str):
    font = GSFont(file_path)
    glyph: Optional[GSGlyph] = font.glyphs["a"]
    assert glyph is not None
    layer: GSLayer = glyph.layers[0]
    path: GSPath = layer.paths[0]
    oldSegments = path.segments
    assert len(path.segments) == 20
    path.reverse()
    assert len(path.segments) == 20
    assert oldSegments[0].nodes[0] == path.segments[0].nodes[0]


def test_segments_2(file_path):
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
    assert len(p.segments) == 4


def test_segments_3(file_path):
    p = GSPath()
    p.nodes = [
        GSNode((327, 185), "offcurve"),
        GSNode((299, 210), "offcurve"),
        GSNode((297, 266), "curve"),
        GSNode((294, 351), "offcurve"),
        GSNode((297, 434), "qcurve"),
        GSNode((299, 490), "offcurve"),
        GSNode((328, 515), "offcurve"),
        GSNode((371, 515), "curve"),
        GSNode((414, 515), "offcurve"),
        GSNode((443, 490), "offcurve"),
        GSNode((445, 434), "curve"),
        GSNode((448, 351), "offcurve"),
        GSNode((445, 266), "qcurve"),
        GSNode((443, 210), "offcurve"),
        GSNode((415, 185), "offcurve"),
        GSNode((371, 185), "curve"),
    ]
    assert len(p.segments) == 6


def test_segments_4(file_path):
    p = GSPath()
    p.nodes = [
        GSNode((327, 185), "line"),
        GSNode((297, 266), "line"),
        GSNode((371, 185), "line"),
    ]
    assert len(p.segments) == 3
    p.closed = False
    assert len(p.segments) == 2
    assert p.segments[0][0].x == 327


def test_segments_5(file_path):
    p = GSPath()
    p.nodes = [
        GSNode((250, 2000), "offcurve"),
        GSNode((250, 1000), "offcurve"),
        GSNode((250, 900), "curve"),
        GSNode((250, 500), "offcurve"),
        GSNode((250, 50), "offcurve"),
        GSNode((250, 0), "curve"),
        GSNode((250, 1700), "curve"),
        # Yes, this is bad construction but we shouldn't
        # infinite loop
    ]
    assert len(p.segments) == 3


def test_bounds_path(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    bounds = path.bounds
    assert bounds.origin.x == 80
    assert bounds.origin.y == -10
    assert bounds.size.width == 289
    assert bounds.size.height == 490


# GSNodeFromFileTest
# def setUp(file_path):
#     super().setUp()
#     self.glyph = self.font.glyphs["a"]
#     self.layer = self.glyph.layers[0]
#     self.path = self.layer.paths[0]
#     self.node = self.path.nodes[0]

def test_repr_node(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    assert node.__repr__() is not None


def test_position_node(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    assert isinstance(node.position, Point)


def test_type(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    assert node.type in [LINE, CURVE, OFFCURVE]


def test_smooth(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    assert node.smooth


def test_index(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    assert isinstance(node.index, int)
    assert node.index == 0
    assert path.nodes[-1].index == 43


def test_nextNode(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    assert isinstance(path.nodes[-1].nextNode, GSNode)
    assert path.nodes[-1].nextNode is path.nodes[0]


def test_prevNode(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    assert isinstance(node.prevNode, GSNode)
    assert node.prevNode is path.nodes[-1]


def test_name_node(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    assert node.name == "Hello"


def test_userData_node(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    assert "1" == node.userData["rememberToMakeCoffee"]


def test_makeNodeFirst(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]

    oldAmount = len(path.nodes)
    oldSecondNode = path.nodes[3]
    path.nodes[3].makeNodeFirst()
    assert oldAmount == len(path.nodes)
    assert oldSecondNode is path.nodes[0]


def test_toggleConnection(file_path):
    font = GSFont(file_path)
    glyph = font.glyphs["a"]
    layer = glyph.layers[0]
    path = layer.paths[0]
    node = path.nodes[0]
    oldConnection = node.smooth
    node.toggleConnection()
    assert oldConnection != node.smooth


class GSCustomParameterTest(unittest.TestCase):
    def test_plistValue_string(self):
        test_string = "Some Value"
        param = GSCustomParameter("New Parameter", test_string)
        assert param.plistValue() == '{\nname = "New Parameter";\nvalue = "Some Value";\n}'

    def test_plistValue_list(self):
        test_list = [1, 2.5, {"key1": "value1"}]
        param = GSCustomParameter("New Parameter", test_list)
        assert param.plistValue() == '{\nname = "New Parameter";\nvalue = (\n1,\n2.5,'"\n{\nkey1 = value1;\n}\n);\n}"

    def test_plistValue_dict(self):
        test_dict = {"key1": "value1", "key2": "value2"}
        param = GSCustomParameter("New Parameter", test_dict)
        assert param.plistValue() == '{\nname = "New Parameter";\nvalue = {\nkey1 = value1;'"\nkey2 = value2;\n};\n}"


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


class SegmentTest(unittest.TestCase):
    def test_bbox_bug(self):
        seg = GSPathSegment(
            [Point(529, 223), Point(447, 456), Point(285, 177), Point(521, 367)]
        )
        bbox = seg.bbox()
        self.assertAlmostEqual(bbox[0], 398.1222655016518)
        self.assertAlmostEqual(bbox[1], 223)
        self.assertAlmostEqual(bbox[2], 529)
        self.assertAlmostEqual(bbox[3], 367)


# FontGlyphsProxyTest
# def setUp(file_path):
#     self.font = GSFont(TESTFILE_PATHV3)

def test_remove_glyphs(file_path):
    font = GSFont(file_path)
    assert font.glyphs[0].name == "A"
    del font.glyphs[0]
    assert font.glyphs[0].name != "A"

    assert font.glyphs["Adieresis"].name == "Adieresis"
    del font.glyphs["Adieresis"]
    assert font.glyphs["Adieresis"] is None

    with pytest.raises(KeyError):
        del font.glyphs["xxxzzz"]

    with pytest.raises(KeyError):
        del font.glyphs[font]


# FontClassesProxyTest
# def setUp(self):
#     self.font = GSFont(TESTFILE_PATHV3)

def test_indexing_by_name(file_path):
    font = GSFont(file_path)
    assert "Languagesystems" in font.featurePrefixes
    assert "c2sc_source" in font.classes
    assert "aalt" in font.features

    assert "XXXX" not in font.featurePrefixes
    assert "XXXX" not in font.classes
    assert "XXXX" not in font.features

    assert font.featurePrefixes["Languagesystems"] in font.featurePrefixes
    assert font.classes["c2sc_source"] in font.classes
    assert font.features["aalt"] in font.features


if __name__ == "__main__":
    unittest.main()
