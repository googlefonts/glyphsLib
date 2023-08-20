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


import re
import os
from typing import Tuple
import xml.etree.ElementTree

from fontTools import unicodedata
import fontTools.agl

__all__ = [
    "get_glyph",
    "GlyphData",
    "GlyphInfo",
    "GSUppercase",
    "GSLowercase",
    "GSSmallcaps",
    "GSMinor",
    "GSBIDI",
    "GSLTR",
    "GSRTL",
    "GSVertical",
]

GSNoCase = None  # 0
GSUppercase = "upper"  # 1
GSLowercase = "lower"  # 2
GSSmallcaps = "small"  # 3
GSMinor = "minor"  # 4

GSBIDI = "BIDI"
GSLTR = "LTR"
GSRTL = "RTL"
GSVertical = 4


def debug(*string):
    # print(*string)
    pass


class GlyphInfo:
    __slots__ = [
        "name",
        "_production",
        "unicodes",
        "category",
        "subCategory",
        "case",
        "script",
        "direction",
        "description",
    ]

    def __init__(
        self,
        name,
        production: str = None,
        unicodes: list = None,
        category: str = None,
        subCategory: str = None,
        case: str = None,
        script: str = None,
        direction: str = GSLTR,
        description: str = None,
    ):
        self.name = name
        self._production = production
        self.unicodes = unicodes
        self.category = category
        self.subCategory = subCategory
        self.case = case
        self.script = script
        self.direction = direction
        self.description = description

    def copy(self):
        copy = GlyphInfo(
            self.name,
            self._production,
            self.unicodes,
            self.category,
            self.subCategory,
            self.case,
            self.script,
            self.direction,
            self.description,
        )
        return copy

    def __repr__(self):
        # if not isinstance(self.name, str):
        #    debug("___self.name", self.name)
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
        if self.direction and self.direction != GSLTR:
            string += " direction:" + self.direction
        if self.description:
            string += " desc:" + self.description
        return string

    @property
    def production(self):
        # debug("__get production", self._production)
        return self._production if self._production is not None else self.name

    @production.setter
    def production(self, production):
        debug("__set production", production)
        self._production = production

    # glyphsLib contains many references to both .production and .production_name
    production_name = production


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
                if glyph_unicode is None:
                    glyph_unicode = glyph.attrib.get("unicodeLegacy")
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


def get_glyph(
    glyph_name: str, data: GlyphData = None, unicodes: list = None
) -> GlyphInfo:
    """Return a named tuple (Glyph) containing information derived from a glyph
    name akin to GSGlyphInfo.

    The information is derived from an included copy of GlyphData.xml
    and GlyphData_Ideographs.xml, going by the glyph name or unicode fallback.
    """
    # Read data on first use.
    if data is None:
        data = _load_data_files()
    return _get_glyph(glyph_name, data, unicodes)[0] or GlyphInfo(glyph_name)


def _load_data_files():
    global GLYPHDATA
    if GLYPHDATA is None:
        from importlib.resources import open_binary

        with open_binary("glyphsLib.data", "GlyphData.xml") as f1:
            with open_binary("glyphsLib.data", "GlyphData_Ideographs.xml") as f2:
                GLYPHDATA = GlyphData.from_files(f1, f2)
    return GLYPHDATA


def _get_glyph(
    glyph_name: str, data: GlyphData, unicodes: str = None, cutSuffix: str = None
) -> Tuple[GlyphInfo, str]:

    info = None

    debug("__get", glyph_name, cutSuffix)

    # Look up data by full glyph name first.
    if cutSuffix is not None:
        info = _lookup_info(glyph_name + cutSuffix, data)
        if info is not None:
            return info, None
    info = _lookup_info(glyph_name, data)
    if info is not None:
        return info, cutSuffix

    # try to lookup up by unicode
    if unicodes is None and len(glyph_name) == 1:
        unicodes = ["%.4X" % ord(glyph_name)]
        debug("__unicodes 0", unicodes)
    if unicodes is not None:
        for uni in unicodes:
            info = _lookup_info_by_unicode(uni, data)
            return info, cutSuffix

    # try to parse the name
    info, cutSuffix = _construct_info(glyph_name, data, cutSuffix)

    return info, cutSuffix or ""


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
    return GlyphInfo(
        attributes.get("name"),
        production=attributes.get("production"),
        unicodes=attributes.get("unicode"),
        category=attributes.get("category"),
        subCategory=attributes.get("subCategory"),
        case=attributes.get("case"),
        script=attributes.get("script"),
        direction=attributes.get("direction", GSLTR),
        description=attributes.get("description"),
    )


