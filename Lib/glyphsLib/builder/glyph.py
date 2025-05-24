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


from typing import Any, Dict, List, Optional, Tuple, Union
import itertools
import logging

import glyphsLib.glyphdata

try:
    from GlyphsApp import GSFontMaster, GSGlyph, GSLayer, GSPath, GSComponent, GSBackgroundLayer
except ImportError:
    from .. import GSFontMaster, GSGlyph, GSLayer, GSPath, GSComponent, GSBackgroundLayer
from .common import from_loose_ufo_time, to_glyphs_time
from .constants import (
    GLYPHLIB_PREFIX,
    GLYPHS_COLORS,
    UFO2FT_COLOR_LAYER_MAPPING_KEY,
    BRACKET_GLYPH_RE,
    BRACKET_GLYPH_SUFFIX_RE,
    SCRIPT_LIB_KEY,
    SHAPE_ORDER_LIB_KEY,
    ORIGINAL_WIDTH_KEY,
    BACKGROUND_WIDTH_KEY,
    POSTSCRIPT_NAMES_KEY,
    PUBLIC_PREFIX,
    LAYER_ID_KEY,
    GLYPHS_PREFIX,
)
from glyphsLib.classes import LAYER_ATTRIBUTE_COLOR
from glyphsLib.types import floatToString3
from glyphsLib.glyphdata import GSGlyphInfo
from ufoLib2.objects import Glyph as UFOGlyph
from ufoLib2.objects import Layer as UFOLayer
logger = logging.getLogger(__name__)


def _clone_layer(layer: GSLayer, paths: Optional[List[GSPath]] = None,
                 components: Optional[List[GSComponent]] = None) -> GSLayer:
    """Clone a GSLayer while optionally replacing paths and components."""
    paths = paths if paths is not None else []
    components = components if components is not None else []
    if len(paths) == len(layer.paths) and len(components) == len(layer.components):
        return layer
    new_layer = GSLayer()
    new_layer.associatedMasterId = layer.associatedMasterId
    new_layer.parent = layer.parent
    new_layer.paths = paths
    new_layer.components = components
    new_layer.attributes = layer.attributes
    return new_layer


# Map of ".uvNNN" extensions to Unicode Variation Selector code points.
# If a glyph name ends with ".uvNNN" with NNN ranging from 001 to 256, then it
# is a variation sequence with uv001 being U+0xFE00 and uv256 being U+0xE01EF.
#
# The only documentation for this is the "More Improvements" section in Glyphs
# 2.6.1 announcement:
# https://glyphsapp.com/news/glyphs-2-6-1-released
# And this forum post:
# https://forum.glyphsapp.com/t/unicode-variation-selector-u-fe01/21701
USV_MAP: Dict[str, str] = {
    f".uv{i + 1:03}": f"{c:04X}"
    for i, c in enumerate(
        itertools.chain(range(0xFE00, 0xFE0F + 1), range(0xE0100, 0xE01EF + 1))
    )
}

USV_EXTENSIONS: Tuple[str, ...] = tuple(USV_MAP.keys())


def to_ufo_shapes(self, ufo_glyph: Any, layer: GSLayer) -> None:
    # NOTE: The UFO v3 and Glyphs data model have incompatible component reference
    # semantics. UFO components always point to a glyph in the same layer, Glyphs
    # components in a ...:
    #  - master layer: point to glyphs in the same master layer.
    #  - non-master layer: point to glyphs in the layer with the same layerKey and fall
    #    back to glyphs in the associated master layer
    # There are some valid use-cases for components in non-master layers, and doing it
    # thoroughly correctly is time-consuming, so we're decomposing just the background
    # layer components as a band-aid.
    if layer.components and isinstance(layer, GSBackgroundLayer):
        logger.warning(
            f"Glyph '{ufo_glyph.name}': All components of the background layer of "
            f"'{layer.foreground.name}' will be decomposed."
        )
        self.to_ufo_components_nonmaster_decompose(ufo_glyph, layer)
        return

    # Store shape order for mixed glyphs
    shape_order_lib_key = ""

    for shape in layer.shapes:
        if isinstance(shape, GSPath):
            self.to_ufo_path(ufo_glyph, shape)
            shape_order_lib_key += "P"
        elif isinstance(shape, GSComponent):
            self.to_ufo_component(ufo_glyph, shape)
            shape_order_lib_key += "C"
        else:
            raise ValueError(f"Unknown shape type {shape}")

    if "P" in shape_order_lib_key and "C" in shape_order_lib_key:
        ufo_glyph.lib[SHAPE_ORDER_LIB_KEY] = shape_order_lib_key


