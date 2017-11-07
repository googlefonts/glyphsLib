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

from collections import deque, OrderedDict
import logging

from .common import to_ufo_time
from .constants import GLYPHS_PREFIX

logger = logging.getLogger(__name__)


def to_ufo_font_attributes(self, family_name):
    """Generate a list of UFOs with metadata loaded from .glyphs data.

    Modifies the list of UFOs in the UFOBuilder (self) in-place.
    """
    font = self.font
    for master in font.masters:
        ufo = master.ufo_object()
        # FIXME: (jany) in the future, yield this UFO (for memory, laze iter)
        self._ufos[master.id] = ufo


def to_glyphs_font_attributes(self, ufo, master, is_initial):
    """
    Copy font attributes from `ufo` either to `self.font` or to `master`.

    Arguments:
    self -- The UFOBuilder
    ufo -- The current UFO being read
    master -- The current master being written
    is_initial -- True iff this the first UFO that we process
    """
    master.id = ufo.lib[GLYPHS_PREFIX + 'fontMasterID']
    # TODO: all the other attributes
