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


from __future__ import (
    print_function, division, absolute_import, unicode_literals)

import os
import datetime
import unittest
import copy
from fontTools.misc.py23 import unicode

import glyphsLib
from glyphsLib.classes import (
    GSFont, GSFontMaster, GSInstance, GSCustomParameter, GSGlyph, GSLayer,
    GSAnchor, GSComponent, GSAlignmentZone, GSClass, GSFeature,
    GSFeaturePrefix, GSGuideLine
)
from glyphsLib.types import point

TESTFILE_PATH = os.path.join(
    os.path.dirname(__file__),
    os.path.join('data', 'GlyphsUnitTestSans.glyphs')
)


def generate_minimal_font():
    font = GSFont()
    font.appVersion = 895
    font.date = datetime.datetime.today()
    font.familyName = 'MyFont'

    master = GSFontMaster()
    master.ascender = 0
    master.capHeight = 0
    master.descender = 0
    master.id = 'id'
    master.xHeight = 0
    font.masters.append(master)

    font.unitsPerEm = 1000
    font.versionMajor = 1
    font.versionMinor = 0

    return font


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
                layer.anchors = getattr(layer, 'anchors', [])
                anchor = GSAnchor()
                anchor.name = anchorname
                anchor.position = (x, y)
                layer.anchors.append(anchor)


def add_component(font, glyphname, componentname,
                  transform):
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


class GSFontTest(unittest.TestCase):
    def test_init(self):
        font = GSFont()
        self.assertEqual(font.familyName, "Unnamed font")
        self.assertEqual(font.versionMajor, 1)
        self.assertEqual(font.versionMinor, 0)
        self.assertEqual(font.appVersion, 0)

        self.assertEqual(len(font.glyphs), 0)
        self.assertEqual(len(font.masters), 0)
        self.assertEqual(font.masters, [])
        self.assertEqual(len(font.instances), 0)
        self.assertEqual(font.instances, [])
        self.assertEqual(len(font.customParameters), 0)

    def test_repr(self):
        font = GSFont()
        self.assertEqual(repr(font), '<GSFont "Unnamed font">')


