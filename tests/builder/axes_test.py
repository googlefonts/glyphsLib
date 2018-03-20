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

import pytest

import defcon
from fontTools import designspaceLib
from glyphsLib import to_glyphs, to_designspace

"""
Goal: check how files with custom axes are roundtripped.
"""


@pytest.mark.parametrize('axes', [
    [('wght', 'Weight alone')],
    [('wdth', 'Width alone')],
    [('XXXX', 'Custom alone')],
    [('wght', 'Weight (with width)'), ('wdth', 'Width (with weight)')],
    [
        ('wght', 'Weight (1/3 default)'),
        ('wdth', 'Width (2/3 default)'),
        ('XXXX', 'Custom (3/3 default)'),
    ],
    [('ABCD', 'First custom'), ('EFGH', 'Second custom')],
    [
        ('ABCD', 'First custom'),
        ('EFGH', 'Second custom'),
        ('IJKL', 'Third custom'),
        ('MNOP', 'Fourth custom'),
    ],
])
def test_weight_width_custom(axes):
    doc = _make_designspace_with_axes(axes)

    font = to_glyphs(doc)

    assert font.customParameters['Axes'] == [
        {'Tag': tag, 'Name': name} for tag, name in axes
    ]

    doc = to_designspace(font)

    assert len(doc.axes) == len(axes)
    for doc_axis, (tag, name) in zip(doc.axes, axes):
        assert doc_axis.tag == tag
        assert doc_axis.name == name


def _make_designspace_with_axes(axes):
    doc = designspaceLib.DesignSpaceDocument()

    # Add a "Regular" source
    regular = doc.newSourceDescriptor()
    regular.font = defcon.Font()
    regular.location = {name: 0 for _, name in axes}
    doc.addSource(regular)

    for tag, name in axes:
        axis = doc.newAxisDescriptor()
        axis.tag = tag
        axis.name = name
        doc.addAxis(axis)

        extreme = doc.newSourceDescriptor()
        extreme.font = defcon.Font()
        extreme.location = {
            name_: 0 if name_ != name else 100 for _, name_ in axes
        }
        doc.addSource(extreme)

    return doc


