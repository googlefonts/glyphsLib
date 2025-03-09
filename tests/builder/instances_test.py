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
import glyphsLib

import pytest
from ..test_helpers import write_designspace_and_UFOs


DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.mark.parametrize(
    "instance_names",
    [None, ["Extra Light"], ["Regular", "Bold"]],
    ids=["default", "include_1", "include_2"],
)

def test_glyphs3_names():
    file = "InstanceFamilyName-G3.glyphs"
    font = glyphsLib.GSFont(os.path.join(DATA, file))

    expected_names = {
        "familyName": [
            "MyFamily",
            "MyFamily",
            "MyFamily 12pt",
            "MyFamily 12pt",
            "MyFamily 72pt",
            "MyFamily 72pt",
        ],
        "preferredFamily": [
            "MyFamily",
            "MyFamily",
            "MyFamily",
            "Typographic MyFamily 12pt",
            "MyFamily",
            "MyFamily",
        ],
        "preferredFamilyName": [
            None,
            None,
            None,
            "Typographic MyFamily 12pt",
            None,
            None,
        ],
        "preferredSubfamilyName": [
            None,
            None,
            None,
            None,
            None,
            "Typographic Black",
        ],
        "windowsFamily": [
            "MyFamily Thin",
            "MyFamily Black",
            "MyFamily 12pt Thin",
            "MyFamily 12pt Black",
            "MyFamily 72pt Thin",
            "MyFamily 72pt Black",
        ],
        "fontName": [
            "MyFamily-Thin",
            "MyFamily-Black",
            "MyFamily12pt-Thin",
            "MyFamily12pt-Black",
            "MyFamily72pt-Thin",
            "MyFamily72pt-Black",
        ],
        "fullName": [
            "MyFamily Thin",
            "MyFamily Black",
            "MyFamily 12pt Thin",
            "MyFamily 12pt Black",
            "MyFamily 72pt Thin",
            "MyFamily 72pt Black",
        ],
    }

    for name, expected in expected_names.items():
        actual = [getattr(instance, name) for instance in font.instances]
        assert expected == actual, name


def test_glyphs2_mapping():
    font = glyphsLib.GSFont(os.path.join(DATA, "Glyphs2Instances.glyphs"))
    master = font.masters[0]
    assert master.internalAxesValues[0] == 200
    assert master.externalAxesValues[0] is None
    master = font.masters[1]
    assert master.internalAxesValues[0] == 800
    assert master.externalAxesValues[0] is None

    instance = font.instances[0]
    assert instance.internalAxesValues[0] == 200
    assert instance.externalAxesValues[0] is None
    instance = font.instances[2]
    assert instance.internalAxesValues[0] == 650
    assert instance.externalAxesValues[0] is None

    # Instance1: designspace 200 -> userspace 400
    # Instance2: designspace 800 -> userspace 900
    # Instance2: designspace 600 -> userspace 650
    doc = glyphsLib.to_designspace(font)
    # FIXME: (georg) mapping is not implied from the weightClass any more
    # assert doc.axes[0].map == [(400, 200), (600, 650), (900, 800)]
    assert doc.instances[0].location == {"Weight": 200}
    assert doc.instances[1].location == {"Weight": 800}
    assert doc.instances[2].location == {"Weight": 650}

    font_rt = glyphsLib.to_glyphs(doc)
    master = font_rt.masters[0]
    assert master.internalAxesValues[0] == 200
    assert master.externalAxesValues[0] is None
    master = font_rt.masters[1]
    assert master.internalAxesValues[0] == 800
    assert master.externalAxesValues[0] is None

    instance = font_rt.instances[0]
    assert instance.internalAxesValues[0] == 200
    assert instance.externalAxesValues[0] is None
    instance = font_rt.instances[2]
    assert instance.internalAxesValues[0] == 650
    assert instance.externalAxesValues[0] is None


def test_glyphs3_mapping():
    font = glyphsLib.GSFont(os.path.join(DATA, "Glyphs3Instances.glyphs"))
    master = font.masters[0]
    assert master.internalAxesValues[0] == 200
    assert master.externalAxesValues[0] is None
    master = font.masters[1]
    assert master.internalAxesValues[0] == 800
    assert master.externalAxesValues[0] is None

    instance = font.instances[0]
    assert instance.internalAxesValues[0] == 200
    assert instance.externalAxesValues[0] is None
    instance = font.instances[2]
    assert instance.internalAxesValues[0] == 650
    assert instance.externalAxesValues[0] is None

    # Instance1: designspace 200 -> userspace 400
    # Instance2: designspace 800 -> userspace 900
    # Instance2: designspace 600 -> userspace 650
    doc = glyphsLib.to_designspace(font)
    # FIXME: (georg) mapping is not implied from the weightClass any more
    # assert doc.axes[0].map == [(400, 200), (600, 650), (900, 800)]
    assert doc.instances[0].location == {"Weight": 200}
    assert doc.instances[1].location == {"Weight": 800}
    assert doc.instances[2].location == {"Weight": 650}

    font_rt = glyphsLib.to_glyphs(doc)
    master = font_rt.masters[0]
    assert master.internalAxesValues[0] == 200
    assert master.externalAxesValues[0] is None
    master = font_rt.masters[1]
    assert master.internalAxesValues[0] == 800
    assert master.externalAxesValues[0] is None

    instance = font_rt.instances[0]
    assert instance.internalAxesValues[0] == 200
    assert instance.externalAxesValues[0] is None
    instance = font_rt.instances[2]
    assert instance.internalAxesValues[0] == 650
    assert instance.externalAxesValues[0] is None


