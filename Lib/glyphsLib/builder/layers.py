# Copyright 2015 Google Inc. All Rights Reserved.
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

import re

from .constants import (
    FOREGROUND_LAYER_ID_KEY,
    GLYPHS_PREFIX,
    LAYER_ID_KEY,
    LAYER_ORIGINAL_NAME_KEY,
)

LAYER_ORDER_PREFIX = GLYPHS_PREFIX + "layerOrderInGlyph."
LAYER_ORDER_TEMP_USER_DATA_KEY = "__layerOrder"


def to_ufo_layer(self, glyph, layer):
    glyphs_layers = self.font.glyphs[glyph.name].layers
    ufo_font = self._sources[layer.associatedMasterId or layer.layerId].font

    if layer.associatedMasterId == layer.layerId:
        ufo_layer = ufo_font.layers.defaultLayer
    else:
        # Find foreground layer and use the same name as a base for the
        # background layer name.
        layer_name = next(
            (
                l.name
                for l in ufo_font.layers
                if l.lib.get(LAYER_ID_KEY) == layer.layerId
            ),
            None,
        )
        if layer_name is None and layer.name in ufo_font.layers:
            ufo_layer = ufo_font.layers[layer.name]
        elif layer_name is None:
            ufo_layer = ufo_font.newLayer(layer.name)
        else:
            ufo_layer = ufo_font.layers[layer_name]

    if LAYER_ID_KEY not in ufo_layer.lib and self.minimize_glyphs_diffs:
        ufo_layer.lib[LAYER_ID_KEY] = layer.layerId

    # Store the layer order when color layers are present or when minimizing
    # Glyphs diffs.
    if (
        any([re.match(r"^Color \d+$", l.name) for l in glyphs_layers])
        or self.minimize_glyphs_diffs
    ):
        ufo_layer.lib[LAYER_ORDER_PREFIX + glyph.name] = _layer_order_in_glyph(
            self, layer
        )
    return ufo_layer


def to_ufo_background_layer(self, glyph, layer):
    ufo_font = self._sources[layer.associatedMasterId or layer.layerId].font
    if layer.associatedMasterId == layer.layerId:
        layer_name = "public.background"
    else:
        # Find foreground layer and use the same name as a base for the
        # background layer name.
        foreground_name = next(
            (
                l.name
                for l in ufo_font.layers
                if l.lib.get(LAYER_ID_KEY) == layer.layerId
            ),
            None,
        )
        if foreground_name is None:
            layer_name = f"{layer.name}.background"
        else:
            layer_name = f"{foreground_name}.background"

    if layer_name not in ufo_font.layers:
        background_layer = ufo_font.newLayer(layer_name)
    else:
        background_layer = ufo_font.layers[layer_name]

    return background_layer


def _layer_order_in_glyph(self, layer):
    # TODO: optimize?
    for order, glyph_layer in enumerate(layer.parent.layers.values()):
        if glyph_layer is layer:
            return order
    return None


def to_glyphs_layer(self, ufo_layer, glyph, master):
    if ufo_layer is self._sources[master.id].font.layers.defaultLayer:
        layer = _get_or_make_foreground(self, glyph, master)
    elif ufo_layer.name == "public.background":
        master_layer = _get_or_make_foreground(self, glyph, master)
        layer = master_layer.background
    elif ufo_layer.name.endswith(".background"):
        # Find or create the foreground layer
        if FOREGROUND_LAYER_ID_KEY in ufo_layer.lib:
            foreground_layerId = ufo_layer.lib[FOREGROUND_LAYER_ID_KEY]
            foreground_layer = next(
                (
                    l
                    for l in self._sources[master.id].font.layers
                    if (l.lib.get(LAYER_ID_KEY) == foreground_layerId)
                ),
                None,
            )
            assert foreground_layer is not None
            foreground_name = foreground_layer.lib.get(LAYER_ORIGINAL_NAME_KEY)
        else:
            foreground_layerId = None
            foreground_name = None

        if foreground_name is None:
            foreground_name = ufo_layer.name[: -len(".background")]

        foreground = next(
            (
                l
                for l in glyph.layers
                if (foreground_layerId is None or foreground_layerId == l.layerId)
                and l.name == foreground_name
                and l.associatedMasterId == master.id
            ),
            None,
        )
        if foreground is None:
            foreground = self.glyphs_module.GSLayer()
            foreground.name = foreground_name
            foreground.associatedMasterId = master.id
        layer = foreground.background
        # Background layers don't have an associated master id nor a name nor an id
    else:
        layer = next(
            (
                l
                for l in glyph.layers
                if l.name == ufo_layer.name and l.associatedMasterId == master.id
            ),
            None,
        )
        if layer is None:
            layer = self.glyphs_module.GSLayer()

        layer.associatedMasterId = master.id
        if LAYER_ID_KEY in ufo_layer.lib:
            layer.layerId = ufo_layer.lib[LAYER_ID_KEY]
        else:
            # Try to find the layerId associated with the ufo_layer and use it
            layerId = next(
                (
                    l.layerId
                    for g in self.font.glyphs
                    for l in g.layers
                    if l.name == ufo_layer.name and l.associatedMasterId == master.id
                ),
                None,
            )
            if layerId:
                layer.layerId = layerId
        if LAYER_ORIGINAL_NAME_KEY in ufo_layer.lib:
            layer.name = ufo_layer.lib[LAYER_ORIGINAL_NAME_KEY]
        else:
            layer.name = ufo_layer.name
        glyph.layers.append(layer)
    order_key = LAYER_ORDER_PREFIX + glyph.name
    if order_key in ufo_layer.lib:
        order = ufo_layer.lib[order_key]
        layer.userData[LAYER_ORDER_TEMP_USER_DATA_KEY] = order
    return layer


def _get_or_make_foreground(self, glyph, master):
    layer = glyph.layers[master.id]
    if layer is None:
        layer = glyph.layers[master.id] = self.glyphs_module.GSLayer()
    layer.layerId = master.id
    layer.name = master.name
    return layer


def to_glyphs_layer_order(self, glyph):
    # TODO: (jany) ask for the rules of layer ordering inside a glyph
    # For now, order according to key in lib
    glyph.layers = sorted(glyph.layers, key=_layer_order)
    for layer in glyph.layers:
        if LAYER_ORDER_TEMP_USER_DATA_KEY in layer.userData:
            del layer.userData[LAYER_ORDER_TEMP_USER_DATA_KEY]


def _layer_order(layer):
    if LAYER_ORDER_TEMP_USER_DATA_KEY in layer.userData:
        return layer.userData[LAYER_ORDER_TEMP_USER_DATA_KEY]
    return float("inf")
