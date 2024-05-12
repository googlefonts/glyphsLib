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


from .common import to_ufo_time, from_ufo_time
from .constants import (
    DEFAULT_FEATURE_WRITERS,
    UFO2FT_FEATURE_WRITERS_KEY,
    UFO2FT_FILTERS_KEY,
    APP_VERSION_LIB_KEY,
    FORMATVERSION_LIB_KEY,
    KEYBOARD_INCREMENT_KEY,
    KEYBOARD_INCREMENT_BIG_KEY,
    KEYBOARD_INCREMENT_HUGE_KEY,
    GRID_SIZE_KEY,
    GRID_SUBDIVISION_KEY,
    MASTER_ORDER_LIB_KEY,
    GLYPHS_PREFIX,
)


def to_ufo_font_attributes(self, family_name):
    """Generate a list of UFOs with metadata loaded from .glyphs data.

    Modifies the list of UFOs in the UFOBuilder (self) in-place.
    """

    font = self.font
    disableAllAutomaticBehaviour = False
    disableAllAutomaticBehaviourParameter = font.customParameters[
        "DisableAllAutomaticBehaviour"
    ]
    if disableAllAutomaticBehaviourParameter:
        disableAllAutomaticBehaviour = disableAllAutomaticBehaviourParameter
    for index, master in enumerate(font.masters):
        ufo = self.ufo_module.Font()

        to_ufo_metadata(master, ufo)
        if not self.minimal:
            to_ufo_metadata_roundtrip(master, ufo)

        self.to_ufo_names(ufo, master, family_name)  # .names
        self.to_ufo_family_user_data(ufo)  # .user_data

        ufo.lib[UFO2FT_FEATURE_WRITERS_KEY] = DEFAULT_FEATURE_WRITERS

        self.to_ufo_properties(ufo, font)
        self.to_ufo_custom_params(ufo, font, "font")  # .custom_params
        self.to_ufo_custom_params(ufo, master, "fontMaster")  # .custom_params
        self.to_ufo_master_attributes(ufo, master)  # .masters

        # Extract nested lib keys to the top level
        nestedUserData = ufo.lib.get("com.schriftgestaltung.fontMaster.userData", {})
        if UFO2FT_FILTERS_KEY not in ufo.lib and UFO2FT_FILTERS_KEY in nestedUserData:
            ufo.lib[UFO2FT_FILTERS_KEY] = nestedUserData[UFO2FT_FILTERS_KEY]

            del nestedUserData[UFO2FT_FILTERS_KEY]
            if not nestedUserData:
                del ufo.lib["com.schriftgestaltung.fontMaster.userData"]

        if not disableAllAutomaticBehaviour:
            if UFO2FT_FILTERS_KEY not in ufo.lib:
                ufo.lib[UFO2FT_FILTERS_KEY] = [
                    {
                        "namespace": "glyphsLib.filters",
                        "name": "eraseOpenCorners",
                        "pre": True,
                    }
                ]

        if has_any_corner_components(font, master):
            filters = ufo.lib.setdefault(UFO2FT_FILTERS_KEY, [])
            if not any(
                hasattr(f, "get") and f.get("name") == "cornerComponents"
                for f in filters
            ):
                filters.append(
                    {
                        "namespace": "glyphsLib.filters",
                        "name": "cornerComponents",
                        "pre": True,
                    }
                )

        ufo.lib[MASTER_ORDER_LIB_KEY] = index

        # FIXME: (jany) in the future, yield this UFO (for memory, lazy iter)
        source = self._designspace.newSourceDescriptor()
        source.font = ufo
        self._designspace.addSource(source)
        self._sources[master.id] = source


INFO_FIELDS = (
    ("unitsPerEm", "upm", True),
    ("versionMajor", "versionMajor", True),
    ("versionMinor", "versionMinor", True),
    ("note", "note", False),
)

