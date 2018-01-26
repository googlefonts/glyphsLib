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

from collections import OrderedDict
import os

from glyphsLib.util import build_ufo_path
from glyphsLib.classes import WEIGHT_CODES
from .constants import (GLYPHS_PREFIX, GLYPHLIB_PREFIX,
                        FONT_CUSTOM_PARAM_PREFIX, MASTER_CUSTOM_PARAM_PREFIX)
from .names import build_stylemap_names
from .masters import UFO_FILENAME_KEY
from .axes import get_axis_definitions, is_instance_active, interp

EXPORT_KEY = GLYPHS_PREFIX + 'export'
WIDTH_KEY = GLYPHS_PREFIX + 'width'
WEIGHT_KEY = GLYPHS_PREFIX + 'weight'
FULL_FILENAME_KEY = GLYPHLIB_PREFIX + 'fullFilename'
MANUAL_INTERPOLATION_KEY = GLYPHS_PREFIX + 'manualInterpolation'
INSTANCE_INTERPOLATIONS_KEY = GLYPHS_PREFIX + 'intanceInterpolations'


def to_designspace_instances(self):
    """Write instance data from self.font to self.designspace."""
    for instance in self.font.instances:
        if is_instance_active(instance) or self.minimize_glyphs_diffs:
            _to_designspace_instance(self, instance)


def _to_designspace_instance(self, instance):
    ufo_instance = self.designspace.newInstanceDescriptor()
    # FIXME: (jany) most of these customParameters are actually attributes,
    # at least according to https://docu.glyphsapp.com/#fontName
    for p in instance.customParameters:
        param, value = p.name, p.value
        if param == 'familyName':
            ufo_instance.familyName = value
        elif param == 'postscriptFontName':
            # Glyphs uses "postscriptFontName", not "postScriptFontName"
            ufo_instance.postScriptFontName = value
        elif param == 'fileName':
            fname = value + '.ufo'
            if self.instance_dir is not None:
                fname = self.instance_dir + '/' + fname
            ufo_instance.filename = fname

    if ufo_instance.familyName is None:
        ufo_instance.familyName = self.family_name
    ufo_instance.styleName = instance.name

    # TODO: investigate the possibility of storing a relative path in the
    #   `filename` custom parameter. If yes, drop the key below.
    fname = instance.customParameters[FULL_FILENAME_KEY]
    if fname is not None:
        if self.instance_dir:
            fname = self.instance_dir + '/' + os.path.basename(fname)
        ufo_instance.filename = fname
    if not ufo_instance.filename:
        instance_dir = self.instance_dir or '.'
        ufo_instance.filename = build_ufo_path(
            instance_dir, ufo_instance.familyName, ufo_instance.styleName)

    location = {}
    for axis_def in get_axis_definitions(self.font):
        location[axis_def.name] = axis_def.get_design_loc(instance)
    ufo_instance.location = location

    # FIXME: (jany) should be the responsibility of ufo2ft?
    # Anyway, only generate the styleMap names if the Glyphs instance already
    # has a linkStyle set up, or if we're not round-tripping (i.e. generating
    # UFOs for fontmake, the traditional use-case of glyphsLib.)
    if instance.linkStyle or not self.minimize_glyphs_diffs:
        ufo_instance.styleMapFamilyName, ufo_instance.styleMapStyleName = \
            build_stylemap_names(
                family_name=ufo_instance.familyName,
                style_name=ufo_instance.styleName,
                is_bold=instance.isBold,
                is_italic=instance.isItalic,
                linked_style=instance.linkStyle,
            )

    ufo_instance.name = ' '.join((ufo_instance.familyName or '',
                                  ufo_instance.styleName or ''))

    if self.minimize_glyphs_diffs:
        ufo_instance.lib[EXPORT_KEY] = instance.active
        ufo_instance.lib[WEIGHT_KEY] = instance.weight
        ufo_instance.lib[WIDTH_KEY] = instance.width

        ufo_instance.lib[INSTANCE_INTERPOLATIONS_KEY] = instance.instanceInterpolations
        ufo_instance.lib[MANUAL_INTERPOLATION_KEY] = instance.manualInterpolation

    # TODO: put the userData/customParameters in lib
    self.designspace.addInstance(ufo_instance)


