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
    unistr = _get_unicode(name, data)
    category, subCategory = _get_category(name, unistr, data)
    return Glyph(name, prodname, unistr, category, subCategory)

if NARROW_PYTHON_BUILD:
    def unilen(text):
        if isinstance(text, bytes):
            text = text.decode("utf_8")
        text_utf32 = text.encode("utf-32-be")
        return len(text_utf32)//4
else:
    unilen = len

def _get_unicode(name, data=glyphdata_generated):
    prodname = data.PRODUCTION_NAMES.get(name, name)
    if name in data.MISSING_UNICODE_STRINGS:
        return None
    unistr = data.IRREGULAR_UNICODE_STRINGS.get(name)
    if unistr is not None or "." in name:
        return unistr
    unistr = agl.toUnicode(prodname)
    if unilen(unistr) == 1:
        return unistr
    return None

def _get_category(name, unistr, data=glyphdata_generated):
    cat = data.IRREGULAR_CATEGORIES.get(name)
    if cat is not None:
        return cat

    basename = name.split(".", 1)[0]  # "A.alt27" --> "A"
    if not basename:  # handle ".notdef", ".null"
        basename = name
    cat = data.IRREGULAR_CATEGORIES.get(basename)
    if cat is not None:
        return cat

    if basename.endswith("-ko"):
        return ("Letter", "Syllable")
    if basename.endswith("-ethiopic") or basename.endswith("-tifi"):
        return ("Letter", None)
    if basename.startswith("box"):
        return ("Symbol", "Geometry")
    if basename.startswith("uniF9"):
        return ("Letter", "Compatibility")

    if unistr is None:
        if name != basename:
            unistr = _get_unicode(basename, data)
        if unistr is None and  "_" in basename:
            # the first component will define the category
            first_component_name = basename.split('_', 1)[0]
            unistr = _get_unicode(first_component_name, data)
    ucat = None
    if unistr is not None:
        ucat = unicodedata.ucd_3_2_0.category(unistr)
    cat = data.DEFAULT_CATEGORIES.get(ucat, (None, None))
    if "_" in basename:
        return (cat[0], "Ligature")
    return cat
