# Copyright 2021 Google Inc. All Rights Reserved.
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

import math

from fontTools.ttLib.tables.otTables import PaintFormat

from .common import to_ufo_color
from .constants import UFO2FT_COLOR_LAYERS_KEY, UFO2FT_COLOR_PALETTES_KEY


def _to_ufo_color_palette_layers(builder, master, layerMapping):
    for (glyph, masterLayer), layers in builder._color_palette_layers:
        if master.id != masterLayer.associatedMasterId:
            continue

        colorLayers = []
        for i, (layer, colorId) in enumerate(layers):
            if layer != masterLayer:
                layerGlyphName = f"{glyph.name}.color{i}"
                ufo_layer = builder.to_ufo_layer(glyph, masterLayer)
                ufo_glyph = ufo_layer.newGlyph(layerGlyphName)
                builder.to_ufo_glyph(ufo_glyph, layer, glyph)
            else:
                layerGlyphName = glyph.name
            colorLayers.append((layerGlyphName, colorId))
        layerMapping[glyph.name] = colorLayers


def _find_or_insert_color(color, palette):
    color = to_ufo_color(color)
    palette, old = palette
    if color not in palette:
        palette.append(color)
    return len(old) + palette.index(color), color[-1]


def _radius(rect, point):
    # Emulate how AppKit’s “drawInRect:relativeCenterPosition:” calculates the
    # radius, since this is what Glyphs uses.
    center = (rect.width * point[0], rect.height * point[1])
    distances = []
    for pt in ((0, 0), (rect.width, 0), (0, rect.height), (rect.width, rect.height)):
        # Should have been “dist = math.dist(center, pt)” but math.dist is new
        # in Python 3.8.
        x0, y0 = center
        x1, y1 = pt
        dist = math.hypot(x1 - x0, y1 - y0)
        distances.append(dist)
    return max(distances)


def _to_gradient_paint(gradient, layer, palette):
    # Glyphs start and stop points seem to be a percentage of the
    # path size, but we want absolute coordinates.
    bounds = layer.bounds
    x0, y0 = gradient["start"]
    x1, y1 = gradient["end"]
    x0 = bounds.origin.x + (bounds.size.width * x0)
    y0 = bounds.origin.y + (bounds.size.height * y0)
    x1 = bounds.origin.x + (bounds.size.width * x1)
    y1 = bounds.origin.y + (bounds.size.height * y1)

    colorStop = []
    for stop in gradient.get("colors"):
        color, o = stop
        paletteIndex, a = _find_or_insert_color(color, palette)
        colorStop.append(dict(StopOffset=o, Alpha=a, PaletteIndex=paletteIndex))

    colorLine = dict(Extend="pad", ColorStop=colorStop)

    gradientType = gradient.get("type")
    if gradientType is None:
        # Linear gradient.
        # We set point 2 to point 1 rotated -90 degrees around
        # point 0, since Glyphs gradients don’t represent them.
        paint = dict(
            Format=PaintFormat.PaintLinearGradient,
            ColorLine=colorLine,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            x2=x0 + (y1 - y0),
            y2=y0 - (x1 - x0),
        )
    elif gradientType == "circle":
        # Radial gradient.
        # We set radius 0 to 0 and point 1 to point 0, since Glyphs
        # gradients don’t represent them.
        r = _radius(bounds.size, gradient["start"])
        paint = dict(
            Format=PaintFormat.PaintRadialGradient,
            ColorLine=colorLine,
            x0=x0,
            y0=y0,
            x1=x0,
            y1=y0,
            r0=0,
            r1=r,
        )
    else:
        raise NotImplementedError(
            f"Unsupported color layer path gradient in '{layer.parent.name}'"
        )

    return paint


def _to_ufo_color_layers(builder, ufo, master, layerMapping):
    palette = ([], ufo.lib.get(UFO2FT_COLOR_PALETTES_KEY, [[]])[0])
    for (glyph, masterLayer), layers in builder._color_layers:
        if master.id != masterLayer.associatedMasterId:
            continue

        assert glyph.name not in layerMapping

        colorLayers = []
        for i, layer in enumerate(layers):
            if layer != masterLayer:
                layerGlyphName = f"{glyph.name}.color{i}"
                ufo_layer = builder.to_ufo_layer(glyph, masterLayer)
                ufo_glyph = ufo_layer.newGlyph(layerGlyphName)
                builder.to_ufo_glyph(ufo_glyph, layer, glyph)
            else:
                layerGlyphName = glyph.name

            attributes = layer.paths[0].attributes
            if "gradient" in attributes:
                gradient = attributes["gradient"]
                paint = _to_gradient_paint(gradient, layer, palette)
            elif "fillColor" in attributes:
                color = attributes["fillColor"]
                paletteIndex, a = _find_or_insert_color(color, palette)
                paint = dict(
                    Format=PaintFormat.PaintSolid, Alpha=a, PaletteIndex=paletteIndex
                )
            else:
                raise NotImplementedError(
                    f"Unsupported color layer path attributes in '{glyph.name}'"
                )

            paintGlyph = dict(
                Format=PaintFormat.PaintGlyph, Glyph=layerGlyphName, Paint=paint
            )
            colorLayers.append(paintGlyph)
        layerMapping[glyph.name] = dict(Format=1, Layers=colorLayers)

    if palette[0]:
        for p in ufo.lib.setdefault(UFO2FT_COLOR_PALETTES_KEY, [[]]):
            p.extend(palette[0])


def to_ufo_color_layers(self, ufo, master):
    layerMapping = {}
    _to_ufo_color_palette_layers(self, master, layerMapping)
    _to_ufo_color_layers(self, ufo, master, layerMapping)
    if layerMapping:
        ufo.lib[UFO2FT_COLOR_LAYERS_KEY] = layerMapping
