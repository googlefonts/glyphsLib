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

from .common import to_ufo_time
from .constants import GLYPHS_PREFIX

logger = logging.getLogger(__name__)


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

    for master in font.masters:
        ufo = self.ufo_module.Font()

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

        self.to_ufo_names(ufo, master, family_name)
        self.to_ufo_blue_values(ufo, master)
        self.to_ufo_family_user_data(ufo)
        self.to_ufo_master_user_data(ufo, master)
        self.to_ufo_guidelines(ufo, master)
        self.to_ufo_custom_params(ufo, master)

        master_id = master.id
        ufo.lib[GLYPHS_PREFIX + 'fontMasterID'] = master_id
        # FIXME: (jany) in the future, yield this UFO (for memory, laze iter)
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
    master.id = ufo.lib[GLYPHS_PREFIX + 'fontMasterID']
    # TODO: all the other attributes
