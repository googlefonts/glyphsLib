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


import collections
import re
from fontTools import unicodedata
import xml.etree.ElementTree

import fontTools.agl


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

    __slots__ = ["names", "alternative_names", "production_names", "unicodes"]

    def __init__(
        self, name_mapping, alt_name_mapping, production_name_mapping, unicodes_mapping
    ):
        self.names = name_mapping
        self.alternative_names = alt_name_mapping
        self.production_names = production_name_mapping
        self.unicodes = unicodes_mapping

    @classmethod
    def from_files(cls, *glyphdata_files):
        """Return GlyphData holding data from a list of XML file paths."""
        name_mapping = {}
        alt_name_mapping = {}
        production_name_mapping = {}
        unicodes_mapping = {}

        for glyphdata_file in glyphdata_files:
            glyph_data = xml.etree.ElementTree.parse(glyphdata_file).getroot()
            for glyph in glyph_data:
                glyph_name = glyph.attrib["name"]
                glyph_name_alternatives = glyph.attrib.get("altNames")
                glyph_name_production = glyph.attrib.get("production")
                glyph_unicode = glyph.attrib.get("unicode")

                name_mapping[glyph_name] = glyph.attrib
                if glyph_name_alternatives:
                    alternatives = glyph_name_alternatives.replace(" ", "").split(",")
                    for glyph_name_alternative in alternatives:
                        alt_name_mapping[glyph_name_alternative] = glyph.attrib
                if glyph_name_production:
                    production_name_mapping[glyph_name_production] = glyph.attrib
                if glyph_unicode:
                    unicodes_mapping[glyph_unicode] = glyph.attrib

        return cls(
            name_mapping, alt_name_mapping, production_name_mapping, unicodes_mapping
        )


def get_glyph(glyph_name, data=None, unicodes=None):
    """Return a named tuple (Glyph) containing information derived from a glyph
    name akin to GSGlyphInfo.

    The information is derived from an included copy of GlyphData.xml
    and GlyphData_Ideographs.xml, going by the glyph name or unicode fallback.
    """

    # Read data on first use.
    global GLYPHDATA
    if GLYPHDATA is None:
        try:
            from importlib.resources import files
        except ImportError:
            # Python <= 3.8 backport
            from importlib_resources import files

        data_dir = files("glyphsLib.data")
        with (data_dir / "GlyphData.xml").open("rb") as f1:
            with (data_dir / "GlyphData_Ideographs.xml").open("rb") as f2:
                GLYPHDATA = GlyphData.from_files(f1, f2)
                assert len(GLYPHDATA.names) > 30000

    if data is None:
        data = GLYPHDATA

    # Look up data by full glyph name first.
    attributes = _lookup_attributes(glyph_name, data)

    # Look up by unicode
    if attributes == {} and unicodes is not None:
        for unicode in unicodes:
            attributes = _lookup_attributes_by_unicode(unicode, data)
            if attributes:
                break

    production_name = attributes.get("production")
    if production_name is None:
        production_name = _construct_production_name(glyph_name, data=data)

    unicode_value = attributes.get("unicode")

    category = attributes.get("category")
    sub_category = attributes.get("subCategory")
    if category is None:
        category, sub_category = _construct_category(glyph_name, data)

    # TODO: Determine script in ligatures.
    script = attributes.get("script")
    description = attributes.get("description")

    return Glyph(
        glyph_name,
        production_name,
        unicode_value,
        category,
        sub_category,
        script,
        description,
    )


def _lookup_attributes(glyph_name, data):
    """Look up glyph attributes in data by glyph name, alternative name or
    production name in order or return empty dictionary.

    Look up by alternative and production names for legacy projects and
    because of issue #232.
    """
    attributes = (
        data.names.get(glyph_name)
        or data.alternative_names.get(glyph_name)
        or data.production_names.get(glyph_name)
        or {}
    )
    # If we are using custom GlyphData, fallback to default GlyphData
    if not attributes and data is not GLYPHDATA:
        attributes = _lookup_attributes(glyph_name, GLYPHDATA)
    return attributes


def _lookup_attributes_by_unicode(unicode, data):
    """Look up glyph attributes in data by unicode
    or return empty dictionary.
    """
    attributes = data.unicodes.get(unicode) or {}
    return attributes


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


