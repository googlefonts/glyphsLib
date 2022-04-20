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
import re, os
from fontTools import unicodedata

import xml.etree.ElementTree

import fontTools.agl


__all__ = ["get_glyph", "GlyphData", "GlyphInfo", "GSUppercase", "GSLowercase", "GSSmallcaps", "GSMinor"]

GSNoCase = None # 0
GSUppercase = "upper" # 1
GSLowercase = "lower" # 2
GSSmallcaps = "small" # 3
GSMinor = "minor" # 4

GSBIDI = 1
GSLTR = 0
GSRTL = 2
GSVertical = 4

class GlyphInfo:
    __slots__ = ["name", "production", "unicodes", "category", "subCategory", "case", "script", "description"]
    def __init__(self, name, production=None, unicodes=None, category=None, subCategory=None, case=None, script=None, description=None):
        self.name = name
        self.production = production
        self.unicodes = unicodes
        self.category = category
        self.subCategory = subCategory
        self.case = case
        self.script = script
        self.description = description
    def copy(self):
        copy = GlyphInfo(self.name, self.production, self.unicodes, self.category, self.subCategory, self.case, self.script, self.description)
        return copy
    def __repr__(self):
        string = "info:" + self.name
        if self.production:
            string += " pro:" + self.production
        if self.unicodes:
            string += " uni:" + self.unicodes
        if self.category:
            string += " cat:" + self.category
        if self.subCategory:
            string += " sub:" + self.subCategory
        if self.case:
            string += " case:" + self.case
        if self.script:
            string += " script:" + self.script
        if self.description:
            string += " desc:" + self.description
        return string
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


def get_glyph(glyph_name, data=None, unicodes=None, cutSuffix=None):
    """Return a named tuple (Glyph) containing information derived from a glyph
    name akin to GSGlyphInfo.

    The information is derived from an included copy of GlyphData.xml
    and GlyphData_Ideographs.xml, going by the glyph name or unicode fallback.
    """

    # Read data on first use.
    if data is None:
        global GLYPHDATA
        if GLYPHDATA is None:
            from importlib.resources import open_binary

            with open_binary("glyphsLib.data", "GlyphData.xml") as f1:
                with open_binary("glyphsLib.data", "GlyphData_Ideographs.xml") as f2:
                    GLYPHDATA = GlyphData.from_files(f1, f2)
        data = GLYPHDATA

    info = None
    # Look up data by full glyph name first.

    if cutSuffix is not None:
        info = _lookup_info(glyph_name + cutSuffix, data)
        if info is not None:
            cutSuffix = None # the info has the suffix, we should not add it again later
    if info is None:
        info = _lookup_info(glyph_name, data)

    # Look up by unicode
    if not info:
        if unicodes is None and len(glyph_name) == 1:
            unicodes = ["%.4X" % ord(glyph_name)]
        if unicodes is not None:
            for uni in unicodes:
                info = _lookup_info_by_unicode(uni, data)
                if info:
                    break
        else:
            info, cutSuffix = _construct_info(glyph_name, data, cutSuffix)
    
    # production_name = info.production
    # if info.production is None:
    #     production_name = _construct_production_name(glyph_name, data=data)
    return info, cutSuffix

def _lookup_info(glyph_name, data):
    """Look up glyphinfo in data by glyph name, alternative name or
    production name in order or return empty dictionary.

    Look up by alternative and production names for legacy projects and
    because of issue #232.
    """
    attributes = (
        data.names.get(glyph_name)
        or data.alternative_names.get(glyph_name)
        or data.production_names.get(glyph_name)
        or None
    )
    if not attributes:
        return None
    return GlyphInfo(attributes.get("name"), attributes.get("production"), attributes.get("unicode"), attributes.get("category"), attributes.get("subCategory"), attributes.get("case"), attributes.get("script"), attributes.get("description"))


def _lookup_info_by_unicode(uni, data):
    """Look up glyphinfo in data by unicode
    or return empty dictionary.
    """
    attributes = data.unicodes.get(uni)
    if not attributes:
        char = chr(int(uni, 16))
        if len(uni) > 4:
            glyph_name = f"u{uni}"
        else:
            glyph_name = f"uni{uni}"
        category, sub_category, case = _translate_category(glyph_name, unicodedata.category(char))
        script = unicodedata.script(char)
        
        return GlyphInfo(glyph_name, category=category, subCategory=sub_category, case=case, script=script)
        return None
    return GlyphInfo(attributes.get("name"), attributes.get("production"), attributes.get("unicode"), attributes.get("category"), attributes.get("subCategory"), attributes.get("case"), attributes.get("script"), attributes.get("description"))