class GSFontFromFileTest(unittest.TestCase):
    def setUp(self):
        with open(TESTFILE_PATH) as fp:
            self.font = glyphsLib.load(fp)

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
        by_name = font.glyphs['adieresis']
        by_unicode_char = font.glyphs['ä']
        by_unicode_value = font.glyphs['00E4']
        by_unicode_value_lowercased = font.glyphs['00e4']
        self.assertEqual(by_index, by_name)
        self.assertEqual(by_unicode_char, by_name)
        self.assertEqual(by_unicode_value, by_name)
        self.assertEqual(by_unicode_value_lowercased, by_name)

    def test_classes(self):
        font = self.font
        font.classes = []
        amount = len(font.classes)
        font.classes.append(GSClass('uppercaseLetters', 'A'))
        self.assertIsNotNone(font.classes[-1].__repr__())
        self.assertEqual(len(font.classes), 1)
        self.assertIn('<GSClass "uppercaseLetters">', str(font.classes))
        # TODO
        # self.assertIn('A', font.classes['uppercaseLetters'].code)
        font.classes.remove(font.classes[0])
        # TODO
        # del(font.classes['uppercaseLetters'])
        newClass1 = GSClass('uppercaseLetters1', 'A')
        newClass2 = GSClass('uppercaseLetters2', 'A')
        font.classes.extend([newClass1, newClass2])
        self.assertEqual(newClass1, font.classes[-2])
        self.assertEqual(newClass2, font.classes[-1])
        newClass = GSClass('uppercaseLetters3', 'A')
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
        font.features.append(GSFeature('liga', 'sub f i by fi;'))
        # TODO
        # self.assertIsNotNone(font.features['liga'].__repr__())
        self.assertEqual(len(font.features), 1)
        # TODO
        # self.assertIn('<GSFeature "liga">', str(font.features))
        # self.assertIn('sub f i by fi;', font.features['liga'].code)
        # del(font.features['liga'])
        del font.features[-1]
        newFeature1 = GSFeature('liga', 'sub f i by fi;')
        newFeature2 = GSFeature('liga', 'sub f l by fl;')
        font.features.extend([newFeature1, newFeature2])
        self.assertEqual(newFeature1, font.features[-2])
        self.assertEqual(newFeature2, font.features[-1])
        newFeature = GSFeature('liga', 'sub f i by fi;')
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
            GSFeaturePrefix('LanguageSystems', 'languagesystem DFLT dflt;'))
        self.assertIsNotNone(font.featurePrefixes[-1].__repr__())
        self.assertEqual(len(font.featurePrefixes), 1)
        self.assertIn('<GSFeaturePrefix "LanguageSystems">',
                      str(font.featurePrefixes))
        self.assertIn('languagesystem DFLT dflt;',
                      font.featurePrefixes[-1].code)
        # TODO
        # del(font.featurePrefixes['LanguageSystems'])
        del font.featurePrefixes[-1]
        newFeaturePrefix1 = GSFeaturePrefix('LanguageSystems1',
                                            'languagesystem DFLT dflt;')
        newFeaturePrefix2 = GSFeaturePrefix('LanguageSystems2',
                                            'languagesystem DFLT dflt;')
        font.featurePrefixes.extend([newFeaturePrefix1, newFeaturePrefix2])
        self.assertEqual(newFeaturePrefix1, font.featurePrefixes[-2])
        self.assertEqual(newFeaturePrefix2, font.featurePrefixes[-1])
        newFeaturePrefix = GSFeaturePrefix('LanguageSystems3',
                                           'languagesystem DFLT dflt;')
        newFeaturePrefix = copy.copy(newFeaturePrefix)
        font.featurePrefixes.insert(0, newFeaturePrefix)
        self.assertEqual(newFeaturePrefix, font.featurePrefixes[0])
        font.featurePrefixes.remove(font.featurePrefixes[-1])
        font.featurePrefixes.remove(font.featurePrefixes[-1])
        font.featurePrefixes.remove(font.featurePrefixes[0])
        self.assertEqual(len(font.featurePrefixes), amount)

    def test_ints(self):
        attributes = [
            "versionMajor", "versionMajor", "upm", "grid", "gridSubDivision",
        ]
        font = self.font
        for attr in attributes:
            self.assertIsInstance(getattr(font, attr), int)

    def test_strings(self):
        attributes = [
            "copyright", "designer", "designerURL", "manufacturer",
            "manufacturerURL", "familyName",
        ]
        font = self.font
        for attr in attributes:
            self.assertIsInstance(getattr(font, attr), unicode)

    def test_note(self):
        font = self.font
        self.assertIsInstance(font.note, unicode)

    # date
    def test_date(self):
        font = self.font
        self.assertIsInstance(font.date, datetime.datetime)

    def test_kerning(self):
        font = self.font
        self.assertIsInstance(font.kerning, dict)

    def test_userData(self):
        font = self.font
        self.assertIsInstance(font.userData, dict)
        # TODO
        # self.assertIsNone(font.userData["TestData"])
        font.userData["TestData"] = 42
        self.assertEqual(font.userData["TestData"], 42)
        del(font.userData["TestData"])
        # TODO
        # self.assertIsNone(font.userData["TestData"])

    def test_disableNiceNames(self):
        font = self.font
        self.assertIsInstance(font.disablesNiceNames, bool)

    def test_customParameters(self):
        font = self.font
        font.customParameters['trademark'] = \
            'ThisFont is a trademark by MyFoundry.com'
        self.assertIn(font.customParameters['trademark'],
                      'ThisFont is a trademark by MyFoundry.com')
        amount = len(list(font.customParameters))
        newParameter = GSCustomParameter('hello1', 'world1')
        font.customParameters.append(newParameter)
        self.assertEqual(newParameter, list(font.customParameters)[-1])
        del font.customParameters[-1]
        newParameter1 = GSCustomParameter('hello2', 'world2')
        newParameter2 = GSCustomParameter('hello3', 'world3')
        newParameter2 = copy.copy(newParameter2)
        font.customParameters.extend([newParameter1, newParameter2])
        self.assertEqual(newParameter1, list(font.customParameters)[-2])
        self.assertEqual(newParameter2, list(font.customParameters)[-1])
        font.customParameters.remove(list(font.customParameters)[-1])
        font.customParameters.remove(list(font.customParameters)[-1])
        newParameter = GSCustomParameter('hello1', 'world1')
        font.customParameters.insert(0, newParameter)
        self.assertEqual(newParameter, list(font.customParameters)[0])
        font.customParameters.remove(list(font.customParameters)[0])
        self.assertEqual(amount, len(list(font.customParameters)))
        del font.customParameters['trademark']

    def test_selection(self):
        font = self.font
        for glyph in font.glyphs:
            glyph.selected = False
        font.glyphs['a'].selected = True
        self.assertEqual(len(list(font.selection)), 1)
        for glyph in font.glyphs:
            glyph.selected = True
        self.assertEqual(len(list(font.selection)), len(font.glyphs))

    # TODO: selectedLayers, currentText, tabs, currentTab

    # TODO: selectedFontMaster, masterIndex

    def test_filepath(self):
        font = self.font
        # TODO
        # self.assertIsNotNone(font.filepath)
        self.assertIsNone(font.filepath)

    # TODO: tool, tools
    # TODO: save(), close()
    # TODO: setKerningForPair(), kerningForPair(), removeKerningForPair()
    # TODO: updateFeatures()
    # TODO: copy(font)