def _construct_category(glyph_name, data):
    """Derive (sub)category of a glyph name."""
    # Glyphs creates glyphs that start with an underscore as "non-exportable" glyphs or
    # construction helpers without a category.
    if glyph_name.startswith("_"):
        return None, None

    # Glyph variants (e.g. "fi.alt") don't have their own entry, so we strip e.g. the
    # ".alt" and try a second lookup with just the base name. A variant is hopefully in
    # the same category as its base glyph.
    base_name = _split_glyph_name(glyph_name, data)[0]
    base_attribute = _lookup_attributes(base_name, data) or {}
    if base_attribute:
        category = base_attribute.get("category")
        sub_category = base_attribute.get("subCategory")
        return category, sub_category

    # Detect ligatures.
    if "_" in base_name:
        base_names = _split_ligature_glyph_name(base_name, data)
        base_names_attributes = [_lookup_attributes(name, data) for name in base_names]
        first_attribute = base_names_attributes[0]

        # If the first part is a Mark, Glyphs 2.6 declares the entire glyph a Mark
        if first_attribute.get("category") == "Mark":
            category = first_attribute.get("category")
            sub_category = first_attribute.get("subCategory")
            return category, sub_category

        # If the first part is a Letter...
        if first_attribute.get("category") == "Letter":
            # ... and the rest are only marks or separators or don't exist, the
            # sub_category is that of the first part ...
            if all(
                a.get("category") in (None, "Mark", "Separator")
                for a in base_names_attributes[1:]
            ):
                category = first_attribute.get("category")
                sub_category = first_attribute.get("subCategory")
                return category, sub_category
            # ... otherwise, a ligature.
            category = first_attribute.get("category")
            sub_category = "Ligature"
            return category, sub_category

        # TODO: Cover more cases. E.g. "one_one" -> ("Number", "Ligature") but
        # "one_onee" -> ("Number", "Composition").

    # Still nothing? Maybe we're looking at something like "uni1234.alt", try
    # using fontTools' AGL module to convert the base name to something meaningful.
    # Corner case: when looking at ligatures, names that don't exist in the AGLFN
    # are skipped, so len("acutecomb_o") == 2 but len("dotaccentcomb_o") == 1.
    character = fontTools.agl.toUnicode(base_name)
    if character:
        category, sub_category = _translate_category(
            glyph_name, unicodedata.category(character[0])
        )
        return category, sub_category

    return None, None


def _translate_category(glyph_name, unicode_category):
    """Return a translation from Unicode category letters to Glyphs
    categories."""
    DEFAULT_CATEGORIES = {
        None: ("Letter", None),
        "Cc": ("Separator", None),
        "Cf": ("Separator", "Format"),
        "Cn": ("Symbol", None),
        "Co": ("Letter", "Compatibility"),
        "Ll": ("Letter", None),
        "Lm": ("Letter", "Modifier"),
        "Lo": ("Letter", None),
        "Lt": ("Letter", None),
        "Lu": ("Letter", None),
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
        return glyphs_category[0], "Ligature"

    return glyphs_category


def _split_ligature_glyph_name(name, data):
    # Split name to ligature parts
    parts = name.split("_")

    # If the last part has a script suffix, strip it and re-split the name.
    if "-" in parts[-1]:
        base, script = name.rsplit("-", 1)
        parts = base.split("_")

        # If there is more than one part, try adding the script suffix to each
        # part, if this results in a known glyph name, use it as the part name.
        if len(parts) > 1:
            for i, part in enumerate(parts):
                new = f"{part}-{script}"
                # If the part already has a script suffix, keep it unchanged.
                if "-" in part:
                    continue
                # If the non suffixed name exists and the suffixed name does
                # not exist, keep the part name unchanged.
                if _lookup_attributes(part, data) and not _lookup_attributes(new, data):
                    continue
                parts[i] = new
    else:
        parts = name.split("_")
    return parts


def _split_glyph_name(name, data):
    # Split glyph name into base and suffix
    base, dot, suffix = name.partition(".")

    # If there are more than one suffix (e.g. ".below.ro"), try adding each
    # suffix to the base name, if it results in a known glyph name, use that as
    # base name.
    if dot and dot in suffix:
        suffixes = suffix.split(dot)
        new = base
        while suffixes:
            new += dot + suffixes.pop(0)
            if _lookup_attributes(new, data):
                return new, dot, dot.join(suffixes)
    return base, dot, suffix


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
    base_name, dot, suffix = _split_glyph_name(glyph_name, data)
    glyphinfo = _lookup_attributes(base_name, data)
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
    base_name_parts = _split_ligature_glyph_name(base_name, data)

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
            part_entry = _lookup_attributes(part, data) or {}
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
