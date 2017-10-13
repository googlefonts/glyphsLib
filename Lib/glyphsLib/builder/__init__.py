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

import logging

from glyphsLib import classes
from glyphsLib.util import clear_data
import defcon

from .context import UFOToGlyphsContext, GlyphsToUFOContext
from .constants import PUBLIC_PREFIX, GLYPHS_PREFIX

# Existing
from .kerning import add_glyph_to_groups, add_groups_to_ufo, load_kerning
from .anchors import propagate_font_anchors, propagate_glyph_anchors
from .glyph import load_glyph
from .features import to_ufo_features

# Re-organized by feature
from .font import to_ufo_font_attributes, to_glyphs_font_attributes

logger = logging.getLogger(__name__)


def to_ufos(font, include_instances=False, family_name=None,
            propagate_anchors=True, debug=False, defcon=defcon):
    """Take .glyphs file data and load it into UFOs.

    Takes in data as Glyphs.app-compatible classes, as documented at
    https://docu.glyphsapp.com/

    If include_instances is True, also returns the parsed instance data.

    If family_name is provided, the master UFOs will be given this name and
    only instances with this name will be returned.

    If debug is True, returns unused input data instead of the resulting UFOs.
    """

    context = GlyphsToUFOContext(font, defcon=defcon)

    # check that source was generated with at least stable version 2.3
    # https://github.com/googlei18n/glyphsLib/pull/65#issuecomment-237158140
    if int(font.appVersion) < 895:
        logger.warn('This Glyphs source was generated with an outdated version '
                    'of Glyphs. The resulting UFOs may be incorrect.')

    source_family_name = font.familyName
    if family_name is None:
        # use the source family name, and include all the instances
        family_name = source_family_name
        do_filter_instances_by_family = False
    else:
        # use a custom 'family_name' to name master UFOs, and only build
        # instances with matching 'familyName' custom parameter
        do_filter_instances_by_family = True
        if family_name == source_family_name:
            # if the 'family_name' provided is the same as the source, only
            # include instances which do _not_ specify a custom 'familyName'
            instance_family_name = None
        else:
            instance_family_name = family_name

    kerning_groups = {}

    # stores background data from "associated layers"
    supplementary_layer_data = []

    # TODO(jamesgk) maybe create one font at a time to reduce memory usage
    to_ufo_font_attributes(context, family_name)

    # get the 'glyphOrder' custom parameter as stored in the lib.plist.
    # We assume it's the same for all ufos.
    first_ufo = next(iter(context.ufos.values()))
    glyphOrder_key = PUBLIC_PREFIX + 'glyphOrder'
    if glyphOrder_key in first_ufo.lib:
        glyph_order = first_ufo.lib[glyphOrder_key]
    else:
        glyph_order = []
    sorted_glyphset = set(glyph_order)

    for glyph in font.glyphs:
        add_glyph_to_groups(kerning_groups, glyph)
        glyph_name = glyph.name
        if glyph_name not in sorted_glyphset:
            # glyphs not listed in the 'glyphOrder' custom parameter but still
            # in the font are appended after the listed glyphs, in the order
            # in which they appear in the source file
            glyph_order.append(glyph_name)

        for layer in glyph.layers.values():
            layer_id = layer.layerId
            layer_name = layer.name

            assoc_id = layer.associatedMasterId
            if assoc_id != layer.layerId:
                if layer_name is not None:
                    supplementary_layer_data.append(
                        (assoc_id, glyph_name, layer_name, layer))
                continue

            ufo = context.ufos[layer_id]
            ufo_glyph = ufo.newGlyph(glyph_name)
            load_glyph(context, ufo_glyph, layer, glyph)

    for layer_id, glyph_name, layer_name, layer_data \
            in supplementary_layer_data:
        ufo_font = context.ufos[layer_id]
        if layer_name not in ufo_font.layers:
            ufo_layer = ufo_font.newLayer(layer_name)
        else:
            ufo_layer = ufo_font.layers[layer_name]
        ufo_glyph = ufo_layer.newGlyph(glyph_name)
        load_glyph(context, ufo_glyph, layer_data, layer_data.parent)

    for ufo in context.ufos.values():
        ufo.lib[glyphOrder_key] = glyph_order
        if propagate_anchors:
            propagate_font_anchors(ufo)
        to_ufo_features(context, ufo)
        add_groups_to_ufo(ufo, kerning_groups)

    for master_id, kerning in font.kerning.items():
        load_kerning(context.ufos[master_id], kerning)

    result = list(context.ufos.values())

    instances = font.instances
    if do_filter_instances_by_family:
        instances = list(filter_instances_by_family(instances,
                                                    instance_family_name))
    instance_data = {'data': instances}

    # the 'Variation Font Origin' is a font-wide custom parameter, thus it is
    # shared by all the master ufos; here we just get it from the first one
    varfont_origin_key = "Variation Font Origin"
    varfont_origin = first_ufo.lib.get(GLYPHS_PREFIX + varfont_origin_key)
    if varfont_origin:
        instance_data[varfont_origin_key] = varfont_origin
    if debug:
        return clear_data(font)
    elif include_instances:
        return result, instance_data
    return result


def to_glyphs(ufos, designspace=None, classes=classes):
    """
    Take a list of UFOs and combine them into a single .glyphs file.

    This should be the inverse function of `to_ufos`,
    so we should have to_glyphs(to_ufos(font)) == font
    """
    context = UFOToGlyphsContext(ufos, designspace, classes)
    context.font = classes.GSFont()
    for index, ufo in enumerate(ufos):
        master = classes.GSFontMaster()
        to_glyphs_font_attributes(context, ufo, master,
                                  is_initial=(index == 0))
        context.font.masters.insert(len(context.font.masters), master)
        # TODO: all the other stuff!
    return context.font


def filter_instances_by_family(instances, family_name=None):
    """Yield instances whose 'familyName' custom parameter is
    equal to 'family_name'.
    """
    for instance in instances:
        familyName = None
        for p in instance.customParameters:
            param, value = p.name, p.value
            if param == 'familyName':
                familyName = value
        if familyName == family_name:
            yield instance

