#!/usr/bin/python
# -*- coding: utf-8 -*-

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

from __future__ import unicode_literals
import re
import datetime
import traceback
import math
from fontTools.misc.py23 import unicode

__all__ = [
    'transform', 'point', 'rect'
]


class baseType(object):
    default = None

    def __init__(self, value=None):
        if value:
            self.value = self.read(value)
        else:
            self.value = self.default

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.plistValue())

    def read(self, src):
        """Return a typed value representing the structured glyphs strings."""
        raise NotImplementedError('%s read' % type(self).__name__)

    def plistValue(self):
        """Return structured glyphs strings representing the typed value."""
        raise NotImplementedError('%s write' % type(self).__name__)


class point(object):
    """Read/write a vector in curly braces."""
    dimension = 2
    default = [None, None]
    regex = re.compile('{%s}' % ', '.join(['([-.e\\d]+)'] * dimension))

    def __init__(self, value=None, value2=None, rect=None):
        if value is not None and value2 is not None:
            self.value = [value, value2]
        elif value is not None and value2 is None:
            value = value.replace('"', '')
            self.value = [float(i) for i in self.regex.match(value).groups()]
        else:
            self.value = self.default

        self.rect = rect

    def __repr__(self):
        return '<point x=%s y=%s>' % (self.value[0], self.value[1])

    def plistValue(self):
        assert (isinstance(self.value, list) and
                len(self.value) == self.dimension)
        if self.value is not self.default:
            return '"{%s}"' % (', '.join(floatToString(v, 3) for v in self.value))

    def __getitem__(self, key):
        if type(key) is int and key < self.dimension:
            if key < len(self.value):
                return self.value[key]
            else:
                return 0
        else:
            raise IndexError

    def __setitem__(self, key, value):
        if type(key) is int and key < self.dimension:
            while self.dimension > len(self.value):
                self.value.append(0)
            self.value[key] = value
        else:
            raise IndexError

    def __len__(self):
        return self.dimension

    @property
    def x(self):
        return self.value[0]
    @x.setter
    def x(self, value):
        self.value[0] = value
        # Update parent rect
        if self.rect:
            self.rect.value[0] = value

    @property
    def y(self):
        return self.value[1]
    @y.setter
    def y(self, value):
        self.value[1] = value
        # Update parent rect
        if self.rect:
            self.rect.value[1] = value


class size(point):
    def __repr__(self):
        return '<size width=%s height=%s>' % (self.value[0], self.value[1])

    @property
    def width(self):
        return self.value[0]
    @width.setter
    def width(self, value):
        self.value[0] = value
        # Update parent rect
        if self.rect:
            self.rect.value[2] = value

    @property
    def height(self):
        return self.value[1]
    @height.setter
    def height(self, value):
        self.value[1] = value
        # Update parent rect
        if self.rect:
            self.rect.value[3] = value


class rect(object):
    """Read/write a rect of two points in curly braces."""
    #crop = "{{0, 0}, {427, 259}}";

    dimension = 4
    default = [0, 0, 0, 0]
    regex = re.compile('{{([-.e\d]+), ([-.e\d]+)}, {([-.e\d]+), ([-.e\d]+)}}')

    def __init__(self, value = None, value2 = None):

        if value is not None and value2 is not None:
            self.value = [value[0], value[1], value2[0], value2[1]]
        elif value is not None and value2 is None:
            value = value.replace('"', '')
            self.value = [float(i) for i in self.regex.match(value).groups()]
        else:
            self.value = self.default

    def plistValue(self):
        assert isinstance(self.value, list) and len(self.value) == self.dimension
        return '"{{%s, %s}, {%s, %s}}"' % (floatToString(self.value[0], 3), floatToString(self.value[1], 3), floatToString(self.value[2], 3), floatToString(self.value[3], 3))

    def __repr__(self):
        return '<rect origin=%s size=%s>' % (str(self.origin), str(self.size))

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        if type(key) is int and key < self.dimension:
            while self.dimension > len(self.value):
                self.value.append(0)
            self.value[key] = value
        else:
            raise KeyError
    def __len__(self):
        return self.dimension

    @property
    def origin(self):
        return point(self.value[0], self.value[1], rect = self)
    @origin.setter
    def origin(self, value):
        self.value[0] = value.x
        self.value[1] = value.y

    @property
    def size(self):
        return size(self.value[2], self.value[3], rect = self)
    @size.setter
    def size(self, value):
        self.value[2] = value.width
        self.value[3] = value.height


