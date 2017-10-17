# coding=UTF-8
#
# Copyright 2017 Google Inc. All Rights Reserved.
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
import difflib
import os.path
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as etree

import defcon
from fontTools.misc.py23 import open
from glyphsLib.builder.constants import GLYPHS_PREFIX
from glyphsLib.interpolation import (
    build_designspace, set_weight_class, set_width_class, build_stylemap_names
)
from glyphsLib.classes import GSInstance, GSCustomParameter


def makeFamily(familyName):
    m1 = makeMaster(familyName, "Regular", weight=90.0)
    m2 = makeMaster(familyName, "Black", weight=190.0)
    instances = {
        "data": [
            makeInstance("Regular", weight=("Regular", 400, 90)),
            makeInstance("Semibold", weight=("Semibold", 600, 128)),
            makeInstance("Bold", weight=("Bold", 700, 151), is_bold=True),
            makeInstance("Black", weight=("Black", 900, 190)),
        ],
    }
    return [m1, m2], instances


def makeMaster(familyName, styleName, weight=None, width=None):
    m = defcon.Font()
    m.info.familyName, m.info.styleName = familyName, styleName
    if weight is not None:
        m.lib[GLYPHS_PREFIX + "weightValue"] = weight
    if width is not None:
        m.lib[GLYPHS_PREFIX + "widthValue"] = width
    return m


def makeInstance(name, weight=None, width=None, is_bold=None, is_italic=None,
                 linked_style=None):
    inst = GSInstance()
    inst.name = name
    if weight is not None:
        # Glyphs 2.3 stores the instance weight in two to three places:
        # 1. as a textual weightClass (such as “Bold”; no value defaults to
        #    "Regular");
        # 2. (optional) as numeric customParameters.weightClass (such as 700),
        #    which corresponds to OS/2.usWeightClass where 100 means Thin,
        #    400 means Regular, 700 means Bold, and 900 means Black;
        # 3. as numeric interpolationWeight (such as 66.0), which typically is
        #    the stem width but can be anything that works for interpolation
        #    (no value defaults to 100).
        weightName, weightClass, interpolationWeight = weight
        if weightName is not None:
            inst.weightClass = weightName
        if weightClass is not None:
            inst.customParameters["weightClass"] = weightClass
        if interpolationWeight is not None:
            inst.interpolationWeight = interpolationWeight
    if width is not None:
        # Glyphs 2.3 stores the instance width in two places:
        # 1. as a textual widthClass (such as “Condensed”; no value defaults
        #    to "Medium (normal)");
        # 2. as numeric interpolationWidth (such as 79), which typically is
        #    a percentage of whatever the font designer considers “normal”
        #    but can be anything that works for interpolation (no value
        #    defaults to 100).
        widthClass, interpolationWidth = width
        if widthClass is not None:
            inst.widthClass = widthClass
        if interpolationWidth is not None:
            inst.interpolationWidth = interpolationWidth
    # TODO: Support custom axes; need to triple-check how these are encoded in
    # Glyphs files. Glyphs 3 will likely overhaul the representation of axes.
    if is_bold is not None:
        inst.isBold = is_bold
    if is_italic is not None:
        inst.isItalic = is_italic
    if linked_style is not None:
        inst.linkStyle = linked_style
    return inst


