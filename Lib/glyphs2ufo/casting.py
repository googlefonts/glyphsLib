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


from __future__ import print_function, division, absolute_import

import datetime
import json
import re

__all__ = [
    'cast_data'
]


CUSTOM_INT_PARAMS = frozenset((
    'ascender', 'blueShift', 'capHeight', 'descender', 'hheaAscender',
    'hheaDescender', 'hheaLineGap', 'macintoshFONDFamilyID',
    'openTypeHeadLowestRecPPEM', 'openTypeHheaAscender',
    'openTypeHheaCaretSlopeRise', 'openTypeHheaCaretSlopeRun',
    'openTypeHheaDescender', 'openTypeHheaLineGap',
    'openTypeOS2StrikeoutPosition', 'openTypeOS2StrikeoutSize',
    'openTypeOS2SubscriptXOffset', 'openTypeOS2SubscriptXSize',
    'openTypeOS2SubscriptYOffset', 'openTypeOS2SubscriptYSize',
    'openTypeOS2SuperscriptXOffset', 'openTypeOS2SuperscriptXSize',
    'openTypeOS2SuperscriptYOffset', 'openTypeOS2SuperscriptYSize',
    'openTypeOS2TypoAscender', 'openTypeOS2TypoDescender',
    'openTypeOS2TypoLineGap', 'openTypeOS2WeightClass', 'openTypeOS2WidthClass',
    'openTypeOS2WinAscent', 'openTypeOS2WinDescent', 'openTypeVheaCaretOffset',
    'openTypeVheaCaretSlopeRise', 'openTypeVheaCaretSlopeRun',
    'openTypeVheaVertTypoAscender', 'openTypeVheaVertTypoDescender',
    'openTypeVheaVertTypoLineGap', 'postscriptBlueFuzz', 'postscriptBlueShift',
    'postscriptDefaultWidthX', 'postscriptSlantAngle',
    'postscriptUnderlinePosition', 'postscriptUnderlineThickness',
    'postscriptUniqueID', 'postscriptWindowsCharacterSet', 'shoulderHeight',
    'smallCapHeight', 'typoAscender', 'typoDescender', 'typoLineGap',
    'underlinePosition', 'underlineThickness', 'unitsPerEm', 'vheaVertAscender',
    'vheaVertDescender', 'vheaVertLineGap', 'winAscent', 'winDescent', 'year'))

CUSTOM_FLOAT_PARAMS = frozenset((
    'postscriptBlueScale',))

CUSTOM_TRUTHY_PARAMS = frozenset((
    'isFixedPitch', 'postscriptForceBold', 'postscriptIsFixedPitch',
    'DisableAllAutomaticBehaviour'))

CUSTOM_INTLIST_PARAMS = frozenset((
    'fsType', 'openTypeOS2CodePageRanges', 'openTypeOS2FamilyClass',
    'openTypeOS2Panose', 'openTypeOS2Type', 'openTypeOS2UnicodeRanges',
    'panose'))


def cast_data(data, types=None):
    """Cast the attributes of parsed glyphs file content."""

    if types is None:
        types = get_type_structure()

    for key, cur_type in types.items():
        if key not in data:
            continue
        if type(cur_type) == dict:
            for cur_data in data[key]:
                cast_data(cur_data, dict(cur_type))
        else:
            data[key] = cur_type(data[key])


def get_type_structure():
    """Generate and return the highest-level type hierarchy for glyphs data.
    https://github.com/schriftgestalt/GlyphsSDK/blob/master/GlyphsFileFormat.md
    """

    return {
        'DisplayStrings': list,
        'classes': {
            'automatic': truthy,
            'code': feature_syntax,
            'name': str
        },
        'copyright': str,
        'customParameters': custom_params,
        'date': glyphs_datetime,
        'designer': str,
        'designerURL': str,
        'disablesAutomaticAlignment': truthy,  # undocumented
        'disablesNiceNames': truthy,  # undocumented
        'familyName': str,
        'featurePrefixes': {
            'automatic': truthy,  # undocumented
            'code': feature_syntax,
            'name': str
        },
        'features': {
            'automatic': truthy,
            'code': feature_syntax,
            'disabled': truthy,  # undocumented
            'name': str,
            'notes': feature_syntax  # undocumented
        },
        'fontMaster': {
            'alignmentZones': pointlist,
            'ascender': int,
            'capHeight': int,
            'customParameters': custom_params,
            'descender': descender_val,
            'guideLines': {  # undocumented
                'angle': num,
                'locked': truthy,  # undocumented
                'position': point
            },
            'horizontalStems': intlist,
            'id': str,
            'userData': user_data,
            'verticalStems': intlist,
            'weight': str,  # undocumented
            'weightValue': int,
            'width': str,  # undocumented
            'widthValue': int,
            'xHeight': int
        },
        'glyphs': {
            'color': int,  # undocumented
            'export': truthy,  # undocumented
            'glyphname': str,
            'lastChange': glyphs_datetime,
            'layers': get_layer_type_structure(),
            'leftKerningGroup': str,
            'leftMetricsKey': str,
            'note': str,  # undocumented
            'rightKerningGroup': str,
            'rightMetricsKey': str,
            'unicode': hex_int,
            'widthMetricsKey': str  # undocumented
        },
        'instances': {
            'customParameters': custom_params,
            'interpolationWeight': int,  # undocumented
            'interpolationWidth': int,  # undocumented
            'name': str,  # undocumented
            'weightClass': str,  # undocumented
            'widthClass': str  # undocumented
        },
        'kerning': kerning,
        'manufacturer': str,
        'manufacturerURL': str,
        'unitsPerEm': int,
        'userData': user_data,
        'versionMajor': int,
        'versionMinor': version_minor
    }


