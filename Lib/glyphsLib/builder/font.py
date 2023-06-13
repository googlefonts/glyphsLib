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
    KEYBOARD_INCREMENT_KEY,
    MASTER_ORDER_LIB_KEY,
)


def to_ufo_font_attributes(self, family_name):
    """Generate a list of UFOs with metadata loaded from .glyphs data.

    Modifies the list of UFOs in the UFOBuilder (self) in-place.
    """

    font = self.font

    for index, master in enumerate(font.masters):
        ufo = self.ufo_module.Font()

        fill_ufo_metadata(master, ufo)
        if not self.minimal:
            fill_ufo_metadata_roundtrip(master, ufo)

        self.to_ufo_names(ufo, master, family_name)  # .names
        self.to_ufo_family_user_data(ufo)  # .user_data

        if has_any_corner_components(font, master):
            ufo.lib.setdefault(UFO2FT_FILTERS_KEY, []).append(
                {
                    "namespace": "glyphsLib.filters",
                    "name": "cornerComponents",
                    "pre": True,
                }
            )

        ufo.lib.setdefault(UFO2FT_FILTERS_KEY, []).append(
            {"namespace": "glyphsLib.filters", "name": "eraseOpenCorners", "pre": True}
        )
        ufo.lib[UFO2FT_FEATURE_WRITERS_KEY] = DEFAULT_FEATURE_WRITERS

        self.to_ufo_custom_params(ufo, font)  # .custom_params
        self.to_ufo_master_attributes(ufo, master)  # .masters

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
    ("copyright", "copyright", False),
    ("openTypeNameDesigner", "designer", False),
    ("openTypeNameDesignerURL", "designerURL", False),
    ("openTypeNameManufacturer", "manufacturer", False),
    ("openTypeNameManufacturerURL", "manufacturerURL", False),
)


def fill_ufo_metadata(master, ufo):
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

    # NOTE: glyphs2ufo will *always* set a UFO public.glyphOrder equal to the
    # order of glyphs in the glyphs file, which can optionally be overwritten
    # by a glyphOrder custom parameter below in `to_ufo_custom_params`.
    ufo.glyphOrder = list(glyph.name for glyph in font.glyphs)


def fill_ufo_metadata_roundtrip(master, ufo):
    font = master.font
    ufo.lib[APP_VERSION_LIB_KEY] = font.appVersion
    ufo.lib[KEYBOARD_INCREMENT_KEY] = font.keyboardIncrement


# UFO to glyphs


def to_glyphs_font_attributes(self, source, master, is_initial):
    """
    Copy font attributes from `ufo` either to `self.font` or to `master`.

    Arguments:
    self -- The UFOBuilder
    ufo -- The current UFO being read
    master -- The current master being written
    is_initial -- True iff this the first UFO that we process
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

    if info.copyright is not None:
        font.copyright = info.copyright
    if info.openTypeNameDesigner is not None:
        font.designer = info.openTypeNameDesigner
    if info.openTypeNameDesignerURL is not None:
        font.designerURL = info.openTypeNameDesignerURL
    if info.openTypeNameManufacturer is not None:
        font.manufacturer = info.openTypeNameManufacturer
    if info.openTypeNameManufacturerURL is not None:
        font.manufacturerURL = info.openTypeNameManufacturerURL

    self.to_glyphs_family_names(ufo)
    self.to_glyphs_family_user_data_from_ufo(ufo)
    self.to_glyphs_custom_params(ufo, font)


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
        for layer in glyph.layers:
            if (
                layer.layerId != master.id
                or layer.associatedMasterId != master.id
                or not layer.hints
            ):
                continue
            if any(h.type.upper() == "CORNER" for h in layer.hints):
                return True
    return False
