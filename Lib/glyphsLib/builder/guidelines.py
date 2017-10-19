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

from glyphsLib.types import Point

LOCKED_NAME_SUFFIX = ' [locked]'


def to_ufo_guidelines(self, ufo_obj, glyphs_obj):
    """Set guidelines."""
    guidelines = glyphs_obj.guides
    if not guidelines:
        return
    new_guidelines = []
    for guideline in guidelines:
        x, y = guideline.position
        angle = guideline.angle
        angle = (360 - angle) % 360
        name = guideline.name
        if guideline.locked:
            name += LOCKED_NAME_SUFFIX
        new_guideline = {'x': x, 'y': y, 'angle': angle}
        if name:
            new_guideline['name'] = name
        new_guidelines.append(new_guideline)
    ufo_obj.guidelines = new_guidelines


def to_glyphs_guidelines(self, ufo_obj, glyphs_obj):
    """Set guidelines."""
    if not ufo_obj.guidelines:
        return
    for guideline in ufo_obj.guidelines:
        new_guideline = self.glyphs_module.GSGuideLine()
        name = guideline.name
        if name is not None and name.endswith(LOCKED_NAME_SUFFIX):
            name = name[:-len(LOCKED_NAME_SUFFIX)]
            new_guideline.locked = True
        new_guideline.name = name
        new_guideline.position = Point(guideline.x, guideline.y)
        new_guideline.angle = (360 - guideline.angle) % 360
        glyphs_obj.guides.append(new_guideline)
