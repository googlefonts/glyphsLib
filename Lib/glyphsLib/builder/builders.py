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
import tempfile
import os

import defcon

# FIXME: import fontTools.designSpaceDocument
from glyphsLib import designSpaceDocument

from glyphsLib import classes, glyphdata_generated
from .constants import PUBLIC_PREFIX, GLYPHS_PREFIX, FONT_CUSTOM_PARAM_PREFIX

GLYPH_ORDER_KEY = PUBLIC_PREFIX + 'glyphOrder'


class _LoggerMixin(object):

    _logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = logging.getLogger(
                ".".join([self.__class__.__module__, self.__class__.__name__]))
        return self._logger


class UFOBuilder(_LoggerMixin):
    """Builder for Glyphs to UFO + designspace."""

    def __init__(self,
                 font,
                 ufo_module=defcon,
                 designspace_module=designSpaceDocument,
                 family_name=None,
                 propagate_anchors=True):
        """Create a builder that goes from Glyphs to UFO + designspace.

        Keyword arguments:
        font -- The GSFont object to transform into UFOs
        ufo_module -- A Python module to use to build UFO objects (you can pass
                      a custom module that has the same classes as the official
                      defcon to get instances of your own classes)
        designspace_module -- A Python module to use to build a Designspace
                              Document. Should look like designSpaceDocument.
        family_name -- if provided, the master UFOs will be given this name and
                       only instances with this name will be returned.
        propagate_anchors -- set to False to prevent anchor propagation
        """
        self.font = font
        self.ufo_module = ufo_module
        self.designspace_module = designspace_module

        # The set of UFOs (= defcon.Font objects) that will be built,
        # indexed by master ID, the same order as masters in the source GSFont.
        self._ufos = OrderedDict()

        # The designSpaceDocument object that will be built (if requested).
        self._designspace = None

        # check that source was generated with at least stable version 2.3
        # https://github.com/googlei18n/glyphsLib/pull/65#issuecomment-237158140
        if int(font.appVersion) < 895:
            self.logger.warn(
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

        # Store set of actually existing master (layer) ids. This helps with
        # catching dangling layer data that Glyphs may ignore, e.g. when
        # copying glyphs from other fonts with, naturally, different master
        # ids. Note: Masters have unique ids according to the Glyphs
        # documentation and can therefore be stored in a set.
        master_layer_ids = {m.id for m in self.font.masters}

        # stores background data from "associated layers"
        supplementary_layer_data = []

        # TODO(jamesgk) maybe create one font at a time to reduce memory usage
        # TODO: (jany) in the future, return a lazy iterator that builds UFOs
        #     on demand.
        self.to_ufo_font_attributes(self.family_name)

        for glyph in self.font.glyphs:
            self.to_ufo_glyph_groups(kerning_groups, glyph)
            glyph_name = glyph.name

            for layer in glyph.layers.values():
                layer_id = layer.layerId
                layer_name = layer.name

                assoc_id = layer.associatedMasterId
                if assoc_id != layer.layerId:
                    # Store all layers, even the invalid ones, and just skip
                    # them and print a warning below.
                    supplementary_layer_data.append(
                        (assoc_id, glyph_name, layer_name, layer))
                    continue

                ufo = self._ufos[layer_id]
                ufo_glyph = ufo.newGlyph(glyph_name)
                self.to_ufo_glyph(ufo_glyph, layer, glyph)
                ufo_layer = ufo.layers.defaultLayer
                ufo_layer.lib[GLYPHS_PREFIX + 'layerOrderInGlyph.' +
                              glyph.name] = self._layer_order_in_glyph(layer)

        for master_id, glyph_name, layer_name, layer \
                in supplementary_layer_data:
            if (layer.layerId not in master_layer_ids and
                    layer.associatedMasterId not in master_layer_ids):
                self.logger.warn(
                    '{}, glyph "{}": Layer "{}" is dangling and will be '
                    'skipped. Did you copy a glyph from a different font? If '
                    'so, you should clean up any phantom layers not associated '
                    'with an actual master.'.format(
                        self.font.familyName, glyph_name, layer.layerId))
                continue

            if not layer_name:
                # Empty layer names are invalid according to the UFO spec.
                self.logger.warn(
                    '{}, glyph "{}": Contains layer without a name which will '
                    'be skipped.'.format(self.font.familyName, glyph_name))
                continue

            ufo_font = self._ufos[master_id]
            if layer_name not in ufo_font.layers:
                ufo_layer = ufo_font.newLayer(layer_name)
            else:
                ufo_layer = ufo_font.layers[layer_name]
            # TODO: (jany) move as much as possible into layers.py
            ufo_layer.lib[GLYPHS_PREFIX + 'layerId'] = layer.layerId
            ufo_layer.lib[GLYPHS_PREFIX + 'layerOrderInGlyph.' +
                          glyph_name] = self._layer_order_in_glyph(layer)
            ufo_glyph = ufo_layer.newGlyph(glyph_name)
            self.to_ufo_glyph(ufo_glyph, layer, layer.parent)

        for ufo in self._ufos.values():
            if self.propagate_anchors:
                self.to_ufo_propagate_font_anchors(ufo)
            self.to_ufo_features(ufo)  # This depends on the glyphOrder key
            self.to_ufo_kerning_groups(ufo, kerning_groups)

        for master_id, kerning in self.font.kerning.items():
            self.to_ufo_kerning(self._ufos[master_id], kerning)

        return self._ufos.values()

    def _layer_order_in_glyph(self, layer):
        # TODO: move to layers.py
        # TODO: optimize?
        for order, glyph_layer in enumerate(layer.parent.layers.values()):
            if glyph_layer == layer:
                return order
        return None

    @property
    def instances(self):
        """Get an iterator over interpolated UFOs of instances."""
        # TODO?
        return []

    @property
    def designspace(self):
        """Get a designspace Document instance that links the masters together
        and holds instance data.
        """
        if self._designspace is not None:
            return self._designspace

        self._designspace = self.designspace_module.DesignSpaceDocument(
            writerClass=designSpaceDocument.InMemoryDocWriter,
            fontClass=self.ufo_module.Font)
        self.to_ufo_instances()
        return self._designspace

    # DEPRECATED
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
        varfont_origin = first_ufo.lib.get(FONT_CUSTOM_PARAM_PREFIX +
                                           varfont_origin_key)
        if varfont_origin:
            instance_data[varfont_origin_key] = varfont_origin
        return instance_data

    # Implementation is split into one file per feature
    from .anchors import to_ufo_propagate_font_anchors, to_ufo_glyph_anchors
    from .annotations import to_ufo_annotations
    from .background_image import to_ufo_background_image
    from .blue_values import to_ufo_blue_values
    from .common import to_ufo_time
    from .components import to_ufo_components, to_ufo_smart_component_axes
    from .custom_params import to_ufo_custom_params
    from .features import to_ufo_features
    from .font import to_ufo_font_attributes
    from .glyph import to_ufo_glyph, to_ufo_glyph_background
    from .guidelines import to_ufo_guidelines
    from .hints import to_ufo_hints
    from .instances import to_ufo_instances
    from .kerning import (to_ufo_kerning, to_ufo_glyph_groups,
                          to_ufo_kerning_groups)
    from .names import to_ufo_names
    from .paths import to_ufo_paths
    from .user_data import (to_ufo_family_user_data, to_ufo_master_user_data,
                            to_ufo_glyph_user_data, to_ufo_layer_user_data,
                            to_ufo_node_user_data)


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


class GlyphsBuilder(_LoggerMixin):
    """Builder for UFO + designspace to Glyphs."""

    def __init__(self, ufos=[], designspace=None, glyphs_module=classes):
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
        if designspace is not None:
            self.designspace = designspace
            if ufos:
                # assert all(ufo in designspace.getFonts() for ufo in ufos)
                self.ufos = ufos
            else:
                self.ufos = [source.font for source in designspace.sources]
        elif ufos:
            self.designspace = None
            self.ufos = ufos
        else:
            raise RuntimeError(
                'Please provide a designspace or at least one UFO.')
        self.glyphs_module = glyphs_module

        self._font = None
        """The GSFont that will be built."""

    @property
    def font(self):
        """Get the GSFont built from the UFOs + designspace."""
        if self._font is not None:
            return self._font

        # Sort UFOS in the original order
        self.to_glyphs_ordered_masters()

        self._font = self.glyphs_module.GSFont()
        for index, ufo in enumerate(self.ufos):
            kerning_groups = self.to_glyphs_kerning_groups(ufo)

            master = self.glyphs_module.GSFontMaster()
            self.to_glyphs_font_attributes(ufo, master,
                                           is_initial=(index == 0))
            self._font.masters.insert(len(self._font.masters), master)

            for layer in ufo.layers:
                for glyph in layer:
                    self.to_glyphs_glyph(glyph, layer, master)
                    self.to_glyphs_glyph_groups(kerning_groups, glyph)

            self.to_glyphs_kerning(ufo, master)

        # Now that all GSGlyph are built, restore the glyph order
        first_ufo = next(iter(self.ufos))
        if GLYPH_ORDER_KEY in first_ufo.lib:
            glyph_order = first_ufo.lib[GLYPH_ORDER_KEY]
            lookup = {name: i for i, name in enumerate(glyph_order)}
            self.font.glyphs = sorted(
                self.font.glyphs,
                key=lambda glyph: lookup.get(glyph.name, 1 << 63))

        # Restore the layer ordering in each glyph
        for glyph in self._font.glyphs:
            self.to_glyphs_layer_order(glyph)

        self.to_glyphs_instances()

        return self._font

    # Implementation is split into one file per feature
    from .anchors import to_glyphs_glyph_anchors
    from .annotations import to_glyphs_annotations
    from .background_image import to_glyphs_background_image
    from .blue_values import to_glyphs_blue_values
    from .components import (to_glyphs_components,
                             to_glyphs_smart_component_axes)
    from .custom_params import (to_glyphs_family_custom_params,
                                to_glyphs_master_custom_params)
    from .features import to_glyphs_features
    from .font import to_glyphs_font_attributes, to_glyphs_ordered_masters
    from .glyph import to_glyphs_glyph
    from .guidelines import to_glyphs_guidelines
    from .hints import to_glyphs_hints
    from .instances import to_glyphs_instances
    from .kerning import (to_glyphs_glyph_groups, to_glyphs_kerning_groups,
                          to_glyphs_kerning)
    from .layers import to_glyphs_layer, to_glyphs_layer_order
    from .names import to_glyphs_family_names, to_glyphs_master_names
    from .paths import to_glyphs_paths
    from .user_data import (to_glyphs_family_user_data,
                            to_glyphs_master_user_data,
                            to_glyphs_glyph_user_data,
                            to_glyphs_layer_user_data,
                            to_glyphs_node_user_data)