def _lookup_info_by_unicode(uni, data):
    """Look up glyphinfo in data by unicode
    or return empty dictionary.
    """
    debug("__XX0", uni)
    attributes = data.unicodes.get(uni)
    debug("__XX1", attributes)
    if not attributes:
        char = chr(int(uni, 16))
        if len(uni) > 4:
            glyph_name = f"u{uni}"
        else:
            glyph_name = f"uni{uni}"
        category, sub_category, case = _translate_category(
            glyph_name, unicodedata.category(char)
        )
        script = unicodedata.script(char)
        debug("__XX3", category, sub_category, case)

        return GlyphInfo(
            glyph_name,
            production=glyph_name,
            category=category,
            subCategory=sub_category,
            case=case,
            script=script,
        )
        return None
    return GlyphInfo(
        attributes.get("name"),
        production=attributes.get("production"),
        unicodes=attributes.get("unicode"),
        category=attributes.get("category"),
        subCategory=attributes.get("subCategory"),
        case=attributes.get("case"),
        script=attributes.get("script"),
        direction=attributes.get("direction"),
        description=attributes.get("description"),
    )


def _agl_compliant_name(glyph_name):
    """Return an AGL-compliant name string or None if we can't make one."""
    MAX_GLYPH_NAME_LENGTH = 63
    clean_name = re.sub("[^0-9a-zA-Z_.]", "", glyph_name)
    if len(clean_name) > MAX_GLYPH_NAME_LENGTH:
        return None
    return clean_name


def _is_unicode_uni_value(name):
    """Return whether we are looking at a uniXXXX value."""
    debug("__n1", name)
    return (
        name.startswith("uni")
        and len(name) > 6
        and ((len(name) - 3) % 4) == 0
        and all(part_char in "0123456789ABCDEF" for part_char in name[3:])
    )


def _is_unicode_u_value(name):
    """Return whether we are looking at a uXXXXX value."""
    debug("__n2", name)
    return (
        name.startswith("u")
        and len(name) > 6
        and ((len(name) - 1) % 5) == 0
        and all(part_char in "0123456789ABCDEF" for part_char in name[1:])
    )


def _underscoreGlyphInfo(glyph_name):
    info = GlyphInfo(glyph_name)
    if (
        glyph_name.startswith("_corner.")
        or glyph_name.startswith("_segment.")
        or glyph_name.startswith("_brush.")
        or glyph_name.startswith("_cap.abc")
    ):
        info.category = "Corner"
    if "-" in glyph_name:
        _, langSuffix = glyph_name.rsplit("-", 1)
        info.script = langSuffix  # TODO: add proper mapping from lang tags to script
    return info


# this means suffixes that are not separated by a '.'
def _infoWithKnownSuffix(base_name: str, data: GlyphData) -> GlyphInfo:
    knownSuffixes = ["superior", "inferior"]
    for knownSuffix in knownSuffixes:

        if not base_name.endswith(knownSuffix):
            continue

        base_name = base_name[: -len(knownSuffix)]
        base_info, _ = _get_glyph(base_name, data)
        if base_info:
            base_info = base_info.copy()
            base_info.case = GSMinor
            if base_info.production:
                base_info.production += knownSuffix
            base_info.name += knownSuffix
            base_info.unicodes = None
            return base_info
    return None


def _applySuffix(base_info, suffix):
    if suffix is None or len(suffix) == 0:
        return base_info

    debug("__base_info suffix", suffix, base_info)
    base_info = base_info.copy()
    base_info.name += suffix
    production = base_info._production
    if production is not None:
        debug("__add prod suffix:", production, suffix)
        production += suffix
        base_info.production = production
    base_info.unicodes = None

    if suffix == ".case":
        base_info.case = GSUppercase
    elif suffix in (".sc", ".smcp", ".c2sc"):
        base_info.case = GSSmallcaps
    elif suffix in (".subs", ".sups", ".sinf"):
        base_info.case = GSMinor
    return base_info


def _construct_liga_info_uniname_(base_name, glyph_name, data, cutSuffix):
    if _is_unicode_uni_value(base_name):
        base_names = []
        for i in range(3, len(base_name), 4):
            base_names.append("uni" + base_name[i : 4 + i])
        if len(base_names) == 1:
            base_info = _lookup_info_by_unicode(base_names[0][3:], data)
            debug("__x1", base_info)
        else:
            base_info, _ = _construct_liga_info_names_(base_names, data)
            debug("__x2", base_info)
        if base_info is not None:
            debug("__x3", base_info)
            return base_info, cutSuffix

    if _is_unicode_u_value(base_name):
        base_names = []
        for i in range(1, len(base_name), 5):
            base_names.append("u" + base_name[i : 5 + i])
        if len(base_names) == 1:
            base_info = _lookup_info_by_unicode(base_names[0][1:], data)
        else:
            base_info = _construct_liga_info_names_(base_names, data)
        if base_info is not None:
            base_info.name = glyph_name
            return base_info, cutSuffix

    return None, cutSuffix


