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
from fontTools.designspaceLib import DesignSpaceDocument
from glyphsLib.builder.instances import apply_instance_data

import pytest
import py.path
from ..test_helpers import write_designspace_and_UFOs


DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.mark.parametrize(
    "instance_names",
    [None, ["Extra Light"], ["Regular", "Bold"]],
    ids=["default", "include_1", "include_2"],
)
def test_apply_instance_data(tmpdir, instance_names, ufo_module):
    font = glyphsLib.GSFont(os.path.join(DATA, "GlyphsUnitTestSans.glyphs"))
    instance_dir = "instances"
    designspace = glyphsLib.to_designspace(font, instance_dir=instance_dir)
    path = str(tmpdir / (font.familyName + ".designspace"))
    write_designspace_and_UFOs(designspace, path)

    test_designspace = DesignSpaceDocument()
    test_designspace.read(designspace.path)
    if instance_names is None:
        # Collect all instances.
        test_instances = [instance.filename for instance in test_designspace.instances]
    else:
        # Collect only selected instances.
        test_instances = [
            instance.filename
            for instance in test_designspace.instances
            if instance.styleName in instance_names
        ]

    # Generate dummy UFOs for collected instances so we don't actually need to
    # interpolate.
    tmpdir.mkdir(instance_dir)
    for instance in test_instances:
        ufo = ufo_module.Font()
        ufo.save(str(tmpdir / instance))

    ufos = apply_instance_data(designspace.path, include_filenames=test_instances)

    for filename in test_instances:
        assert os.path.isdir(str(tmpdir / filename))
    assert len(ufos) == len(test_instances)

    for ufo in ufos:
        assert ufo.info.openTypeOS2WeightClass in {
            100,
            200,
            300,
            400,
            500,
            700,
            900,
            357,
        }
        assert ufo.info.openTypeOS2WidthClass is None  # GlyphsUnitTestSans is wght only


def test_reexport_apply_instance_data():
    # this is for compatibility with fontmake
    # https://github.com/googlefonts/fontmake/issues/451
    from glyphsLib.interpolation import apply_instance_data as reexported

    assert reexported is apply_instance_data


def test_reencode_glyphs(tmpdir):
    data_dir = py.path.local(DATA)

    designspace_path = data_dir / "TestReencode.designspace"
    designspace_path.copy(tmpdir)

    ufo_path = data_dir / "TestReencode-Regular.ufo"
    ufo_path.copy(tmpdir.ensure_dir("TestReencode-Regular.ufo"))

    instance_dir = tmpdir.ensure_dir("instance_ufo")
    ufo_path.copy(instance_dir.ensure_dir("TestReencode-Regular.ufo"))
    ufo_path.copy(instance_dir.ensure_dir("TestReencodeUI-Regular.ufo"))

    ufos = apply_instance_data(str(tmpdir / "TestReencode.designspace"))

    assert len(ufos) == 2
    assert ufos[0]["A"].unicode == 0x0041
    assert ufos[0]["A.alt"].unicode is None
    assert ufos[0]["C"].unicode == 0x0043
    # Reencode Glyphs: A.alt=0041, C=
    assert ufos[1]["A"].unicode is None
    assert ufos[1]["A.alt"].unicode == 0x0041
    assert ufos[1]["C"].unicode is None


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


def test_glyphs3_mapping():
    font = glyphsLib.GSFont(os.path.join(DATA, "Glyphs3Instances.glyphs"))
    # Instance1: designspace 200 -> userspace 400
    # Instance2: designspace 800 -> userspace 900
    # Instance2: designspace 600 -> userspace 650
    doc = glyphsLib.to_designspace(font)
    assert doc.axes[0].map == [(400, 200), (600, 650), (900, 800)]
    assert doc.instances[0].location == {"Weight": 200}
    assert doc.instances[1].location == {"Weight": 800}
    assert doc.instances[2].location == {"Weight": 650}


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


def test_rename_glyphs(tmpdir):
    font = glyphsLib.GSFont(os.path.join(DATA, "RenameGlyphsTest.glyphs"))
    instance_dir = tmpdir.ensure_dir("instance_ufo")
    designspace = glyphsLib.to_designspace(font, instance_dir=instance_dir)
    path = str(tmpdir / (font.familyName + ".designspace"))
    write_designspace_and_UFOs(designspace, path)

    ufo_path = tmpdir / "RenameGlyphsTest-Regular.ufo"
    ufo_path.copy(instance_dir.ensure_dir("RenameGlyphsTest-Straight.ufo"))
    ufo_path.copy(instance_dir.ensure_dir("RenameGlyphsTest-Swapped.ufo"))

    ufos = apply_instance_data(designspace.path)

    assert len(ufos) == 2

    assert len(ufos[0]["a"][0]) == 4  # Square
    assert len(ufos[0]["b"][0]) == 12  # Circle
    assert ufos[0]["a"].unicode == 0x0061
    assert ufos[0]["b"].unicode == 0x0062

    assert len(ufos[1]["a"][0]) == 12  # Circle
    assert len(ufos[1]["b"][0]) == 4  # Square
    assert ufos[0]["a"].unicode == 0x0061
    assert ufos[0]["b"].unicode == 0x0062
