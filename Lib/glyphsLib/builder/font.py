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

from __future__ import (print_function, division, absolute_import,
                        unicode_literals)

from collections import deque, OrderedDict
import logging

from .common import to_ufo_time, from_ufo_time
from .constants import GLYPHS_PREFIX

logger = logging.getLogger(__name__)

APP_VERSION_LIB_KEY = GLYPHS_PREFIX + 'appVersion'
KEYBOARD_INCREMENT_KEY = GLYPHS_PREFIX + 'keyboardIncrement'
MASTER_ID_LIB_KEY = GLYPHS_PREFIX + 'fontMasterID'
MASTER_ORDER_LIB_KEY = GLYPHS_PREFIX + 'fontMasterOrder'


def to_ufo_font_attributes(self, family_name):
    """Generate a list of UFOs with metadata loaded from .glyphs data.

    Modifies the list of UFOs in the UFOBuilder (self) in-place.
    """

    font = self.font

    # "date" can be missing; Glyphs.app removes it on saving if it's empty:
    # https://github.com/googlei18n/glyphsLib/issues/134
    date_created = getattr(font, 'date', None)
    if date_created is not None:
        date_created = to_ufo_time(date_created)
    units_per_em = font.upm
    version_major = font.versionMajor
    version_minor = font.versionMinor
    copyright = font.copyright
    designer = font.designer
    designer_url = font.designerURL
    manufacturer = font.manufacturer
    manufacturer_url = font.manufacturerURL
    glyph_order = list(glyph.name for glyph in font.glyphs)

    for index, master in enumerate(font.masters):
        ufo = self.ufo_module.Font()

        ufo.lib[APP_VERSION_LIB_KEY] = font.appVersion
        ufo.lib[KEYBOARD_INCREMENT_KEY] = font.keyboardIncrement

        if date_created is not None:
            ufo.info.openTypeHeadCreated = date_created
        ufo.info.unitsPerEm = units_per_em
        ufo.info.versionMajor = version_major
        ufo.info.versionMinor = version_minor

        if copyright:
            ufo.info.copyright = copyright
        if designer:
            ufo.info.openTypeNameDesigner = designer
        if designer_url:
            ufo.info.openTypeNameDesignerURL = designer_url
        if manufacturer:
            ufo.info.openTypeNameManufacturer = manufacturer
        if manufacturer_url:
            ufo.info.openTypeNameManufacturerURL = manufacturer_url

        ufo.info.ascender = master.ascender
        ufo.info.capHeight = master.capHeight
        ufo.info.descender = master.descender
        ufo.info.xHeight = master.xHeight

        horizontal_stems = master.horizontalStems
        vertical_stems = master.verticalStems
        italic_angle = -master.italicAngle
        if horizontal_stems:
            ufo.info.postscriptStemSnapH = horizontal_stems
        if vertical_stems:
            ufo.info.postscriptStemSnapV = vertical_stems
        if italic_angle:
            ufo.info.italicAngle = italic_angle

        width = master.width
        weight = master.weight
        if weight:
            ufo.lib[GLYPHS_PREFIX + 'weight'] = weight
        if width:
            ufo.lib[GLYPHS_PREFIX + 'width'] = width
        for number in ('', '1', '2', '3'):
            custom_name = getattr(master, 'customName' + number)
            if custom_name:
                ufo.lib[GLYPHS_PREFIX + 'customName' + number] = custom_name
            custom_value = getattr(master, 'customValue' + number)
            if custom_value:
                ufo.lib[GLYPHS_PREFIX + 'customValue' + number] = custom_value

        ufo.glyphOrder = glyph_order

        self.to_ufo_names(ufo, master, family_name)
        self.to_ufo_blue_values(ufo, master)
        self.to_ufo_family_user_data(ufo)
        self.to_ufo_master_user_data(ufo, master)
        self.to_ufo_guidelines(ufo, master)
        self.to_ufo_custom_params(ufo, master)

        master_id = master.id
        ufo.lib[MASTER_ID_LIB_KEY] = master_id
        ufo.lib[MASTER_ORDER_LIB_KEY] = index
        # FIXME: (jany) in the future, yield this UFO (for memory, lazy iter)
        self._ufos[master_id] = ufo


