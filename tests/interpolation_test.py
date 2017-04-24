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
from glyphsLib.builder import GLYPHS_PREFIX
from glyphsLib.interpolation import build_designspace


def makeFamily(familyName):
    m1 = makeMaster(familyName, "Regular", weight=90.0)
    m2 = makeMaster(familyName, "Black", weight=190.0)
    instances = {
        "defaultFamilyName": familyName,
        "data": [
            makeInstance("Regular", weight=("Regular", 400, 90)),
            makeInstance("Semibold", weight=("Semibold", 600, 128)),
            makeInstance("Bold", weight=("Bold", 700, 151)),
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


def makeInstance(name, weight=None, width=None):
    result = {"name": name}
    params = []
    if weight is not None:
        # Glyphs 2.3 stores the instance weight in two to three places:
        # 1. as a textual weightClass (such as “Bold”);
        # 2. (optional) as numeric customParameters.weightClass (such as 700),
        #    which corresponds to OS/2.usWeightClass where 100 means Thin,
        #    400 means Regular, 700 means Bold, and 900 means Black;
        # 3. as numeric interpolationWeight (such as 66.0), which typically is
        #    the stem width but can be anything that works for interpolation.
        weightName, weightClass, interpolationWeight = weight
        result["weightClass"] = weightName
        if weightClass is not None:
            params.append({"name": "weightClass", "value": weightClass})
        result["interpolationWeight"] = interpolationWeight
    if width is not None:
        # Glyphs 2.3 stores the instance width in two places:
        # 1. as a textual widthClass (such as “Condensed”);
        # 2. as numeric interpolationWidth (such as 79), which typically is
        #    a percentage of whatever the font designer considers “normal”
        #    but can be anything that works for interpolation.
        widthClass, interpolationWidth = width
        result["widthClass"] = widthClass
        result["interpolationWidth"] = interpolationWidth
    # TODO: Support custom axes; need to triple-check how these are encoded in
    # Glyphs files. Glyphs 3 will likely overhaul the representation of axes.
    if params:
        result["customParameters"] = params
    return result


class DesignspaceTest(unittest.TestCase):
    def build_designspace(self, masters, instances):
        master_dir = tempfile.mkdtemp()
        designspace, _ = build_designspace(
            masters, master_dir, os.path.join(master_dir, "out"), instances)
        with open(designspace, mode="r", encoding="utf-8") as f:
            result = f.readlines()
        shutil.rmtree(master_dir)
        return result

    def expect_designspace(self, masters, instances, expectedFile):
        actual = self.build_designspace(masters, instances)
        path, _ = os.path.split(__file__)
        expectedPath = os.path.join(path, "data", expectedFile)
        with open(expectedPath, mode="r", encoding="utf-8") as f:
            expected = f.readlines()
        if actual != expected:
            for line in difflib.unified_diff(
                    expected, actual,
                    fromfile=expectedPath, tofile=designspace):
                sys.stderr.write(line)
            self.fail("*.designspace file is different from expected")

    def test_basic(self):
        masters, instances = makeFamily("DesignspaceTest Basic")
        self.expect_designspace(masters, instances,
                                "DesignspaceTestBasic.designspace")

    def test_inactive_from_active(self):
        # Glyphs.app recognizes active=0 as a flag for inactive instances.
        # https://github.com/googlei18n/glyphsLib/issues/129
        masters, instances = makeFamily("DesignspaceTest Inactive")
        for inst in instances["data"]:
            if inst["name"] != "Semibold":
                inst["active"] = False
        self.expect_designspace(masters, instances,
                                "DesignspaceTestInactive.designspace")

    def test_inactive_from_exports(self):
        # Glyphs.app recognizes exports=0 as a flag for inactive instances.
        # https://github.com/googlei18n/glyphsLib/issues/129
        masters, instances = makeFamily("DesignspaceTest Inactive")
        for inst in instances["data"]:
            if inst["name"] != "Semibold":
                inst["exports"] = False
        self.expect_designspace(masters, instances,
                                "DesignspaceTestInactive.designspace")

    def test_familyName(self):
        masters, instances = makeFamily("DesignspaceTest FamilyName")
        customFamily = makeInstance("Regular", weight=("Bold", 600, 151))
        customFamily["customParameters"].append({
            "name": "familyName",
            "value": "Custom Family"})
        instances["data"] = [
            makeInstance("Regular", weight=("Regular", 400, 90)),
            customFamily,
        ]
        self.expect_designspace(masters, instances,
                                "DesignspaceTestFamilyName.designspace")

    def test_postscriptFontName(self):
        master = makeMaster("PSNameTest", "Master")
        thin, black = makeInstance("Thin"), makeInstance("Black")
        instances = {"data": [thin, black]}
        black.setdefault("customParameters", []).append({
            "name": "postscriptFontName",
            "value": "PSNameTest-Superfat",
        })
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
            makeInstance("Bold", weight=("Bold", 700, 151)),
        ]
        self.expect_designspace(masters, instances,
                                "DesignspaceTestInstanceOrder.designspace")

    def test_twoAxes(self):
        # In NotoSansArabic-MM.glyphs, the regular width only contains
        # parameters for the weight axis. For the width axis, glyphsLib
        # should use 100 as default value (just like Glyphs.app does).
        masters = [
            makeMaster("TwoAxes", "Regular", weight=90),
            makeMaster("TwoAxes", "Black", weight=190),
            makeMaster("TwoAxes", "Thin", weight=26),
            makeMaster("TwoAxes", "ExtraCond", weight=90, width=70),
            makeMaster("TwoAxes", "ExtraCond Black", weight=190, width=70),
            makeMaster("TwoAxes", "ExtraCond Thin", weight=26, width=70),
        ]

        _, instances = makeFamily("DesignspaceTest TwoAxes")
        instances["data"] = [
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
        self.expect_designspace(masters, instances,
                                "DesignspaceTestTwoAxes.designspace")


if __name__ == "__main__":
    sys.exit(unittest.main())