PROPERTIES_FIELDS = {
    "compatibleFullNames": "openTypeNameCompatibleFullName",
    "copyrights": "copyright",
    "descriptions": "openTypeNameDescription",
    "designers": "openTypeNameDesigner",
    "designerURL": "openTypeNameDesignerURL",
    # "familyNames": "familyName",
    "preferredFamilyNames": "openTypeNamePreferredFamilyName",
    "preferredSubfamilyNames": "openTypeNamePreferredSubfamilyName",
    "licenses": "openTypeNameLicense",
    "licenseURL": "openTypeNameLicenseURL",
    "manufacturers": "openTypeNameManufacturer",
    "manufacturerURL": "openTypeNameManufacturerURL",
    "postscriptFontName": "postscriptFontName",
    "postscriptFullNames": "postscriptFullName",
    "sampleTexts": "openTypeNameSampleText",
    "trademarks": "trademark",
    "uniqueID": "openTypeNameUniqueID",
    # "variationsPostScriptNamePrefix": "variationsPostScriptNamePrefix", # TODO: what is the correct ufo key?
    "vendorID": "openTypeOS2VendorID",
    "versionString": "openTypeNameVersion",
    "WWSFamilyName": "openTypeNameWWSFamilyName",
    "WWSSubfamilyName": "openTypeNameWWSSubfamilyName",
}


def to_ufo_metadata(master, ufo):
    font = master.font

    # "date" can be missing; Glyphs.app removes it on saving if it's empty:
    # https://github.com/googlefonts/glyphsLib/issues/134
    for info_key, glyphs_key, always in INFO_FIELDS:
        value = getattr(font, glyphs_key)
        if always or value:
            setattr(ufo.info, info_key, value)

    date_created = getattr(font, "date", None)
    if date_created is not None:
        date_created = to_ufo_time(date_created)

    if date_created is not None:
        ufo.info.openTypeHeadCreated = date_created
    for infoValue in font.properties:
        ufo_key = PROPERTIES_FIELDS[infoValue.key]
        setattr(ufo.info, ufo_key, infoValue.value)
    # NOTE: glyphs2ufo will *always* set a UFO public.glyphOrder equal to the
    # order of glyphs in the glyphs file, which can optionally be overwritten
    # by a glyphOrder custom parameter below in `to_ufo_custom_params`.
    ufo.glyphOrder = list(glyph.name for glyph in font.glyphs)


def to_glyphs_metadata(ufo, font):
    for glyphs_key, ufo_key in PROPERTIES_FIELDS.items():
        value = getattr(ufo.info, ufo_key)
        if value:
            font.properties[glyphs_key] = value


def to_ufo_metadata_roundtrip(master, ufo):
    font = master.font
    ufo.lib[APP_VERSION_LIB_KEY] = font.appVersion
    ufo.lib[FORMATVERSION_LIB_KEY] = font.formatVersion
    if font._defaultsForName["keyboardIncrement"] != font.keyboardIncrement:
        ufo.lib[KEYBOARD_INCREMENT_KEY] = font.keyboardIncrement
    if font._defaultsForName["keyboardIncrementBig"] != font.keyboardIncrementBig:
        ufo.lib[KEYBOARD_INCREMENT_BIG_KEY] = font.keyboardIncrementBig
    if font._defaultsForName["keyboardIncrementHuge"] != font.keyboardIncrementHuge:
        ufo.lib[KEYBOARD_INCREMENT_HUGE_KEY] = font.keyboardIncrementHuge
    if font._defaultsForName["keyboardIncrementHuge"] != font.keyboardIncrementHuge:
        ufo.lib[KEYBOARD_INCREMENT_HUGE_KEY] = font.keyboardIncrementHuge
    if font._defaultsForName["grid"] != font.grid:
        ufo.lib[GRID_SIZE_KEY] = font.grid
    if font._defaultsForName["gridSubDivision"] != font.gridSubDivision:
        ufo.lib[GRID_SUBDIVISION_KEY] = font.gridSubDivision
    if font.customParameters["glyphOrder"] is None:
        ufo.lib[GLYPHS_PREFIX + "useGlyphOrder"] = False


