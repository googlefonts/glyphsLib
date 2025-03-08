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

from typing import Optional, Tuple
from glyphsLib.classes import GSFont, GSFontMaster
from fontTools.designspaceLib import SourceDescriptor
from ufoLib2 import Font as UFOFont
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
    UFO_NAME_MAPPING,
    LANGUAGE_MAPPING,
    GLYPHS_PROPERTIES_2_UFO_FIELDS,
)


def to_ufo_font_attributes(self, family_name: Optional[str]) -> None:
    """Generate UFOs with metadata from a .glyphs font.

    Modifies the list of UFOs in the UFOBuilder in-place.
    """
    font: GSFont = self.font

    disable_all_automatic_behaviour = font.customParameters.get("DisableAllAutomaticBehaviour", False)

    for index, master in enumerate(font.masters):
        ufo = self.ufo_module.Font()

        to_ufo_metadata(master, ufo)
        if not self.minimal:
            to_ufo_metadata_roundtrip(master, ufo)

        self.to_ufo_names(ufo, master, family_name)
        self.to_ufo_family_user_data(ufo)
        ufo.lib[UFO2FT_FEATURE_WRITERS_KEY] = DEFAULT_FEATURE_WRITERS

        self.to_ufo_properties(ufo, font)
        self.to_ufo_custom_params(ufo, font, "font")
        self.to_ufo_custom_params(ufo, master, "fontMaster")
        self.to_ufo_master_attributes(ufo, master)

        nested_user_data = ufo.lib.get("com.schriftgestaltung.fontMaster.userData", {})
        if UFO2FT_FILTERS_KEY not in ufo.lib and UFO2FT_FILTERS_KEY in nested_user_data:
            ufo.lib[UFO2FT_FILTERS_KEY] = nested_user_data.pop(UFO2FT_FILTERS_KEY)
            if not nested_user_data:
                del ufo.lib["com.schriftgestaltung.fontMaster.userData"]

        if not disable_all_automatic_behaviour:
            ufo.lib.setdefault(UFO2FT_FILTERS_KEY, [
                {
                    "namespace": "glyphsLib.filters",
                    "name": "eraseOpenCorners",
                    "pre": True,
                }
            ])

        if has_any_corner_components(font, master):
            filters = ufo.lib.setdefault(UFO2FT_FILTERS_KEY, [])
            if not any(isinstance(f, dict) and f.get("name") == "cornerComponents" for f in filters):
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


INFO_FIELDS: Tuple[Tuple[str, str, bool], ...] = (
    ("unitsPerEm", "upm", True),
    ("versionMajor", "versionMajor", True),
    ("versionMinor", "versionMinor", True),
    ("note", "note", False),
)


def to_ufo_metadata(master: GSFontMaster, ufo: UFOFont) -> None:
    """Transfer metadata from Glyphs master to UFO."""
    font: GSFont = master.font
    # "date" can be missing; Glyphs.app removes it on saving if it's empty:
    # https://github.com/googlefonts/glyphsLib/issues/134
    for info_key, glyphs_key, always in INFO_FIELDS:
        value = getattr(font, glyphs_key, None)
        if always or value:
            setattr(ufo.info, info_key, value)

    date_created = getattr(font, "date", None)
    if date_created is not None:
        ufo.info.openTypeHeadCreated = to_ufo_time(date_created)

    openTypeNameRecords = ufo.info.openTypeNameRecords or []
    for infoValue in font.properties:
        ufo_key = GLYPHS_PROPERTIES_2_UFO_FIELDS.get(infoValue.key)
        if not ufo_key:
            continue
        if infoValue.value:
            setattr(ufo.info, ufo_key, infoValue.value)
        elif infoValue.values:
            default_value = None
            name_id = UFO_NAME_MAPPING[ufo_key]
            for script_key, text in infoValue.values.items():
                if script_key in ["dflt", "ENG"]:
                    default_value = text
                else:
                    language_id = LANGUAGE_MAPPING.get(script_key)
                    nameRecord = {
                        "nameID": name_id,
                        "platformID": 3,
                        "encodingID": 1,
                        "languageID": language_id,
                        "string": infoValue.values[script_key]
                    }
                    openTypeNameRecords.append(nameRecord)  # type: ignore
            if default_value:
                setattr(ufo.info, ufo_key, default_value)
            if openTypeNameRecords:
                ufo.info.openTypeNameRecords = openTypeNameRecords
    # NOTE: glyphs2ufo will *always* set a UFO public.glyphOrder equal to the
    # order of glyphs in the glyphs file, which can optionally be overwritten
    # by a glyphOrder custom parameter below in `to_ufo_custom_params`.
    ufo.glyphOrder = [glyph.name for glyph in font.glyphs]


def to_glyphs_metadata(ufo: UFOFont, font: GSFont):
    for glyphs_key, ufo_key in GLYPHS_PROPERTIES_2_UFO_FIELDS.items():
        value = getattr(ufo.info, ufo_key)
        if value:
            font.properties[glyphs_key] = value


def to_ufo_metadata_roundtrip(master: GSFontMaster, ufo: UFOFont) -> None:
    """Store additional metadata in UFO lib for roundtrip compatibility."""
    font: GSFont = master.font
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

# UFO to Glyphs Conversion


def to_glyphs_font_attributes(self, source: SourceDescriptor, master: GSFontMaster, is_initial: bool) -> None:
    """
    Copy font attributes from `ufo` either to `self.font` or to `master`.

    Arguments:
    self -- The UFOBuilder
    source -- The current UFO source being read
    master -- The current master being written
    is_initial -- True if this is the first UFO being processed
    """
    if is_initial:
        _set_glyphs_font_attributes(self, source)
    else:
        _compare_and_merge_glyphs_font_attributes(self, source)


def _set_glyphs_font_attributes(self, source: SourceDescriptor) -> None:

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


def _compare_and_merge_glyphs_font_attributes(self, source: SourceDescriptor) -> None:
    ufo: UFOFont = source.font
    self.to_glyphs_family_names(ufo, merge=True)


def to_glyphs_ordered_masters(self):
    """Modify in-place the list of UFOs to restore their original order in
    the Glyphs file (if any, otherwise does not change the order)."""
    return sorted(self.designspace.sources, key=_original_master_order)


def _original_master_order(source: SourceDescriptor) -> int:
    try:
        return source.font.lib[MASTER_ORDER_LIB_KEY]
    # Key may not be found or source.font be None if it's a layer source.
    except (KeyError, AttributeError):
        return 1 << 31


def has_any_corner_components(font: GSFont, master: GSFontMaster) -> bool:
    """Check if any layer in a master contains corner components."""
    return any(
        any(layer.hasCorners for layer in glyph._layers.values() if layer.associatedMasterId == master.id)
        for glyph in font.glyphs
    )
