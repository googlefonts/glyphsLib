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


import os

from .axes import font_uses_axis_locations
from .constants import (
    GLYPHS_PREFIX,
    MASTER_ID_LIB_KEY,
    UFO_YEAR_KEY,
    UFO_NOTE_KEY,
    UFO_FILENAME_CUSTOM_PARAM,
)
from glyphsLib.util import best_repr, best_repr_list


def to_ufo_master_attributes(self, ufo, master):
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
    if italic_angle is not None:
        ufo.info.italicAngle = best_repr(italic_angle)
    
    userData = dict(master.userData)
    year = userData.get(UFO_YEAR_KEY)
    if year is not None:
        ufo.info.year = year
        del(userData[UFO_YEAR_KEY])
    note = userData.get(UFO_NOTE_KEY)
    if note is not None:
        ufo.info.note = note
        delf(userData[UFO_NOTE_KEY])
    # All of this will go into the designspace as well
    # "Native" designspace fonts will only have the designspace info
    if master.font.formatVersion >= 3:
        axesValues = []
        axes = []
        for axis in master.font.axes:
            value = master.internalAxesValues[axis.axisId]
            axesValues.append(value)
            axesDict = {"name": axis.name, "tag": axis.axisTag}
            if axis.hidden:
                axesDict["hidden"] = True
            axes.append(axesDict)
        if axes and axesValues:
            ufo.lib[GLYPHS_PREFIX + "axes"] = axes
            ufo.lib[GLYPHS_PREFIX + "axesValues"] = axesValues
    else:
        legacyNames = [
            "weightValue",
            "widthValue",
            "customValue",
            "customValue1",
            "customValue2",
            "customValue3",
        ]
        idx = -1
        for axis in master.font.axes:
            idx += 1
            value = master.internalAxesValues[axis.axisId]
            lib_key = legacyNames[idx]
            if master._defaultsForName[lib_key] == value:
                continue
            ufo.lib[GLYPHS_PREFIX + lib_key] = value

    if font_uses_axis_locations(self.font):
        # Set the OS/2 weightClass and widthClas according the this master's
        # user location ("Axis Location" parameter)
        for axis in self.font.axes:
            if axis.axisTag in ("wght", "wdth"):
                user_loc = get_user_loc(master, axis)
                axis.set_ufo_user_loc(ufo, user_loc)

    # Set vhea values to glyphsapp defaults if they haven't been declared.
    # ufo2ft needs these set in order for a ufo to be recognised as
    # vertical. Glyphsapp uses the font upm, not the typo metrics
    # for these.
    custom_params = list(master.customParameters)
    if self.is_vertical:

        font_upm = self.font.upm
        if not any(
            k in custom_params for k in ("vheaVertAscender", "vheaVertTypoAscender")
        ):
            ufo.info.openTypeVheaVertTypoAscender = int(font_upm / 2)
        if not any(
            k in custom_params for k in ("vheaVertDescender", "vheaVertTypoDescender")
        ):
            ufo.info.openTypeVheaVertTypoDescender = -int(font_upm / 2)
        if not any(
            k in custom_params for k in ("vheaVertLineGap", "vheaVertTypoLineGap")
        ):
            ufo.info.openTypeVheaVertTypoLineGap = font_upm
    if custom_params:
        ufo.lib[GLYPHS_PREFIX + "fontMaster.customParameters"] = custom_params
    self.to_ufo_blue_values(ufo, master)
    self.to_ufo_guidelines(ufo, master)
    self.to_ufo_master_user_data(ufo, userData)
    # Note: master's custom parameters will be applied later on, after glyphs and
    # features have been generated (see UFOBuilder::masters method).

    master_id = master.id
    if self.minimize_glyphs_diffs:
        ufo.lib[MASTER_ID_LIB_KEY] = master_id


def to_glyphs_master_attributes(self, source, master):
    ufo = source.font

    # Glyphs ensures that the master ID is unique by simply making up a new one when
    # finding a duplicate.
    ufo_master_id_lib_key = ufo.lib.get(MASTER_ID_LIB_KEY)
    if ufo_master_id_lib_key and not self.font.masters[ufo_master_id_lib_key]:
        master.id = ufo_master_id_lib_key

    if source.filename is not None and self.minimize_ufo_diffs:
        master.customParameters[UFO_FILENAME_CUSTOM_PARAM] = source.filename
    elif ufo.path and self.minimize_ufo_diffs:
        # Don't be smart, we don't know where the UFOs come from so we can't make them
        # relative to anything.
        master.customParameters[UFO_FILENAME_CUSTOM_PARAM] = os.path.basename(ufo.path)

    if ufo.info.ascender is not None:
        master.ascender = ufo.info.ascender
    if ufo.info.capHeight is not None:
        master.capHeight = ufo.info.capHeight
    if ufo.info.descender is not None:
        master.descender = ufo.info.descender
    if ufo.info.xHeight is not None:
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
    if ufo.info.note is not None:
        master.userData[UFO_NOTE_KEY] = ufo.info.note

    self.to_glyphs_blue_values(ufo, master)
    self.to_glyphs_master_names(ufo, master)
    self.to_glyphs_master_user_data(ufo, master)
    self.to_glyphs_guidelines(ufo, master)
    self.to_glyphs_custom_params(ufo, master)
