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

import logging
import re

logger = logging.getLogger(__name__)


def to_ufo_kerning(self, ufo, kerning_data):
    """Add .glyphs kerning to an UFO."""

    warning_msg = 'Non-existent glyph class %s found in kerning rules.'
    class_glyph_pairs = []

    for left, pairs in kerning_data.items():
        match = re.match(r'@MMK_L_(.+)', left)
        left_is_class = bool(match)
        if left_is_class:
            left = 'public.kern1.%s' % match.group(1)
            if left not in ufo.groups:
                logger.warn(warning_msg % left)
                continue
        for right, kerning_val in pairs.items():
            match = re.match(r'@MMK_R_(.+)', right)
            right_is_class = bool(match)
            if right_is_class:
                right = 'public.kern2.%s' % match.group(1)
                if right not in ufo.groups:
                    logger.warn(warning_msg % right)
                    continue
            if left_is_class != right_is_class:
                if left_is_class:
                    pair = (left, right, True)
                else:
                    pair = (right, left, False)
                class_glyph_pairs.append(pair)
            ufo.kerning[left, right] = kerning_val

    seen = {}
    for classname, glyph, is_left_class in reversed(class_glyph_pairs):
        _remove_rule_if_conflict(ufo, seen, classname, glyph, is_left_class)


def _remove_rule_if_conflict(ufo, seen, classname, glyph, is_left_class):
    """Check if a class-to-glyph kerning rule has a conflict with any existing
    rule in `seen`, and remove any conflicts if they exist.
    """

    original_pair = (classname, glyph) if is_left_class else (glyph, classname)
    val = ufo.kerning[original_pair]
    rule = original_pair + (val,)

    old_glyphs = ufo.groups[classname]
    new_glyphs = []
    for member in old_glyphs:
        pair = (member, glyph) if is_left_class else (glyph, member)
        existing_rule = seen.get(pair)
        if (existing_rule is not None and
            existing_rule[-1] != val and
            pair not in ufo.kerning):
            logger.warn(
                'Conflicting kerning rules found in %s master for glyph pair '
                '"%s, %s" (%s and %s), removing pair from latter rule' %
                ((ufo.info.styleName,) + pair + (existing_rule, rule)))
        else:
            new_glyphs.append(member)
            seen[pair] = rule

    if new_glyphs != old_glyphs:
        del ufo.kerning[original_pair]
        for member in new_glyphs:
            pair = (member, glyph) if is_left_class else (glyph, member)
            ufo.kerning[pair] = val


def to_ufo_glyph_groups(self, kerning_groups, glyph_data):
    """Add a glyph to its kerning groups, creating new groups if necessary."""

    glyph_name = glyph_data.name
    group_keys = {
        '1': 'rightKerningGroup',
        '2': 'leftKerningGroup'}
    for side, group_key in group_keys.items():
        group = getattr(glyph_data, group_key)
        if group is None or len(group) == 0:
            continue
        group = 'public.kern%s.%s' % (side, group)
        kerning_groups[group] = kerning_groups.get(group, []) + [glyph_name]


def to_ufo_kerning_groups(self, ufo, kerning_groups):
    """Add kerning groups to an UFO."""

    for name, glyphs in kerning_groups.items():
        ufo.groups[name] = glyphs