class DesignspaceTest(unittest.TestCase):
    def build_designspace(self, masters, instances):
        master_dir = tempfile.mkdtemp()
        try:
            designspace, _ = build_designspace(
                masters, master_dir, os.path.join(master_dir, "out"), instances)
            with open(designspace, mode="r", encoding="utf-8") as f:
                result = f.readlines()
        finally:
            shutil.rmtree(master_dir)
        return result

    def expect_designspace(self, masters, instances, expectedFile):
        actual = self.build_designspace(masters, instances)
        path, _ = os.path.split(__file__)
        expectedPath = os.path.join(path, "data", expectedFile)
        with open(expectedPath, mode="r", encoding="utf-8") as f:
            expected = f.readlines()
        if os.path.sep == '\\':
            # On windows, the test must not fail because of a difference between
            # forward and backward slashes in filname paths.
            # The failure happens because of line 217 of "mutatorMath\ufo\document.py"
            # > pathRelativeToDocument = os.path.relpath(fileName, os.path.dirname(self.path))
            expected = [line.replace('filename="out/', 'filename="out\\') for line in expected]
        if actual != expected:
            for line in difflib.unified_diff(
                    expected, actual,
                    fromfile=expectedPath, tofile="<generated>"):
                sys.stderr.write(line)
            self.fail("*.designspace file is different from expected")

    def test_basic(self):
        masters, instances = makeFamily("DesignspaceTest Basic")
        self.expect_designspace(masters, instances,
                                "DesignspaceTestBasic.designspace")

    def test_inactive_from_exports(self):
        # Glyphs.app recognizes exports=0 as a flag for inactive instances.
        # https://github.com/googlei18n/glyphsLib/issues/129
        masters, instances = makeFamily("DesignspaceTest Inactive")
        for inst in instances["data"]:
            if inst.name != "Semibold":
                inst.exports = False
        self.expect_designspace(masters, instances,
                                "DesignspaceTestInactive.designspace")

    def test_familyName(self):
        masters, instances = makeFamily("DesignspaceTest FamilyName")
        customFamily = makeInstance("Regular", weight=("Bold", 600, 151))
        customFamily.customParameters["familyName"] = "Custom Family"
        instances["data"] = [
            makeInstance("Regular", weight=("Regular", 400, 90)),
            customFamily,
        ]
        self.expect_designspace(masters, instances,
                                "DesignspaceTestFamilyName.designspace")

    def test_fileName(self):
        masters, instances = makeFamily("DesignspaceTest FamilyName")
        customFileName= makeInstance("Regular", weight=("Bold", 600, 151))
        customFileName.customParameters["fileName"] = "Custom FileName"
        instances["data"] = [
            makeInstance("Regular", weight=("Regular", 400, 90)),
            customFileName,
        ]
        self.expect_designspace(masters, instances,
                                "DesignspaceTestFileName.designspace")

    def test_noRegularMaster(self):
        # Currently, fonttools.varLib fails to build variable fonts
        # if the default axis value does not happen to be at the
        # location of one of the interpolation masters.
        # glyhpsLib tries to work around this downstream limitation.
        masters = [
            makeMaster("NoRegularMaster", "Thin", weight=26),
            makeMaster("NoRegularMaster", "Black", weight=190),
        ]
        instances = {"data": [
            makeInstance("Black", weight=("Black", 900, 190)),
            makeInstance("Regular", weight=("Regular", 400, 90)),
            makeInstance("Bold", weight=("Thin", 100, 26)),
        ]}
        doc = etree.fromstringlist(self.build_designspace(masters, instances))
        weightAxis = doc.find('axes/axis[@tag="wght"]')
        self.assertEqual(weightAxis.attrib["minimum"], "100.0")
        self.assertEqual(weightAxis.attrib["default"], "100.0")  # not 400
        self.assertEqual(weightAxis.attrib["maximum"], "900.0")

    def test_postscriptFontName(self):
        master = makeMaster("PSNameTest", "Master")
        thin, black = makeInstance("Thin"), makeInstance("Black")
        instances = {"data": [thin, black]}
        black.customParameters["postscriptFontName"] = "PSNameTest-Superfat"
        d = etree.fromstringlist(self.build_designspace([master], instances))

        def psname(doc, style):
            inst = doc.find('instances/instance[@stylename="%s"]' % style)
            return inst.attrib.get('postscriptfontname')
        self.assertIsNone(psname(d, "Thin"))
        self.assertEqual(psname(d, "Black"), "PSNameTest-Superfat")

    def test_instanceOrder(self):
        # The generated *.designspace file should place instances
        # in the same order as they appear in the original source.
        # https://github.com/googlei18n/glyphsLib/issues/113
        masters, instances = makeFamily("DesignspaceTest InstanceOrder")
        instances["data"] = [
            makeInstance("Black", weight=("Black", 900, 190)),
            makeInstance("Regular", weight=("Regular", 400, 90)),
            makeInstance("Bold", weight=("Bold", 700, 151), is_bold=True),
        ]

        self.expect_designspace(masters, instances,
                                "DesignspaceTestInstanceOrder.designspace")

    def test_twoAxes(self):
        # In NotoSansArabic-MM.glyphs, the regular width only contains
        # parameters for the weight axis. For the width axis, glyphsLib
        # should use 100 as default value (just like Glyphs.app does).
        familyName = "DesignspaceTest TwoAxes"
        masters = [
            makeMaster(familyName, "Regular", weight=90),
            makeMaster(familyName, "Black", weight=190),
            makeMaster(familyName, "Thin", weight=26),
            makeMaster(familyName, "ExtraCond", weight=90, width=70),
            makeMaster(familyName, "ExtraCond Black", weight=190, width=70),
            makeMaster(familyName, "ExtraCond Thin", weight=26, width=70),
        ]
        instances = {
            "data": [
                makeInstance("Thin", weight=("Thin", 100, 26)),
                makeInstance("Regular", weight=("Regular", 400, 90)),
                makeInstance("Semibold", weight=("Semibold", 600, 128)),
                makeInstance("Black", weight=("Black", 900, 190)),
                makeInstance("ExtraCondensed Thin",
                             weight=("Thin", 100, 26),
                             width=("Extra Condensed", 70)),
                makeInstance("ExtraCondensed",
                             weight=("Regular", 400, 90),
                             width=("Extra Condensed", 70)),
                makeInstance("ExtraCondensed Black",
                             weight=("Black", 900, 190),
                             width=("Extra Condensed", 70)),
            ]
        }
        self.expect_designspace(masters, instances,
                                "DesignspaceTestTwoAxes.designspace")

    def test_variationFontOrigin(self):
        # Glyphs 2.4.1 introduced a custom parameter “Variation Font Origin”
        # to specify which master should be considered the origin.
        # https://glyphsapp.com/blog/glyphs-2-4-1-released
        masters = [
            makeMaster("Family", "Thin", weight=26),
            makeMaster("Family", "Regular", weight=100),
            makeMaster("Family", "Medium", weight=111),
            makeMaster("Family", "Black", weight=190),
        ]
        instances = {
            "data": [
                makeInstance("Black", weight=("Black", 900, 190)),
                makeInstance("Medium", weight=("Medium", 444, 111)),
                makeInstance("Regular", weight=("Regular", 400, 100)),
                makeInstance("Thin", weight=("Thin", 100, 26)),
            ],
            "Variation Font Origin": "Medium",
        }
        doc = etree.fromstringlist(self.build_designspace(masters, instances))
        medium = doc.find('sources/source[@stylename="Medium"]')
        self.assertEqual(medium.find("lib").attrib["copy"], "1")
        weightAxis = doc.find('axes/axis[@tag="wght"]')
        self.assertEqual(weightAxis.attrib["default"], "444.0")

    def test_designspace_name(self):
        master_dir = tempfile.mkdtemp()
        try:
            designspace_path, _ = build_designspace(
                [
                    makeMaster("Family Name", "Regular", weight=100),
                    makeMaster("Family Name", "Bold", weight=190),
                ], master_dir, os.path.join(master_dir, "out"), {})
            # no shared base style name, only write the family name
            self.assertEqual(os.path.basename(designspace_path),
                             "FamilyName.designspace")

            designspace_path, _ = build_designspace(
                [
                    makeMaster("Family Name", "Italic", weight=100),
                    makeMaster("Family Name", "Bold Italic", weight=190),
                ], master_dir, os.path.join(master_dir, "out"), {})
            # 'Italic' is the base style; append to designspace name
            self.assertEqual(os.path.basename(designspace_path),
                             "FamilyName-Italic.designspace")
        finally:
            shutil.rmtree(master_dir)


