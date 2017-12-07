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

from glyphsLib.util import build_ufo_path
from .constants import (GLYPHS_PREFIX, GLYPHLIB_PREFIX,
                        FONT_CUSTOM_PARAM_PREFIX, MASTER_CUSTOM_PARAM_PREFIX)
from .names import build_stylemap_names
from .masters import UFO_FILENAME_KEY

EXPORT_KEY = GLYPHS_PREFIX + 'export'
WIDTH_KEY = GLYPHS_PREFIX + 'width'
WEIGHT_KEY = GLYPHS_PREFIX + 'weight'
WEIGHT_CLASS_KEY = GLYPHS_PREFIX + 'weightClass'
WIDTH_CLASS_KEY = GLYPHS_PREFIX + 'widthClass'
MANUAL_INTERPOLATION_KEY = GLYPHS_PREFIX + 'manualInterpolation'
INSTANCE_INTERPOLATIONS_KEY = GLYPHS_PREFIX + 'intanceInterpolations'


def to_designspace_instances(self):
    """Write instance data from self.font to self.designspace."""

    # base_family = masters[0].info.familyName
    # assert all(m.info.familyName == base_family for m in masters), \
    #     'Masters must all have same family'

    # for font in masters:
    #     write_ufo(font, master_dir)

    # needed so that added masters and instances have correct relative paths
    # tmp_path = os.path.join(master_dir, 'tmp.designspace')
    # writer = DesignSpaceDocumentWriter(tmp_path)

    # instances = list(filter(is_instance_active, instance_data.get('data', [])))
    ufo_masters = list(self.masters)
    if ufo_masters:
        varfont_origin = _get_varfont_origin(ufo_masters)
        regular = _find_regular_master(ufo_masters, regularName=varfont_origin)
        _to_designspace_axes(self, regular)
        _to_designspace_sources(self, regular)

    for instance in self.font.instances:
        _to_designspace_instance(self, instance)


def _get_varfont_origin(masters):
    # the 'Variation Font Origin' is a font-wide custom parameter, thus it is
    # shared by all the master ufos; here we just get it from the first one
    assert len(masters) > 0
    varfont_origin_key = "Variation Font Origin"
    return masters[0].lib.get(FONT_CUSTOM_PARAM_PREFIX + varfont_origin_key)


def _find_regular_master(masters, regularName=None):
    """Find the "regular" master among the master UFOs.

    Tries to find the master with the passed 'regularName'.
    If there is no such master or if regularName is None,
    tries to find a base style shared between all masters
    (defaulting to "Regular"), and then tries to find a master
    with that style name. If there is no master with that name,
    returns the first master in the list.
    """
    assert len(masters) > 0
    if regularName is not None:
        for font in masters:
            if font.info.styleName == regularName:
                return font
    base_style = find_base_style(masters)
    if not base_style:
        base_style = 'Regular'
    for font in masters:
        if font.info.styleName == base_style:
            return font
    return masters[0]


def find_base_style(masters):
    """Find a base style shared between all masters.
    Return empty string if none is found.
    """
    base_style = masters[0].info.styleName.split()
    for font in masters:
        style = font.info.styleName.split()
        base_style = [s for s in style if s in base_style]
    base_style = ' '.join(base_style)
    return base_style


# Glyphs.app's default values for the masters' {weight,width,custom}Value
# and for the instances' interpolation{Weight,Width,Custom} properties.
# When these values are set, they are omitted from the .glyphs source file.
# FIXME: (jany) This behaviour should be in classes.py
DEFAULT_LOCS = {
    'weight': 100,
    'width': 100,
    'custom': 0,
    'custom1': 0,
    'custom2': 0,
    'custom3': 0,
}

WEIGHT_CODES = {
    'Thin': 250,
    'ExtraLight': 250,
    'UltraLight': 250,
    'Light': 300,
    None: 400,  # default value normally omitted in source
    'Normal': 400,
    'Regular': 400,
    'Medium': 500,
    'DemiBold': 600,
    'SemiBold': 600,
    'Bold': 700,
    'UltraBold': 800,
    'ExtraBold': 800,
    'Black': 900,
    'Heavy': 900,
}

WIDTH_CODES = {
    'Ultra Condensed': 1,
    'Extra Condensed': 2,
    'Condensed': 3,
    'SemiCondensed': 4,
    None: 5,  # default value normally omitted in source
    'Medium (normal)': 5,
    'Semi Expanded': 6,
    'Expanded': 7,
    'Extra Expanded': 8,
    'Ultra Expanded': 9,
}


