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

"""This module holds internally-used functions to determine various properties
of a glyph.

These properties assist in applying automatisms to glyphs when round-
tripping.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import os
import re
import unicodedata
import xml.etree.ElementTree

import fontTools.agl

import glyphsLib

__all__ = ["get_glyph", "GlyphData"]

# This is an internally-used named tuple and not meant to be a GSGlyphData replacement.
Glyph = collections.namedtuple(
    "Glyph",
    "name, production_name, unicode, category, subCategory, script, description",
)

# Global variable holding the actual GlyphData data, assigned on first use.
GLYPHDATA = None


class GlyphData:
    """Map (alternative) names and production names to GlyphData data.

    This class holds the GlyphData data as provided on
    https://github.com/schriftgestalt/GlyphsInfo and provides lookup by
    name, alternative name and production name through normal
    dictionaries.
    """

    __slots__ = ["names", "alternative_names", "production_names"]

    def __init__(self, name_mapping, alt_name_mapping, production_name_mapping):
        self.names = name_mapping
        self.alternative_names = alt_name_mapping
        self.production_names = production_name_mapping

    @classmethod
    def from_files(cls, *glyphdata_files):
        """Return GlyphData holding data from a list of XML file paths."""
        name_mapping = {}
        alt_name_mapping = {}
        production_name_mapping = {}

        for glyphdata_file in glyphdata_files:
            glyph_data = xml.etree.ElementTree.parse(glyphdata_file).getroot()
            for glyph in glyph_data:
                glyph_name = glyph.attrib["name"]
                glyph_name_alternatives = glyph.attrib.get("altNames")
                glyph_name_production = glyph.attrib.get("production")

                name_mapping[glyph_name] = glyph.attrib
                if glyph_name_alternatives:
                    alternatives = glyph_name_alternatives.replace(" ", "").split(",")
                    for glyph_name_alternative in alternatives:
                        alt_name_mapping[glyph_name_alternative] = glyph.attrib
                if glyph_name_production:
                    production_name_mapping[glyph_name_production] = glyph.attrib

        return cls(name_mapping, alt_name_mapping, production_name_mapping)


def get_glyph(glyph_name, data=None):
    """Return a named tuple (Glyph) containing information derived from a glyph
    name akin to GSGlyphInfo.

    The information is derived from an included copy of GlyphData.xml
    and GlyphData_Ideographs.xml, going purely by the glyph name.
    """

    # Read data on first use.
    if data is None:
        global GLYPHDATA
        if GLYPHDATA is None:
            GLYPHDATA = GlyphData.from_files(
                os.path.join(
                    os.path.dirname(glyphsLib.__file__), "data", "GlyphData.xml"
                ),
                os.path.join(
                    os.path.dirname(glyphsLib.__file__),
                    "data",
                    "GlyphData_Ideographs.xml",
                ),
            )
        data = GLYPHDATA

    # Look up data by full glyph name first. Also try the full alternative name for
    # legacy projects and production name (Issue #232).
    attributes = (
        data.names.get(glyph_name)
        or data.alternative_names.get(glyph_name)
        or data.production_names.get(glyph_name)
        or {}
    )

    production_name = attributes.get("production") or _construct_production_name(
        glyph_name, data=data
    )
    unicode_value = attributes.get("unicode")
    category = attributes.get("category")
    sub_category = attributes.get("subCategory")
    script = attributes.get("script")
    description = attributes.get("description")

    # Glyph variants (e.g. "fi.alt") don't have their own entry, so we strip e.g. the
    # ".alt" and try a second lookup with just the base name. A variant is hopefully in
    # the same category as its base glyph.
    if category is None:
        base_name = glyph_name.split(".", 1)[0]
        base_attribute = data.names.get(base_name) or {}
        category = base_attribute.get("category")
        sub_category = base_attribute.get("subCategory")

    # Still nothing? Maybe someone we're looking at something like "uni1234.alt", try
    # one more time using fontTools' AGL module to convert the base name to something
    # meaningful.
    if category is None:
        character = fontTools.agl.toUnicode(base_name)
        if character:
            category, sub_category = _construct_category(
                glyph_name, unicodedata.category(character[0])
            )

    return Glyph(
        glyph_name,
        production_name,
        unicode_value,
        category,
        sub_category,
        script,
        description,
    )


def _agl_compliant_name(glyph_name):
    """Return an AGL-compliant name string or None if we can't make one."""
    MAX_GLYPH_NAME_LENGTH = 63
    clean_name = re.sub("[^0-9a-zA-Z_.]", "", glyph_name)
    if len(clean_name) > MAX_GLYPH_NAME_LENGTH:
        return None
    return clean_name


def _is_unicode_u_value(name):
    """Return whether we are looking at a uXXXX value."""
    return name.startswith("u") and all(
        part_char in "0123456789ABCDEF" for part_char in name[1:]
    )