def _agl_compliant_name(glyph_name):
    """Return an AGL-compliant name string or None if we can't make one."""
    MAX_GLYPH_NAME_LENGTH = 63
    clean_name = re.sub("[^0-9a-zA-Z_.]", "", glyph_name)
    if len(clean_name) > MAX_GLYPH_NAME_LENGTH:
        return None
    return clean_name

def _is_unicode_uni_value(name):
    """Return whether we are looking at a uniXXXX value."""
    return name.startswith("uni") and len(name) > 6 and ((len(name) - 3) % 4) == 0 and all(
        part_char in "0123456789ABCDEF" for part_char in name[3:]
    )


def _is_unicode_u_value(name):
    """Return whether we are looking at a uXXXXX value."""
    return name.startswith("u") and len(name) > 6 and ((len(name) - 1) % 5) == 0 and all(
        part_char in "0123456789ABCDEF" for part_char in name[1:]
    )


def _construct_info(glyph_name, data, cutSuffix=None):
    """Derive (sub)category of a glyph name."""
    # Glyphs creates glyphs that start with an underscore as "non-exportable" glyphs or
    # construction helpers without a category.
    if glyph_name.startswith("_"):
        info = GlyphInfo(glyph_name)
        if glyph_name.startswith("_corner.") or glyph_name.startswith("_segment.") or glyph_name.startswith("_brush.") or glyph_name.startswith("_cap.abc"):
            info.category = "Corner"
        if "-" in glyph_name:
            _, langSuffix = glyph_name.rsplit("-", 1)
            info.script = langSuffix # TODO: add proper mapping from lang tags to script
        return info, cutSuffix

    # Glyph variants (e.g. "fi.alt") don't have their own entry, so we strip e.g. the
    # ".alt" and try a second lookup with just the base name. A variant is hopefully in
    # the same category as its base glyph.
    suffix = ""
    base_info = None
    base_name = glyph_name
    base_name, lastSuffix = os.path.splitext(base_name)
    while len(lastSuffix) > 0:
        suffix += lastSuffix
        base_info, suffix = get_glyph(base_name, data, cutSuffix=suffix)
        if base_info is not None:
            break
        base_name, lastSuffix = os.path.splitext(base_name)

    if base_info is None:
        knownSuffixes = ["superior", "inferior"]
        for knownSuffix in knownSuffixes:
            if base_name.endswith(knownSuffix):
                base_name = base_name[:-len(knownSuffix)]
                base_info, _ = get_glyph(base_name)
                if base_info:
                    base_info = base_info.copy()
                    base_info.case = GSMinor;
                    if base_info.production:
                        base_info.production += knownSuffix
                    base_info.name += knownSuffix
                    base_info.unicodes = None
                    return base_info, cutSuffix

    if base_info:
        if len(suffix) > 0:
            base_info = base_info.copy()
            base_info.name += suffix
            production = base_info.production
            if production is not None:
                production += suffix
                base_info.production = production
            base_info.unicodes = None
            
            if suffix == ".case":
                base_info.case = GSUppercase
            elif suffix in (".sc", ".smcp", ".c2sc"):
                base_info.case = GSSmallcaps
            elif suffix in (".subs", ".sups", ".sinf"):
                base_info.case = GSMinor
        return base_info, cutSuffix

    # Detect ligatures.
    if "_" in base_name:
        base_names = base_name.split("_")
        # The last name has a suffix, add it to all the names.
        if "-" in base_names[-1]:
            _, s = base_names[-1].rsplit("-", 1)
            base_names = [
                (n if n.endswith(f"-{s}") else f"{n}-{s}") for n in base_names
            ]
        
        base_info, suffixes = _construct_liga_info_names_(base_names, data, cutSuffix)
        print("__A", glyph_name, base_info)
        if base_info is not None:
            base_info.name = glyph_name
            return base_info, cutSuffix

    if _is_unicode_uni_value(base_name):
        base_names = []
        for i in range(3, len(base_name), 4):
            base_names.append("uni" + base_name[i:4+i])
        if len(base_names) == 1:
            base_info = _lookup_info_by_unicode(base_names[0][3:], data)
        else:
            base_info = _construct_liga_info_names_(base_names, data)
        if base_info is not None:
            base_info.name = glyph_name
            return base_info, cutSuffix

    if _is_unicode_u_value(base_name):
        base_names = []
        for i in range(1, len(base_name), 5):
            base_names.append("u" + base_name[i:5+i])
        if len(base_names) == 1:
            base_info = _lookup_info_by_unicode(base_names[0][1:], data)
        else:
            base_info = _construct_liga_info_names_(base_names, data)
        if base_info is not None:
            base_info.name = glyph_name
            return base_info, cutSuffix
    
    # TODO: Cover more cases. E.g. "one_one" -> ("Number", "Ligature") but
    # "one_onee" -> ("Number", "Composition").

    # Still nothing? Maybe we're looking at something like "uni1234.alt", try
    # using fontTools' AGL module to convert the base name to something meaningful.
    # Corner case: when looking at ligatures, names that don't exist in the AGLFN
    # are skipped, so len("acutecomb_o") == 2 but len("dotaccentcomb_o") == 1.
    character = fontTools.agl.toUnicode(base_name)
    if character:
        category, sub_category, case = _translate_category(
            glyph_name, unicodedata.category(character[0])
        )
        name = fontTools.agl.UV2AGL.get(ord(character[0]))
        if name is None:
            name = glyph_name
        return GlyphInfo(name, category=category, subCategory=sub_category, case=case)

    return None, None # GlyphInfo(glyph_name)


