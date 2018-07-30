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


# FIXME: (jany) Shouldn't this be the class GSGlyphInfo?
Glyph = namedtuple("Glyph", "name,production_name,unicode,category,subCategory")


def get_glyph(name, data=glyphdata_generated):
    """Return a named tuple (Glyph) containing information derived from a glyph
    name akin to GSGlyphInfo.

    The information is derived from an included copy of GlyphsData.xml,
    going purely by the glyph name.
    """

    # First, get the base name of the glyph. .notdef and .null are exceptions.
    # Periods denote glyph variants as per the AGLFN convetion, which should
    # be in the same category as their base glyph.
    if name in (".notdef", ".null"):
        base_name = name
    else:
        base_name = name.split(".", maxsplit=1)[0]

    # Next, look up the glyph name in Glyph's name database to get a Unicode
    # pseudoname, or "production name" as found in a font's post table 
    # (e.g. "A-cy" -> "uni0410") so that e.g. PDF readers can map from names
    # to Unicode values. FontTool's agl module can turn this into the actual
    # character.
    production_name = data.PRODUCTION_NAMES.get(base_name)

    # Some Glyphs files use production names instead of Glyph's "nice names".
    # We catch this here, so that we can return the same properties as if
    # the Glyphs file had been following the Glyphs naming conventions.
    # https://github.com/googlei18n/glyphsLib/issues/232
    if production_name is None:
        rev_prodname = data.PRODUCTION_NAMES_REVERSED.get(base_name)
        if rev_prodname is not None:
            production_name = base_name
            base_name = rev_prodname

    # Finally, if we couldn't find a known production name one way or another,
    # conclude that the glyph name doesn't carry any Uncode semantics. Use the
    # bare name in that case.
    if production_name is None:
        production_name = name

    # Next, derive the actual character from the production name, e.g.
    # "uni0414" -> "Д". Two caveats:
    # 1. For some glyphs, Glyphs does not have a category even when one could
    #    be derived.
    # 2. For some others, Glyphs has a different idea than the agl module.
    if base_name in data.MISSING_UNICODE_STRINGS:  # 1.
        character = None
    else:
        character = data.IRREGULAR_UNICODE_STRINGS.get(base_name)  # 2.
        if character is None:
            character = agl.toUnicode(production_name) or None

    # Lastly, generate the category in the sense of Glyph's 
    # GSGlyphInfo.category and .subCategory.
    category, sub_category = _get_category(base_name, character, data)

    return Glyph(base_name, production_name, character, category, sub_category)


def _get_unicode_category(character):
    """Return the Unicode general category for a character.

    We use data for a fixed Unicode version (3.2) so that our generated
    data files are independent of Python runtime that runs the rules. By
    switching to current Unicode data, we could save some entries in our
    exception tables, but the gains are not very large; only about one
    thousand entries.
    """

    if not character:
        return None

    if NARROW_PYTHON_BUILD:
        utf32_str = character.encode("utf-32-be")
        nchars = len(utf32_str) // 4
        first_char = unichr(struct.unpack('>%dL' % nchars, utf32_str)[0])
    else:
        first_char = character[0]

    return unicodedata.ucd_3_2_0.category(first_char)


def _get_category(glyph_name, character, data=glyphdata_generated):
    """Return category and subCategory of a glyph name as defined by
    GlyphsData.xml."""

    # Glyphs assigns some glyph names different categories than Unicode.
    categories = data.IRREGULAR_CATEGORIES.get(glyph_name)
    if categories is not None:
        return categories

    # More exceptions.
    if glyph_name.endswith("-ko"):
        return ("Letter", "Syllable")
    if glyph_name.endswith("-ethiopic") or glyph_name.endswith("-tifi"):
        return ("Letter", None)
    if glyph_name.startswith("box"):
        return ("Symbol", "Geometry")
    if glyph_name.startswith("uniF9"):
        return ("Letter", "Compatibility")
    
    # Finally, look up the actual categories.
    unicode_category = _get_unicode_category(character)
    categories = data.DEFAULT_CATEGORIES.get(unicode_category, (None, None))
    
    # Special case: names like "one_two" are (_, Ligatures) but e.g.
    # "brevecomb_acutecomb" is a (Mark, Nonspacing).
    if "_" in glyph_name and categories[0] != "Mark":
        return (categories[0], "Ligature")
    
    return categories
