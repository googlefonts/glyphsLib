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

from .constants import BRACKET_GLYPH_RE, UFO_KERN_GROUP_PATTERN


def to_ufo_kerning(self):
    used_groups = set()
    for master in self.font.masters:
        ufo = self._sources[master.id].font
        kerning_source = master.metricsSource  # Maybe be a linked master
        if kerning_source is None:
            kerning_source = master
        if kerning_source.id in self.font.kerningLTR:
            kerning = self.font.kerningLTR[kerning_source.id]
            used_groups.update(_to_ufo_kerning(self, ufo, kerning))
        if kerning_source.id in self.font.kerningRTL:
            kerning = self.font.kerningRTL[kerning_source.id]
            used_groups.update(_to_ufo_kerning(self, ufo, kerning, "RTL"))

    # Prune kerning groups that are not used in kerning rules
    # (added but unused .RTL groups, see groups.py)
    for master in self.font.masters:
        ufo = self._sources[master.id].font
        for group in list(ufo.groups.keys()):
            # Group exists in font but not in kerning rules
            if group.startswith("public.kern") and group not in used_groups:
                del ufo.groups[group]

    # Remove .RTL from groups
    for master in self.font.masters:
        ufo = self._sources[master.id].font
        for group in list(ufo.groups.keys()):
            if group.startswith("public.kern") and group.endswith(".RTL"):
                ufo.groups[group.replace(".RTL", "")] = ufo.groups[group]
                del ufo.groups[group]

    # Remove .RTL from kerning
    for master in self.font.masters:
        ufo = self._sources[master.id].font
        print(ufo.kerning)
        for first, second in list(ufo.kerning.keys()):
            if (
                first.startswith("public.kern")
                and first.endswith(".RTL")
                and second.startswith("public.kern")
                and second.endswith(".RTL")
            ):
                print("kerning both", first, second)
                ufo.kerning[
                    first.replace(".RTL", ""), second.replace(".RTL", "")
                ] = ufo.kerning[first, second]
                del ufo.kerning[first, second]
            elif first.startswith("public.kern") and first.endswith(".RTL"):
                print("kerning first", first, second)
                ufo.kerning[first.replace(".RTL", ""), second] = ufo.kerning[
                    first, second
                ]
                del ufo.kerning[first, second]
            elif second.startswith("public.kern") and second.endswith(".RTL"):
                print("kerning second", first, second)
                ufo.kerning[first, second.replace(".RTL", "")] = ufo.kerning[
                    first, second
                ]
                del ufo.kerning[first, second]


def _to_ufo_kerning(self, ufo, kerning_data, direction="LTR"):
    """Add .glyphs kerning to an UFO."""

    class_missing_msg = "Non-existent glyph class %s found in kerning rules."
    overwriting_kerning_msg = "Overwriting kerning value for %s."

    used_groups = set()

    for first, pairs in kerning_data.items():
        first, is_class = _ufo_class_name(first, direction, 1)
        if is_class:
            used_groups.add(first)
        if is_class and first not in ufo.groups:
            self.logger.warning(class_missing_msg, first)

        for second, kerning_val in pairs.items():
            second, is_class = _ufo_class_name(second, direction, 2)
            if is_class:
                used_groups.add(second)
            if is_class and second not in ufo.groups:
                self.logger.warning(class_missing_msg, second)

            if (first, second) in ufo.kerning:
                self.logger.warning(overwriting_kerning_msg, first, second)
            ufo.kerning[first, second] = kerning_val

    return used_groups


def _ufo_class_name(name, direction, order):
    """Return the UFO class name for a .glyphs class name."""
    if order == 1:
        side = "L" if direction == "LTR" else "R"
    else:
        assert order == 2
        side = "R" if direction == "LTR" else "L"

    match = re.match(rf"@MMK_{side}_(.+)", name)

    name_is_class = bool(match)
    if name_is_class:
        name = f"public.kern{order}.{match.group(1)}"
        if direction == "RTL":
            name += ".RTL"

    return name, name_is_class


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
