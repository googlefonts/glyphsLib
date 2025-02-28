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

from .constants import (
    GLYPHS_PREFIX,
    MASTER_ID_LIB_KEY,
    UFO_YEAR_KEY,
    UFO_NOTE_KEY,
    UFO_FILENAME_CUSTOM_PARAM,
)
from glyphsLib.classes import (
    GSMetric,
    GSMetricValue,
    GSMetricsKeyItalicAngle,
)
from glyphsLib.util import best_repr  # , best_repr_list

# from glyphsLib.classes import GSCustomParameter


def to_ufo_master_attributes(self, ufo, master):  # noqa: C901
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
        del userData[UFO_YEAR_KEY]
    note = userData.get(UFO_NOTE_KEY)
    if note is not None:
        ufo.info.note = note
        del userData[UFO_NOTE_KEY]
    # All of this will also be in the designspace, Just to be sure we store it here to
    # TODO: (gs) do we really need this
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

    filteredMetrics = []
    for metric in master.font.metrics:
        if not metric.filter:
            continue
        metricValue = master.metricValues.get(metric.id)
        if not metricValue:
            continue

        filteredMetric = {
            "type": metric.type,
            "filter": metric.filter,
        }
        if metricValue.position:
            filteredMetric["pos"] = metricValue.position
        if metric.type != GSMetricsKeyItalicAngle and metricValue.overshoot:
            filteredMetric["over"] = metricValue.overshoot
        if metric.name:
            filteredMetric["name"] = metric.name
        filteredMetrics.append(filteredMetric)
    if filteredMetrics:
        ufo.lib[GLYPHS_PREFIX + "filteredMetrics"] = filteredMetrics

    if len(master.font.numbers) > 0:
        numberDicts = []
        for number in master.font.numbers:
            numberValue = master.numbers[number.id]
            numberDict = {
                "name": number.name,
                "value": numberValue,
            }
            numberDicts.append(numberDict)
        ufo.lib[GLYPHS_PREFIX + "numbers"] = numberDicts

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
    # if custom_params:
    #     ufo.lib[GLYPHS_PREFIX + "fontMaster.customParameters"] = custom_params
    self.to_ufo_blue_values(ufo, master)
    self.to_ufo_guidelines(ufo, master)
    self.to_ufo_master_user_data(ufo, userData)
    # Note: master's custom parameters will be applied later on, after glyphs and
    # features have been generated (see UFOBuilder::masters method).
    if self.minimize_glyphs_diffs:
        ufo.lib[MASTER_ID_LIB_KEY] = master.id


def to_glyphs_master_attributes(self, source, master):  # noqa: C901
    ufo = source.font

    # Glyphs ensures that the master ID is unique by simply making up a new one when
    # finding a duplicate.
    ufo_master_id_lib_key = ufo.lib.get(MASTER_ID_LIB_KEY)
    if ufo_master_id_lib_key and not self.font.masters[ufo_master_id_lib_key]:
        master.id = ufo_master_id_lib_key

    if source.filename is not None and self.minimize_ufo_diffs:
        master.customParameters[UFO_FILENAME_CUSTOM_PARAM] = source.filename
    elif ufo.path and self.minimize_ufo_diffs:
        # Don't be smart, we don't know where the UFOs come from, so we can't make them
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
    filteredMetrics = ufo.lib.get(GLYPHS_PREFIX + "filteredMetrics")
    if filteredMetrics:
        for metricDict in filteredMetrics:
            metric = self._font.metricFor(metricDict["type"], name=metricDict.get("name"), filter=metricDict["filter"], add_if_missing=True)
            metricValue = GSMetricValue(position=metricDict.get("pos"), overshoot=metricDict.get("over"))
            master.metricValues[metric.id] = metricValue
            metricValue.metric = metric
        metric = self._font.metricFor("italic angle", name=None, filter=None, add_if_missing=False)
        if metric:
            self._font.metrics.remove(metric)
            self._font.metrics.append(metric)

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

    numberDicts = ufo.lib.get(GLYPHS_PREFIX + "numbers")
    if numberDicts and isinstance(numberDicts, list):
        numberValues = []
        for numberDict in numberDicts:
            number = self.font.numberForName(numberDict["name"])
            if not number:
                number = GSMetric(numberDict["name"])
                self.font.numbers.append(number)
            numberValues.append(numberDict["value"])
        master._numbers = numberValues

    if ufo.info.year is not None:
        master.userData[UFO_YEAR_KEY] = ufo.info.year
    if ufo.info.note is not None and self._font.note != ufo.info.note:
        master.userData[UFO_NOTE_KEY] = ufo.info.note

    self.to_glyphs_blue_values(ufo, master)
    self.to_glyphs_master_names(ufo, master)
    self.to_glyphs_master_user_data(ufo, master)
    self.to_glyphs_guidelines(ufo, master)
    self.to_glyphs_custom_params(ufo, master, "fontMaster")
    if source.styleName:
        master.name = source.styleName

    if GLYPHS_PREFIX + "visible" in ufo.lib:
        master.visible = ufo.lib[GLYPHS_PREFIX + "visible"]
