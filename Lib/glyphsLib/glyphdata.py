# -*- coding=utf-8 -*-
#
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

from __future__ import (print_function, division, absolute_import,
                        unicode_literals)
from collections import namedtuple
from fontTools import agl
from fontTools.misc.py23 import unichr
from glyphsLib import glyphdata_generated
import sys
import struct
import unicodedata

NARROW_PYTHON_BUILD = sys.maxunicode < 0x10FFFF


Glyph = namedtuple("Glyph", "name,production_name,unicode,category,subCategory")


def get_glyph(name, data=glyphdata_generated):
    prodname = data.PRODUCTION_NAMES.get(name, name)
    unistr = data.IRREGULAR_UNICODE_STRINGS.get(name)
    if unistr is None:
        unistr = agl.toUnicode(prodname)
    if unistr != "" and name not in data.MISSING_UNICODE_STRINGS:
        unistr_result = unistr
    else:
        unistr_result = None
    category, subCategory = _get_category(name, unistr, data)
    return Glyph(name, prodname, unistr_result, category, subCategory)


def _get_unicode_category(unistr):
    # We use data for a fixed Unicode version (3.2) so that our generated
    # data files are independent of Python runtime that runs the rules.
    # By switching to current Unicode data, we could save some entries
    # in our exception tables, but the gains are not very large; only
    # about one thousand entries.
    if not unistr:
        return None
    if NARROW_PYTHON_BUILD:
        utf32_str = unistr.encode("utf-32-be")
        nchars = len(utf32_str)//4
        first_char = unichr(struct.unpack('>%dL' % nchars, utf32_str)[0])
    else:
        first_char = unistr[0]
    return unicodedata.ucd_3_2_0.category(first_char)


def _get_category(name, unistr, data=glyphdata_generated):
    cat = data.IRREGULAR_CATEGORIES.get(name)
    if cat is not None:
        return cat
    if name.endswith("-ko"):
        return ("Letter", "Syllable")
    if name.endswith("-ethiopic") or name.endswith("-tifi"):
        return ("Letter", None)
    if name.startswith("box"):
        return ("Symbol", "Geometry")
    if name.startswith("uniF9"):
        return ("Letter", "Compatibility")
    ucat = _get_unicode_category(unistr)
    return data.DEFAULT_CATEGORIES[ucat]