def _construct_info_from_agl_(base_name):
    # Still nothing? Maybe we're looking at something like "uni1234.alt", try
    # using fontTools' AGL module to convert the base name to something meaningful.
    # Corner case: when looking at ligatures, names that don't exist in the AGLFN
    # are skipped, so len("acutecomb_o") == 2 but len("dotaccentcomb_o") == 1.
    character = fontTools.agl.toUnicode(base_name)
    debug("__char", base_name)
    if character is None or len(character) == 0:
        return None

    category, sub_category, case = _translate_category(
        base_name, unicodedata.category(character[0])
    )
    name = fontTools.agl.UV2AGL.get(ord(character[0]))
    if name is None:
        name = base_name
    return GlyphInfo(name, category=category, subCategory=sub_category, case=case)


def _construct_info(
    glyph_name: str, data: GlyphData, cutSuffix: str = None
) -> Tuple[GlyphInfo, str]:
    """Derive info of a glyph name."""
    # Glyphs creates glyphs that start with an underscore as "non-exportable" glyphs or
    # construction helpers without a category.
    debug("__glyph_name", glyph_name, cutSuffix)
    if glyph_name.startswith("_"):
        return _underscoreGlyphInfo(glyph_name), cutSuffix

    # Glyph variants (e.g. "fi.alt") don't have their own entry, so we strip e.g. the
    # ".alt" and try a second lookup with just the base name. A variant is hopefully in
    # the same category as its base glyph.
    suffix = ""
    base_info = None
    base_name = glyph_name
    base_name, lastSuffix = os.path.splitext(base_name)

    while len(lastSuffix) > 0:
        suffix += lastSuffix
        base_info, suffix = _get_glyph(base_name, data, cutSuffix=suffix)
        if base_info is not None:
            break
        base_name, lastSuffix = os.path.splitext(base_name)

    debug("__lastSuffix ({}), ({}), ({})".format(lastSuffix, suffix, cutSuffix))
    if base_info is None:
        base_info = _infoWithKnownSuffix(base_name, data)
        if base_info:
            return base_info, cutSuffix

    if base_info:
        base_info = _applySuffix(base_info, suffix)
        return base_info, cutSuffix

    # Detect ligatures.
    base_info, cutSuffix = _construct_liga_info_name_(base_name, data, cutSuffix)
    if base_info is not None:
        return base_info, cutSuffix

    base_info, cutSuffix = _construct_liga_info_uniname_(
        base_name, glyph_name, data, cutSuffix
    )
    if base_info is not None:
        return base_info, cutSuffix

    # TODO: Cover more cases. E.g. "one_one" -> ("Number", "Ligature") but
    # "one_onee" -> ("Number", "Composition").

    base_info = _construct_info_from_agl_(base_name)
    if base_info is not None:
        return base_info, cutSuffix

    return None, None  # GlyphInfo(glyph_name)


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


def _construct_liga_info_name_(base_name, data, cutSuffix):
    if "_" in base_name:
        base_names = base_name.split("_")
        # The last name has a suffix, add it to all the names.
        if "-" in base_names[-1]:
            _, s = base_names[-1].rsplit("-", 1)
            base_names = [
                (n if n.endswith(f"-{s}") else f"{n}-{s}") for n in base_names
            ]
        base_info, suffixes = _construct_liga_info_names_(base_names, data, cutSuffix)

        if base_info is not None:
            # if cutSuffix is not None and base_info.name.endswith(cutSuffix):
            #    glyph_name += cutSuffix
            #    cutSuffix = ""
            return base_info, suffixes
    return None, cutSuffix


