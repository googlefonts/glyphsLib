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

from .constants import GLYPHS_PREFIX

MASTER_USER_DATA_KEY = GLYPHS_PREFIX + 'fontMaster.userData'


def to_ufo_family_user_data(self, ufo):
    """Set family-wide user data as Glyphs does."""
    user_data = self.font.userData
    for key in user_data.keys():
        ufo.lib[key] = user_data[key]


def to_ufo_master_user_data(self, ufo, master):
    """Set master-specific user data as Glyphs does."""
    user_data = master.userData
    if user_data:
        data = {}
        for key in user_data.keys():
            data[key] = user_data[key]
        ufo.lib[MASTER_USER_DATA_KEY] = data


def to_glyphs_family_user_data(self, ufo):
    """Set the GSFont userData from the UFO family-wide user data."""
    pass


def to_glyphs_master_user_data(self, ufo, master):
    """Set the GSFontMaster userData from the UFO master-specific user data."""
    pass
