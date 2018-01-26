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

import os

from glyphsLib.util import build_ufo_path

from .masters import UFO_FILENAME_KEY
from .axes import get_axis_definitions, get_regular_master


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
    source.name = '%s %s' % (source.familyName, source.styleName)

    # TODO: (jany) make sure to use forward slashes? Maybe it should be the
    #   responsibility of DesignspaceDocument
    if UFO_FILENAME_KEY in master.userData:
        source.filename = master.userData[UFO_FILENAME_KEY]
    else:
        # TODO: (jany) allow another naming convention?
        source.filename = os.path.basename(
            # FIXME: (jany) have this function not write the dot
            build_ufo_path('.', source.familyName, source.styleName))

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
            axis_def.set_design_loc(master, source.location[axis_def.name])
        except KeyError:
            # The location does not have this axis?
            pass

