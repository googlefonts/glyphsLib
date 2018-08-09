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


def get_glyph(glyph_name, data=glyphdata_generated):
    """Return a named tuple (Glyph) containing information derived from a glyph
    name akin to GSGlyphInfo.

    The information is derived from an included copy of GlyphsData.xml,
    going purely by the glyph name.
    """

    # First, get the base name of the glyph. .notdef and .null are exceptions.
    # Periods denote glyph variants as per the AGLFN convention, which should
    # be in the same category as their base glyph.
    if glyph_name in (".notdef", ".null"):
        base_name = glyph_name
    else:
        base_name = glyph_name.split(".", 1)[0]

    # Next, look up the glyph name in Glyph's name database to get a Unicode
    # pseudoname, or "production name" as found in a font's post table
    # (e.g. "A-cy" -> "uni0410") so that e.g. PDF readers can map from names
    # to Unicode values. FontTool's agl module can turn this into the actual
    # character.
    production_name = _lookup_production_name(glyph_name)

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
    # conclude that the glyph name doesn't carry any Unicode semantics. Use the
    # bare name in that case.
    if production_name is None:
        production_name = glyph_name

    # Next, derive the actual characters from the production name, e.g.
    # "uni0414" -> "Д". Two caveats:
    # 1. For some glyphs, Glyphs does not have a mapped character even when one
    #    could be derived.
    # 2. For some others, Glyphs has a different idea than the agl module.
    unicode_characters = None
    if base_name not in data.MISSING_UNICODE_STRINGS:  # 1.
        unicode_characters = data.IRREGULAR_UNICODE_STRINGS.get(base_name)  # 2.
        if unicode_characters is None:
            unicode_characters = agl.toUnicode(production_name) or None

    # Lastly, generate the category in the sense of Glyph's
    # GSGlyphInfo.category and .subCategory.
    category, sub_category = _get_category(base_name, unicode_characters, data)

    return Glyph(
        glyph_name, production_name, unicode_characters, category, sub_category
    )


def _lookup_production_name(glyph_name, data=glyphdata_generated):
    """Return the production name for a glyph name from the GlyphsData.xml
    database according to the AGL specification.

    Handles single glyphs (e.g. "brevecomb") and ligatures (e.g.
    "brevecomb_acutecomb"). Returns None when a valid and semantically
    meaningful production name can't be constructed or when the AGL
    specification would be violated, get_glyph() will use the bare glyph
    name then.

    Note:
    - Glyph name is the full name, e.g. "brevecomb_acutecomb.case".
    - Base name is the base part, e.g. "brevecomb_acutecomb"
    - Suffix is e.g. "case".
    """

    # The OpenType feature file specification says it's 63, the AGL says it's 31. We
    # settle on 63. makeotf uses 63 as explained by Read Roberts from Adobe in
    # https://github.com/fontforge/fontforge/pull/2500#issuecomment-143263393
    # (Sep 25, 2015).
    MAX_GLYPH_NAME_LENGTH = 63

    def is_unicode_u_value(name):
        return name.startswith("u") and all(
            part_char in "0123456789ABCDEF" for part_char in name[1:]
        )

    base_name, dot, suffix = glyph_name.partition(".")

    # First, look up the full glyph name and base name in the AGLFN and in
    # PRODUCTION_NAMES.
    if (
        glyph_name in agl.AGL2UV
        or base_name in agl.AGL2UV
        or glyph_name in (".notdef", ".null")
    ):
        return glyph_name

    if glyph_name in data.PRODUCTION_NAMES:  # e.g. ain_alefMaksura-ar.fina -> uniFD13
        return data.PRODUCTION_NAMES[glyph_name]
    if base_name in data.PRODUCTION_NAMES:
        final_production_name = data.PRODUCTION_NAMES[base_name] + dot + suffix
        if len(final_production_name) > MAX_GLYPH_NAME_LENGTH:
            return None
        return final_production_name

    # If we aren't looking at a ligature and the name still hasn't been found,
    # the glyph probably has no Unicode semantics, so return None.
    if "_" not in base_name:
        return None

    # So we have a ligature that is not mapped in PRODUCTION_NAMES. Split it up and
    # look up the individual parts.
    base_name_parts = base_name.split("_")

    # If all parts are in the AGLFN list, the glyph name is our production
    # name already.
    if all(part in agl.AGL2UV for part in base_name_parts):
        if len(glyph_name) > MAX_GLYPH_NAME_LENGTH:
            return None
        return glyph_name

    _character_outside_BMP = False
    production_names = []
    for part in base_name_parts:
        if part in agl.AGL2UV:
            production_names.append(part)
        else:
            part_production_name = data.PRODUCTION_NAMES.get(part)
            if part_production_name:
                production_names.append(part_production_name)

                # Note if there are any characters outside the Unicode BMP, e.g.
                # "u10FFF" or "u10FFFF". Do not catch e.g. "u013B" though.
                if len(part_production_name) > 5 and is_unicode_u_value(
                    part_production_name
                ):
                    _character_outside_BMP = True

            else:
                return None

    # Some names Glyphs uses resolve to other names that are not uniXXXX names and may
    # contain dots (e.g. idotaccent -> i.loclTRK). If there is any name with a "." in
    # it before the last element, punt. We'd have to introduce a "." into the ligature
    # midway, which is invalid according to the AGL. Example: "a_i.loclTRK" is valid,
    # but "a_i.loclTRK_a" isn't.
    if any("." in part for part in production_names[:-1]):
        return None

    # If any production name starts with a "uni" and there are none of the
    # "uXXXXX" format, try to turn all parts into "uni" names and concatenate
    # them.
    if not _character_outside_BMP and any(
        part.startswith("uni") for part in production_names
    ):
        uni_names = []

        for part in production_names:
            if part.startswith("uni"):
                uni_names.append(part[3:])
            elif len(part) == 5 and is_unicode_u_value(part):
                uni_names.append(part[1:])
            elif part in agl.AGL2UV:
                uni_names.append("{:04X}".format(agl.AGL2UV[part]))
            else:
                return None

        final_production_name = "uni" + "".join(uni_names) + dot + suffix
    else:
        final_production_name = "_".join(production_names) + dot + suffix

    if len(final_production_name) > MAX_GLYPH_NAME_LENGTH:
        return None

    return final_production_name


def _get_unicode_category(unicode_characters):
    """Return the Unicode general category for a character (or the first
    character of a string).

    We use data for a fixed Unicode version (3.2) so that our generated
    data files are independent of Python runtime that runs the rules. By
    switching to current Unicode data, we could save some entries in our
    exception tables, but the gains are not very large; only about one
    thousand entries.
    """

    if not unicode_characters:
        return None

    if NARROW_PYTHON_BUILD:
        utf32_str = unicode_characters.encode("utf-32-be")
        nchars = len(utf32_str) // 4
        first_char = unichr(struct.unpack('>%dL' % nchars, utf32_str)[0])
    else:
        first_char = unicode_characters[0]

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