def to_glyphs_instances(self):
    if self.designspace is None:
        return

    for ufo_instance in self.designspace.instances:
        instance = self.glyphs_module.GSInstance()

        # TODO: lots of stuff!
        # active
        # name
        # weight
        # width
        # weightValue
        # widthValue
        # customValue
        # isItalic
        # isBold
        # linkStyle
        # familyName
        # preferredFamily
        # preferredSubfamilyName
        # windowsFamily
        # windowsStyle
        # windowsLinkedToStyle
        # fontName
        # fullName
        # customParameters
        # instanceInterpolations
        # manualInterpolation

        try:
            instance.active = ufo_instance.lib[EXPORT_KEY]
        except KeyError:
            # If not specified, the default is to export all instances
            instance.active = True

        instance.name = ufo_instance.styleName

        for axis_def in get_axis_definitions(self.font):
            design_loc = None
            try:
                design_loc = ufo_instance.location[axis_def.name]
                axis_def.set_design_loc(instance, design_loc)
            except KeyError:
                # The location does not have this axis?
                pass

            if axis_def.tag in ('wght', 'wdth'):
                # Retrieve the user location (weightClass/widthClass)
                # TODO: (jany) update comments
                # First way: for UFOs/designspace of other origins, read
                # the mapping backwards and check that the user location
                # matches the instance's weight/width. If not, set the the
                # custom param.
                user_loc = design_loc
                mapping = None
                for axis in self.designspace.axes:
                    if axis.tag == axis_def.tag:
                        mapping = axis.map
                if mapping:
                    reverse_mapping = [(dl, ul) for ul, dl in mapping]
                    user_loc = interp(reverse_mapping, design_loc)
                if user_loc is not None:
                    axis_def.set_user_loc(instance, user_loc)

        try:
            # Restore the original weightClass when there is an ambiguity based
            # on the value, e.g. Thin, ExtraLight, UltraLight all map to 250.
            # No problem with width, because 1:1 mapping in WIDTH_CODES.
            weight = ufo_instance.lib[WEIGHT_KEY]
            if (not instance.weight or
                    WEIGHT_CODES[instance.weight] == WEIGHT_CODES[weight]):
                instance.weight = weight
        except KeyError:
            # FIXME: what now
            pass

        try:
            if not instance.width:
                instance.width = ufo_instance.lib[WIDTH_KEY]
        except KeyError:
            # FIXME: what now
            pass

        if ufo_instance.familyName is not None:
            if ufo_instance.familyName != self.font.familyName:
                instance.familyName = ufo_instance.familyName

        smfn = ufo_instance.styleMapFamilyName
        if smfn is not None:
            if smfn.startswith(ufo_instance.familyName):
                smfn = smfn[len(ufo_instance.familyName):].strip()
            instance.linkStyle = smfn

        if ufo_instance.styleMapStyleName is not None:
            style = ufo_instance.styleMapStyleName
            instance.isBold = ('bold' in style)
            instance.isItalic = ('italic' in style)

        if ufo_instance.postScriptFontName is not None:
            instance.fontName = ufo_instance.postScriptFontName

        try:
            instance.manualInterpolation = ufo_instance.lib[
                MANUAL_INTERPOLATION_KEY]
        except KeyError:
            pass

        try:
            instance.instanceInterpolations = ufo_instance.lib[
                INSTANCE_INTERPOLATIONS_KEY]
        except KeyError:
            # TODO: (jany) compute instanceInterpolations from the location
            # if instance.manualInterpolation: warn about data loss
            pass

        if self.minimize_ufo_diffs:
            instance.customParameters[
                FULL_FILENAME_KEY] = ufo_instance.filename

        # FIXME: (jany) cannot `.append()` because no proxy => no parent
        self.font.instances = self.font.instances + [instance]