def to_ufo_glyph(self, ufo_glyph: UFOGlyph, layer: GSLayer, glyph: GSGlyph, do_color_layers: bool = True) -> None:  # noqa: C901
    """Add .glyphs metadata, paths, components, and anchors to a glyph."""
    assert layer.associatedMasterId  # gs TODO: remove the `or layer.layerId`
    ufo_font = self._sources[layer.associatedMasterId or layer.layerId].font

    if layer.isMasterLayer and do_color_layers:
        self.to_ufo_glyph_color(ufo_glyph, layer, glyph)
    if glyph.unicodes:
        ufo_glyph.unicodes = [int(uval, 16) for uval in glyph.unicodes]

    export: bool = glyph.export
    if not export:
        if self.write_skipexportglyphs:
            skip_export_glyphs = self._designspace.lib.setdefault("public.skipExportGlyphs", [])
            skip_export_glyphs.append(glyph.name)
        else:
            ufo_glyph.lib[GLYPHLIB_PREFIX + "Export"] = export

    # If glyph name ends with ".uvNNN" find and the font has a glyph with the
    # same name without the ".uvNNN", then add a Unicode Variation Sequence
    # entry with the Unicode Variation Selector corresponding to the extension
    # and the unicode of the base glyph.
    if export and "." in glyph.name and glyph.name.endswith(USV_EXTENSIONS):
        base_name, ext = glyph.name.rsplit(".", 1)
        if base_name in glyph.parent.glyphs and glyph.parent.glyphs[base_name].unicode:
            uni = glyph.parent.glyphs[base_name].unicode
            usv = USV_MAP[f".{ext}"]
            USV_KEY = PUBLIC_PREFIX + "unicodeVariationSequences"
            ufo_font.lib.setdefault(USV_KEY, {}).setdefault(usv, {})[uni] = glyph.name

    # we can't use use the glyphs.unicodes values since they aren't always
    # correctly padded
    glyph_name = ufo_glyph.name
    if not glyph_name:
        return
    unicodes = [f"{c:04X}" for c in ufo_glyph.unicodes]
    # FIXME: (jany) next line should be an API of GSGlyph?
    glyphinfo: GSGlyphInfo = glyphsLib.glyphdata.get_glyph(glyph_name, unicodes=unicodes)

    if self.glyphdata is not None:
        custom: GSGlyphInfo = glyphsLib.glyphdata.get_glyph(
            glyph_name, self.glyphdata, unicodes=unicodes
        )
        production_name: Optional[str] = glyph.productionName or (
            custom.productionName
            if custom.productionName != glyphinfo.productionName
            else None
        )
        category: Optional[str] = glyph.category or (
            custom.category if custom.category != glyphinfo.category else None
        )
        subCategory: Optional[str] = glyph.subCategory or (
            custom.subCategory if custom.subCategory != glyphinfo.subCategory else None
        )
        script: Optional[str] = glyph.script or (
            custom.script if custom.script != glyphinfo.script else None
        )
    else:
        production_name, category, subCategory, script = (
            glyph.productionName,
            glyph.category,
            glyph.subCategory,
            glyph.script,
        )

    production_name = production_name or glyphinfo.productionName

    glyph_name = ufo_glyph.name
    if production_name and glyph_name:
        # Ensure production name get the correct suffix
        bracket_glyph_name = BRACKET_GLYPH_RE.match(glyph_name)
        prod_bracket_glyph_name = BRACKET_GLYPH_RE.match(production_name)
        if bracket_glyph_name and not prod_bracket_glyph_name:
            match = BRACKET_GLYPH_SUFFIX_RE.match(glyph_name)
            if match:
                production_name += match.group(1)

    if production_name and production_name != glyph_name:
        ufo_font.lib.setdefault(POSTSCRIPT_NAMES_KEY, {})[glyph_name] = production_name

    if script is not None:
        ufo_glyph.lib[SCRIPT_LIB_KEY] = script

    # if glyph contains custom 'category' and 'subCategory' overrides, store
    # them in the UFO glyph's lib
    if category is not None:
        ufo_glyph.lib[GLYPHLIB_PREFIX + "category"] = category
    else:
        category = glyphinfo.category
    if subCategory is not None:
        ufo_glyph.lib[GLYPHLIB_PREFIX + "subCategory"] = subCategory
    else:
        subCategory = glyphinfo.subCategory

    # Load width before background, which is loaded with lib data

    width: float = effective_width(layer, glyph)
    if category == "Mark" and subCategory == "Nonspacing" and width > 0:
        # zero the width of Nonspacing Marks like Glyphs.app does on export
        # TODO: (jany) check for customParameter DisableAllAutomaticBehaviour
        # FIXME: (jany) also don't do that when rt UFO -> glyphs -> UFO
        ufo_glyph.lib[ORIGINAL_WIDTH_KEY] = width
        ufo_glyph.width = 0
    else:
        ufo_glyph.width = width

    if not self.minimal:
        to_ufo_glyph_round_tripping(ufo_glyph, glyph, layer)  # below
        self.to_ufo_background_image(ufo_glyph, layer)  # .background_image
        self.to_ufo_guidelines(ufo_glyph, layer)  # .guidelines
        self.to_ufo_glyph_background(ufo_glyph, layer)  # below
        self.to_ufo_annotations(ufo_glyph, layer)  # .annotations
        self.to_ufo_smart_component_axes(ufo_glyph, glyph)  # .components

        if glyph.tags:
            ufo_glyph.lib[GLYPHLIB_PREFIX + "tags"] = glyph.tags

        if layer.smartComponentPoleMapping:
            ufo_glyph.lib[GLYPHLIB_PREFIX + "smartComponentPoleMapping"] = dict(layer.smartComponentPoleMapping)

        if not layer.isMasterLayer:
            ufo_glyph.lib[LAYER_ID_KEY] = layer.layerId
        if layer.attributes:
            ufo_glyph.lib[GLYPHS_PREFIX + "layer.attributes"] = dict(layer.attributes)

    self.to_ufo_glyph_user_data(ufo_font, ufo_glyph, glyph)  # .user_data
    self.to_ufo_layer_user_data(ufo_glyph, layer)  # .user_data

    # Optimization: profiling glyphs2ufo of NotoSans-MM.glyphs (6000 glyphs) on a Mac
    # mini late 2014, Python 3.6.8, revealed that a whopping 17% of the time was spent
    # converting lastChange to UFO timestamps. I could not reproduce this on a Windows
    # 10/Python 3.7 setup, so this might be a platform thing. If-guarding anyway
    # because these timestamps are useless in a UFO scenario if you use Git.

    # This *should* be gated with not self.minimal, but that breaks regression tests
    if (
        self.minimize_glyphs_diffs
        and glyph.parent.customParameters["Disable Last Change"] is not True
        and glyph.lastChange is not None
    ):
        ufo_glyph.lib[GLYPHLIB_PREFIX + "lastChange"] = to_glyphs_time(glyph.lastChange)

    self.to_ufo_hints(ufo_glyph, layer)  # .hints

    self.to_ufo_shapes(ufo_glyph, layer)

    self.to_ufo_glyph_anchors(ufo_glyph, layer.anchors)  # .anchors

    if self.is_vertical:
        self.to_ufo_glyph_height_and_vertical_origin(ufo_glyph, layer)  # below

    if glyph.bottomKerningGroup:
        ufo_glyph.lib[GLYPHLIB_PREFIX + "kernBottom"] = glyph.bottomKerningGroup
    if glyph.topKerningGroup:
        ufo_glyph.lib[GLYPHLIB_PREFIX + "kernTop"] = glyph.topKerningGroup

    if layer.attributes.get("hasOverlap", False):
        ufo_glyph.lib["public.truetype.overlap"] = True


