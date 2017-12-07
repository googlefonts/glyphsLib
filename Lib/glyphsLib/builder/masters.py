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

import uuid
import os

from .constants import GLYPHS_PREFIX, GLYPHLIB_PREFIX

MASTER_ID_LIB_KEY = GLYPHS_PREFIX + 'fontMasterID'
UFO_FILENAME_KEY = GLYPHLIB_PREFIX + 'ufoFilename'


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
    if italic_angle:
        ufo.info.italicAngle = italic_angle

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


def to_glyphs_master_attributes(self, ufo, master):
    try:
        master.id = ufo.lib[MASTER_ID_LIB_KEY]
    except KeyError:
        master.id = str(uuid.uuid4())

    if ufo.path and self.minimize_ufo_diffs:
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

    # Retrieve the master locations: weight, width, custom 0 - 1 - 2 - 3
    source = _get_designspace_source_for_ufo(self, ufo)
    for axis in ['weight', 'width']:
        # First, try the designspace
        try:
            # TODO: ??? name = source.lib[...]
            # setattr(master, axis, name)
            raise KeyError
        except KeyError:
            # Second, try the custom key
            try:
                setattr(master, axis, ufo.lib[GLYPHS_PREFIX + axis])
            except KeyError:
                # FIXME: (jany) as last resort, use 400/700 as a location,
                #   from the weightClass/widthClass?
                pass

        value_key = axis + 'Value'
        # First, try the designspace
        try:
            loc = source.location[axis]
            setattr(master, value_key, loc)
        except KeyError:
            # Second, try the custom key
            try:
                setattr(master, value_key, ufo.lib[GLYPHS_PREFIX + value_key])
            except KeyError:
                # FIXME: (jany) as last resort, use 400/700 as a location,
                #   from the weightClass/widthClass?
                pass

    for number in ('', '1', '2', '3'):
        # For the custom locations, we need both the name and the value
        # FIXME: (jany) not sure it's worth implementing if everything is going
        # to change soon on Glyphs.app's side.
        pass
        # try:
        #     axis = 'custom' + number
        #     value_key = 'customValue' + number
        #     loc = source.location[axis]
        #     value_key = axis + 'Value'
        #     if axis.startswith('custom'):
        #     setattr(instance, value_key, loc)
        # except KeyError:
        #     pass

        # name_key = GLYPHS_PREFIX + 'customName' + number
        # if name_key in ufo.lib:
        #     custom_name = ufo.lib[name_key]
        #     if custom_name:
        #         setattr(master, 'customName' + number, custom_name)
        # value_key = GLYPHS_PREFIX + 'customValue' + number
        # if value_key in ufo.lib:
        #     custom_value = ufo.lib[value_key]
        #     if custom_value:
        #         setattr(master, 'customValue' + number, custom_value)

    self.to_glyphs_blue_values(ufo, master)
    self.to_glyphs_master_names(ufo, master)
    self.to_glyphs_master_user_data(ufo, master)
    self.to_glyphs_guidelines(ufo, master)
    self.to_glyphs_custom_params(ufo, master)


def _get_designspace_source_for_ufo(self, ufo):
    for source in self.designspace.sources:
        if source.font == ufo:
            return source