class transform(point):
    """Read/write a six-element vector."""
    dimension = 6
    default = [None, None, None, None, None, None]
    regex = re.compile('{%s}' % ', '.join(['([-.e\d]+)'] * dimension))

    def __init__(self, value = None, value2 = None, value3 = None, value4 = None, value5 = None, value6 = None):

        if value is not None and value2 is not None and value3 is not None and value4 is not None and value5 is not None and value6 is not None:
            self.value = [value, value2, value3, value4, value5, value6]
        elif value is not None and value2 is None:
            value = value.replace('"', '')
            self.value = [float(i) for i in self.regex.match(value).groups()]
        else:
            self.value = self.default

    def __repr__(self):
        return '<affine transformation %s>' % (' '.join(map(str, self.value)))

    def plistValue(self):
        assert (isinstance(self.value, list) and
                len(self.value) == self.dimension)
        return '"{%s}"' % (', '.join(floatToString(v, 5) for v in self.value))


class glyphs_datetime(baseType):
    """Read/write a datetime.  Doesn't maintain time zone offset."""

    def read(self, src):
        src = src.replace('"', '')
        """Parse a datetime object from a string."""
        # parse timezone ourselves, since %z is not always supported
        # see: http://bugs.python.org/issue6641
        string, tz = src.rsplit(' ', 1)
        if 'AM' in string or 'PM' in string:
            datetime_obj = datetime.datetime.strptime(
                string, '%Y-%m-%d %I:%M:%S %p'
            )
        else:
            datetime_obj = datetime.datetime.strptime(
                string, '%Y-%m-%d %H:%M:%S'
            )
        offset = datetime.timedelta(
            hours=int(tz[:3]), minutes=int(tz[0] + tz[3:]))
        return datetime_obj + offset

    def plistValue(self):
        return "\"%s +0000\"" % self.value

    def strftime(self, val):
        try:
            return self.value.strftime(val)
        except:
            return None


class color(baseType):

    def read(self, src=None):
        src.replace('"', '')
        if src is None:
            return None
        if src[0] == "(":
            src = src[1:-1]
            color = src.split(",")
            color = tuple([int(c) for c in color])
        else:
            color = int(src)
        return color

    def __repr__(self):
        return self.value.__repr__()

    def plistValue(self):
        if self.value is not None:
            return str(self.value)
        return None


# mutate list in place
def _mutate_list(fn, l):
    assert isinstance(l, list)
    for i in range(len(l)):
        l[i] = fn(l[i])
    return l


def readIntlist(src):
    return _mutate_list(int, src)


def writeIntlist(val):
    return _mutate_list(str, val)


def actualPrecition(Float):
    ActualPrecition = 5
    Integer = round(Float * 100000.0)
    while ActualPrecition >= 0:
        if Integer != round(Integer / 10.0) * 10:
            return ActualPrecition

        Integer = round(Integer / 10.0)
        ActualPrecition -= 1

    if ActualPrecition < 0:
        ActualPrecition = 0
    return ActualPrecition


def floatToString(Float, precision=3):
    try:
        ActualPrecition = actualPrecition(Float)
        precision = min(precision, ActualPrecition)
        fractional = math.modf(math.fabs(Float))[0]
        if precision >= 5 and fractional >= 0.000005 and fractional <= 0.999995:
            return "%.5f" % Float
        elif precision >= 4 and fractional >= 0.00005 and fractional <= 0.99995:
            return "%.4f" % Float
        elif precision >= 3 and fractional >= 0.0005 and fractional <= 0.9995:
            return "%.3f" % Float
        elif precision >= 2 and fractional >= 0.005 and fractional <= 0.995:
            return "%.2f" % Float
        elif precision >= 1 and fractional >= 0.05 and fractional <= 0.95:
            return "%.1f" % Float
        else:
            return "%.0f" % Float
    except:
        print(traceback.format_exc())