class GSFontMasterFromFileTest(unittest.TestCase):
    def setUp(self):
        with open(TESTFILE_PATH) as fp:
            self.font = glyphsLib.load(fp)
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
        self.assertIsInstance(obj, float)
        master.weightValue = 0.5
        self.assertEqual(master.weightValue, 0.5)
        obj = old_obj
        self.assertIsInstance(master.weightValue, float)
        self.assertIsInstance(master.widthValue, float)
        self.assertIsInstance(master.customValue, float)
        self.assertIsInstance(master.ascender, float)
        self.assertIsInstance(master.capHeight, float)
        self.assertIsInstance(master.xHeight, float)
        self.assertIsInstance(master.descender, float)
        self.assertIsInstance(master.italicAngle, float)
        for attr in ["weightValue", "widthValue", "customValue", "ascender",
                     "capHeight", "xHeight", "descender", "italicAngle"]:
            value = getattr(master, attr)
            self.assertIsInstance(value, float)
            setattr(master, attr, 0.5)
            self.assertEqual(getattr(master, attr), 0.5)
            setattr(master, attr, value)
        self.assertIsInstance(master.customName, unicode)

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

        # guideLines
        self.assertIsInstance(master.guideLines, list)
        master.guideLines = []
        self.assertEqual(len(master.guideLines), 0)
        newGuide = GSGuideLine()
        newGuide.position = point("{100, 100}")
        newGuide.angle = -10.0
        master.guideLines.append(newGuide)
        self.assertIsNotNone(master.guideLines[0].__repr__())
        self.assertEqual(len(master.guideLines), 1)
        del master.guideLines[0]
        self.assertEqual(len(master.guideLines), 0)

        # guides
        self.assertIsInstance(master.guides, list)
        master.guides = []
        self.assertEqual(len(master.guides), 0)
        newGuide = GSGuideLine()
        newGuide.position = point("{100, 100}")
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
        master.customParameters['trademark'] = \
            'ThisFont is a trademark by MyFoundry.com'
        self.assertGreaterEqual(len(master.customParameters), 1)
        del(master.customParameters['trademark'])


class GSAlignmentZoneFromFileTest(unittest.TestCase):

    def setUp(self):
        with open(TESTFILE_PATH) as fp:
            self.font = glyphsLib.load(fp)
        self.master = self.font.masters[0]

    def test_attributes(self):
        master = self.master
        for i, zone in enumerate([
                (800, 10),
                (700, 10),
                (470, 10),
                (0, -10),
                (-200, -10)]):
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


