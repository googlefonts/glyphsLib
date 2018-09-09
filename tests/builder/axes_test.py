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

import pytest

import defcon
from fontTools import designspaceLib
from glyphsLib import to_glyphs, to_designspace, to_ufos

"""
Goal: check how files with custom axes are roundtripped.
"""


@pytest.mark.parametrize(
    "axes",
    [
        [("wght", "Weight alone")],
        [("wdth", "Width alone")],
        [("XXXX", "Custom alone")],
        [("wght", "Weight (with width)"), ("wdth", "Width (with weight)")],
        [
            ("wght", "Weight (1/3 default)"),
            ("wdth", "Width (2/3 default)"),
            ("XXXX", "Custom (3/3 default)"),
        ],
        [("ABCD", "First custom"), ("EFGH", "Second custom")],
        [
            ("ABCD", "First custom"),
            ("EFGH", "Second custom"),
            ("IJKL", "Third custom"),
            ("MNOP", "Fourth custom"),
        ],
    ],
)
def test_weight_width_custom(axes):
    """Test that having axes in any order or quantity does not confuse
    glyphsLib, even when the weight or width are not in the default positions.
    """
    doc = _make_designspace_with_axes(axes)

    font = to_glyphs(doc)

    assert font.customParameters["Axes"] == [
        {"Tag": tag, "Name": name} for tag, name in axes
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
        extreme.location = {name_: 0 if name_ != name else 100 for _, name_ in axes}
        doc.addSource(extreme)

    return doc


def test_masters_have_user_locations():
    """Test the new axis definition with custom parameters.
    See https://github.com/googlei18n/glyphsLib/issues/280.

    For tests about the previous system with weight/width/custom,
    see `tests/builder/interpolation_test.py`.
    """
    # Get a font with two masters
    font = to_glyphs([defcon.Font(), defcon.Font()])
    font.customParameters["Axes"] = [{"Tag": "opsz", "Name": "Optical"}]
    # There is only one axis, so the design location is stored in the weight
    font.masters[0].weightValue = 0
    # The user location is stored as a custom parameter
    font.masters[0].customParameters["Axis Location"] = [
        {"Axis": "Optical", "Location": 13}
    ]
    font.masters[1].weightValue = 1000
    font.masters[1].customParameters["Axis Location"] = [
        {"Axis": "Optical", "Location": 100}
    ]

    doc = to_designspace(font)
    assert len(doc.axes) == 1
    assert doc.axes[0].map == [(13, 0), (100, 1000)]
    assert len(doc.sources) == 2
    assert doc.sources[0].location == {"Optical": 0}
    assert doc.sources[1].location == {"Optical": 1000}

    font = to_glyphs(doc)
    assert font.customParameters["Axes"] == [{"Tag": "opsz", "Name": "Optical"}]
    assert font.masters[0].weightValue == 0
    assert font.masters[0].customParameters["Axis Location"] == [
        {"Axis": "Optical", "Location": 13}
    ]
    assert font.masters[1].weightValue == 1000
    assert font.masters[1].customParameters["Axis Location"] == [
        {"Axis": "Optical", "Location": 100}
    ]


def test_master_user_location_goes_into_os2_classes():
    font = to_glyphs([defcon.Font(), defcon.Font()])
    font.customParameters["Axes"] = [
        {"Tag": "wght", "Name": "Weight"},
        {"Tag": "wdth", "Name": "Width"},
    ]
    font.masters[0].weightValue = 0
    font.masters[0].widthValue = 1000
    # This master will be Light Expanded
    # as per https://docs.microsoft.com/en-gb/typography/opentype/spec/os2#uswidthclass
    font.masters[0].customParameters["Axis Location"] = [
        {"Axis": "Weight", "Location": 300},
        {"Axis": "Width", "Location": 125},
    ]
    font.masters[1].weightValue = 1000
    font.masters[1].widthValue = 0
    # This master is Black Ultra-condensed but not quite
    font.masters[1].customParameters["Axis Location"] = [
        {"Axis": "Weight", "Location": 920},  # instead of 900
        {"Axis": "Width", "Location": 55},  # instead of 50
    ]

    light, black = to_ufos(font)

    assert light.info.openTypeOS2WeightClass == 300
    assert light.info.openTypeOS2WidthClass == 7

    assert black.info.openTypeOS2WeightClass == 920
    assert black.info.openTypeOS2WidthClass == 1


def test_mapping_is_same_regardless_of_axes_custom_parameter():
    # https://github.com/googlei18n/glyphsLib/issues/409
    # https://github.com/googlei18n/glyphsLib/issues/411

    # First, try without the custom param
    font = to_glyphs([defcon.Font(), defcon.Font(), defcon.Font()])
    font.masters[0].name = "ExtraLight"
    font.masters[0].weightValue = 200
    font.masters[1].name = "Regular"
    font.masters[1].weightValue = 400
    font.masters[2].name = "Bold"
    font.masters[2].weightValue = 700

    doc = to_designspace(font)
    assert doc.axes[0].minimum == 200
    assert doc.axes[0].maximum == 700
    assert doc.axes[0].map == []

    # Now with the custom parameter. Should produce the same results
    font.customParameters["Axes"] = [{"Name": "Weight", "Tag": "wght"}]

    doc = to_designspace(font)
    assert doc.axes[0].minimum == 200
    assert doc.axes[0].maximum == 700
    assert doc.axes[0].map == []
