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

from __future__ import (print_function, division, absolute_import,
                        unicode_literals)
import logging
logger = logging.getLogger(__name__)

import glyphsLib
from .common import to_ufo_time
from .constants import (GLYPHLIB_PREFIX, GLYPHS_COLORS, GLYPHS_PREFIX,
                        PUBLIC_PREFIX)


def to_ufo_glyph(self, ufo_glyph, layer, glyph_data):
    """Add .glyphs metadata, paths, components, and anchors to a glyph."""
    from glyphsLib import glyphdata  # Expensive import

    uval = glyph_data.unicode
    if uval is not None:
        ufo_glyph.unicode = int(uval, 16)
    note = glyph_data.note
    if note is not None:
        ufo_glyph.note = note
    last_change = glyph_data.lastChange
    if last_change is not None:
        ufo_glyph.lib[GLYPHLIB_PREFIX + 'lastChange'] = to_ufo_time(last_change)
    color_index = glyph_data.color
    if color_index is not None:
        ufo_glyph.lib[GLYPHLIB_PREFIX + 'ColorIndex'] = color_index
        color_tuple = None
        if isinstance(color_index, list):
            if not all(i in range(0, 256) for i in color_index):
                logger.warn('Invalid color tuple {} for glyph {}. '
                            'Values must be in range 0-255'.format(color_index, glyph_data.name))
            else:
                color_tuple = ','.join('{0:.4f}'.format(i/255) if i in range(1, 255) else str(i//255) for i in color_index)
        elif isinstance(color_index, int) and color_index in range(len(GLYPHS_COLORS)):
            color_tuple = GLYPHS_COLORS[color_index]
        else:
            logger.warn('Invalid color index {} for {}'.format(color_index, glyph_data.name))
        if color_tuple is not None:
            ufo_glyph.lib[PUBLIC_PREFIX + 'markColor'] = color_tuple
    export = glyph_data.export
    if not export:
        ufo_glyph.lib[GLYPHLIB_PREFIX + 'Export'] = export
    glyphinfo = glyphdata.get_glyph(ufo_glyph.name)
    production_name = glyph_data.production or glyphinfo.production_name
    if production_name != ufo_glyph.name:
        postscriptNamesKey = PUBLIC_PREFIX + 'postscriptNames'
        if postscriptNamesKey not in ufo_glyph.font.lib:
            ufo_glyph.font.lib[postscriptNamesKey] = dict()
        ufo_glyph.font.lib[postscriptNamesKey][ufo_glyph.name] = production_name

    for key in ['leftMetricsKey', 'rightMetricsKey', 'widthMetricsKey']:
        glyph_metrics_key = getattr(layer, key)
        if glyph_metrics_key is None:
            glyph_metrics_key = getattr(glyph_data, key)
        if glyph_metrics_key:
            ufo_glyph.lib[GLYPHLIB_PREFIX + key] = glyph_metrics_key

    # if glyph contains custom 'category' and 'subCategory' overrides, store
    # them in the UFO glyph's lib
    category = glyph_data.category
    if category is None:
        category = glyphinfo.category
    else:
        ufo_glyph.lib[GLYPHLIB_PREFIX + 'category'] = category
    subCategory = glyph_data.subCategory
    if subCategory is None:
        subCategory = glyphinfo.subCategory
    else:
        ufo_glyph.lib[GLYPHLIB_PREFIX + 'subCategory'] = subCategory

    # load width before background, which is loaded with lib data
    width = layer.width
    if width is None:
        pass
    elif category == 'Mark' and subCategory == 'Nonspacing' and width > 0:
        # zero the width of Nonspacing Marks like Glyphs.app does on export
        # TODO: check for customParameter DisableAllAutomaticBehaviour
        ufo_glyph.lib[GLYPHLIB_PREFIX + 'originalWidth'] = width
        ufo_glyph.width = 0
    else:
        ufo_glyph.width = width
    self.to_ufo_glyph_libdata(ufo_glyph, layer)

    pen = ufo_glyph.getPointPen()
    self.to_ufo_draw_paths(pen, layer.paths)
    self.to_ufo_draw_components(pen, layer.components)
    self.to_ufo_glyph_anchors(ufo_glyph, layer.anchors)


def to_ufo_glyph_background(self, glyph, background):
    """Set glyph background."""

    if not background:
        return

    if glyph.layer.name != 'public.default':
        layer_name = glyph.layer.name + '.background'
    else:
        layer_name = 'public.background'
    font = glyph.font
    if layer_name not in font.layers:
        layer = font.newLayer(layer_name)
    else:
        layer = font.layers[layer_name]
    new_glyph = layer.newGlyph(glyph.name)
    new_glyph.width = glyph.width
    pen = new_glyph.getPointPen()
    self.to_ufo_draw_paths(pen, background.paths)
    self.to_ufo_draw_components(pen, background.components)
    self.to_ufo_glyph_anchors(new_glyph, background.anchors)
    self.to_ufo_guidelines(new_glyph, background)


def to_ufo_glyph_libdata(self, glyph, layer):
    """Add to a glyph's lib data."""

    self.to_ufo_guidelines(glyph, layer)
    self.to_ufo_glyph_background(glyph, layer.background)
    for key in ['annotations', 'hints']:
        try:
            value = getattr(layer, key)
        except KeyError:
            continue
        if key == 'annotations':
            annotations = []
            for an in list(value.values()):
                annot = {}
                for attr in ['angle', 'position', 'text', 'type', 'width']:
                    val = getattr(an, attr, None)
                    if attr == 'position' and val:
                        val = list(val)
                    if val:
                        annot[attr] = val
                annotations.append(annot)
            value = annotations
        elif key == 'hints':
            hints = []
            for hi in value:
                hint = {}
                for attr in ['horizontal', 'options', 'stem', 'type']:
                    val = getattr(hi, attr, None)
                    hint[attr] = val
                for attr in ['origin', 'other1', 'other2', 'place', 'scale',
                             'target']:
                    val = getattr(hi, attr, None)
                    if val is not None and not any(v is None for v in val):
                        hint[attr] = list(val)
                hints.append(hint)
            value = hints

        if value:
            glyph.lib[GLYPHS_PREFIX + key] = value

    # data related to components stored in lists of booleans
    # each list's elements correspond to the components in order
    for key in ['alignment', 'locked']:
        values = [getattr(c, key) for c in layer.components]
        if any(values):
            key = key[0].upper() + key[1:]
            glyph.lib['%scomponents%s' % (GLYPHS_PREFIX, key)] = values