def to_ufo_glyph_round_tripping(ufo_glyph: Any, glyph: GSGlyph, layer: GSLayer) -> None:
    """Store additional glyph metadata for round tripping."""
    # ufo_glyph: ufoLib2.objects.glyph.Glyph

    if glyph.note:
        ufo_glyph.note = glyph.note

    color_index = glyph.color
    if color_index is not None:
        # .3f is enough precision to round-trip uint8 to float losslessly.
        # https://github.com/unified-font-object/ufo-spec/issues/61
        # #issuecomment-389759127
        if (
            isinstance(color_index, list)
            and len(color_index) == 4
            and all(0 <= v < 256 for v in color_index)
        ):
            ufo_glyph.markColor = ",".join(
                floatToString3(v / 255.0) for v in color_index
            )
        elif isinstance(color_index, int) and color_index in range(len(GLYPHS_COLORS)):
            ufo_glyph.markColor = GLYPHS_COLORS[color_index]
        else:
            logger.warning(f"Glyph {glyph.name}, layer {layer.name}: Invalid color index/tuple {color_index}")

    color_index = layer.color
    if color_index is not None:
        ufo_glyph.lib[GLYPHLIB_PREFIX + "ColorIndexLayer"] = color_index

    for key in ["leftMetricsKey", "rightMetricsKey", "widthMetricsKey"]:
        value = getattr(layer, key, None)
        if value:
            ufo_glyph.lib[GLYPHLIB_PREFIX + "layer." + key] = value
        value = getattr(glyph, key, None)
        if value:
            ufo_glyph.lib[GLYPHLIB_PREFIX + key] = value


