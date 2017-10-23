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

from collections import deque


def to_ufo_names(self, ufo, master, family_name):
    width = master.width
    weight = master.weight
    custom = master.customName
    is_italic = bool(master.italicAngle)

    styleName = build_style_name(
        width if width != 'Regular' else '',
        weight,
        custom,
        is_italic
    )
    styleMapFamilyName, styleMapStyleName = build_stylemap_names(
        family_name=family_name,
        style_name=styleName,
        is_bold=(styleName == 'Bold'),
        is_italic=is_italic
    )
    ufo.info.familyName = family_name
    ufo.info.styleName = styleName
    ufo.info.styleMapFamilyName = styleMapFamilyName
    ufo.info.styleMapStyleName = styleMapStyleName


def build_stylemap_names(family_name, style_name, is_bold=False,
                         is_italic=False, linked_style=None):
    """Build UFO `styleMapFamilyName` and `styleMapStyleName` based on the
    family and style names, and the entries in the "Style Linking" section
    of the "Instances" tab in the "Font Info".

    The value of `styleMapStyleName` can be either "regular", "bold", "italic"
    or "bold italic", depending on the values of `is_bold` and `is_italic`.

    The `styleMapFamilyName` is a combination of the `family_name` and the
    `linked_style`.

    If `linked_style` is unset or set to 'Regular', the linked style is equal
    to the style_name with the last occurrences of the strings 'Regular',
    'Bold' and 'Italic' stripped from it.
    """

    styleMapStyleName = ' '.join(s for s in (
        'bold' if is_bold else '',
        'italic' if is_italic else '') if s) or 'regular'
    if not linked_style or linked_style == 'Regular':
        linked_style = _get_linked_style(style_name, is_bold, is_italic)
    if linked_style:
        styleMapFamilyName = family_name + ' ' + linked_style
    else:
        styleMapFamilyName = family_name
    return styleMapFamilyName, styleMapStyleName


def build_style_name(width='', weight='', custom='', is_italic=False):
    """Build style name from width, weight, and custom style strings
    and whether the style is italic.
    """

    return ' '.join(
        s for s in (custom, width, weight, 'Italic' if is_italic else '') if s
    ) or 'Regular'


def _get_linked_style(style_name, is_bold, is_italic):
    # strip last occurrence of 'Regular', 'Bold', 'Italic' from style_name
    # depending on the values of is_bold and is_italic
    linked_style = deque()
    is_regular = not (is_bold or is_italic)
    for part in reversed(style_name.split()):
        if part == 'Regular' and is_regular:
            is_regular = False
        elif part == 'Bold' and is_bold:
            is_bold = False
        elif part == 'Italic' and is_italic:
            is_italic = False
        else:
            linked_style.appendleft(part)
    return ' '.join(linked_style)
