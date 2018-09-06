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

import logging
import os

from glyphsLib.util import build_ufo_path

from .masters import UFO_FILENAME_KEY
from .axes import get_axis_definitions, get_regular_master, font_uses_new_axes, interp


logger = logging.getLogger(__name__)


def to_designspace_sources(self):
    regular_master = get_regular_master(self.font)
    for master in self.font.masters:
        _to_designspace_source(self, master, (master is regular_master))


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
        # happen to have the same weight name.
        n = "_"
        while any(
            s is not source and s.filename == source.filename
            for s in self._sources.values()
        ):
            source.filename = os.path.basename(
                build_ufo_path("", source.familyName, source.styleName + n)
            )
            n += "_"
            logger.warning(
                "The master with id {} has the same style name ({}) "
                "as another one. All masters should have distinctive "
                "(style) names. Use the 'Master name' custom parameter"
                " on a master to give it a unique name. Proceeding "
                "with an unchanged name, but appending '_' to the file"
                " name on disk.".format(master.id, source.styleName)
            )

    location = {}
    for axis_def in get_axis_definitions(self.font):
        location[axis_def.name] = axis_def.get_design_loc(master)
    source.location = location


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
