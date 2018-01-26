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

import os
from collections import OrderedDict

from .constants import GLYPHS_PREFIX, GLYPHLIB_PREFIX

MASTER_ID_LIB_KEY = GLYPHS_PREFIX + 'fontMasterID'
UFO_FILENAME_KEY = GLYPHLIB_PREFIX + 'ufoFilename'
UFO_YEAR_KEY = GLYPHLIB_PREFIX + 'ufoYear'
UFO_TRADEMARK_KEY = GLYPHLIB_PREFIX + 'ufoTrademark'
UFO_NOTE_KEY = GLYPHLIB_PREFIX + 'ufoNote'


def to_ufo_master_attributes(self, source, master):
    ufo = source.font
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

    year = master.userData[UFO_YEAR_KEY]
    if year is not None:
        ufo.info.year = year
    trademark = master.userData[UFO_TRADEMARK_KEY]
    if trademark is not None:
        ufo.info.trademark = trademark
    note = master.userData[UFO_NOTE_KEY]
    if note is not None:
        ufo.info.note = note

    # All of this will go into the designspace as well
    # "Native" designspace fonts will only have the designspace info
    # FIXME: (jany) maybe we should not duplicate the information and only
    # write it in the designspace?
    width = master.width
    widthValue = master.widthValue
    weight = master.weight
    weightValue = master.weightValue
    if weight:
        ufo.lib[GLYPHS_PREFIX + 'weight'] = weight
    if weightValue is not None:
        ufo.lib[GLYPHS_PREFIX + 'weightValue'] = weightValue
    if width:
        ufo.lib[GLYPHS_PREFIX + 'width'] = width
    if widthValue:
        ufo.lib[GLYPHS_PREFIX + 'widthValue'] = widthValue
    for number in ('', '1', '2', '3'):
        custom_name = getattr(master, 'customName' + number)
        if custom_name:
            ufo.lib[GLYPHS_PREFIX + 'customName' + number] = custom_name
        custom_value = getattr(master, 'customValue' + number)
        if custom_value:
            ufo.lib[GLYPHS_PREFIX + 'customValue' + number] = custom_value

    self.to_ufo_blue_values(ufo, master)
    self.to_ufo_guidelines(ufo, master)
    self.to_ufo_master_user_data(ufo, master)
    self.to_ufo_custom_params(ufo, master)

    master_id = master.id
    if self.minimize_glyphs_diffs:
        ufo.lib[MASTER_ID_LIB_KEY] = master_id


def to_glyphs_master_attributes(self, source, master):
    ufo = source.font
    try:
        master.id = ufo.lib[MASTER_ID_LIB_KEY]
    except KeyError:
        # GSFontMaster has a random id by default
        pass

    if source.filename is not None and self.minimize_ufo_diffs:
        master.userData[UFO_FILENAME_KEY] = source.filename
    elif ufo.path and self.minimize_ufo_diffs:
        master.userData[UFO_FILENAME_KEY] = os.path.basename(ufo.path)

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

    if ufo.info.year is not None:
        master.userData[UFO_YEAR_KEY] = ufo.info.year
    if ufo.info.trademark is not None:
        master.userData[UFO_TRADEMARK_KEY] = ufo.info.trademark
    if ufo.info.note is not None:
        master.userData[UFO_NOTE_KEY] = ufo.info.note

    self.to_glyphs_blue_values(ufo, master)
    self.to_glyphs_master_names(ufo, master)
    self.to_glyphs_master_user_data(ufo, master)
    self.to_glyphs_guidelines(ufo, master)
    self.to_glyphs_custom_params(ufo, master)
