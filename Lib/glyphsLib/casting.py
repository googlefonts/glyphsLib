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
from fontTools.misc.py23 import basestring
import datetime
import logging
import re

__all__ = [
    'cast_data',
    'uncast_data'
]

logger = logging.getLogger(__name__)


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
    'vheaVertDescender', 'vheaVertLineGap', 'weightClass', 'widthClass',
    'winAscent', 'winDescent', 'xHeight', 'year'))

CUSTOM_FLOAT_PARAMS = frozenset((
    'postscriptBlueScale',))

CUSTOM_NUM_PARAMS = CUSTOM_INT_PARAMS | CUSTOM_FLOAT_PARAMS

CUSTOM_TRUTHY_PARAMS = frozenset((
    'isFixedPitch', 'postscriptForceBold', 'postscriptIsFixedPitch',
    'Don\u2019t use Production Names', 'DisableAllAutomaticBehaviour',
    'Use Typo Metrics', 'Has WWS Names'))


CUSTOM_INTLIST_PARAMS = frozenset((
    'fsType', 'openTypeOS2CodePageRanges', 'openTypeOS2FamilyClass',
    'openTypeOS2Panose', 'openTypeOS2Type', 'openTypeOS2UnicodeRanges',
    'panose', 'unicodeRanges'))

# mutate list in place
def _mutate_list(fn, l):
    assert isinstance(l, list)
    for i in range(len(l)):
        l[i] = fn(l[i])
    return l

class RWGlyphs(object):
    def __init__(self, value = None):
        if isinstance(value, (str, unicode)):
            value = self.read(value)
        self.value = value

    def convert(self, data, to_typed):
        return self.read(data) if to_typed else self.write(data)

    def read(self, src):
        """Return a typed value representing the structured glyphs strings."""
        raise NotImplementedError('%s read' % type(self).__name__)

    def write(self, val):
        """Return structured glyphs strings representing the typed value."""
        raise NotImplementedError('%s write' % type(self).__name__)


class RWBackground(RWGlyphs):
    """Use background type structure to cast a single dictionary."""
    def convert(self, data, to_typed):
        _convert_data(data, to_typed, _BACKGROUND_TYPE_STRUCTURE)
        return data


class RWDefault(RWGlyphs):
    """Passes src, val through unchanged."""

    def read(self, src):
        return src

    def write(self, val):
        return val


class RWString(RWGlyphs):
    """Reads/writes the value as a string.  Same behavior as default, but
    here so we can keep the distinction clear.  Default can get lists as
    arguments, this should only get strings."""

    def read(self, src):
        return src

    def write(self, val):
        if not isinstance(val, basestring):
            logger.error('val (%s): "%s"' % (type(val).__name__, val))
            raise ValueError('not a string')
        return val


class RWTruthy(RWGlyphs):
    """Reads/write a boolean."""

    def read(self, src):
        if src is None:
            return False
        return bool(int(src))

    def write(self, val):
        assert isinstance(val, bool)
        return str(int(val))


class RWInteger(RWGlyphs):
    """Read/write an int."""

    def read(self, src):
        return int(src)

    def write(self, val):
        assert isinstance(val, int)
        return str(val)


class RWNum(RWGlyphs):
    """Read/write an int or float."""

    def read(self, src):
        float_val = float(src)
        return int(float_val) if float_val.is_integer() else float_val

    def write(self, val):
        if isinstance(val, float):
            if val.is_integer():
                val = int(val)
        elif isinstance(val, int):
            pass
        else:
            raise TypeError(
                "expected int or float, found " + type(val).__name__)
        return repr(val)


class RWHexInt(RWGlyphs):
    """Read/write a hex int."""

    def read(self, src):
        return int(src, 16)

    def write(self, val):
        assert isinstance(val, int)
        return '%04X' % val


class RWVector(RWGlyphs):
    """Read/write a vector in curly braces."""

    def __init__(self, dimension, value = None):
        self.dimension = dimension
        self.regex = re.compile('{%s}' % ', '.join(['([-.e\d]+)'] * dimension))
        super(RWVector, self).__init__(value)
        

    def read(self, src):
        """Parse a vector from a string with format {X, Y, Z, ...}."""
        n = num()
        return [n.read(i) for i in self.regex.match(src).groups()]

    def write(self, val):
        assert isinstance(val, list) and len(val) == self.dimension
        return '{%s}' % (', '.join(str(v) for v in val))


class RWPoint(RWVector):
    """Read/write a two-element vector."""
    def __init__(self, value = None):
        if value:
            super(RWPoint, self).__init__(2, value)
        else:
            super(RWPoint, self).__init__(2, (0, 0))


class RWTransform(RWVector):
    """Read/write a six-element vector."""
    
    def __init__(self, dimension = 6, value = None):
        super(RWTransform, self).__init__(6, value)
    
    def read(self, src = None):
        if src:
            return super(RWTransform, self).read(src)
        else:
            return (1, 0, 0, 1, 0, 0)




class RWIntList(RWGlyphs):
    """Read/write a list of ints."""

    def read(self, src):
        return _mutate_list(int, src)

    def write(self, val):
        return _mutate_list(str, val)


class RWPointList(RWGlyphs):
    """Read/write a list of points."""

    def read(self, src):
        return _mutate_list(point.read, src)

    def write(self, val):
        return _mutate_list(point.write, val)


class RWNodeList(RWGlyphs):
    """Read/write a list of nodes."""

    def read(self, src):
        return _mutate_list(node.read, src)

    def write(self, val):
        return _mutate_list(node.write, val)


