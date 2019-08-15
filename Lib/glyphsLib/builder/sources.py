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

import collections
import logging
import os

import fontTools.designspaceLib
from glyphsLib.util import build_ufo_path

from .masters import UFO_FILENAME_KEY
from .axes import get_axis_definitions, get_regular_master, font_uses_new_axes, interp


logger = logging.getLogger(__name__)


def to_designspace_sources(self):
    regular_master = get_regular_master(self.font)
    for master in self.font.masters:
        _to_designspace_source(self, master, (master is regular_master))
    _to_designspace_source_layer(self)
    _warn_duplicate_master_locations(self)


def _warn_duplicate_master_locations(self):
    designspace = self._designspace
    master_locations = collections.defaultdict(list)
    for source in designspace.sources:
        master_locations[tuple(source.location.items())].append(source)
    duplicates = {l: s for l, s in master_locations.items() if len(s) > 1}
    if duplicates:
        msg = [
            "DesignSpace sources contain duplicate locations; "
            "varLib expects each master to define a unique location."
        ]
        if any(s.layerName for s in designspace.sources):
            msg.append(
                " Make sure that you used consistent 'brace layer' names"
                " in all the glyph layers that share the same location."
            )
        for loc, sources in sorted(duplicates.items()):
            msg.append(
                "\n  %r => %r"
                % ([s.layerName if s.layerName else s.name for s in sources], dict(loc))
            )
        logger.warning("".join(msg))


def _to_designspace_source(self, master, is_regular):
    source = self._sources[master.id]
    ufo = source.font

    if is_regular:
        source.copyLib = True
        source.copyInfo = True
        source.copyGroups = True
        source.copyFeatures = True

    source.familyName = ufo.info.familyName
    source.styleName = ufo.info.styleName
    # TODO: recover original source name from userData
    # UFO_SOURCE_NAME_KEY
    source.name = "{} {}".format(source.familyName, source.styleName)

    if UFO_FILENAME_KEY in master.userData:
        source.filename = master.userData[UFO_FILENAME_KEY]
    else:
        # TODO: (jany) allow another naming convention?
        source.filename = build_ufo_path("", source.familyName, source.styleName)

    # Make sure UFO filenames are unique, lest we overwrite masters that
    # happen to have the same weight name. Careful, name clashes can also happen when
    # the masters have a UFO_FILENAME_KEY: when the user duplicates a master in Glyphs
    # but forgets to change the UFO filename key in the master's userData (ha!).
    # Attention: The following is done regardless of where source.filename came from.
    # Depending on the duplicate's order in the master list, this could lead to the
    # legitimate master's filename getting an underscore appended!
    n = 1
    while any(
        s is not source and s.filename == source.filename
        for s in self._sources.values()
    ):
        filename_stem, filename_ext = os.path.splitext(source.filename)
        source.filename = "{}#{}{}".format(filename_stem, n, filename_ext)
        if UFO_FILENAME_KEY in master.userData:
            logger.warning(
                "The master with the style name '{}' (ID {}) would be written to the "
                "same destination as another master. Change the "
                "master.userData['com.schriftgestaltung.Glyphs.ufoFilename'] "
                "parameter to select a different destination. Proceeding, but appending"
                " '#{}' to the filename on disk.".format(source.styleName, master.id, n)
            )
        else:
            logger.warning(
                "The master with the style name '{}' (ID {}) has the same style name "
                "as another one. All masters should have distinctive "
                "(style) names. Use the 'Master name' custom parameter"
                " on a master to give it a unique name. Proceeding "
                "with an unchanged name, but appending '#{}' to the file"
                " name on disk.".format(source.styleName, master.id, n)
            )
        n += 1

    location = {}
    for axis_def in get_axis_definitions(self.font):
        location[axis_def.name] = axis_def.get_design_loc(master)
    source.location = location


