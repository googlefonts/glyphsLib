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

import logging

from glyphsLib import classes
import defcon

from .builders import UFOBuilder, GlyphsBuilder

logger = logging.getLogger(__name__)


def to_ufos(font, include_instances=False, family_name=None,
            propagate_anchors=True, ufo_module=defcon):
    """Take .glyphs file data and load it into UFOs.

    Takes in data as Glyphs.app-compatible classes, as documented at
    https://docu.glyphsapp.com/

    If include_instances is True, also returns the parsed instance data.

    If family_name is provided, the master UFOs will be given this name and
    only instances with this name will be returned.
    """
    builder = UFOBuilder(
        font,
        ufo_module=ufo_module,
        family_name=family_name,
        propagate_anchors=propagate_anchors)

    result = list(builder.masters)

    if include_instances:
        return result, builder.instance_data
    return result


def to_glyphs(ufos, designspace=None, glyphs_module=classes):
    """
    Take a list of UFOs and combine them into a single .glyphs file.

    This should be the inverse function of `to_ufos`,
    so we should have to_glyphs(to_ufos(font)) == font
    """
    builder = GlyphsBuilder(
        ufos, designspace=designspace, glyphs_module=glyphs_module)
    return builder.font