def _to_designspace_axes(self, regular_master):
    # According to Georg Seifert, Glyphs 3 will have a better model
    # for describing variation axes.  The plan is to store the axis
    # information globally in the Glyphs file. In addition to actual
    # variation axes, this new structure will probably also contain
    # stylistic information for design axes that are not variable but
    # should still be stored into the OpenType STAT table.
    #
    # We currently take the minima and maxima from the instances, and
    # have hard-coded the default value for each axis.  We could be
    # smarter: for the minima and maxima, we could look at the masters
    # (whose locations are only stored in interpolation space, not in
    # user space) and reverse-interpolate these locations to user space.
    # Likewise, we could try to infer the default axis value from the
    # masters. But it's probably not worth this effort, given that
    # the upcoming version of Glyphs is going to store explicit
    # axis desriptions in its file format.

    # FIXME: (jany) find interpolation data in GSFontMaster rather than in UFO?
    # It would allow to drop the DEFAULT_LOCS dictionary
    masters = list(self.masters)
    instances = self.font.instances

    for name, tag, userLocParam, defaultUserLoc, codes in (
            ('weight', 'wght', 'weightClass', 400, WEIGHT_CODES),
            ('width', 'wdth', 'widthClass', 100, WIDTH_CODES),
            ('custom', 'XXXX', None, 0, None),
            ('custom1', 'XXX1', None, 0, None),
            ('custom2', 'XXX2', None, 0, None),
            ('custom3', 'XXX3', None, 0, None)):
        key = MASTER_CUSTOM_PARAM_PREFIX + name + 'Value'
        if name.startswith('custom'):
            key = MASTER_CUSTOM_PARAM_PREFIX + 'customValue' + name[len('custom'):]
        if any(key in master.lib for master in masters):
            axis = self.designspace.newAxisDescriptor()
            axis.tag = tag
            axis.name = name
            regularInterpolLoc = regular_master.lib.get(key, DEFAULT_LOCS[name])
            regularUserLoc = defaultUserLoc

            labelName = name.title()
            if name.startswith('custom'):
                name_key = MASTER_CUSTOM_PARAM_PREFIX + 'customName' + name[len('custom'):]
                for master in masters:
                    if name_key in master.lib:
                        labelName = master.lib[name_key]
                        break
            axis.labelNames = {"en": labelName}

            interpolLocKey = name + 'Value'
            if name.startswith('custom'):
                interpolLocKey = 'customValue' + name[len('custom'):]
            mapping = []
            for instance in instances:
                interpolLoc = getattr(instance, interpolLocKey)
                userLoc = interpolLoc
                if userLocParam in instance.customParameters:
                    userLoc = float(instance.customParameters[userLocParam])
                elif (codes is not None and getattr(instance, name) and
                        getattr(instance, name) in codes):
                    userLoc = codes[getattr(instance, name)]
                mapping.append((userLoc, interpolLoc))
                if interpolLoc == regularInterpolLoc:
                    regularUserLoc = userLoc
            mapping = sorted(set(mapping))  # avoid duplicates
            if mapping:
                axis.minimum = min([userLoc for userLoc, _ in mapping])
                axis.maximum = max([userLoc for userLoc, _ in mapping])
                axis.default = min(axis.maximum, max(axis.minimum, regularUserLoc))  # clamp
            else:
                axis.minimum = axis.maximum = axis.default = defaultUserLoc
            axis.map = mapping
            self.designspace.addAxis(axis)


def _to_designspace_sources(self, regular):
    """Add master UFOs to the designspace document."""
    # FIXME: (jany) maybe read data from the GSFontMasters directly?
    for master, font in zip(self.font.masters, self.masters):
        source = self.designspace.newSourceDescriptor()
        source.font = font
        source.familyName = font.info.familyName
        source.styleName = font.info.styleName
        source.name = '%s %s' % (source.familyName, source.styleName)
        if UFO_FILENAME_KEY in master.userData:
            source.filename = master.userData[UFO_FILENAME_KEY]
        else:
            source.filename = build_ufo_path('.', source.familyName,
                                             source.styleName)

        # MutatorMath.DesignSpaceDocumentWriter iterates over the location
        # dictionary, which is non-deterministic so it can cause test failures.
        # We therefore use an OrderedDict to which we insert in axis order.
        # Since glyphsLib will switch to DesignSpaceDocument once that is
        # integrated into fonttools, it's not worth fixing upstream.
        # https://github.com/googlei18n/glyphsLib/issues/165
        # FIXME: (jany) still needed?
        location = OrderedDict()
        for axis in self.designspace.axes:
            value_key = axis.name + 'Value'
            if axis.name.startswith('custom'):
                # FIXME: (jany) this is getting boring
                value_key = 'customValue' + axis.name[len('custom'):]
            location[axis.name] = font.lib.get(
                MASTER_CUSTOM_PARAM_PREFIX + value_key, DEFAULT_LOCS[axis.name])
        source.location = location
        if font is regular:
            source.copyLib = True
            source.copyInfo = True
            source.copyGroups = True
            source.copyFeatures = True
        self.designspace.addSource(source)