def effective_width(layer: GSLayer, glyph: GSGlyph) -> float:
    """
    The width may be taken from another master via the customParameters
    'Link Metrics With Master' or 'Link Metrics With First Master'.
    """

    font = glyph.parent
    master = font.masters[layer.layerId]
    if master:
        metrics_source = master.metricsSource
        if metrics_source:
            metric_layer = font.glyphs[glyph.name].layers[metrics_source.id]
            if metric_layer:
                width = metric_layer.width
                if layer.width != width:
                    logger.debug(
                        f"{layer.parent.name}: Applying width from master "
                        f"'{metrics_source.id}': {layer.width} -> {width}"
                    )
                return width or 0
    return layer.width or 0


def to_ufo_glyph_color(
    self, ufo_glyph: Any, layer: "GSLayer", glyph: "GSGlyph", do_color_layers: bool = True
) -> None:
    # Here we handle color layers. If this is a master layer and the glyph
    # has color layers, add ufo2ft lib key with the layer mapping.

    # There are two kinds of color layers: first, color palette layers that
    # are handled below, which are used to build COLRv0 table. For color
    # palette layers, the layer mapping is a tuple of (layer name, palette
    # index), but we don’t know the final UFO layer names yet, so we use
    # Glyphs layer IDs and change them to layer names in
    # to_ufo_color_layer_names().
    # When building minimal UFOs, we instead collect color layers and later
    # add them as separate glyphs to the UFO font.

    masterId: str = layer.associatedMasterId
    if any(
        l.associatedMasterId == masterId and l.isColorPaletteLayer
        for layerId, l in glyph._layers.items()
    ):
        layerMapping: List[Tuple[str, int]] = [
            (l.layerId, l._color_palette_index())
            for layerId, l in glyph._layers.items()
            if l.isColorPaletteLayer
            and l.associatedMasterId == layer.associatedMasterId
        ]

        if not self.minimal:
            ufo_glyph.lib[UFO2FT_COLOR_LAYER_MAPPING_KEY] = layerMapping
        elif glyph.export:
            palette_layers: List[Tuple[GSLayer, int]] = [
                (glyph.layers[layerId], colorId) for layerId, colorId in layerMapping
            ]
            self._color_palette_layers.append(((glyph, layer), palette_layers))

    if self.minimal:
        # The other kind of color layers supports solid colors and
        # gradients among other things, and we use it to build COLRv1
        # table.
        # For each color layer, we collect paths that has the same
        # attributes, then we make a clone of the layer for each group with
        # only the paths in this group. We do this splitting because a
        # COLRv1 layer can’t have multiple gradients or colors.
        color_layers: List[GSLayer] = [
            l
            for l in glyph.layers
            if l.attributes.get(LAYER_ATTRIBUTE_COLOR)
            and l.associatedMasterId == layer.associatedMasterId
        ]
        if color_layers:
            layers: List[GSLayer] = []
            for color_layer in color_layers:
                # Group consecutive paths with same attributes together.
                groups: List[List[GSPath]] = [
                    list(g)
                    for _, g in itertools.groupby(
                        color_layer.paths, key=lambda p: p.attributes
                    )
                ]
                for paths in groups:
                    layers.append(_clone_layer(color_layer, paths=paths))

                # Group components based on whether component glyph has
                # color layers or not.
                component_groups: List[Tuple[bool, List[GSComponent]]] = [
                    (k, list(g))
                    for k, g in itertools.groupby(
                        color_layer.components,
                        key=lambda c: any(
                            l.attributes.get(LAYER_ATTRIBUTE_COLOR)
                            for l in c.component.layers
                            if l.associatedMasterId == layer.associatedMasterId
                        ),
                    )
                ]
                for has_color, components in component_groups:
                    if not has_color:
                        new_layer: GSLayer = _clone_layer(color_layer, components=components)
                        new_layer.attributes = {}
                        layers.append(new_layer)
                    else:
                        for c in components:
                            layers.append(_clone_layer(color_layer, components=[c]))

            self._color_layers.append(((glyph, layer), layers))