def to_glyphs_font_attributes(self, ufo, master, is_initial):
    """
    Copy font attributes from `ufo` either to `self.font` or to `master`.

    Arguments:
    self -- The UFOBuilder
    ufo -- The current UFO being read
    master -- The current master being written
    is_initial -- True iff this the first UFO that we process
    """
    # TODO: (jany) when is_initial, write to context.font without question
    #     but when !is_initial, compare the last context.font.whatever and
    #     what we would be writing, to guard against the info being
    #     modified in only one of the UFOs in a MM. Maybe do this check later,
    #     when the roundtrip without modification works.
    if is_initial:
        _set_glyphs_font_attributes(self, ufo)
    else:
        # self._compare_and_merge_glyphs_font_attributes(ufo)
        pass
    _set_glyphs_master_attributes(self, ufo, master)


def _set_glyphs_font_attributes(self, ufo):
    font = self.font
    info = ufo.info

    if APP_VERSION_LIB_KEY in ufo.lib:
        font.appVersion = ufo.lib[APP_VERSION_LIB_KEY]
    if KEYBOARD_INCREMENT_KEY in ufo.lib:
        font.keyboardIncrement = ufo.lib[KEYBOARD_INCREMENT_KEY]

    if info.openTypeHeadCreated is not None:
        # FIXME: (jany) should wrap in glyphs_datetime? or maybe the GSFont
        #     should wrap in glyphs_datetime if needed?
        font.date = from_ufo_time(info.openTypeHeadCreated)
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
    self.to_glyphs_family_user_data(ufo)
    self.to_glyphs_family_custom_params(ufo)
    self.to_glyphs_features(ufo)


def _set_glyphs_master_attributes(self, ufo, master):
    try:
        master.id = ufo.lib[MASTER_ID_LIB_KEY]
    except KeyError:
        pass

    master.ascender = ufo.info.ascender
    master.capHeight = ufo.info.capHeight
    master.descender = ufo.info.descender
    master.xHeight = ufo.info.xHeight

    horizontal_stems = ufo.info.postscriptStemSnapH
    vertical_stems = ufo.info.postscriptStemSnapV
    italic_angle = 0
    if ufo.info.italicAngle:
        italic_angle = -ufo.info.italicAngle
    if horizontal_stems:
        master.horizontalStems = horizontal_stems
    if vertical_stems:
        master.verticalStems = vertical_stems
    if italic_angle:
        master.italicAngle = italic_angle

    try:
        master.width = ufo.lib[GLYPHS_PREFIX + 'width']
    except KeyError:
        pass
    try:
        master.weight = ufo.lib[GLYPHS_PREFIX + 'weight']
    except KeyError:
        pass

    for number in ('', '1', '2', '3'):
        name_key = GLYPHS_PREFIX + 'customName' + number
        if name_key in ufo.lib:
            custom_name = ufo.lib[name_key]
            if custom_name:
                setattr(master, 'customName' + number, custom_name)
        value_key = GLYPHS_PREFIX + 'customValue' + number
        if value_key in ufo.lib:
            custom_value = ufo.lib[value_key]
            if custom_value:
                setattr(master, 'customValue' + number, custom_value)

    self.to_glyphs_blue_values(ufo, master)
    self.to_glyphs_master_names(ufo, master)
    self.to_glyphs_master_user_data(ufo, master)
    self.to_glyphs_guidelines(ufo, master)
    self.to_glyphs_master_custom_params(ufo, master)


def to_glyphs_ordered_masters(self):
    """Modify in-place the list of UFOs to restore their original order."""
    self.ufos = sorted(self.ufos, key=_original_master_order)


def _original_master_order(ufo):
    try:
        return ufo.lib[MASTER_ORDER_LIB_KEY]
    except:
        return float('infinity')
