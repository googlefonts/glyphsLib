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


import re
from collections import OrderedDict
from copy import deepcopy

from .constants import BRACKET_GLYPH_RE, UFO_KERN_GROUP_PATTERN


def flip_class_side(s):
    if s.startswith("@MMK_L_"):
        return f"@MMK_R_{s[7:]}"
    elif s.startswith("@MMK_R_"):
        return f"@MMK_L_{s[7:]}"
    return s


def to_ufo_kerning(self):
    for master in self.font.masters:
        kerning_source = master.metricsSource  # Maybe be a linked master
        if kerning_source is None:
            kerning_source = master
        both_directions = (
            kerning_source.id in self.font.kerningLTR
            and kerning_source.id in self.font.kerningRTL
        )
        combined_kerning = OrderedDict()
        if kerning_source.id in self.font.kerningLTR:
            kerning = self.font.kerningLTR[kerning_source.id]
            combined_kerning = deepcopy(kerning) if both_directions else kerning
        if kerning_source.id in self.font.kerningRTL:
            for kern1, subtable in self.font.kerningRTL[kerning_source.id].items():
                # flip RTL sides and combine with existing LTR dicts, but take care
                # not to overwrite whole kern2 subtable when the flipped kern1
                # coincides with an existing LTR kern1
                # https://github.com/googlefonts/glyphsLib/issues/1039
                kern1_key = flip_class_side(kern1)
                existing_kern2 = combined_kerning.setdefault(kern1_key, {})
                new_kern2 = {flip_class_side(kern2): v for kern2, v in subtable.items()}
                # TODO: use 3.9+ dict.update() or | operator after we drop python3.8
                combined_kerning[kern1_key] = {**existing_kern2, **new_kern2}
        if combined_kerning:
            _to_ufo_kerning(self, self._sources[master.id].font, combined_kerning)


def _to_ufo_kerning(self, ufo, kerning_data):
    """Add .glyphs kerning to an UFO."""

    warning_msg = "Non-existent glyph class %s found in kerning rules."

    for left, pairs in kerning_data.items():
        match = re.match(r"@MMK_L_(.+)", left)
        left_is_class = bool(match)
        if left_is_class:
            left = "public.kern1.%s" % match.group(1)
            if left not in ufo.groups:
                self.logger.warning(warning_msg % left)
        for right, kerning_val in pairs.items():
            match = re.match(r"@MMK_R_(.+)", right)
            right_is_class = bool(match)
            if right_is_class:
                right = "public.kern2.%s" % match.group(1)
                if right not in ufo.groups:
                    self.logger.warning(warning_msg % right)
            ufo.kerning[left, right] = kerning_val


def to_glyphs_kerning(self):
    """Add UFO kerning to GSFont."""
    for master_id, source in self._sources.items():
        for (left, right), value in source.font.kerning.items():
            if BRACKET_GLYPH_RE.match(left) or BRACKET_GLYPH_RE.match(right):
                # Skip all bracket glyph entries, as they are duplicates of their
                # parents'.
                continue
            left_match = UFO_KERN_GROUP_PATTERN.match(left)
            right_match = UFO_KERN_GROUP_PATTERN.match(right)
            if left_match:
                left = "@MMK_L_{}".format(left_match.group(2))
            if right_match:
                right = "@MMK_R_{}".format(right_match.group(2))
            self.font.setKerningForPair(master_id, left, right, value)
