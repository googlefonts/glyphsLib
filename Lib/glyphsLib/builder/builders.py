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

from __future__ import print_function, division, absolute_import, unicode_literals

from collections import OrderedDict, defaultdict
import logging
import tempfile
import os
from textwrap import dedent

import defcon

from fontTools import designspaceLib

from glyphsLib import classes
from .constants import PUBLIC_PREFIX, GLYPHS_PREFIX, FONT_CUSTOM_PARAM_PREFIX
from .axes import WEIGHT_AXIS_DEF, WIDTH_AXIS_DEF, find_base_style, class_to_value

GLYPH_ORDER_KEY = PUBLIC_PREFIX + "glyphOrder"


class _LoggerMixin(object):

    _logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = logging.getLogger(
                ".".join([self.__class__.__module__, self.__class__.__name__])
            )
        return self._logger


class UFOBuilder(_LoggerMixin):
    """Builder for Glyphs to UFO + designspace."""

    def __init__(
        self,
        font,
        ufo_module=defcon,
        designspace_module=designspaceLib,
        family_name=None,
        instance_dir=None,
        propagate_anchors=True,
        use_designspace=False,
        minimize_glyphs_diffs=False,
    ):
        """Create a builder that goes from Glyphs to UFO + designspace.

        Keyword arguments:
        font -- The GSFont object to transform into UFOs
        ufo_module -- A Python module to use to build UFO objects (you can pass
                      a custom module that has the same classes as the official
                      defcon to get instances of your own classes)
        designspace_module -- A Python module to use to build a Designspace
                              Document. Default is fontTools.designspaceLib.
        family_name -- if provided, the master UFOs will be given this name and
                       only instances with this name will be returned.
        instance_dir -- if provided, instance UFOs will be located in this
                        directory, according to their Designspace filenames.
        propagate_anchors -- set to False to prevent anchor propagation
        use_designspace -- set to True to make optimal use of the designspace:
                           data that is common to all ufos will go there.
        minimize_glyphs_diffs -- set to True to store extra info in UFOs
                                 in order to get smaller diffs between .glyphs
                                 .glyphs files when going glyphs->ufo->glyphs.
        """
        self.font = font
        self.ufo_module = ufo_module
        self.designspace_module = designspace_module
        self.instance_dir = instance_dir
        self.propagate_anchors = propagate_anchors
        self.use_designspace = use_designspace
        self.minimize_glyphs_diffs = minimize_glyphs_diffs

        # The set of (SourceDescriptor + UFO)s that will be built,
        # indexed by master ID, the same order as masters in the source GSFont.
        self._sources = OrderedDict()

        # The designSpaceDocument object that will be built.
        # The sources will be built in any case, at the same time that we build
        # the master UFOs, when the user requests them.
        # The axes, instances, rules... will only be built if the designspace
        # document itself is requested by the user.
        self._designspace = self.designspace_module.DesignSpaceDocument()
        self._designspace_is_complete = False

        # check that source was generated with at least stable version 2.3
        # https://github.com/googlei18n/glyphsLib/pull/65#issuecomment-237158140
        if int(font.appVersion) < 895:
            self.logger.warning(
                "This Glyphs source was generated with an outdated version "
                "of Glyphs. The resulting UFOs may be incorrect."
            )

        if family_name is None:
            # use the source family name, and include all the instances
            self.family_name = self.font.familyName
            self._do_filter_instances_by_family = False
        else:
            self.family_name = family_name
            # use a custom 'family_name' to name master UFOs, and only build
            # instances with matching 'familyName' custom parameter
            self._do_filter_instances_by_family = True

    @property
    def masters(self):
        """Get an iterator over master UFOs that match the given family_name.
        """
        if self._sources:
            for source in self._sources.values():
                yield source.font
            return

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
            for layer in glyph.layers.values():
                if layer.associatedMasterId != layer.layerId:
                    # The layer is not the main layer of a master
                    # Store all layers, even the invalid ones, and just skip
                    # them and print a warning below.
                    supplementary_layer_data.append((glyph, layer))
                    continue

                ufo_layer = self.to_ufo_layer(glyph, layer)
                ufo_glyph = ufo_layer.newGlyph(glyph.name)
                self.to_ufo_glyph(ufo_glyph, layer, glyph)

        for glyph, layer in supplementary_layer_data:
            if (
                layer.layerId not in master_layer_ids
                and layer.associatedMasterId not in master_layer_ids
            ):
                if self.minimize_glyphs_diffs:
                    self.logger.warning(
                        '{}, glyph "{}": Layer "{}" is dangling and will be '
                        "skipped. Did you copy a glyph from a different font?"
                        " If so, you should clean up any phantom layers not "
                        "associated with an actual master.".format(
                            self.font.familyName, glyph.name, layer.layerId
                        )
                    )
                continue

            if not layer.name:
                # Empty layer names are invalid according to the UFO spec.
                if self.minimize_glyphs_diffs:
                    self.logger.warning(
                        '{}, glyph "{}": Contains layer without a name which '
                        "will be skipped.".format(self.font.familyName, glyph.name)
                    )
                continue

            ufo_layer = self.to_ufo_layer(glyph, layer)
            ufo_glyph = ufo_layer.newGlyph(glyph.name)
            self.to_ufo_glyph(ufo_glyph, layer, layer.parent)

        for source in self._sources.values():
            ufo = source.font
            if self.propagate_anchors:
                self.to_ufo_propagate_font_anchors(ufo)
            for layer in ufo.layers:
                self.to_ufo_layer_lib(layer)

        self.to_ufo_features()  # This depends on the glyphOrder key
        self.to_ufo_groups()
        self.to_ufo_kerning()

        for source in self._sources.values():
            yield source.font

    @property
    def designspace(self):
        """Get a designspace Document instance that links the masters together
        and holds instance data.
        """
        if self._designspace_is_complete:
            return self._designspace
        self._designspace_is_complete = True
        ufos = list(self.masters)  # Make sure that the UFOs are built
        self.to_designspace_axes()
        self.to_designspace_sources()
        self.to_designspace_instances()
        self.to_designspace_family_user_data()

        # append base style shared by all masters to designspace file name
        base_family = self.family_name or "Unnamed"
        base_style = find_base_style(self.font.masters)
        if base_style:
            base_style = "-" + base_style
        name = (base_family + base_style).replace(" ", "") + ".designspace"
        self.designspace.filename = name

        return self._designspace

    # DEPRECATED
    @property
    def instance_data(self):
        instances = self.font.instances
        if self._do_filter_instances_by_family:
            instances = list(filter_instances_by_family(instances, self.family_name))
        instance_data = {"data": instances, "designspace": self.designspace}

        first_ufo = next(iter(self.masters))

        # the 'Variation Font Origin' is a font-wide custom parameter, thus it is
        # shared by all the master ufos; here we just get it from the first one
        varfont_origin_key = "Variation Font Origin"
        varfont_origin = first_ufo.lib.get(
            FONT_CUSTOM_PARAM_PREFIX + varfont_origin_key
        )
        if varfont_origin:
            instance_data[varfont_origin_key] = varfont_origin
        return instance_data

    # Implementation is split into one file per feature
    from .anchors import to_ufo_propagate_font_anchors, to_ufo_glyph_anchors
    from .annotations import to_ufo_annotations
    from .axes import to_designspace_axes
    from .background_image import to_ufo_background_image
    from .blue_values import to_ufo_blue_values
    from .common import to_ufo_time
    from .components import to_ufo_components, to_ufo_smart_component_axes
    from .custom_params import to_ufo_custom_params
    from .features import to_ufo_features
    from .font import to_ufo_font_attributes
    from .glyph import to_ufo_glyph, to_ufo_glyph_background
    from .groups import to_ufo_groups
    from .guidelines import to_ufo_guidelines
    from .hints import to_ufo_hints
    from .instances import to_designspace_instances
    from .kerning import to_ufo_kerning
    from .layers import to_ufo_layer, to_ufo_background_layer
    from .masters import to_ufo_master_attributes
    from .names import to_ufo_names
    from .paths import to_ufo_paths
    from .sources import to_designspace_sources
    from .user_data import (
        to_designspace_family_user_data,
        to_ufo_family_user_data,
        to_ufo_master_user_data,
        to_ufo_glyph_user_data,
        to_ufo_layer_lib,
        to_ufo_layer_user_data,
        to_ufo_node_user_data,
    )