def _to_designspace_instance(self, instance):
    ufo_instance = self.designspace.newInstanceDescriptor()
    for p in instance.customParameters:
        param, value = p.name, p.value
        if param == 'familyName':
            ufo_instance.familyName = value
        elif param == 'postscriptFontName':
            # Glyphs uses "postscriptFontName", not "postScriptFontName"
            ufo_instance.postScriptFontName = value
        elif param == 'fileName':
            ufo_instance.filename = value + '.ufo'
    if ufo_instance.familyName is None:
        ufo_instance.familyName = self.family_name

    ufo_instance.styleName = instance.name
    if not ufo_instance.filename:
        ufo_instance.filename = build_ufo_path('.', ufo_instance.familyName,
                                               ufo_instance.styleName)
    # ofiles.append((ufo_path, instance))
    # MutatorMath.DesignSpaceDocumentWriter iterates over the location
    # dictionary, which is non-deterministic so it can cause test failures.
    # We therefore use an OrderedDict to which we insert in axis order.
    # Since glyphsLib will switch to DesignSpaceDocument once that is
    # integrated into fonttools, it's not worth fixing upstream.
    # https://github.com/googlei18n/glyphsLib/issues/165
    # FIXME: (jany) still needed?
    location = OrderedDict()
    # FIXME: (jany) make a function for iterating axes and the related properties?
    for axis in self.designspace.axes:
        value_key = axis.name + 'Value'
        if axis.name.startswith('custom'):
            value_key = 'customValue' + axis.name[len('custom'):]
        location[axis.name] = getattr(instance, value_key)

    ufo_instance.location = location

    ufo_instance.styleMapFamilyName, ufo_instance.styleMapStyleName = \
        build_stylemap_names(
            family_name=ufo_instance.familyName,
            style_name=ufo_instance.styleName,
            is_bold=instance.isBold,
            is_italic=instance.isItalic,
            linked_style=instance.linkStyle,
        )

    ufo_instance.name = ' '.join((ufo_instance.familyName,
                                  ufo_instance.styleName))

    ufo_instance.lib[EXPORT_KEY] = instance.active
    ufo_instance.lib[WEIGHT_KEY] = instance.weight
    ufo_instance.lib[WIDTH_KEY] = instance.width

    if 'weightClass' in instance.customParameters:
        ufo_instance.lib[WEIGHT_CLASS_KEY] = instance.customParameters['weightClass']
    if 'widthClass' in instance.customParameters:
        ufo_instance.lib[WIDTH_CLASS_KEY] = instance.customParameters['widthClass']

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

        try:
            instance.weight = ufo_instance.lib[WEIGHT_KEY]
        except KeyError:
            # FIXME: what now
            pass

        try:
            instance.width = ufo_instance.lib[WIDTH_KEY]
        except KeyError:
            # FIXME: what now
            pass

        for axis in [
                'weight', 'width', 'custom', 'custom1', 'custom2', 'custom3']:
            # Retrieve the interpolation location
            try:
                loc = ufo_instance.location[axis]
                value_key = axis + 'Value'
                if axis.startswith('custom'):
                    value_key = 'customValue' + axis[len('custom'):]
                setattr(instance, value_key, loc)
            except KeyError:
                # FIXME: (jany) what now?
                pass

        for axis, lib_key in [('weight', WEIGHT_CLASS_KEY),
                              ('width', WIDTH_CLASS_KEY)]:
            # Retrieve the user location (weightClass/widthClass)
            try:
                # First way: for round-tripped data, read the glyphsLib key
                instance.customParameters[axis + 'Class'] = ufo_instance.lib[
                    lib_key]
            except KeyError:
                # Second way: for UFOs/designspace of other origins, read the
                #   mapping backwards and check that the user location matches
                #   the instance's weight/width. If not, set the the custom param.
                # TODO: (jany)
                pass

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

        self.font.instances.append(instance)