def get_layer_type_structure():
    """Generate and return type hierarchy for a glyph layer."""

    structure = get_background_type_structure()
    structure.update({
        'associatedMasterId': str,
        'background': background,
        'layerId': str
    })
    return structure


def get_background_type_structure():
    """Generate and return type hierarchy for a glyph background."""

    return {
        'anchors': {
            'name': str,
            'position': point
        },
        'annotations': default,  # undocumented
        'components': {
            'anchor': str,
            'disableAlignment': truthy,  # undocumented
            'locked': truthy,  # undocumented
            'name': str,
            'transform': transform
        },
        'guideLines': {  # undocumented
            'angle': num,
            'position': point
        },
        'hints': default,  # undocumented
        'leftMetricsKey': str,
        'rightMetricsKey': str,
        'name': str,
        'paths': {
            'closed': truthy,
            'nodes': nodelist
        },
        'width': num
    }


def background(data):
    """Use background type structure to cast a single dictionary."""

    cast_data(data, get_background_type_structure())
    return data


def default(value):
    """Just return the value (i.e. don't cast it to anything)."""
    return value


def truthy(string):
    """Determine if an int stored in a string is truthy."""
    return bool(int(string))


def num(string):
    """Prefer casting to int, but use float if necessary."""

    val = float(string)
    int_val = int(val)
    return int_val if int_val == val else val


def hex_int(string):
    """Return the hexidecimal value represented by a string."""
    return int(string, 16)


def vector(string, dimension):
    """Parse a vector from a string with format {X, Y, Z, ...}."""

    rx = '{%s}' % ', '.join(['([-.e\d]+)'] * dimension)
    return [num(i) for i in re.match(rx, string).groups()]


def point(string):
    return vector(string, 2)


def transform(string):
    return vector(string, 6)


def node(string):
    """Cast a node from a string with format X Y TYPE [SMOOTH]."""

    rx = '([-.e\d]+) ([-.e\d]+) (LINE|CURVE|OFFCURVE|n/a)(?: (SMOOTH))?'
    m = re.match(rx, string).groups()
    return [num(m[0]), num(m[1]), m[2].lower(), bool(m[3])]


def intlist(strlist):
    return map(int, strlist)


def pointlist(strlist):
    return map(point, strlist)


def nodelist(strlist):
    return map(node, strlist)


def glyphs_datetime(string):
    """Parse a datetime object from a string."""

    # parse timezone ourselves, since %z is not always supported
    # see: http://bugs.python.org/issue6641
    string, tz = string.rsplit(' ', 1)
    datetime_obj = datetime.datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
    offset = datetime.timedelta(hours=int(tz[:3]), minutes=int(tz[0] + tz[3:]))
    return datetime_obj + offset


def kerning(kerning_data):
    """Cast the values in kerning data to ints."""

    new_data = {}
    for master_id, master_map in kerning_data.items():
        new_data[master_id] = {}
        for left_glyph, glyph_map in master_map.items():
            new_data[master_id][left_glyph] = {}
            for right_glyph, value in glyph_map.items():
                new_data[master_id][left_glyph][right_glyph] = num(value)
    return new_data


def descender_val(string):
    """Ensure that descender values are always negative."""

    num = int(string)
    assert num < 0
    return num


def version_minor(string):
    """Ensure that the minor version number is between 0 and 999."""

    num = int(string)
    assert num >= 0 and num <= 999
    return num


def feature_syntax(string):
    """Replace escaped characters with their intended characters.
    Unescapes curved quotes to straight quotes, so that we can definitely
    include this casted data in feature syntax.
    """

    replacements = (
        ('\\012', '\n'), ('\\011', '\t'), ('\\U2018', "'"), ('\\U2019', "'"),
        ('\\U201C', '"'), ('\\U201D', '"'))
    for escaped, unescaped in replacements:
        string = string.replace(escaped, unescaped)
    return string


def custom_params(param_list):
    """Cast some known data in custom parameters."""

    for param in param_list:
        name = param['name']
        value = param['value']
        if name in CUSTOM_INT_PARAMS:
            param['value'] = int(value)
        if name in CUSTOM_FLOAT_PARAMS:
            param['value'] = float(value)
        if name in CUSTOM_TRUTHY_PARAMS:
            param['value'] = truthy(value)
        if name in CUSTOM_INTLIST_PARAMS:
            param['value'] = intlist(value)

    return param_list


def user_data(data_dict):
    """Cast some known user data."""

    num_params = ('GSOffsetHorizontal', 'GSOffsetVertical')

    new_data = {}
    for key, val in data_dict.iteritems():
        if key in num_params:
            new_data[key] = num(val)

    data_dict.update(new_data)
    return data_dict