def filter_instances_by_family(instances, family_name=None):
    """Yield instances whose 'familyName' custom parameter is
    equal to 'family_name'.
    """
    return (i for i in instances if i.familyName == family_name)


class GlyphsBuilder(_LoggerMixin):
    """Builder for UFO + designspace to Glyphs."""

    def __init__(
        self, ufos=[], designspace=None, glyphs_module=classes, minimize_ufo_diffs=False
    ):
        """Create a builder that goes from UFOs + designspace to Glyphs.

        If you provide:
            * Some UFOs, no designspace: the given UFOs will be combined.
                No instance data will be created, only the weight and width
                axes will be set up (if relevant).
            * A designspace, no UFOs: the UFOs will be loaded according to
                the designspace's sources. Instance and axis data will be
                converted to Glyphs.
            * Both a designspace and some UFOs: not supported for now.
                TODO: (jany) find out whether there is a use-case here?

        Keyword arguments:
        ufos -- The list of UFOs to combine into a GSFont
        designspace -- A MutatorMath Designspace to use for the GSFont
        glyphs_module -- The glyphsLib.classes module to use to build glyphsLib
                         classes (you can pass a custom module with the same
                         classes as the official glyphsLib.classes to get
                         instances of your own classes, or pass the Glyphs.app
                         module that holds the official classes to import UFOs
                         into Glyphs.app)
        minimize_ufo_diffs -- set to True to store extra info in .glyphs files
                              in order to get smaller diffs between UFOs
                              when going UFOs->glyphs->UFOs
        """
        self.glyphs_module = glyphs_module
        self.minimize_ufo_diffs = minimize_ufo_diffs

        if designspace is not None:
            if ufos:
                raise NotImplementedError
            self.designspace = self._valid_designspace(designspace)
        elif ufos:
            self.designspace = self._fake_designspace(ufos)
        else:
            raise RuntimeError("Please provide a designspace or at least one UFO.")

        self._font = None
        """The GSFont that will be built."""

    @property
    def font(self):
        """Get the GSFont built from the UFOs + designspace."""
        if self._font is not None:
            return self._font

        # Sort UFOS in the original order from the Glyphs file
        sorted_sources = self.to_glyphs_ordered_masters()

        self._font = self.glyphs_module.GSFont()
        self._sources = OrderedDict()  # Same as in UFOBuilder
        for index, source in enumerate(sorted_sources):
            master = self.glyphs_module.GSFontMaster()
            self.to_glyphs_font_attributes(source, master, is_initial=(index == 0))
            self.to_glyphs_master_attributes(source, master)
            self._font.masters.insert(len(self._font.masters), master)
            self._sources[master.id] = source

            for layer in _sorted_backgrounds_last(source.font.layers):
                self.to_glyphs_layer_lib(layer)
                for glyph in layer:
                    self.to_glyphs_glyph(glyph, layer, master)

        self.to_glyphs_features()
        self.to_glyphs_groups()
        self.to_glyphs_kerning()

        # Now that all GSGlyph are built, restore the glyph order
        if self.designspace.sources:
            first_ufo = self.designspace.sources[0].font
            if GLYPH_ORDER_KEY in first_ufo.lib:
                glyph_order = first_ufo.lib[GLYPH_ORDER_KEY]
                lookup = {name: i for i, name in enumerate(glyph_order)}
                self.font.glyphs = sorted(
                    self.font.glyphs, key=lambda glyph: lookup.get(glyph.name, 1 << 63)
                )
            # FIXME: (jany) We only do that on the first one. Maybe we should
            # merge the various `public.glyphorder` values?

            # Restore the layer ordering in each glyph
            for glyph in self._font.glyphs:
                self.to_glyphs_layer_order(glyph)

        self.to_glyphs_family_user_data_from_designspace()
        self.to_glyphs_axes()
        self.to_glyphs_sources()
        self.to_glyphs_instances()

        return self._font

    def _valid_designspace(self, designspace):
        """Make sure that the user-provided designspace has loaded fonts and
        that names are the same as those from the UFOs.
        """
        # TODO: (jany) really make a copy to avoid modifying the original object
        copy = designspace
        for source in copy.sources:
            if not hasattr(source, "font") or source.font is None:
                if source.path:
                    # FIXME: (jany) consider not changing the caller's objects
                    source.font = defcon.Font(source.path)
                else:
                    dirname = os.path.dirname(designspace.path)
                    ufo_path = os.path.join(dirname, source.filename)
                    source.font = defcon.Font(ufo_path)
            if source.location is None:
                source.location = {}
            for name in ("familyName", "styleName"):
                if getattr(source, name) != getattr(source.font.info, name):
                    self.logger.warning(
                        dedent(
                            """\
                        The {name} is different between the UFO and the designspace source:
                            source filename: {filename}
                            source {name}: {source_name}
                            ufo {name}: {ufo_name}

                        The UFO name will be used.
                    """
                        ).format(
                            name=name,
                            filename=source.filename,
                            source_name=getattr(source, name),
                            ufo_name=getattr(source.font.info, name),
                        )
                    )
                    setattr(source, name, getattr(source.font.info, name))
        return copy

    def _fake_designspace(self, ufos):
        """Build a fake designspace with the given UFOs as sources, so that all
        builder functions can rely on the presence of a designspace.
        """
        designspace = designspaceLib.DesignSpaceDocument()

        ufo_to_location = defaultdict(dict)

        # Make weight and width axis if relevant
        for info_key, axis_def in zip(
            ("openTypeOS2WeightClass", "openTypeOS2WidthClass"),
            (WEIGHT_AXIS_DEF, WIDTH_AXIS_DEF),
        ):
            axis = designspace.newAxisDescriptor()
            axis.tag = axis_def.tag
            axis.name = axis_def.name
            mapping = []
            for ufo in ufos:
                user_loc = getattr(ufo.info, info_key)
                if user_loc is not None:
                    design_loc = class_to_value(axis_def.tag, user_loc)
                    mapping.append((user_loc, design_loc))
                    ufo_to_location[ufo][axis_def.name] = design_loc

            mapping = sorted(set(mapping))
            if len(mapping) > 1:
                axis.map = mapping
                axis.minimum = min([user_loc for user_loc, _ in mapping])
                axis.maximum = max([user_loc for user_loc, _ in mapping])
                axis.default = min(
                    axis.maximum, max(axis.minimum, axis_def.default_user_loc)
                )
                designspace.addAxis(axis)

        for ufo in ufos:
            source = designspace.newSourceDescriptor()
            source.font = ufo
            source.familyName = ufo.info.familyName
            source.styleName = ufo.info.styleName
            # source.name = '%s %s' % (source.familyName, source.styleName)
            source.path = ufo.path
            source.location = ufo_to_location[ufo]
            designspace.addSource(source)
        return designspace

    # Implementation is split into one file per feature
    from .anchors import to_glyphs_glyph_anchors
    from .annotations import to_glyphs_annotations
    from .axes import to_glyphs_axes
    from .background_image import to_glyphs_background_image
    from .blue_values import to_glyphs_blue_values
    from .components import to_glyphs_components, to_glyphs_smart_component_axes
    from .custom_params import to_glyphs_custom_params
    from .features import to_glyphs_features
    from .font import to_glyphs_font_attributes, to_glyphs_ordered_masters
    from .glyph import to_glyphs_glyph
    from .groups import to_glyphs_groups
    from .guidelines import to_glyphs_guidelines
    from .hints import to_glyphs_hints
    from .instances import to_glyphs_instances
    from .kerning import to_glyphs_kerning
    from .layers import to_glyphs_layer, to_glyphs_layer_order
    from .masters import to_glyphs_master_attributes
    from .names import to_glyphs_family_names, to_glyphs_master_names
    from .paths import to_glyphs_paths
    from .sources import to_glyphs_sources
    from .user_data import (
        to_glyphs_family_user_data_from_designspace,
        to_glyphs_family_user_data_from_ufo,
        to_glyphs_master_user_data,
        to_glyphs_glyph_user_data,
        to_glyphs_layer_lib,
        to_glyphs_layer_user_data,
        to_glyphs_node_user_data,
    )


def _sorted_backgrounds_last(ufo_layers):
    # Stable sort that groups all foregrounds first and all backgrounds last
    return sorted(
        ufo_layers, key=lambda layer: 1 if layer.name.endswith(".background") else 0
    )
