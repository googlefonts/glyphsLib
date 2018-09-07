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

from __future__ import print_function, division, absolute_import, unicode_literals
import os

import pytest
import defcon

from glyphsLib import to_glyphs, to_designspace


def test_designspace_generation_regular_same_family_name(tmpdir):
    ufo_Lt = defcon.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Lt.info.styleName = "Light"
    ufo_Lt.info.openTypeOS2WeightClass = 300

    ufo_Rg = defcon.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular"
    ufo_Rg.info.openTypeOS2WeightClass = 400

    ufo_Md = defcon.Font()
    ufo_Md.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Md.info.styleName = "Medium"
    ufo_Md.info.openTypeOS2WeightClass = 500

    ufo_Bd = defcon.Font()
    ufo_Bd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Bd.info.styleName = "Bold"
    ufo_Bd.info.openTypeOS2WeightClass = 700

    ufo_ExBd = defcon.Font()
    ufo_ExBd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_ExBd.info.styleName = "XBold"
    ufo_ExBd.info.openTypeOS2WeightClass = 800

    font = to_glyphs([ufo_Lt, ufo_Rg, ufo_Md, ufo_Bd, ufo_ExBd])
    designspace = to_designspace(font)

    path = os.path.join(str(tmpdir), "actual.designspace")
    designspace.write(path)
    with open(path) as fp:
        actual = fp.read()

    expected_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "DesignspaceGenTestRegular.designspace"
    )
    with open(expected_path) as fp:
        expected = fp.read()

    assert expected == actual


def test_designspace_generation_italic_same_family_name(tmpdir):
    ufo_Lt = defcon.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Lt.info.styleName = "Light Italic"
    ufo_Lt.info.openTypeOS2WeightClass = 300
    ufo_Lt.info.italicAngle = -11

    ufo_Rg = defcon.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular Italic"
    ufo_Rg.info.openTypeOS2WeightClass = 400
    ufo_Rg.info.italicAngle = -11

    ufo_Md = defcon.Font()
    ufo_Md.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Md.info.styleName = "Medium Italic"
    ufo_Md.info.openTypeOS2WeightClass = 500
    ufo_Md.info.italicAngle = -11

    ufo_Bd = defcon.Font()
    ufo_Bd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Bd.info.styleName = "Bold Italic"
    ufo_Bd.info.openTypeOS2WeightClass = 700
    ufo_Bd.info.italicAngle = -11

    ufo_ExBd = defcon.Font()
    ufo_ExBd.info.familyName = "CoolFoundry Examplary Serif"
    ufo_ExBd.info.styleName = "XBold Italic"
    ufo_ExBd.info.openTypeOS2WeightClass = 800
    ufo_ExBd.info.italicAngle = -11

    font = to_glyphs([ufo_Lt, ufo_Rg, ufo_Md, ufo_Bd, ufo_ExBd])
    designspace = to_designspace(font)

    path = os.path.join(str(tmpdir), "actual.designspace")
    designspace.write(path)
    with open(path) as fp:
        actual = fp.read()

    expected_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "DesignspaceGenTestItalic.designspace"
    )
    with open(expected_path) as fp:
        expected = fp.read()

    assert expected == actual


def test_designspace_generation_regular_different_family_names(tmpdir):
    ufo_Lt = defcon.Font()
    ufo_Lt.info.familyName = "CoolFoundry Examplary Serif Light"
    ufo_Lt.info.styleName = "Regular"
    ufo_Lt.info.openTypeOS2WeightClass = 300

    ufo_Rg = defcon.Font()
    ufo_Rg.info.familyName = "CoolFoundry Examplary Serif"
    ufo_Rg.info.styleName = "Regular"
    ufo_Rg.info.openTypeOS2WeightClass = 400

    # Different family names are not allowed
    # REVIEW: reasonable requirement?
    with pytest.raises(Exception):
        to_glyphs([ufo_Lt, ufo_Rg])


def test_designspace_generation_same_weight_name(tmpdir):
    ufo_Bd = defcon.Font()
    ufo_Bd.info.familyName = "Test"
    ufo_Bd.info.styleName = "Bold"

    ufo_ExBd = defcon.Font()
    ufo_ExBd.info.familyName = "Test"
    ufo_ExBd.info.styleName = "Bold"

    ufo_XExBd = defcon.Font()
    ufo_XExBd.info.familyName = "Test"
    ufo_XExBd.info.styleName = "Bold"

    font = to_glyphs([ufo_Bd, ufo_ExBd, ufo_XExBd])
    designspace = to_designspace(font)

    assert designspace.sources[0].filename != designspace.sources[1].filename
    assert designspace.sources[1].filename != designspace.sources[2].filename
    assert designspace.sources[0].filename != designspace.sources[2].filename
