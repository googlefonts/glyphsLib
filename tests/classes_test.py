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

import collections
import datetime
import unittest

from fontTools.misc.loggingTools import CapturingLogHandler

from glyphsLib.classes import GSFont, GSFontMaster, GSInstance, \
    GSCustomParameter, GSGlyph, GSLayer, GSPath, GSNode, GSAnchor, \
    GSComponent, GSAlignmentZone


def generate_minimal_font():
    font = GSFont()
    font.appVersion = 895
    font.date = datetime.datetime.today()
    font.familyName = 'MyFont'

    master = GSFontMaster()
    master.ascender = 0
    master.capHeight = 0
    master.descender = 0
    master.id = 'id'
    master.xHeight = 0
    font.masters.append(master)

    font.unitsPerEm = 1000
    font.versionMajor = 1
    font.versionMinor = 0

    return font


def add_glyph(font, glyphname):
    glyph = GSGlyph()
    glyph.name = glyphname
    font.glyphs.append(glyph)
    layer = GSLayer()
    layer.layerId = font.masters[0].id
    layer.associatedMasterId = font.masters[0].id
    layer.width = 0
    glyph.layers.append(layer)
    return glyph


def add_anchor(font, glyphname, anchorname, x, y):
    for glyph in font.glyphs:
        if glyph.name == glyphname:
            for master in font.masters:
                layer = glyph.layers[master.id]
                layer.anchors = getattr(layer, 'anchors', [])
                anchor = GSAnchor()
                anchor.name = anchorname
                anchor.position = (x, y)
                layer.anchors.append(anchor)


def add_component(font, glyphname, componentname,
                  transform):
    for glyph in font.glyphs:
        if glyph.name == glyphname:
            for layer in glyph.layers.values():
                component = GSComponent()
                component.name = componentname
                component.transform = transform
                layer.components.append(component)


class GlyphLayersTest(unittest.TestCase):
    def test_check_master_layer(self):
        font = generate_minimal_font()
        glyph = add_glyph(font, "A")
        self.assertIsNotNone(glyph)
        master = font.masters[0]
        self.assertIsNotNone(master)
        layer = glyph.layers[master.id]
        self.assertIsNotNone(layer)

        layer = glyph.layers["XYZ123"]
        self.assertIsNone(layer)


if __name__ == '__main__':
    unittest.main()
