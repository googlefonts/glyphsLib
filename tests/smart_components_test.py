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

import pytest

from fontTools.pens.areaPen import AreaPen
from glyphsLib import to_ufos, load
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
    # draw a rect counter-clockwise (to the right, top, left and close)
    path.nodes.append(GSNode((x, y)))
    path.nodes.append(GSNode((x + w, y)))
    path.nodes.append(GSNode((x + w, y + h)))
    path.nodes.append(GSNode((x, y + h)))
    return path


@pytest.mark.parametrize(
    "values,expected_rect",
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
        # Extrapolation
        ({"Width": 0, "Height": 800, "Shift": 0}, (100, 100, 100, 800)),
    ],
)
def test_smart_component_regular(values, expected_rect, smart_font):
    component = smart_font.glyphs["a"].layers[0].components[0]
    for key, value in values.items():
        component.smartComponentValues[key] = value

    (ufo,) = to_ufos(smart_font)

    rect, clockwise = get_rectangle_data(ufo)
    assert rect == expected_rect
    assert not clockwise


@pytest.mark.parametrize(
    "values,expected_rect",
    [
        # Eight corners
        ({"Width": 0, "Height": 100, "Shift": 0}, (-200, 100, 100, 100)),
        ({"Width": 1, "Height": 100, "Shift": 0}, (-600, 100, 500, 100)),
        ({"Width": 0, "Height": 500, "Shift": 0}, (-200, 100, 100, 500)),
        ({"Width": 1, "Height": 500, "Shift": 0}, (-600, 100, 500, 500)),
        ({"Width": 0, "Height": 100, "Shift": -100}, (-100, 0, 100, 100)),
        ({"Width": 1, "Height": 100, "Shift": -100}, (-500, 0, 500, 100)),
        ({"Width": 0, "Height": 500, "Shift": -100}, (-100, 0, 100, 500)),
        ({"Width": 1, "Height": 500, "Shift": -100}, (-500, 0, 500, 500)),
        # Some points in the middle
        ({"Width": 0.5, "Height": 300, "Shift": -50}, (-350, 50, 300, 300)),
        # Extrapolation
        ({"Width": 0, "Height": 800, "Shift": 0}, (-200, 100, 100, 800)),
    ],
)
def test_smart_component_regular_flipped_x(values, expected_rect, smart_font):
    # same as test_smart_component_regular but with transform that flips x
    component = smart_font.glyphs["a"].layers[0].components[0]
    component.transform[0] = -1.0
    for key, value in values.items():
        component.smartComponentValues[key] = value

    (ufo,) = to_ufos(smart_font)

    rect, clockwise = get_rectangle_data(ufo)
    assert rect == expected_rect
    # after decomposing the flipped component, the original counter-clockwise
    # path direction should not change
    assert not clockwise


def get_rectangle_data(ufo, glyph_name="a"):
    """Retrieve the results of the smart component interpolation."""
    a = ufo[glyph_name]
    contour = a[0]

    left = min(node.x for node in contour)
    right = max(node.x for node in contour)
    top = max(node.y for node in contour)
    bottom = min(node.y for node in contour)

    pen = AreaPen(ufo)
    contour.draw(pen)
    clockwise = pen.value < 0

    return (left, bottom, right - left, top - bottom), clockwise


def test_smarts_with_one_master(datadir, ufo_module):
    file = "DumbSmarts.glyphs"
    with open(str(datadir.join(file)), encoding="utf-8") as f:
        original_glyphs_font = load(f)

    ufos = to_ufos(original_glyphs_font, ufo_module=ufo_module)

    assert len(ufos[0]["lam-ar.swsh"].components) == 1
    assert len(ufos[0]["lam-ar.swsh"]) == 1
    assert len(ufos[1]["lam-ar.swsh"].components) == 1
    assert len(ufos[1]["lam-ar.swsh"]) == 1