def to_ufo_glyph_height_and_vertical_origin(self, ufo_glyph: UFOGlyph, layer: GSLayer) -> None:
    # implentation based on:
    # https://github.com/googlefonts/glyphsLib/issues/557#issuecomment-667074856

    assert self.is_vertical

    ascender, descender = _get_typo_ascender_descender(layer.master)

    if layer.vertWidth is not None:
        ufo_glyph.height = layer.vertWidth
    else:
        ufo_glyph.height = ascender - descender

    if layer.vertOrigin is not None:
        ufo_glyph.verticalOrigin = ascender - layer.vertOrigin
    else:
        ufo_glyph.verticalOrigin = ascender


def _get_typo_ascender_descender(master: GSFontMaster) -> Tuple[Union[int, float], Union[int, float]]:
    """Glyphsapp will use the typo metrics to set the vertOrigin and
    vertWidth. If typo metrics are not present, the master
    ascender and descender are used instead."""

    if "typoAscender" in master.customParameters:
        ascender = master.customParameters["typoAscender"]
    else:
        ascender = master.ascender
    if "typoDescender" in master.customParameters:
        descender = master.customParameters["typoDescender"]
    else:
        descender = master.descender
    return ascender, descender


def to_ufo_glyph_background(self, glyph: "GSGlyph", layer: "GSLayer") -> None:
    """Set glyph background layer."""
    if not layer.hasBackground:
        return

    background: GSBackgroundLayer = layer.background
    ufo_layer = self.to_ufo_background_layer(layer)
    ufo_glyph = ufo_layer.newGlyph(glyph.name)

    width: Optional[Union[int, float]] = background.userData[BACKGROUND_WIDTH_KEY]
    if width is not None:
        ufo_glyph.width = width

    self.to_ufo_background_image(ufo_glyph, background)
    self.to_ufo_shapes(ufo_glyph, background)
    self.to_ufo_glyph_anchors(ufo_glyph, background.anchors)
    self.to_ufo_guidelines(ufo_glyph, background)


# UFO to Glyphs