def _translate_category(glyph_name, unicode_category):
    """Return a translation from Unicode category letters to Glyphs
    categories."""
    DEFAULT_CATEGORIES = {
        None: ("Letter", None),
        "Cc": ("Separator", None, None),
        "Cf": ("Separator", "Format", None),
        "Cn": ("Symbol", None, None),
        "Co": ("Letter", "Compatibility", None),
        "Ll": ("Letter", None, "lower"),
        "Lm": ("Letter", "Modifier", None),
        "Lo": ("Letter", None, None),
        "Lt": ("Letter", None, "upper"),
        "Lu": ("Letter", None, "upper"),
        "Mc": ("Mark", "Spacing Combining", None),
        "Me": ("Mark", "Enclosing", None),
        "Mn": ("Mark", "Nonspacing", None),
        "Nd": ("Number", "Decimal Digit", None),
        "Nl": ("Number", None, None),
        "No": ("Number", "Decimal Digit", None),
        "Pc": ("Punctuation", None, None),
        "Pd": ("Punctuation", "Dash", None),
        "Pe": ("Punctuation", "Parenthesis", None),
        "Pf": ("Punctuation", "Quote", None),
        "Pi": ("Punctuation", "Quote", None),
        "Po": ("Punctuation", None, None),
        "Ps": ("Punctuation", "Parenthesis", None),
        "Sc": ("Symbol", "Currency", None),
        "Sk": ("Mark", "Spacing", None),
        "Sm": ("Symbol", "Math", None),
        "So": ("Symbol", None, None),
        "Zl": ("Separator", None, None),
        "Zp": ("Separator", None, None),
        "Zs": ("Separator", "Space", None),
    }

    glyphs_category = DEFAULT_CATEGORIES.get(unicode_category, ("Letter", None, None))

    # Exception: Something like "one_two" should be a (_, Ligature),
    # "acutecomb_brevecomb" should however stay (Mark, Nonspacing).
    if "_" in glyph_name and glyphs_category[0] != "Mark":
        return glyphs_category[0], "Ligature", glyphs_category[2]

    return glyphs_category
    
