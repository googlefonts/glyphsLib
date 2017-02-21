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

import defcon
from fontTools.misc.py23 import open
from glyphsLib.builder import GLYPHS_PREFIX
from glyphsLib.interpolation import build_designspace


def makeFamily(familyName):
    m1, m2 = defcon.Font(), defcon.Font()
    m1.info.familyName, m1.info.styleName = familyName, "Regular"
    m1.lib[GLYPHS_PREFIX + "weightValue"] = 400.0
    m2.info.familyName, m2.info.styleName = familyName, "Black"
    m2.lib[GLYPHS_PREFIX + "weightValue"] = 900.0
    instances = {
        "defaultFamilyName": familyName,
        "data": [
            {"name": "Regular", "interpolationWeight": 400.0},
            {"name": "Semibold", "interpolationWeight": 600.0},
            {"name": "Bold", "interpolationWeight": 700.0},
            {"name": "Black", "interpolationWeight": 900.0},
        ],
    }
    return [m1, m2], instances


class DesignspaceTest(unittest.TestCase):
    def expect_designspace(self, masters, instances, expectedFile):
        master_dir = tempfile.mkdtemp()
        designspace, _ = build_designspace(
            masters, master_dir, os.path.join(master_dir, "out"), instances)
        with open(designspace, mode="r", encoding="utf-8") as f:
            actual = f.readlines()
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
        shutil.rmtree(master_dir)

    def test_basic(self):
        masters, instances = makeFamily("DesignspaceTest Basic")
        self.expect_designspace(masters, instances,
                                "DesignspaceTestBasic.designspace")

    def test_inactive(self):
        masters, instances = makeFamily("DesignspaceTest Inactive")
        for inst in instances["data"]:
            inst["active"] = (inst["name"] == "Semibold")
        self.expect_designspace(masters, instances,
                                "DesignspaceTestInactive.designspace")

    def test_familyName(self):
        masters, instances = makeFamily("DesignspaceTest FamilyName")
        instances["data"] = [
            {"name": "Regular", "interpolationWeight": 400.0},
            {
                "name": "Regular",
                "interpolationWeight": 600.0,
                "customParameters": [
                    {"name": "familyName", "value": "Custom Family"},
                ],
            },
        ]
        self.expect_designspace(masters, instances,
                                "DesignspaceTestFamilyName.designspace")

    def test_instanceOrder(self):
        # The generated *.designspace file should place instances
        # in the same order as they appear in the original source.
        # https://github.com/googlei18n/glyphsLib/issues/113
        masters, instances = makeFamily("DesignspaceTest InstanceOrder")
        instances["data"] = [
            {"name": "Black", "interpolationWeight": 900.0},
            {"name": "Regular", "interpolationWeight": 400.0},
            {"name": "Bold", "interpolationWeight": 700.0},
        ]
        self.expect_designspace(masters, instances,
                                "DesignspaceTestInstanceOrder.designspace")


if __name__ == "__main__":
    sys.exit(unittest.main())
