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

from .constants import UFO2FT_COLOR_LAYERS_KEY


def to_ufo_color_layers(self):
    for (glyph, masterLayer), layers in self._color_palette_layers:
        ufo_font = self._sources[
            masterLayer.associatedMasterId or masterLayer.layerId
        ].font
        colorLayers = []
        for i, (layer, colorId) in enumerate(layers):
            if layer != masterLayer:
                layerGlyphName = f"{glyph.name}.color{i}"
                ufo_layer = self.to_ufo_layer(glyph, masterLayer)
                ufo_glyph = ufo_layer.newGlyph(layerGlyphName)
                self.to_ufo_glyph(ufo_glyph, layer, glyph)
            else:
                layerGlyphName = glyph.name
            colorLayers.append((layerGlyphName, colorId))
        ufo_font.lib.setdefault(UFO2FT_COLOR_LAYERS_KEY, {})[glyph.name] = colorLayers