def _applySimpleIndicShaping(base_infos, data: GlyphData):
    for idx in range(len(base_infos)):
        info = base_infos[idx]
        if "halant-" in info.name:
            if idx + 1 < len(base_infos):
                next_info = base_infos[idx + 1]
                if next_info.name.startswith("ra-"):
                    base_infos[idx] = None
                    rakar_name = next_info.name.replace("ra-", "rakar-")
                    rakar_info, _ = _get_glyph(rakar_name, data)
                    base_infos[idx + 1] = rakar_info
                    continue
            if idx > 0:
                replaceIdx = idx - 1
                previous_info = base_infos[replaceIdx]
                if previous_info.name.startswith("rakar-") and replaceIdx > 0:
                    replaceIdx -= 1
                    previous_info = base_infos[replaceIdx]
                    if previous_info is None and idx > 0:
                        replaceIdx -= 1
                        previous_info = base_infos[replaceIdx]
                if previous_info.category != "Halfform" and "a-" in previous_info.name:
                    halfform_name = previous_info.name.replace("a-", "-")
                    halfform_info, _ = _get_glyph(halfform_name, data)
                    base_infos[replaceIdx] = halfform_info
                    base_infos[idx] = None
                    continue


def _baseinfo_from_infos(base_infos, cutSuffix, data):
    first_info = None
    if cutSuffix and len(cutSuffix) > 0:
        # when base_name + suffix are in the glyph data
        first_info = _lookup_info(base_infos[0].name + cutSuffix, data)
        # assert first_info is None or base_names[0] == base_infos[0].name
    if first_info is None:
        first_info = base_infos[0]

    name_parts = []
    lang_suffix = None
    for info in base_infos:
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
        for componentInfo in base_infos:
            cat = componentInfo.category
            if componentInfo is not None:
                if cat != "Mark" and cat != "Separator":
                    numberOfLetters += 1
                if componentInfo.subCategory == "Halfform":
                    numberOfHalfforms += 1
        # debug("__num", numberOfLetters, numberOfHalfforms)
        if numberOfLetters - numberOfHalfforms > 1:
            base_info.subCategory = "Ligature"
        elif numberOfHalfforms > 0:
            base_info.subCategory = "Conjunct"
        elif base_info.script not in ("latin", "cyrillic", "greek"):
            base_info.subCategory = "Composition"
    elif first_info.category != "Mark":
        base_info.subCategory = "Ligature"
    base_info.name = _construct_join_names(name_parts)
    if lang_suffix is not None and len(lang_suffix) > 0:
        base_info.name += "-" + lang_suffix
    base_info.production = _construct_production_infos(base_infos)
    base_info.unicodes = None
    return base_info


def _suffix_parts(base_names, cutSuffix):
    suffix_parts = None
    if cutSuffix is not None and "_" in cutSuffix:
        if "." in cutSuffix[1:]:
            dot_index = cutSuffix[1:].find(".")
            first_suffix = cutSuffix[1:dot_index]
            remaining_suffix = cutSuffix[dot_index:]
        else:
            first_suffix = cutSuffix[1:]
            remaining_suffix = None
        suffix_parts = first_suffix.split("_")
        if len(suffix_parts) == len(base_names):
            cutSuffix = remaining_suffix
        else:
            suffix_parts = None
    return suffix_parts, cutSuffix


def _base_info_suffixes(base_names, cutSuffix, data):

    suffix_parts, cutSuffix = _suffix_parts(base_names, cutSuffix)

    base_infos = []
    base_suffixes = []
    hasSuffix = False
    idx = 0
    for name in base_names:
        if suffix_parts is not None:
            part_suffix = suffix_parts[idx]
            if len(part_suffix) > 0:
                part_suffix = "." + part_suffix
        else:
            part_suffix = None
        info, needSuffix = _get_glyph(name, data, cutSuffix=part_suffix)
        debug("__4c", name, info)
        if info is None and "-" in name:  # for "a_Dboldscript-math"
            shortName, _ = name.rsplit("-", 1)
            info, needSuffix = _get_glyph(shortName, data, cutSuffix=part_suffix)
            if info:
                name = shortName
        if info is None:
            info = GlyphInfo(name)

        debug("__4d", name, info)
        base_infos.append(info.copy())
        if needSuffix is not None and len(needSuffix) > 1 and needSuffix[0] == ".":
            needSuffix = needSuffix[1:]
        base_suffixes.append(needSuffix or "")
        if needSuffix:
            hasSuffix = True
        idx += 1
    if not hasSuffix:
        base_suffixes = []
    if cutSuffix is not None and len(cutSuffix) > 0:
        base_suffixes.append(cutSuffix)

    return base_infos, base_suffixes


