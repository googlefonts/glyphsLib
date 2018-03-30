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
from test_helpers import write_designspace_and_UFOs


TESTFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    os.path.join('data', 'GlyphsUnitTestSans.glyphs')
)


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
    font = glyphsLib.GSFont(TESTFILE_PATH)
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