class GSInstanceFromFileTest(unittest.TestCase):

    def setUp(self):
        with open(TESTFILE_PATH) as fp:
            self.font = glyphsLib.load(fp)
        self.instance = self.font.instances[0]

    def test_attributes(self):
        instance = self.instance
        self.assertIsNotNone(instance.__repr__())

        # TODO: active
        # self.assertIsInstance(instance.active, bool)

        # name
        self.assertIsInstance(instance.name, unicode)

        # weight
        self.assertIsInstance(instance.weight, unicode)

        # width
        self.assertIsInstance(instance.width, unicode)

        # weightValue
        # widthValue
        # customValue
        for attr in ["weightValue", "widthValue", "customValue"]:
            value = getattr(instance, attr)
            self.assertIsInstance(value, float)
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
        self.assertIsInstance(instance.linkStyle, unicode)

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
            # self.assertIsInstance(getattr(instance, attr), unicode)
            if not hasattr(instance, attr):
                print("instance does not have %s" % attr)
                if (hasattr(instance, "parent") and
                        hasattr(instance.parent, attr)):
                    value = getattr(instance.parent)
                    print(value, type(value))

        # customParameters
        instance.customParameters['trademark'] = \
            'ThisFont is a trademark by MyFoundry.com'
        self.assertGreaterEqual(len(instance.customParameters), 1)
        del(instance.customParameters['trademark'])

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


class GSGlyphFromFileTest(unittest.TestCase):

    def setUp(self):
        with open(TESTFILE_PATH) as fp:
            self.font = glyphsLib.load(fp)
        self.glyph = self.font.glyphs['a']

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
        newLayer.name = '1'
        glyph.layers.append(newLayer)
        self.assertIn('<GSLayer "1" (a)>', str(glyph.layers[-1]))
        self.assertEqual(newLayer, glyph.layers[-1])
        del glyph.layers[-1]
        newLayer1 = GSLayer()
        newLayer1.name = '2'
        newLayer2 = GSLayer()
        newLayer2.name = '3'
        glyph.layers.extend([newLayer1, newLayer2])
        self.assertEqual(newLayer1, glyph.layers[-2])
        self.assertEqual(newLayer2, glyph.layers[-1])
        newLayer = GSLayer()
        newLayer.name = '4'
        # indices here don't make sense because layer get appended using a UUID
        glyph.layers.insert(0, newLayer)
        # so the latest layer got appended at the end also
        self.assertEqual(newLayer, glyph.layers[-1])
        glyph.layers.remove(glyph.layers[-1])
        glyph.layers.remove(glyph.layers[-1])
        glyph.layers.remove(glyph.layers[-1])
        self.assertEqual(amount, len(glyph.layers))


class GSCustomParameterTest(unittest.TestCase):

    def test_plistValue_string(self):
        test_string = "Some Value"
        param = GSCustomParameter("New Parameter", test_string)
        self.assertEqual(
            param.plistValue(),
            '{\nname = "New Parameter";\nvalue = "Some Value";\n}'
        )

    def test_plistValue_list(self):
        test_list = [
            1,
            2.5,
            {"key1": "value1"},
        ]
        param = GSCustomParameter("New Parameter", test_list)
        self.assertEqual(
            param.plistValue(),
            '{\nname = "New Parameter";\nvalue = (\n1,\n2.5,'
            '\n{\nkey1 = value1;\n}\n);\n}'
        )

    def test_plistValue_dict(self):
        test_dict = {
            "key1": "value1",
            "key2": "value2",
        }
        param = GSCustomParameter("New Parameter", test_dict)
        self.assertEqual(
            param.plistValue(),
            '{\nname = "New Parameter";\nvalue = {\nkey1 = value1;'
            '\nkey2 = value2;\n};\n}'
        )


if __name__ == '__main__':
    unittest.main()
