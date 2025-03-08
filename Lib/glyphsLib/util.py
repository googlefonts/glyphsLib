# Copyright 2016 Google Inc. All Rights Reserved.
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

# TODO: (jany) merge with builder/common.py

from __future__ import annotations
from typing import List, Optional, Tuple, Any
import logging
import itertools
import os
import shutil
from fontTools.misc.textTools import num2binary

logger = logging.getLogger(__name__)


def build_ufo_path(out_dir, family_name, style_name):
    """Build string to use as a UFO path."""

    return os.path.join(
        out_dir,
        "%s-%s.ufo"
        % ((family_name or "").replace(" ", ""), (style_name or "").replace(" ", "")),
    )


def open_ufo(path, font_class, **kwargs):
    try:
        return font_class.open(path, lazy=False, **kwargs)  # ufoLib2
    except AttributeError:
        return font_class(path, **kwargs)  # defcon, fontParts, etc.


def write_ufo(ufo, out_dir):
    """Write a UFO."""

    out_path = build_ufo_path(out_dir, ufo.info.familyName, ufo.info.styleName)

    logger.info("Writing %s" % out_path)
    clean_ufo(out_path)
    ufo.save(out_path)


def clean_ufo(path):
    """Make sure old UFO data is removed, as it may contain deleted glyphs."""

    if path.endswith(".ufo") and os.path.exists(path):
        shutil.rmtree(path)


def ufo_create_background_layer_for_all_glyphs(ufo_font):
    """Create a background layer for all glyphs in ufo_font if not present to
    reduce roundtrip differences."""

    if "public.background" in ufo_font.layers:
        background = ufo_font.layers["public.background"]
    else:
        background = ufo_font.newLayer("public.background")

    for glyph in ufo_font:
        if glyph.name not in background:
            background.newGlyph(glyph.name)


def cast_to_number_or_bool(inputstr):
    """Cast a string to int, float or bool. Return original string if it can't be
    converted.

    Scientific expression is converted into float.
    """
    if inputstr.strip().lower() == "true":
        return True
    elif inputstr.strip().lower() == "false":
        return False
    try:
        return int(inputstr)
    except ValueError:
        try:
            return float(inputstr)
        except ValueError:
            return inputstr


def reverse_cast_to_number_or_bool(input):
    if input is True:
        return "true"  # FIXME: (jany) dubious, glyphs handbook says should be 1
    if input is False:
        return "false"  # FIXME: (jany) dubious, glyphs handbook says should be 0
    return str(input)


def best_repr(float_or_int):
    if isinstance(float_or_int, float) and float_or_int.is_integer():
        return int(float_or_int)
    return float_or_int


def best_repr_list(list_of_float_or_int):
    new_list = []
    for float_or_int in list_of_float_or_int:
        if isinstance(float_or_int, float) and float_or_int.is_integer():
            new_list.append(int(float_or_int))
        else:
            new_list.append(float_or_int)
    return new_list


def bin_to_int_list(value: int) -> List[int]:
    string = num2binary(value)
    string = string.replace(" ", "")  # num2binary add a space every 8 digits
    return [i for i, v in enumerate(reversed(string)) if v == "1"]


def int_list_to_bin(value):
    result = 0
    for i in value:
        result += 1 << i
    return result


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def tostr(s, encoding="ascii", errors="strict"):
    if not isinstance(s, str):
        return s.decode(encoding, errors)
    else:
        return s


def pairs(list):
    "s -> (s0,s1), (s2,s3), (s4, s5), ..."
    return [list[i: i + 2] for i in range(0, len(list), 2)]


def freezedict(dct):
    return frozenset(dct.items())


class LoggerMixin:
    _logger: Optional[logging.Logger] = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = logging.getLogger(
                ".".join([self.__class__.__module__, self.__class__.__name__])
            )
        return self._logger


def designspace_min_max(axis):
    """Return the minimum/maximum of an axis in designspace coordinates"""
    if not axis.map:
        return axis.minimum, axis.maximum
    designspace_scale = [design_location for _, design_location in axis.map]
    return min(designspace_scale), max(designspace_scale)


class PeekableIterator:
    """Helper class to iterate and peek over a list."""

    def __init__(self, list):
        self.index = 0
        self.list = list

    def has_next(self, n=0):
        return (self.index + n) < len(self.list)

    def __iter__(self):
        return self

    def __next__(self):
        res = self.list[self.index]
        self.index += 1
        return res

    next = __next__

    def peek(self, n=0):
        return self.list[self.index + n]


stringClasses: Any = str
listClasses: Tuple = (list, tuple)
try:
    from Foundation import NSString, NSArray

    stringClasses = (str, NSString)
    listClasses = (list, tuple, NSArray)
except ImportError:
    pass


def isString(value):
    return isinstance(value, stringClasses)


def isList(value):
    return isinstance(value, listClasses)


# sentinel object to indicate a deprecated argument
_DeprecatedArgument = object()