def _construct_liga_info_names_(base_names, data, cutSuffix=None):
    debug("__4a", base_names, cutSuffix)

    base_infos, base_suffixes = _base_info_suffixes(base_names, cutSuffix, data)

    _applySimpleIndicShaping(base_infos, data)

    while None in base_infos:
        base_infos.remove(None)
    if len(base_infos) == 0:
        return None

    base_info = _baseinfo_from_infos(base_infos, cutSuffix, data)

    base_suffix = "_".join(base_suffixes)
    if len(base_suffix) > 0 and base_suffix[0] != ".":
        base_suffix = "." + base_suffix
    if len(base_suffix) < len(base_suffixes):  # all base_suffixes are empty
        base_suffix = None
    return base_info, base_suffix


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
    debug("__YY1", infos)
    # So we have a ligature that is not mapped in the data. Split it up and
    # look up the individual parts.

    # Turn all parts of the ligature into production names.
    # _all_uninames = True  # Never used
    production_names = []
    suffix = ""
    for part in infos:
        if part is not None:
            part_name = part.name
            if part_name not in fontTools.agl.AGL2UV:
                part_name = part.production
                if part_name is None and (
                    _is_unicode_uni_value(part.name) or _is_unicode_u_value(part.name)
                ):
                    part_name = part.name
                if not part_name:
                    # We hit a part that does not seem to be a valid glyph name known
                    # to us,
                    # so the entire glyph name can't carry Unicode meaning. Return it
                    # sanitized.
                    debug("__g", part.name)
                    part_name = _agl_compliant_name(part.name)
            period_pos = part_name.find(".")
            if period_pos > 0:
                part_suffix = part_name[period_pos:]
                part_name = part_name[0:period_pos]
                debug("__part_suffix + suffix", part_suffix, suffix)
                suffix += part_suffix

            production_names.append(part_name)
    count = 0
    while ".medi." in suffix or ".init." in suffix or ".fina." in suffix:
        suffix = suffix.replace(".fina.fina", ".fina")
        suffix = suffix.replace(".medi.fina", ".fina")
        suffix = suffix.replace(".medi.fina", ".fina")
        suffix = suffix.replace(".medi.medi", ".medi")
        suffix = suffix.replace(".init.medi", ".init")
        suffix = suffix.replace(".init.medi", ".init")
        suffix = suffix.replace(".init.fina", "")
        if count > 3:
            break
        count += 1
    # Some names Glyphs uses resolve to other names that are not uniXXXX names and may
    # contain dots (e.g. idotaccent -> i.loclTRK). If there is any name with a "." in
    # it before the last element, punt. We'd have to introduce a "." into the ligature
    # midway, which is invalid according to the AGL. Example: "a_i.loclTRK" is valid,
    # but "a_i.loclTRK_a" isn't.
    # if any("." in part for part in production_names[:-1]):
    #    return _agl_compliant_name(glyph_name)

    # If any production name starts with a "uni" and there are none of the
    # "uXXXXX" format, try to turn all parts into "uni" names and concatenate
    # them.
    debug("__g1", production_names)
    production_name = _construct_join_names(production_names)
    debug("__g1", production_names, ">", production_name)
    if len(suffix) > 0:
        debug("__production_name + suffix", production_name, suffix)
        production_name += suffix
    production_name = production_name.replace("094D094D0930", "094D0930094D")
    return production_name


def _construct_join_names(names):
    debug("__YY2", names)
    uni_names = []
    has_uni_value = False
    has_u_value = False
    for part in names:
        if _is_unicode_uni_value(part):
            uni_names.append(part[3:])
            has_uni_value = True
        elif _is_unicode_u_value(part):
            uni_names.append(part[1:])
            has_u_value = True
        elif part in fontTools.agl.AGL2UV:
            uni_names.append("{:04X}".format(fontTools.agl.AGL2UV[part]))
    if len(names) == len(uni_names) and (has_uni_value or has_u_value):
        debug("__YY4", uni_names)
        if not has_u_value:
            final_name = "uni" + "".join(uni_names)
        else:
            final_name = "u"
            for uni in uni_names:
                if len(uni) == 4:
                    final_name += "0" + uni
                else:
                    final_name += uni
    else:
        debug("__YY5", names)
        suffixes = []
        base_names = []
        # ["a", "parallel.circled"] > "a_parallel._circled"
        # (base name and suffix have the same number of underscores)
        for name in names:
            if "." in name:
                parts = name.split(".", 1)
                base_names.append(parts[0])
                suffixes.append(parts[1])
            else:
                base_names.append(name)
                suffixes.append("")

        final_name = "_".join(base_names)
        final_suffix = "_".join(suffixes)
        if len(final_suffix) >= len(suffixes):
            final_name += "." + final_suffix
    debug("__YY6", final_name)
    return _agl_compliant_name(final_name)