def to_glyphs_glyph(self, ufo_glyph: UFOGlyph, ufo_layer: UFOLayer, master: GSFontMaster) -> None:  # noqa: C901
    """Add UFO glif metadata, paths, components, and anchors to a GSGlyph.
    If the matching GSGlyph does not exist, then it is created,
    else it is updated with the new data.
    In all cases, a matching GSLayer is created in the GSGlyph to hold paths.
    """
    # FIXME: (jany) split between glyph and layer attributes
    #        have a write the first time, compare the next times for glyph
    #        always write for the layer

    # NOTE: This optimizes around the performance drain that is glyph name lookup
    #       without replacing the actual data structure. Ideally, FontGlyphsProxy
    #       provides O(1) lookup for all the ways you can use strings to look up
    #       glyphs.

    ufo_glyph_name = ufo_glyph.name

    assert ufo_glyph_name

    glyph: Optional[GSGlyph] = self.font.glyphs[ufo_glyph_name]

    if glyph is None:
        glyph = GSGlyph(name=ufo_glyph_name)
        # FIXME: (jany) ordering? gs: sort after loading from 'public.glyphOrder'
        self.font.glyphs.append(glyph)

    if ufo_glyph.unicodes:
        glyph.unicodes = [f"{c:04X}" for c in ufo_glyph.unicodes]
    if ufo_glyph.note:
        glyph.note = ufo_glyph.note
    if GLYPHLIB_PREFIX + "lastChange" in ufo_glyph.lib:
        last_change: str = ufo_glyph.lib[GLYPHLIB_PREFIX + "lastChange"]
        # We cannot be strict about the dateformat because it's not an official
        # UFO field mentioned in the spec, so it could happen to have a timezone
        glyph.lastChange = from_loose_ufo_time(last_change)
    if ufo_glyph.markColor:
        glyph.color = _to_glyphs_color(ufo_glyph.markColor)

    # The export flag can be stored in the glyph's lib key (for upgrading legacy
    # sources) or the Designspace-level public.skipExportGlyphs lib key (canonical
    # place to store the information). The UFO level lib key is ignored.
    if GLYPHLIB_PREFIX + "Export" in ufo_glyph.lib:
        glyph.export = ufo_glyph.lib[GLYPHLIB_PREFIX + "Export"]
    if ufo_glyph.name in self.skip_export_glyphs:
        glyph.export = False

    ufo_font = self._sources[master.id].font
    if POSTSCRIPT_NAMES_KEY in ufo_font.lib and ufo_glyph.name in ufo_font.lib[POSTSCRIPT_NAMES_KEY]:
        glyph.production = ufo_font.lib[POSTSCRIPT_NAMES_KEY][ufo_glyph.name]
        # FIXME: (jany) maybe put something in glyphinfo? No, it's readonly
        #        maybe don't write in glyph.production if glyphinfo already
        #        has something
        # glyphinfo = glyphsLib.glyphdata.get_glyph(ufo_glyph.name)
        # production_name = glyph.production or glyphinfo.production_name

    glyphinfo = glyphsLib.glyphdata.get_glyph(ufo_glyph_name)  # FIXME: load glyphInfo at the end, not for each layer?

    layer: GSLayer = self.to_glyphs_layer(ufo_layer, ufo_glyph, glyph, master)

    for key in ["leftMetricsKey", "rightMetricsKey", "widthMetricsKey", "topMetricsKey", "bottomMetricsKey"]:
        # Also read the old version of the key that didn't have a prefix and
        # store it on the layer (because without the "glyph"/"layer" prefix we
        # didn't know whether it originally came from the layer of the glyph,
        # so it's easier to put it back on the most specific level, i.e. the
        # layer)
        for prefix, glyphs_object in (
            ("", glyph),
            ("layer.", layer)
        ):
            full_key = GLYPHLIB_PREFIX + prefix + key
            if full_key in ufo_glyph.lib:
                value: Any = ufo_glyph.lib[full_key]
                setattr(glyphs_object, key, value)

    if SCRIPT_LIB_KEY in ufo_glyph.lib:
        glyph.script = ufo_glyph.lib[SCRIPT_LIB_KEY]

    if GLYPHLIB_PREFIX + "category" in ufo_glyph.lib:
        # TODO: (jany) store category only if different from glyphinfo?
        category = ufo_glyph.lib[GLYPHLIB_PREFIX + "category"]
        glyph.category = category
    else:
        category = glyphinfo.category
    if GLYPHLIB_PREFIX + "subCategory" in ufo_glyph.lib:
        sub_category = ufo_glyph.lib[GLYPHLIB_PREFIX + "subCategory"]
        glyph.subCategory = sub_category
    else:
        sub_category = glyphinfo.subCategory

    if hasattr(layer, "foreground"):
        width: Optional[Union[int, float]] = ufo_glyph.width
        if width:
            # Don't store "0", it's the default in UFO.
            # Store in userData because the background's width is not relevant
            # in Glyphs.
            layer.userData[BACKGROUND_WIDTH_KEY] = width
    else:
        layer.width = ufo_glyph.width

    if category == "Mark" and sub_category == "Nonspacing" and layer.width == 0:
        # Restore originalWidth
        if ORIGINAL_WIDTH_KEY in ufo_glyph.lib:
            layer.width = ufo_glyph.lib[ORIGINAL_WIDTH_KEY]
            # TODO: (jany) check for customParam DisableAllAutomaticBehaviour?

    hasOverlap: Optional[bool] = ufo_glyph.lib.get("public.truetype.overlap")
    if hasOverlap is not None:
        layer.attributes["hasOverlap"] = hasOverlap

    color_index: Optional[int] = ufo_glyph.lib.get(GLYPHLIB_PREFIX + "ColorIndexLayer")
    if color_index is not None:
        layer.color = color_index

    self.to_glyphs_background_image(ufo_glyph, layer)
    self.to_glyphs_guidelines(ufo_glyph, layer)
    self.to_glyphs_annotations(ufo_glyph, layer)
    self.to_glyphs_hints(ufo_glyph, layer)
    self.to_glyphs_glyph_user_data(ufo_font, glyph)
    self.to_glyphs_layer_user_data(ufo_glyph, layer)
    self.to_glyphs_smart_component_axes(ufo_glyph, glyph)

    tags: Optional[List[str]] = ufo_glyph.lib.get(GLYPHLIB_PREFIX + "tags")
    if tags:
        glyph.tags = tags

    self.to_glyphs_paths(ufo_glyph, layer)
    self.to_glyphs_components(ufo_glyph, layer)

    if SHAPE_ORDER_LIB_KEY in ufo_glyph.lib:
        # Reshuffle shapes array to match original shape order
        new_shapes: List[Any] = []
        path_counter: int = 0
        comp_counter: int = 0
        for sign in ufo_glyph.lib[SHAPE_ORDER_LIB_KEY]:
            if sign == "P":
                new_shapes.append(layer.paths[path_counter])
                path_counter += 1
            elif sign == "C":
                new_shapes.append(layer.components[comp_counter])
                comp_counter += 1
            else:
                raise ValueError(f"Unknown shape type {sign}")
        layer.shapes = new_shapes

    kernBottom: Optional[str] = ufo_glyph.lib.get(GLYPHLIB_PREFIX + "kernBottom")
    if kernBottom and not glyph.bottomKerningGroup:
        glyph.bottomKerningGroup = kernBottom

    kernTop: Optional[str] = ufo_glyph.lib.get(GLYPHLIB_PREFIX + "kernTop")
    if kernTop and not glyph.topKerningGroup:
        glyph.topKerningGroup = kernTop

    self.to_glyphs_glyph_anchors(ufo_glyph, layer)
    self.to_glyphs_glyph_height_and_vertical_origin(ufo_glyph, master, layer)

    smartComponentPoleMapping: Optional[Dict[str, Any]] = ufo_glyph.lib.get(GLYPHLIB_PREFIX + "smartComponentPoleMapping")
    if smartComponentPoleMapping:
        layer.smartComponentPoleMapping = smartComponentPoleMapping


def _to_glyphs_color(color: str) -> Union[int, List[int]]:
    """
    If the color matches one of Glyphs's predefined colors, return that index.
    """
    for index, glyphs_color in enumerate(GLYPHS_COLORS):
        if str(color) == glyphs_color:
            return index

    # Otherwise, make a Glyphs-formatted RGBA color list: [u8, u8, u8, u8].
    # Glyphs up to version 2.5.1 always set the alpha channel to 1. It should
    # round-trip the actual value in later versions.
    # https://github.com/googlefonts/glyphsLib/pull/363#issuecomment-390418497
    return [round(float(component) * 255) for component in color.split(",")]


def to_glyphs_glyph_height_and_vertical_origin(self, ufo_glyph: Any, master: "GSFontMaster", layer: "GSLayer") -> None:
    """Convert glyph height and vertical origin to Glyphs format."""
    ascender, descender = _get_typo_ascender_descender(master)
    if ufo_glyph.height != (ascender - descender):
        layer.vertWidth = ufo_glyph.height

    if ufo_glyph.verticalOrigin is not None and ufo_glyph.verticalOrigin != ascender:
        layer.vertOrigin = ascender - ufo_glyph.verticalOrigin