class RWDateTime(RWGlyphs):
    """Read/write a datetime.  Doesn't maintain time zone offset."""
    def __init__(self, value = None):
        if value:
            self.value = self.read(value)
        else:
            self.value = None
    
    def read(self, src):
        """Parse a datetime object from a string."""
        # parse timezone ourselves, since %z is not always supported
        # see: http://bugs.python.org/issue6641
        string, tz = src.rsplit(' ', 1)
        datetime_obj = datetime.datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
        offset = datetime.timedelta(hours=int(tz[:3]), minutes=int(tz[0] + tz[3:]))
        return datetime_obj + offset

    def write(self, val):
        return str(val) + ' +0000'
    def strftime(self, args):
        try:
            return self.value.strftime(val)
        except:
            return None
            
class RWColor(RWGlyphs):

    def read(self, src = None):
        if src is None:
            return None
        if src[0] == "(":
            src = src[1:-1]
            color = src.split(",")
            color = tuple([int(c) for c in color])
        else:
            color = int(src)
        return color
    def write(self, val):
        raise "Not implemented"

class RWKerning(RWGlyphs):
    """Read/write kerning data structure."""

    def read(self, src):
        """Cast the values in kerning data to ints."""
        for master_id, master_map in src.items():
            for left_glyph, glyph_map in master_map.items():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = num.read(value)
        return src

    def write(self, val):
        for master_id, master_map in val.items():
            for left_glyph, glyph_map in master_map.items():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = num.write(value)
        return val


class RWDescenderVal(RWNum):
    """Read and check value of descender."""

    def read(self, src):
        val = int(src)
        assert val < 0
        return val


class RWVersionMinor(RWNum):
    """Read and check value of minor version."""

    def read(self, src):
        val = int(src)
        assert 0 <= val <= 999
        return val


class RWCustomParams(RWGlyphs):
    """Read/write custom params."""

    def read(self, src):
        assert isinstance(src, list)
        for param in src:
            name = param['name']
            value = param['value']

            if name in CUSTOM_NUM_PARAMS:
                value = num.read(value)
            elif name in CUSTOM_TRUTHY_PARAMS:
                value = truthy.read(value)
            elif name in CUSTOM_INTLIST_PARAMS:
                value = intlist.read(value)

            param['value'] = value
        return src

    def write(self, val):
        assert isinstance(val, list)
        for param in val:
            name = param['name']
            value = param['value']

            if name in CUSTOM_NUM_PARAMS:
                value = num.write(value)
            elif name in CUSTOM_TRUTHY_PARAMS:
                value = truthy.write(value)
            elif name in CUSTOM_INTLIST_PARAMS:
                value = intlist.write(value)
            param['value'] = value
        return val


class RWUserData(RWGlyphs):
    """Read/write some known user data."""

    _num_params = ('GSOffsetHorizontal', 'GSOffsetVertical')

    def read(self, src):
        """Cast some known user data."""
        new_data = {}
        for k, v in src.items():
            if k in RWUserData._num_params:
                new_data[k] = num.read(v)
        src.update(new_data)
        return src

    def write(self, val):
        new_data = {}
        for k, v in val.items():
            if k in RWUserData._num_params:
                new_data[k] = num.write(v)
        val.update(new_data)
        return val


# Like singletons, but... not.  Used as type structure values.

background = RWBackground
default = RWDefault
string = RWString
integer = RWInteger
truthy = RWTruthy
num = RWNum
hex_int = RWHexInt
point = RWPoint
transform = RWTransform
#node = RWNode()
intlist = RWIntList()
pointlist = RWPointList()
nodelist = RWNodeList()
glyphs_datetime = RWDateTime
color = RWColor
kerning = RWKerning()
descender_val = RWDescenderVal
version_minor = RWVersionMinor
custom_params = RWCustomParams
user_data = RWUserData

def cast_data(data):
    _convert_data(data, True, _TYPE_STRUCTURE)


def uncast_data(data):
    _convert_data(data, False, _TYPE_STRUCTURE)


def _convert_data(data, to_typed, types):
    """Cast the attributes of parsed glyphs file content."""

    for key, cur_type in types.items():
        if key not in data:
            continue
        if isinstance(cur_type, dict):
            # data[key] is a list of data of type dict
            for cur_data in data[key]:
                _convert_data(cur_data, to_typed, cur_type)
        else:
            data[key] = cur_type.convert(data[key], to_typed)
def actualPrecition(Float):
    ActualPrecition = 3
    Integer = round(Float * 1000.0)
    while ActualPrecition >= 0:
        if Integer != round(Integer / 10.0) * 10:
            return ActualPrecition
        
        Integer = round(Integer / 10.0)
        ActualPrecition -= 1
    
    if ActualPrecition < 0:
        ActualPrecition = 0
    return ActualPrecition


def floatToString(Float, precision = 3):
    try:
        ActualPrecition = actualPrecition(Float)
        precision = min(precision, ActualPrecition)
        fractional = math.modf(math.fabs(Float))[0]
        if precision >= 3 and fractional >= 0.001 and fractional <= 0.999:
            return "%.3f" % Float
        if precision == 2 and fractional >= 0.01 and fractional <= 0.99:
            return "%.2f" % Float
        if precision == 1 and fractional >= 0.1 and fractional <= 0.9:
            return "%.1f" % Float
        else:
            return "%d" % Float
    except:
        print(traceback.format_exc())