WEIGHT_CLASS_KEY = GLYPHS_PREFIX + "weightClass"
WIDTH_CLASS_KEY = GLYPHS_PREFIX + "widthClass"


class SetWeightWidthClassesTest(unittest.TestCase):

    def test_no_weigth_class(self):
        ufo = defcon.Font()
        # name here says "Bold", however no excplit weightClass
        # is assigned
        set_weight_class(ufo, makeInstance("Bold"))
        # the default OS/2 weight class is set
        self.assertEqual(ufo.info.openTypeOS2WeightClass, 400)
        # non-empty value is stored in the UFO lib even if same as default
        self.assertEqual(ufo.lib[WEIGHT_CLASS_KEY], "Regular")

    def test_weight_class(self):
        ufo = defcon.Font()
        data = makeInstance(
            "Bold",
            weight=("Bold", None, 150)
        )

        set_weight_class(ufo, data)

        self.assertEqual(ufo.info.openTypeOS2WeightClass, 700)
        self.assertEqual(ufo.lib[WEIGHT_CLASS_KEY], "Bold")

    def test_explicit_default_weight(self):
        ufo = defcon.Font()
        data = makeInstance(
            "Regular",
            weight=("Regular", None, 100)
        )

        set_weight_class(ufo, data)
        # the default OS/2 weight class is set
        self.assertEqual(ufo.info.openTypeOS2WeightClass, 400)
        # non-empty value is stored in the UFO lib even if same as default
        self.assertEqual(ufo.lib[WEIGHT_CLASS_KEY], "Regular")

    def test_no_width_class(self):
        ufo = defcon.Font()
        # no explicit widthClass set, instance name doesn't matter
        set_width_class(ufo, makeInstance("Normal"))
        # the default OS/2 width class is set
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 5)
        # non-empty value is stored in the UFO lib even if same as default
        self.assertEqual(ufo.lib[WIDTH_CLASS_KEY], "Medium (normal)")

    def test_width_class(self):
        ufo = defcon.Font()
        data = makeInstance(
            "Condensed",
            width=("Condensed", 80)
        )

        set_width_class(ufo, data)

        self.assertEqual(ufo.info.openTypeOS2WidthClass, 3)
        self.assertEqual(ufo.lib[WIDTH_CLASS_KEY], "Condensed")

    def test_explicit_default_width(self):
        ufo = defcon.Font()
        data = makeInstance(
            "Regular",
            width=("Medium (normal)", 100)
        )

        set_width_class(ufo, data)
        # the default OS/2 width class is set
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 5)
        # non-empty value is stored in the UFO lib even if same as default
        self.assertEqual(ufo.lib[WIDTH_CLASS_KEY], "Medium (normal)")

    def test_weight_and_width_class(self):
        ufo = defcon.Font()
        data = makeInstance(
            "SemiCondensed ExtraBold",
            weight=("ExtraBold", None, 160),
            width=("SemiCondensed", 90)
        )

        set_weight_class(ufo, data)
        set_width_class(ufo, data)

        self.assertEqual(ufo.info.openTypeOS2WeightClass, 800)
        self.assertEqual(ufo.lib[WEIGHT_CLASS_KEY], "ExtraBold")
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 4)
        self.assertEqual(ufo.lib[WIDTH_CLASS_KEY], "SemiCondensed")

    def test_unknown_weight_class(self):
        ufo = defcon.Font()
        # "DemiLight" is not among the predefined weight classes listed in
        # Glyphs.app/Contents/Frameworks/GlyphsCore.framework/Versions/A/
        # Resources/weights.plist
        # NOTE It is not possible from the user interface to set a custom
        # string as instance 'weightClass' since the choice is constrained
        # by a drop-down menu.
        data = makeInstance(
            "DemiLight Italic",
            weight=("DemiLight", 350, 70)
        )

        set_weight_class(ufo, data)

        # we do not set any OS/2 weight class; user needs to provide
        # a 'weightClass' custom parameter in this special case
        self.assertTrue(ufo.info.openTypeOS2WeightClass is None)


if __name__ == "__main__":
    sys.exit(unittest.main())
