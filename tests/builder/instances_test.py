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

from __future__ import print_function, division, absolute_import, unicode_literals
import os
import glyphsLib
from fontTools.designspaceLib import DesignSpaceDocument
from glyphsLib.builder.instances import apply_instance_data
import defcon

import pytest
import py.path
from ..test_helpers import write_designspace_and_UFOs


DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.mark.parametrize(
    "instance_names",
    [None, ["Extra Light"], ["Regular", "Bold"]],
    ids=["default", "include_1", "include_2"],
)
def test_apply_instance_data(tmpdir, instance_names):
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
        ufo = defcon.Font()
        ufo.save(str(tmpdir / instance))

    ufos = apply_instance_data(designspace.path, include_filenames=test_instances)

    for filename in test_instances:
        assert os.path.isdir(str(tmpdir / filename))
    assert len(ufos) == len(test_instances)

    for ufo in ufos:
        assert ufo.info.openTypeOS2WeightClass is not None
        assert ufo.info.openTypeOS2WidthClass is not None


def test_reexport_apply_instance_data():
    # this is for compatibility with fontmake
    # https://github.com/googlei18n/fontmake/issues/451
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