def _construct_category(glyph_name, unicode_category):
    """Return a translation from Unicode category letters to Glyphs
    categories."""
    DEFAULT_CATEGORIES = {
        None: ("Letter", None),
        "Cc": ("Separator", None),
        "Cf": ("Separator", "Format"),
        "Cn": ("Symbol", None),
        "Co": ("Letter", "Compatibility"),
        "Ll": ("Letter", "Lowercase"),
        "Lm": ("Letter", "Modifier"),
        "Lo": ("Letter", None),
        "Lt": ("Letter", "Uppercase"),
        "Lu": ("Letter", "Uppercase"),
        "Mc": ("Mark", "Spacing Combining"),
        "Me": ("Mark", "Enclosing"),
        "Mn": ("Mark", "Nonspacing"),
        "Nd": ("Number", "Decimal Digit"),
        "Nl": ("Number", None),
        "No": ("Number", "Decimal Digit"),
        "Pc": ("Punctuation", None),
        "Pd": ("Punctuation", "Dash"),
        "Pe": ("Punctuation", "Parenthesis"),
        "Pf": ("Punctuation", "Quote"),
        "Pi": ("Punctuation", "Quote"),
        "Po": ("Punctuation", None),
        "Ps": ("Punctuation", "Parenthesis"),
        "Sc": ("Symbol", "Currency"),
        "Sk": ("Mark", "Spacing"),
        "Sm": ("Symbol", "Math"),
        "So": ("Symbol", None),
        "Zl": ("Separator", None),
        "Zp": ("Separator", None),
        "Zs": ("Separator", "Space"),
    }

    glyphs_category = DEFAULT_CATEGORIES.get(unicode_category, ("Letter", None))

    # Exception: Something like "one_two" should be a (_, Ligature),
    # "acutecomb_brevecomb" should however stay (Mark, Nonspacing).
    if "_" in glyph_name and glyphs_category[0] != "Mark":
        return (glyphs_category[0], "Ligature")

    return glyphs_category


def _construct_production_name(glyph_name, data=None):
    """Return the production name for a glyph name from the GlyphData.xml
    database according to the AGL specification.

    This should be run only if there is no official entry with a production
    name in it.

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

    # At this point, we have already checked the data for the full glyph name, so
    # directly go to the base name here (e.g. when looking at "fi.alt").
    base_name, dot, suffix = glyph_name.partition(".")
    glyphinfo = (
        data.names.get(base_name)
        or data.alternative_names.get(base_name)
        or data.production_names.get(base_name)
        or {}
    )
    if glyphinfo and glyphinfo.get("production"):
        # Found the base glyph.
        return glyphinfo["production"] + dot + suffix

    if glyph_name in fontTools.agl.AGL2UV or base_name in fontTools.agl.AGL2UV:
        # Glyph name is actually an AGLFN name.
        return glyph_name

    if "_" not in base_name:
        # Nothing found so far and the glyph name isn't a ligature ("_"
        # somewhere in it). The name does not carry any discernable Unicode
        # semantics, so just return something sanitized.
        return _agl_compliant_name(glyph_name)

    # So we have a ligature that is not mapped in the data. Split it up and
    # look up the individual parts.
    base_name_parts = base_name.split("_")

    # If all parts are in the AGLFN list, the glyph name is our production
    # name already.
    if all(part in fontTools.agl.AGL2UV for part in base_name_parts):
        return _agl_compliant_name(glyph_name)

    # Turn all parts of the ligature into production names.
    _character_outside_BMP = False
    production_names = []
    for part in base_name_parts:
        if part in fontTools.agl.AGL2UV:
            # A name present in the AGLFN is a production name already.
            production_names.append(part)
        else:
            part_entry = data.names.get(part) or {}
            part_production_name = part_entry.get("production")
            if part_production_name:
                production_names.append(part_production_name)

                # Take note if there are any characters outside the Unicode
                # BMP, e.g. "u10FFF" or "u10FFFF". Do not catch e.g. "u013B"
                # though.
                if len(part_production_name) > 5 and _is_unicode_u_value(
                    part_production_name
                ):
                    _character_outside_BMP = True
            else:
                # We hit a part that does not seem to be a valid glyph name known to us,
                # so the entire glyph name can't carry Unicode meaning. Return it
                # sanitized.
                return _agl_compliant_name(glyph_name)

    # Some names Glyphs uses resolve to other names that are not uniXXXX names and may
    # contain dots (e.g. idotaccent -> i.loclTRK). If there is any name with a "." in
    # it before the last element, punt. We'd have to introduce a "." into the ligature
    # midway, which is invalid according to the AGL. Example: "a_i.loclTRK" is valid,
    # but "a_i.loclTRK_a" isn't.
    if any("." in part for part in production_names[:-1]):
        return _agl_compliant_name(glyph_name)

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
            elif len(part) == 5 and _is_unicode_u_value(part):
                uni_names.append(part[1:])
            elif part in fontTools.agl.AGL2UV:
                uni_names.append("{:04X}".format(fontTools.agl.AGL2UV[part]))
            else:
                return None

        final_production_name = "uni" + "".join(uni_names) + dot + suffix
    else:
        final_production_name = "_".join(production_names) + dot + suffix

    return _agl_compliant_name(final_production_name)