def test_glyphs2_mapping_AxisLocation():
    font = glyphsLib.GSFont(os.path.join(DATA, "Glyphs2InstancesAxisLocation.glyphs"))
    master = font.masters[0]
    assert master.internalAxesValues[0] == 200
    assert master.externalAxesValues[0] == 400
    master = font.masters[1]
    assert master.internalAxesValues[0] == 800
    assert master.externalAxesValues[0] == 900

    instance = font.instances[0]
    assert instance.internalAxesValues[0] == 200
    assert instance.externalAxesValues[0] == 400
    instance = font.instances[2]
    assert instance.internalAxesValues[0] == 650
    assert instance.externalAxesValues[0] == 600

    # Instance1: designspace 200 -> userspace 400
    # Instance2: designspace 800 -> userspace 900
    # Instance2: designspace 600 -> userspace 650
    doc = glyphsLib.to_designspace(font)
    assert doc.axes[0].map == [(400, 200), (600, 650), (900, 800)]
    assert doc.instances[0].location == {"Weight": 200}
    assert doc.instances[1].location == {"Weight": 800}
    assert doc.instances[2].location == {"Weight": 650}

    font_rt = glyphsLib.to_glyphs(doc)
    master = font_rt.masters[0]
    assert master.internalAxesValues[0] == 200
    assert master.externalAxesValues[0] == 400
    master = font_rt.masters[1]
    assert master.internalAxesValues[0] == 800
    assert master.externalAxesValues[0] == 900

    instance = font_rt.instances[0]
    assert instance.internalAxesValues[0] == 200
    assert instance.externalAxesValues[0] == 400
    instance = font_rt.instances[2]
    assert instance.internalAxesValues[0] == 650
    assert instance.externalAxesValues[0] == 600


def test_glyphs3_mapping_AxisLocation():
    font = glyphsLib.GSFont(os.path.join(DATA, "Glyphs3InstancesAxisLocation.glyphs"))

    master = font.masters[0]
    assert master.internalAxesValues[0] == 200
    assert master.externalAxesValues[0] == 400
    master = font.masters[1]
    assert master.internalAxesValues[0] == 800
    assert master.externalAxesValues[0] == 900

    instance = font.instances[0]
    assert instance.internalAxesValues[0] == 200
    assert instance.externalAxesValues[0] == 400
    instance = font.instances[2]
    assert instance.internalAxesValues[0] == 650
    assert instance.externalAxesValues[0] == 600

    # Instance1: designspace 200 -> userspace 400
    # Instance2: designspace 800 -> userspace 900
    # Instance2: designspace 600 -> userspace 650
    doc = glyphsLib.to_designspace(font)
    assert doc.axes[0].map == [(400, 200), (600, 650), (900, 800)]
    assert doc.instances[0].location == {"Weight": 200}
    assert doc.instances[1].location == {"Weight": 800}
    assert doc.instances[2].location == {"Weight": 650}

    font_rt = glyphsLib.to_glyphs(doc)
    master = font_rt.masters[0]
    assert master.internalAxesValues[0] == 200
    assert master.externalAxesValues[0] == 400
    master = font_rt.masters[1]
    assert master.internalAxesValues[0] == 800
    assert master.externalAxesValues[0] == 900

    instance = font_rt.instances[0]
    assert instance.internalAxesValues[0] == 200
    assert instance.externalAxesValues[0] == 400
    instance = font_rt.instances[2]
    assert instance.internalAxesValues[0] == 650
    assert instance.externalAxesValues[0] == 600


def test_glyphs3_instance_filtering():
    font = glyphsLib.GSFont(os.path.join(DATA, "InstanceFamilyName-G3.glyphs"))
    assert len(font.instances) == 6

    # Loaded from default font family name
    assert not font.instances[0].properties
    assert not font.instances[1].properties
    assert font.instances[0].familyName == "MyFamily"
    assert font.instances[1].familyName == "MyFamily"

    # Loaded from .properties
    assert font.instances[2].familyName == "MyFamily 12pt"
    assert font.instances[3].familyName == "MyFamily 12pt"
    assert font.instances[4].familyName == "MyFamily 72pt"
    assert font.instances[5].familyName == "MyFamily 72pt"

    doc = glyphsLib.to_designspace(font)
    assert len(doc.instances) == 6

    doc = glyphsLib.to_designspace(font, family_name="MyFamily 12pt")
    assert len(doc.instances) == 2


def test_glyphs3_instance_properties(tmpdir):
    expected_num_properties = [0, 0, 1, 2, 1, 2]

    file = "InstanceFamilyName-G3.glyphs"
    font = glyphsLib.GSFont(os.path.join(DATA, file))

    for expected, instance in zip(expected_num_properties, font.instances):
        assert expected == len(instance.properties)

    font.save(tmpdir / file)
    font = glyphsLib.GSFont(tmpdir / file)

    for expected, instance in zip(expected_num_properties, font.instances):
        assert expected == len(instance.properties)
