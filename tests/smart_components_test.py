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

from glyphsLib import to_ufos
from glyphsLib.classes import (
    GSFont,
    GSFontMaster,
    GSGlyph,
    GSLayer,
    GSPath,
    GSNode,
    GSSmartComponentAxis,
    GSComponent,
)


# https://glyphsapp.com/tutorials/smart-components


@pytest.fixture
def smart_font():
    """Make a font with a smart component in the shape of a rectangle."""
    font = GSFont()
    master = GSFontMaster()
    font.masters.append(master)

    rectangle = GSGlyph()
    rectangle.name = "_part.rectangle"
    # Could also be rectangle.name = '_smart.rectangle'
    font.glyphs.append(rectangle)

    # Three axes
    width = GSSmartComponentAxis()
    width.name = "Width"
    # This one is easy 0-1
    width.bottomValue = 0.0
    width.topValue = 1.0
    rectangle.smartComponentAxes.append(width)

    height = GSSmartComponentAxis()
    height.name = "Height"
    # This one is off the origin
    height.bottomValue = 100
    height.topValue = 500
    rectangle.smartComponentAxes.append(height)

    shift = GSSmartComponentAxis()
    shift.name = "Shift"
    # This one has negative values
    shift.bottomValue = -100
    shift.topValue = 0
    rectangle.smartComponentAxes.append(shift)

    # Four masters
    regular = GSLayer()
    regular.layerId = font.masters[0].id
    regular.associatedMasterId = font.masters[0].id
    regular.width = 300
    rectangle.layers.append(regular)
    regular.paths.append(rectangle_path(100, 100, 100, 100))
    regular.smartComponentPoleMapping["Width"] = 1  # 1 is bottom pole
    regular.smartComponentPoleMapping["Height"] = 1
    regular.smartComponentPoleMapping["Shift"] = 2  # 2 is the top pole

    wide = GSLayer()
    wide.name = "Wide"
    wide.layerId = "wide"
    wide.associatedMasterId = font.masters[0].id
    wide.width = 700
    rectangle.layers.append(wide)
    wide.paths.append(rectangle_path(100, 100, 500, 100))
    wide.smartComponentPoleMapping["Width"] = 2
    wide.smartComponentPoleMapping["Height"] = 1
    wide.smartComponentPoleMapping["Shift"] = 2

    tall = GSLayer()
    tall.name = "Tall"
    tall.layerId = "tall"
    tall.associatedMasterId = font.masters[0].id
    tall.width = 300
    rectangle.layers.append(tall)
    tall.paths.append(rectangle_path(100, 100, 100, 500))
    tall.smartComponentPoleMapping["Width"] = 1
    tall.smartComponentPoleMapping["Height"] = 2
    tall.smartComponentPoleMapping["Shift"] = 2

    shifted = GSLayer()
    shifted.name = "Shifted"
    shifted.layerId = "shifted"
    shifted.associatedMasterId = font.masters[0].id
    shifted.width = 100
    rectangle.layers.append(shifted)
    shifted.paths.append(rectangle_path(0, 0, 100, 100))
    shifted.smartComponentPoleMapping["Width"] = 1
    shifted.smartComponentPoleMapping["Height"] = 1
    shifted.smartComponentPoleMapping["Shift"] = 1

    # Also add a normal glyph in which we can instanciate the component
    a = GSGlyph()
    a.name = "a"
    font.glyphs.append(a)
    regular = GSLayer()
    regular.layerId = font.masters[0].id
    regular.associatedMasterId = font.masters[0].id
    regular.width = 1000
    a.layers.append(regular)

    component = GSComponent(rectangle.name)
    component.smartComponentValues = {}
    regular.components.append(component)

    return font


def rectangle_path(x, y, w, h):
    path = GSPath()
    path.nodes.append(GSNode((x, y)))
    path.nodes.append(GSNode((x + w, y)))
    path.nodes.append(GSNode((x + w, y + h)))
    path.nodes.append(GSNode((x, y + h)))
    return path


def test_dump_smart_font(smart_font, tmpdir):
    smart_font.save("smart.glyphs")


@pytest.mark.parametrize(
    "values,expected",
    [
        # Eight corners
        ({"Width": 0, "Height": 100, "Shift": 0}, (100, 100, 100, 100)),
        ({"Width": 1, "Height": 100, "Shift": 0}, (100, 100, 500, 100)),
        ({"Width": 0, "Height": 500, "Shift": 0}, (100, 100, 100, 500)),
        ({"Width": 1, "Height": 500, "Shift": 0}, (100, 100, 500, 500)),
        ({"Width": 0, "Height": 100, "Shift": -100}, (0, 0, 100, 100)),
        ({"Width": 1, "Height": 100, "Shift": -100}, (0, 0, 500, 100)),
        ({"Width": 0, "Height": 500, "Shift": -100}, (0, 0, 100, 500)),
        ({"Width": 1, "Height": 500, "Shift": -100}, (0, 0, 500, 500)),
        # Some points in the middle
        ({"Width": 0.5, "Height": 300, "Shift": -50}, (50, 50, 300, 300)),
    ],
)
def test_smart_component_regular(values, expected, smart_font):
    component = smart_font.glyphs["a"].layers[0].components[0]
    for key, value in values.items():
        component.smartComponentValues[key] = value

    (ufo,) = to_ufos(smart_font)

    assert get_rectangle_data(ufo) == expected


def get_rectangle_data(ufo, glyph_name="a", component_index=0):
    """Retrieve the results of the smart component interpolation."""
    a = ufo[glyph_name]
    rectangle = ufo[a.components[component_index].baseGlyph]
    contour = rectangle[0]
    left = min(node.x for node in contour)
    right = max(node.x for node in contour)
    top = max(node.y for node in contour)
    bottom = min(node.y for node in contour)
    return (left, bottom, right - left, top - bottom)