# UFO to glyphs


def to_glyphs_font_attributes(self, source, master, is_initial):
    """
    Copy font attributes from `ufo` either to `self.font` or to `master`.

    Arguments:
    self -- The UFOBuilder
    ufo -- The current UFO being read
    master -- The current master being written
    is_initial -- True if this the first UFO that we process
    """
    if is_initial:
        _set_glyphs_font_attributes(self, source)
    else:
        _compare_and_merge_glyphs_font_attributes(self, source)


def _set_glyphs_font_attributes(self, source):
    font = self.font
    ufo = source.font
    info = ufo.info

    if APP_VERSION_LIB_KEY in ufo.lib:
        font.appVersion = ufo.lib[APP_VERSION_LIB_KEY]
    if KEYBOARD_INCREMENT_KEY in ufo.lib:
        font.keyboardIncrement = ufo.lib[KEYBOARD_INCREMENT_KEY]
    if KEYBOARD_INCREMENT_BIG_KEY in ufo.lib:
        font.keyboardIncrementBig = ufo.lib[KEYBOARD_INCREMENT_BIG_KEY]
    if KEYBOARD_INCREMENT_HUGE_KEY in ufo.lib:
        font.keyboardIncrementHuge = ufo.lib[KEYBOARD_INCREMENT_HUGE_KEY]
    if GRID_SIZE_KEY in ufo.lib:
        font.grid = ufo.lib[GRID_SIZE_KEY]
    if GRID_SUBDIVISION_KEY in ufo.lib:
        font.gridSubDivision = ufo.lib[GRID_SUBDIVISION_KEY]
    if info.openTypeHeadCreated is not None:
        # FIXME: (jany) should wrap in glyphs_datetime? or maybe the GSFont
        #     should wrap in glyphs_datetime if needed?
        font.date = from_ufo_time(info.openTypeHeadCreated)
    if info.unitsPerEm is not None:
        font.upm = info.unitsPerEm
    if info.versionMajor is not None:
        font.versionMajor = info.versionMajor
    if info.versionMinor is not None:
        font.versionMinor = info.versionMinor
    if info.note:
        font.note = info.note

    # if info.copyright is not None:
    #     font.copyright = info.copyright
    # if info.trademark is not None:
    #     font.trademark = info.trademark
    # if info.openTypeNameDesigner is not None:
    #     font.designer = info.openTypeNameDesigner
    # if info.openTypeNameDesignerURL is not None:
    #     font.designerURL = info.openTypeNameDesignerURL
    # if info.openTypeNameManufacturer is not None:
    #     font.manufacturer = info.openTypeNameManufacturer
    # if info.openTypeNameManufacturerURL is not None:
    #     font.manufacturerURL = info.openTypeNameManufacturerURL

    to_glyphs_metadata(ufo, font)
    self.to_glyphs_family_names(ufo)
    self.to_glyphs_family_user_data_from_ufo(ufo)
    self.to_glyphs_custom_params(ufo, font, "font")


def _compare_and_merge_glyphs_font_attributes(self, source):
    ufo = source.font
    self.to_glyphs_family_names(ufo, merge=True)


def to_glyphs_ordered_masters(self):
    """Modify in-place the list of UFOs to restore their original order in
    the Glyphs file (if any, otherwise does not change the order)."""
    return sorted(self.designspace.sources, key=_original_master_order)


def _original_master_order(source):
    try:
        return source.font.lib[MASTER_ORDER_LIB_KEY]
    # Key may not be found or source.font be None if it's a layer source.
    except (KeyError, AttributeError):
        return 1 << 31


def has_any_corner_components(font, master):
    for glyph in font.glyphs:
        for layerId, layer in glyph._layers.items():
            if layer.associatedMasterId != master.id or not layer.hints:
                continue
            if layer.hasCorners:
                return True
    return False
