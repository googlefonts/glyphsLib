#
# Copyright 2020 Google Inc. All Rights Reserved.
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

import os.path

import pytest

from glyphsLib.builder.axes import get_regular_master

from glyphsLib.classes import GSFont


def test_custom_parameter_vfo_current():
    """Tests get_regular_master when 'Variable Font Origin' custom parameter name 
    is used with master set to 'Regular Text'.  This is the current default 
    custom parameter name in the Glyphs editor / glyphs source file specification."""
    source_path = os.path.join("tests", "data", "CustomParameterVFO.glyphs")
    font = GSFont(source_path)
    assert font.customParameters["Variation Font Origin"] is None
    test_id = font.customParameters["Variable Font Origin"]
    assert test_id == "ACC63F3E-1323-486A-94AF-B18797A154CE"
    matched = False
    for master in font.masters:
        if master.id == test_id:
            assert master.name == "Regular Text"
            matched = True
    assert matched is True
    default_master = get_regular_master(font)
    assert default_master.name == "Regular Text"


def test_custom_parameter_vfo_old_name():
    """Tests get_regular_master when 'Variation Font Origin' custom parameter name 
    is used with master set to 'Regular Text'.  This custom parameter name is not
    used in current releases of the Glyphs editor / glyphs source file specification."""
    source_path = os.path.join("tests", "data", "CustomParameterVFO-oldname.glyphs")
    font = GSFont(source_path)
    assert font.customParameters["Variable Font Origin"] is None
    test_id = font.customParameters["Variation Font Origin"]
    assert test_id == "ACC63F3E-1323-486A-94AF-B18797A154CE"
    matched = False
    for master in font.masters:
        if master.id == test_id:
            assert master.name == "Regular Text"
            matched = True
    assert matched is True
    default_master = get_regular_master(font)
    assert default_master.name == "Regular Text"


def test_custom_parameter_vfo_not_set():
    """Tests default behavior of get_regular_master when Variable Font Origin custom
    parameter is not set"""
    source_path = os.path.join("tests", "data", "CustomParameterVFO-noVFO.glyphs")
    font = GSFont(source_path)
    assert font.customParameters["Variable Font Origin"] is None
    assert font.customParameters["Variation Font Origin"] is None
    default_master = get_regular_master(font)
    assert default_master.name == "Regular Text"