def _to_designspace_source_layer(self):
    # To construct a source layer, we need
    # 1. The Designspace source filename and font object which holds the layer.
    # 2. The (brace) layer name itself.
    # 3. The location of the intermediate master in the design space.
    # (For logging purposes, it's nice to know which glyphs contain the layer.)
    #
    # Note that a brace layer can be associated with different master layers (e.g. the
    # 'a' can have a '{400}' brace layer associated with 'Thin', and 'b''s can be
    # associte with 'Black').
    # Also note that if a brace layer name has less values than there are axes, they
    # are supposed to take on the values from the associated master as the missing
    # values.

    # First, collect all brace layers in the font and which glyphs and which masters
    # they belong to.
    layer_name_to_master_ids = collections.defaultdict(set)
    layer_name_to_glyph_names = collections.defaultdict(list)
    for glyph in self.font.glyphs:
        for layer in glyph.layers:
            if (
                "{" in layer.name
                and "}" in layer.name
                and ".background" not in layer.name
            ):
                layer_name_to_master_ids[layer.name].add(layer.associatedMasterId)
                layer_name_to_glyph_names[layer.name].append(glyph.name)

    # Next, insert the brace layers in a defined location in the existing designspace.
    designspace = self._designspace
    layers_to_insert = collections.defaultdict(list)
    for layer_name, master_ids in layer_name_to_master_ids.items():
        # Construct coordinates first...
        brace_coordinates = [
            int(c)
            for c in layer_name[
                layer_name.index("{") + 1 : layer_name.index("}")
            ].split(",")
        ]

        for master_id in master_ids:
            # ... as they may need to be filled up with the values of the associated
            # master.
            master = self._sources[master_id]
            master_coordinates = brace_coordinates
            if len(master_coordinates) < len(designspace.axes):
                master_locations = [master.location[a.name] for a in designspace.axes]
                master_coordinates = (
                    brace_coordinates + master_locations[len(brace_coordinates) :]
                )
            elif len(master_coordinates) > len(designspace.axes):
                logger.warning(
                    "Glyph(s) %s, brace layer '%s' defines more locations than "
                    "there are design axes.",
                    layer_name_to_glyph_names[layer_name],
                    layer_name,
                )

            # If we have more locations than axes, ignore the extra locations.
            layer_coordinates_mapping = collections.OrderedDict(
                (axis.name, location)
                for axis, location in zip(designspace.axes, master_coordinates)
            )

            s = fontTools.designspaceLib.SourceDescriptor()
            s.filename = master.filename
            s.font = master.font
            s.layerName = layer_name
            s.name = "{} {}".format(master.name, layer_name)
            s.location = layer_coordinates_mapping

            # We collect all generated SourceDescriptors first, grouped by the masters
            # they belong to, so we can insert them in a defined order in the next step.
            layers_to_insert[master_id].append(s)

    # Splice brace layers into the appropriate location after their master.
    for master_id, brace_layers in layers_to_insert.items():
        master = self._sources[master_id]
        insert_index = designspace.sources.index(master) + 1
        brace_layers.sort(key=lambda x: tuple(x.location.values()))
        designspace.sources[insert_index:insert_index] = brace_layers


def to_glyphs_sources(self):
    for master in self.font.masters:
        _to_glyphs_source(self, master)


def _to_glyphs_source(self, master):
    source = self._sources[master.id]

    # Retrieve the master locations: weight, width, custom 0 - 1 - 2 - 3
    for axis_def in get_axis_definitions(self.font):
        try:
            design_location = source.location[axis_def.name]
        except KeyError:
            # The location does not have this axis?
            continue

        axis_def.set_design_loc(master, design_location)
        if font_uses_new_axes(self.font):
            # The user location can be found by reading the mapping backwards
            mapping = []
            for axis in self.designspace.axes:
                if axis.tag == axis_def.tag:
                    mapping = axis.map
                    break
            reverse_mapping = [(dl, ul) for ul, dl in mapping]
            user_location = interp(reverse_mapping, design_location)
            axis_def.set_user_loc(master, user_location)
