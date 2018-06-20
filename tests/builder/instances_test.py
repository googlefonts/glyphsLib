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

from __future__ import (print_function, division, absolute_import,
                        unicode_literals)
import os
import glyphsLib
from mutatorMath.ufo.document import DesignSpaceDocumentReader
from glyphsLib.builder.instances import apply_instance_data
import defcon

import pytest
import py.path
from ..test_helpers import write_designspace_and_UFOs


DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.mark.parametrize(
    "instance_names",
    [
        None,
        ["Extra Light"],
        ["Regular", "Bold"],
    ],
    ids=["default", "include_1", "include_2"],
)
def test_apply_instance_data(tmpdir, instance_names):
    font = glyphsLib.GSFont(os.path.join(DATA, "GlyphsUnitTestSans.glyphs"))
    instance_dir = "instances"
    designspace = glyphsLib.to_designspace(font, instance_dir=instance_dir)
    path = str(tmpdir / (font.familyName + '.designspace'))
    write_designspace_and_UFOs(designspace, path)
    builder = DesignSpaceDocumentReader(designspace.path, ufoVersion=3)
    if instance_names is None:
        # generate all instances
        builder.process()
        include_filenames = None
    else:
        # generate only selected instances
        for name in instance_names:
            builder.readInstance(("stylename", name))
        # make relative filenames from paths returned by MutatorMath
        include_filenames = {os.path.relpath(instance_path, str(tmpdir))
                             for instance_path in builder.results.values()}

    ufos = apply_instance_data(designspace.path,
                               include_filenames=include_filenames)

    for filename in include_filenames or ():
        assert os.path.isdir(str(tmpdir / filename))
    assert len(ufos) == len(builder.results)
    assert isinstance(ufos[0], defcon.Font)


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