def _construct_liga_info_names_(base_names, data, cutSuffix=None):

    base_names_infos = []
    base_names_suffixes = []
    for name in base_names:
        
        info, needSuffix = get_glyph(name, data, cutSuffix=cutSuffix)
        if info is None and "-" in name: # for "a_Dboldscript-math"
            name, _ = name.rsplit("-", 1)
            info, needSuffix = get_glyph(name, data, cutSuffix=cutSuffix)
        if "halant-" in info.name:
            previous_info = base_names_infos[-1]
            if previous_info.category != "Halfform" and "a-" in previous_info.name:
                halfform_name = previous_info.name.replace("a-", "-")
                halfform_info, cutSuffix = get_glyph(halfform_name, data, cutSuffix=cutSuffix)
                base_names_infos[-1] = halfform_info
                continue
        base_names_infos.append(info.copy())
        base_names_suffixes.append(needSuffix)
    if len(base_names_infos) == 0:
        return None
    first_info = base_names_infos[0]
    name_parts = []
    lang_suffix = None
    for info in base_names_infos:
        part_name = info.name
        if "-" in part_name:
            part_name, _lang_suffix = part_name.rsplit("-", 1)
            if _lang_suffix is not None and len(_lang_suffix) > 0:
                lang_suffix = _lang_suffix
        name_parts.append(part_name)

    base_info = first_info.copy()
    # If the first part is a Letter...
    if first_info.category == "Letter" or first_info.category == "Number":
        # ... and the rest are only marks or separators or don't exist, the
        # sub_category is that of the first part ...
        numberOfLetters = 0
        numberOfHalfforms = 0
        for componentInfo in base_names_infos:
            if componentInfo.category != "Mark" and componentInfo.category != "Separator":
                numberOfLetters += 1
            if componentInfo.subCategory == "Halfform":
                numberOfHalfforms += 1
        if numberOfLetters - numberOfHalfforms > 1:
            base_info.subCategory = "Ligature"
        elif numberOfHalfforms > 0:
            base_info.subCategory = "Conjunct"
        elif base_info.script not in ("latin", "cyrillic", "greek"):
            base_info.subCategory = "Composition"
    else:
         base_info.subCategory = "Ligature"

    base_info.production = _construct_production_infos(base_names_infos)
    base_info.unicodes = None
    return base_info, base_names_suffixes

def _construct_production_infos(infos, data=None):

    """Return the production name for the info objects according to the
    AGL specification.

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
    # So we have a ligature that is not mapped in the data. Split it up and
    # look up the individual parts.

    # Turn all parts of the ligature into production names.
    _all_uninames = True
    production_names = []
    suffix = ""
    for part in infos:
        part_name = part.name
        if part_name not in fontTools.agl.AGL2UV:
            part_name = part.production
            if part_name is None and (_is_unicode_uni_value(part.name) or _is_unicode_u_value(part.name)):
                part_name = part.name
            if not part_name:
                # We hit a part that does not seem to be a valid glyph name known to us,
                # so the entire glyph name can't carry Unicode meaning. Return it
                # sanitized.
                return _agl_compliant_name(glyph_name)
        period_pos = part_name.find(".")
        if period_pos > 0:
            part_suffix = part_name[period_pos:]
            part_name = part_name[0:period_pos]
            suffix = part_suffix + suffix
            print
        production_names.append(part_name)
        
    # Some names Glyphs uses resolve to other names that are not uniXXXX names and may
    # contain dots (e.g. idotaccent -> i.loclTRK). If there is any name with a "." in
    # it before the last element, punt. We'd have to introduce a "." into the ligature
    # midway, which is invalid according to the AGL. Example: "a_i.loclTRK" is valid,
    # but "a_i.loclTRK_a" isn't.
    #if any("." in part for part in production_names[:-1]):
    #    return _agl_compliant_name(glyph_name)

    # If any production name starts with a "uni" and there are none of the
    # "uXXXXX" format, try to turn all parts into "uni" names and concatenate
    # them.
    production_name = _construct_join_names(production_names)
    if len(suffix) > 0:
        production_name += suffix
    production_name = production_name.replace("094D094D0930", "094D0930094D")
    return production_name

def _construct_join_names(names):
    if any(
        (_is_unicode_uni_value(part) or _is_unicode_u_value(part)) for part in names
    ):
        uni_names = []
        for part in names:
            if part.startswith("uni"):
                uni_names.append(part[3:])
            elif len(part) == 5 and _is_unicode_u_value(part):
                uni_names.append(part[1:])
            elif part in fontTools.agl.AGL2UV:
                uni_names.append("{:04X}".format(fontTools.agl.AGL2UV[part]))
            else:
                return None
        final_production_name = "uni" + "".join(uni_names)
    else:
        final_production_name = "_".join(names)
        replace_parts = [
            ["ra_halant", "rakar"], # TODO: this should not be done for malayalam and kannada
            ["a_halant", ""] # TODO: this should not be done for kannada
        ]
        for replace_part in replace_parts:
            final_production_name = final_production_name.replace(replace_part[0], replace_part[1])
    return _agl_compliant_name(final_production_name)
