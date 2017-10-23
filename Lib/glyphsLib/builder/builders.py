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

from collections import OrderedDict
import logging

import defcon

logger = logging.getLogger(__name__)

from glyphsLib import classes
from .constants import PUBLIC_PREFIX, GLYPHS_PREFIX


class UFOBuilder(object):
    """Builder for Glyphs to UFO + designspace."""

    def __init__(self,
                 font,
                 ufo_module=defcon,
                 family_name=None,
                 propagate_anchors=True):
        """Create a builder that goes from Glyphs to UFO + designspace.

        Keyword arguments:
        font -- The GSFont object to transform into UFOs
        ufo_module -- A Python module to use to build UFO objects (you can pass
                      a custom module that has the same classes as the official
                      defcon to get instances of your own classes)
        family_name -- if provided, the master UFOs will be given this name and
                       only instances with this name will be returned.
        propagate_anchors -- set to False to prevent anchor propagation
        """
        self.font = font
        self.ufo_module = ufo_module

        # The set of UFOs (= defcon.Font objects) that will be built,
        # indexed by master ID, the same order as masters in the source GSFont.
        self._ufos = OrderedDict()

        # The MutatorMath Designspace object that will be built (if requested).
        self._designspace = None

        # check that source was generated with at least stable version 2.3
        # https://github.com/googlei18n/glyphsLib/pull/65#issuecomment-237158140
        if int(font.appVersion) < 895:
            logger.warn(
                'This Glyphs source was generated with an outdated version '
                'of Glyphs. The resulting UFOs may be incorrect.')

        source_family_name = self.font.familyName
        if family_name is None:
            # use the source family name, and include all the instances
            self.family_name = source_family_name
            self._do_filter_instances_by_family = False
        else:
            self.family_name = family_name
            # use a custom 'family_name' to name master UFOs, and only build
            # instances with matching 'familyName' custom parameter
            self._do_filter_instances_by_family = True
            if family_name == source_family_name:
                # if the 'family_name' provided is the same as the source, only
                # include instances which do _not_ specify a custom 'familyName'
                self._instance_family_name = None
            else:
                self._instance_family_name = family_name

        self.propagate_anchors = propagate_anchors


    @property
    def masters(self):
        """Get an iterator over master UFOs that match the given family_name.
        """
        if self._ufos:
            return self._ufos.values()
        kerning_groups = {}

        # stores background data from "associated layers"
        supplementary_layer_data = []

        # TODO(jamesgk) maybe create one font at a time to reduce memory usage
        # TODO: (jany) in the future, return a lazy iterator that builds UFOs
        #     on demand.
        self.to_ufo_font_attributes(self.family_name)

        # get the 'glyphOrder' custom parameter as stored in the lib.plist.
        # We assume it's the same for all ufos.
        first_ufo = next(iter(self._ufos.values()))
        glyphOrder_key = PUBLIC_PREFIX + 'glyphOrder'
        if glyphOrder_key in first_ufo.lib:
            glyph_order = first_ufo.lib[glyphOrder_key]
        else:
            glyph_order = []
        sorted_glyphset = set(glyph_order)

        for glyph in self.font.glyphs:
            self.to_ufo_glyph_groups(kerning_groups, glyph)
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

                ufo = self._ufos[layer_id]
                ufo_glyph = ufo.newGlyph(glyph_name)
                self.to_ufo_glyph(ufo_glyph, layer, glyph)

        for layer_id, glyph_name, layer_name, layer_data \
                in supplementary_layer_data:
            ufo_font = self._ufos[layer_id]
            if layer_name not in ufo_font.layers:
                ufo_layer = ufo_font.newLayer(layer_name)
            else:
                ufo_layer = ufo_font.layers[layer_name]
            ufo_glyph = ufo_layer.newGlyph(glyph_name)
            self.to_ufo_glyph(ufo_glyph, layer_data, layer_data.parent)

        for ufo in self._ufos.values():
            ufo.lib[glyphOrder_key] = glyph_order
            if self.propagate_anchors:
                self.to_ufo_propagate_font_anchors(ufo)
            self.to_ufo_features(ufo)
            self.to_ufo_kerning_groups(ufo, kerning_groups)

        for master_id, kerning in self.font.kerning.items():
            self.to_ufo_kerning(self._ufos[master_id], kerning)

        return self._ufos.values()


    @property
    def instances(self):
        """Get an iterator over interpolated UFOs of instances."""
        # TODO?
        return []


    @property
    def designspace(self):
        """Get a designspace Document instance that links the masters together.
        """
        # TODO?
        pass


    @property
    def instance_data(self):
        instances = self.font.instances
        if self._do_filter_instances_by_family:
            instances = list(
                filter_instances_by_family(instances,
                                           self._instance_family_name))
        instance_data = {'data': instances}

        first_ufo = next(iter(self.masters))

        # the 'Variation Font Origin' is a font-wide custom parameter, thus it is
        # shared by all the master ufos; here we just get it from the first one
        varfont_origin_key = "Variation Font Origin"
        varfont_origin = first_ufo.lib.get(GLYPHS_PREFIX + varfont_origin_key)
        if varfont_origin:
            instance_data[varfont_origin_key] = varfont_origin
        return instance_data


    # Implementation is spit into one file per feature
    from .anchors import to_ufo_propagate_font_anchors, to_ufo_glyph_anchors
    from .blue_values import to_ufo_blue_values
    from .common import to_ufo_time
    from .components import to_ufo_draw_components
    from .custom_params import to_ufo_custom_params
    from .features import to_ufo_features
    from .font import to_ufo_font_attributes
    from .glyph import (to_ufo_glyph, to_ufo_glyph_background,
                        to_ufo_glyph_libdata)
    from .guidelines import to_ufo_guidelines
    from .kerning import (to_ufo_kerning, to_ufo_glyph_groups,
                          to_ufo_kerning_groups)
    from .names import to_ufo_names
    from .paths import to_ufo_draw_paths
    from .user_data import to_ufo_family_user_data, to_ufo_master_user_data


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


class GlyphsBuilder(object):
    """Builder for UFO + designspace to Glyphs."""

    def __init__(self, ufos, designspace=None, glyphs_module=classes):
        """Create a builder that goes from UFOs + designspace to Glyphs.

        Keyword arguments:
        ufos -- The list of UFOs to combine into a GSFont
        designspace -- A MutatorMath Designspace to use for the GSFont
        glyphs_module -- The glyphsLib.classes module to use to build glyphsLib
                         classes (you can pass a custom module with the same
                         classes as the official glyphsLib.classes to get
                         instances of your own classes, or pass the Glyphs.app
                         module that holds the official classes to import UFOs
                         into Glyphs.app)
        """
        self.ufos = ufos
        self.designspace = designspace
        self.glyphs_module = glyphs_module

        self._font = None
        """The GSFont that will be built."""


    @property
    def font(self):
        """Get the GSFont built from the UFOs + designspace."""
        if self._font is not None:
            return self._font

        self._font = self.glyphs_module.GSFont()
        for index, ufo in enumerate(self.ufos):
            master = self.glyphs_module.GSFontMaster()
            self.to_glyphs_font_attributes(ufo, master,
                                           is_initial=(index == 0))
            self._font.masters.insert(len(self._font.masters), master)
            # TODO: all the other stuff!
        return self._font


    # Implementation is spit into one file per feature
    from .font import to_glyphs_font_attributes
    from .blue_values import to_glyphs_blue_values
