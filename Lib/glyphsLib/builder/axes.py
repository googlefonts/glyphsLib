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

from glyphsLib import classes
from glyphsLib.classes import WEIGHT_CODES, WIDTH_CODES
from .constants import (GLYPHS_PREFIX, GLYPHLIB_PREFIX,
                        FONT_CUSTOM_PARAM_PREFIX, MASTER_CUSTOM_PARAM_PREFIX)

# This is a key into GSFont.userData to store axes defined in the designspace
AXES_KEY = GLYPHLIB_PREFIX + 'axes'

# From the spec: https://www.microsoft.com/typography/otspec/os2.htm#wtc
CLASSES_DICT = {
    'wght': {
        100: ('Thin', 100),
        200: ('Extra-light', 200),
        300: ('Light', 300),
        400: ('Regular', 400),
        500: ('Medium', 500),
        600: ('Semi-bold', 600),
        700: ('Bold', 700),
        800: ('Extra-bold', 800),
        900: ('Black', 900),
    },
    'wdth': {
        1: ('Ultra-condensed', 50),
        2: ('Extra-condensed', 62.5),
        3: ('Condensed', 75),
        4: ('Semi-condensed', 87.5),
        5: ('Medium', 100),
        6: ('Semi-expanded', 112.5),
        7: ('Expanded', 125),
        8: ('Extra-expanded', 150),
        9: ('Ultra-expanded', 200),
    }
}


def class_to_name(axis, ufo_class):
    """
    >>> class_to_name('wdth', 7)
    'Expanded'
    """
    return CLASSES_DICT[axis][int(ufo_class)][0]


def class_to_value(axis, ufo_class):
    """
    >>> class_to_value('wdth', 7)
    125
    """
    if axis == 'wght':
        # 600.0 => 600, 250 => 250
        return int(ufo_class)
    return CLASSES_DICT[axis][int(ufo_class)][1]


def user_loc_code_to_value(axis_tag, user_loc):
    """ Go from Glyphs UI strings to user space location.

    >>> user_loc_code_to_value('wght', 'ExtraLight')
    250
    >>> user_loc_code_to_value('wdth', 'SemiCondensed')
    87.5
    """
    if axis_tag == 'wght':
        return class_to_value('wght', WEIGHT_CODES.get(user_loc, user_loc))
    if axis_tag == 'wdth':
        return class_to_value('wdth', WIDTH_CODES.get(user_loc, user_loc))

    # Currently this function should only be called with a width or weight
    raise NotImplementedError


def user_loc_value_to_class(axis_tag, user_loc):
    """
    >>> user_loc_value_to_class('wdth', 62)
    2
    """
    if axis_tag == 'wght':
        return int(user_loc)
    return min(sorted(CLASSES_DICT[axis_tag].items()),
               key=lambda item: abs(item[1][1] - user_loc))[0]


def user_loc_value_to_code(axis_tag, user_loc):
    """
    >>> user_loc_value_to_code('wdth', 150)
    'Extra Expanded'
    """
    codes = {}
    if axis_tag == 'wght':
        codes = WEIGHT_CODES
    elif axis_tag == 'wdth':
        codes = WIDTH_CODES
    else:
        raise NotImplementedError
    class_ = user_loc_value_to_class(axis_tag, user_loc)
    return min(sorted((code, class_) for code, class_ in codes.items()
                      if code is not None),
               key=lambda item: abs(item[1] - class_))[0]


def to_designspace_axes(self):
    if not self.font.masters:
        return
    regular_master = get_regular_master(self.font)
    assert isinstance(regular_master, classes.GSFontMaster)

    for axis_def in get_axis_definitions(self.font):
        axis = self.designspace.newAxisDescriptor()
        axis.tag = axis_def.tag
        axis.name = axis_def.name

        regularDesignLoc = axis_def.get_design_loc(regular_master)
        regularUserLoc = axis_def.get_user_loc(regular_master)

        axis.labelNames = {"en": axis_def.name}
        instance_mapping = []
        for instance in self.font.instances:
            if is_instance_active(instance) or self.minimize_glyphs_diffs:
                designLoc = axis_def.get_design_loc(instance)
                userLoc = axis_def.get_user_loc(instance)
                instance_mapping.append((userLoc, designLoc))

                # FIXME: (jany) why the next two lines?
                if designLoc == regularDesignLoc:
                    regularUserLoc = userLoc
        instance_mapping = sorted(set(instance_mapping))  # avoid duplicates

        master_mapping = []
        for master in self.font.masters:
            designLoc = axis_def.get_design_loc(master)
            # FIXME: (jany) in latest Glyphs (1113) masters don't have
            # a user loc
            userLoc = axis_def.get_user_loc(master)
            master_mapping.append((userLoc, designLoc))
        master_mapping = sorted(set(master_mapping))

        minimum = maximum = default = axis_def.default_user_loc
        # Prefer the instance-based mapping
        mapping = instance_mapping or master_mapping
        if mapping:
            minimum = min([userLoc for userLoc, _ in mapping])
            maximum = max([userLoc for userLoc, _ in mapping])
            default = min(maximum, max(minimum, regularUserLoc))  # clamp

        if (minimum < maximum or minimum != axis_def.default_user_loc or
                len(instance_mapping) > 1 or len(master_mapping) > 1):
            axis.map = mapping
            axis.minimum = minimum
            axis.maximum = maximum
            axis.default = default
            self.designspace.addAxis(axis)


def to_glyphs_axes(self):
    weight = None
    width = None
    customs = []
    for axis in self.designspace.axes:
        if axis.tag == 'wght':
            weight = axis
        elif axis.tag == 'wdth':
            width = axis
        else:
            customs.append(axis)

    axes_parameter = []
    if weight is not None:
        axes_parameter.append({'Name': weight.name or 'Weight', 'Tag': 'wght'})
        # TODO: (jany) store other data about this axis?
    elif width is not None or customs:
        # Add a dumb weight axis to not mess up the indices
        # FIXME: (jany) I inferred this requirement from the code in
        # https://github.com/googlei18n/glyphsLib/pull/306
        # which seems to suggest that the first value is always weight and
        # the second always width
        axes_parameter.append({'Name': 'Weight', 'Tag': 'wght'})

    if width is not None:
        axes_parameter.append({'Name': width.name or 'Width', 'Tag': 'wdth'})
        # TODO: (jany) store other data about this axis?
    elif customs:
        # Add a dumb weight axis to not mess up the indices
        # FIXME: (jany) I inferred this requirement from the code in
        # https://github.com/googlei18n/glyphsLib/pull/306
        # which seems to suggest that the first value is always weight and
        # the second always width
        axes_parameter.append({'Name': 'Width', 'Tag': 'wdth'})

    for custom in customs:
        axes_parameter.append({
            'Name': custom.name,
            'Tag': custom.tag,
        })
        # TODO: (jany) store other data about this axis?

    if axes_parameter and not _is_subset_of_default_axes(axes_parameter):
        self.font.customParameters['Axes'] = axes_parameter

    if self.minimize_ufo_diffs:
        # TODO: (jany) later, when Glyphs can manage general designspace axes
        # self.font.userData[AXES_KEY] = [
        #     dict(
        #         tag=axis.tag,
        #         name=axis.name,
        #         minimum=axis.minimum,
        #         maximum=axis.maximum,
        #         default=axis.default,
        #         hidden=axis.hidden,
        #         labelNames=axis.labelNames,
        #     )
        #     for axis in self.designspace.axes
        # ]
        pass


class AxisDefinition(object):
    def __init__(self, tag, name, design_loc_key, default_design_loc=0.0,
                 user_loc_key=None, user_loc_param=None, default_user_loc=0.0):
        self.tag = tag
        self.name = name
        self.design_loc_key = design_loc_key
        self.default_design_loc = default_design_loc
        self.user_loc_key = user_loc_key
        self.user_loc_param = user_loc_param
        self.default_user_loc = default_user_loc

    def get_design_loc(self, master_or_instance):
        return getattr(master_or_instance, self.design_loc_key)

    def set_design_loc(self, master_or_instance, value):
        setattr(master_or_instance, self.design_loc_key, value)

    def get_user_loc(self, master_or_instance):
        if self.tag == 'wdth':
            # FIXME: (jany) existing test "DesignspaceTestTwoAxes.designspace"
            # suggests that the user location is the same as the design loc
            # for the width only
            return self.get_design_loc(master_or_instance)

        user_loc = self.default_user_loc
        if self.user_loc_key is not None:
            user_loc = getattr(master_or_instance, self.user_loc_key)
            user_loc = user_loc_code_to_value(self.tag, user_loc)
        # The custom param takes over the key if it exists
        # e.g. for weight:
        #       key = "weight" -> "Bold" -> 700
        # but param = "weightClass" -> 600       => 600 wins
        if self.user_loc_param is not None:
            class_ = master_or_instance.customParameters[self.user_loc_param]
            if class_ is not None:
                user_loc = class_to_value(self.tag, class_)
        return user_loc

    def set_user_loc(self,  master_or_instance, value):
        # Try to set the key if possible, i.e. if there is a key, and
        # if there exists a code that can represent the given value, e.g.
        # for "weight": 600 can be represented by SemiBold so we use that,
        # but for 550 there is no code so we will have to set the custom
        # parameter as well.
        code = user_loc_value_to_code(self.tag, value)
        value_for_code = user_loc_code_to_value(self.tag, code)
        if self.user_loc_key is not None:
            setattr(master_or_instance, self.user_loc_key, code)
        if self.user_loc_param is not None and value != value_for_code:
            try:
                class_ = user_loc_value_to_class(self.tag, value)
                master_or_instance.customParameters[self.user_loc_param] = class_
            except:
                pass

    def set_user_loc_code(self, master_or_instance, code):
        # The previous method `set_user_loc` will not roundtrip every
        # time, for example for value = 600, both "DemiBold" and "SemiBold"
        # would work, so we provide this other method to set a specific code.
        if self.user_loc_key is not None:
            setattr(master_or_instance, self.user_loc_key, code)


DEFAULT_AXES_DEFS = (
    AxisDefinition('wght', 'Weight', 'weightValue', 100.0,
                   'weight', 'weightClass', 400.0),
    AxisDefinition('wdth', 'Width', 'widthValue', 100.0,
                   'width', 'widthClass', 100.0),
    AxisDefinition('XXXX', 'Custom', 'customValue', 0.0, None, None, 0.0),
)


# Adapted from PR https://github.com/googlei18n/glyphsLib/pull/306
def get_axis_definitions(font):
    axesParameter = font.customParameters["Axes"]
    if axesParameter is None:
        return DEFAULT_AXES_DEFS

    axesDef = []
    designLocKeys = ('weightValue', 'widthValue', 'customValue',
                     'customValue1', 'customValue2', 'customValue3')
    defaultDesignLocs = (100.0, 100.0, 0.0, 0.0, 0.0, 0.0)
    userLocKeys = ('weight', 'width', None, None, None, None)
    userLocParams = ('weightClass', 'widthClass', None, None, None, None)
    defaultUserLocs = (400.0, 100.0, 0.0, 0.0, 0.0, 0.0)
    for idx, axis in enumerate(axesParameter):
        axesDef.append(AxisDefinition(
            axis.get("Tag", "XXX%d" % idx if idx > 0 else "XXXX"),
            axis["Name"], designLocKeys[idx], defaultDesignLocs[idx],
            userLocKeys[idx], userLocParams[idx], defaultUserLocs[idx]))
    return axesDef


def _is_subset_of_default_axes(axes_parameter):
    if len(axes_parameter) > 3:
        return False
    for axis, axis_def in zip(axes_parameter, DEFAULT_AXES_DEFS):
        if set(axis.keys()) != {'Name', 'Tag'}:
            return False
        if axis['Name'] != axis_def.name:
            return False
        if axis['Tag'] != axis_def.tag:
            return False
    return True


def get_regular_master(font):
    """Find the "regular" master among the GSFontMasters.

    Tries to find the master with the passed 'regularName'.
    If there is no such master or if regularName is None,
    tries to find a base style shared between all masters
    (defaulting to "Regular"), and then tries to find a master
    with that style name. If there is no master with that name,
    returns the first master in the list.
    """
    if not font.masters:
        return None
    regular_name = font.customParameters['Variation Font Origin']
    if regular_name is not None:
        for master in font.masters:
            if master.name == regular_name:
                return master
    base_style = find_base_style(font.masters)
    if not base_style:
        base_style = 'Regular'
    for master in font.masters:
        if master.name == base_style:
            return master
    # Second try: maybe the base style has regular in it as well
    for master in font.masters:
        name_without_regular = ' '.join(
            n for n in master.name.split(' ') if n != 'Regular')
        if name_without_regular == base_style:
            return master
    return font.masters[0]


def find_base_style(masters):
    """Find a base style shared between all masters.
    Return empty string if none is found.
    """
    if not masters:
        return ''
    base_style = (masters[0].name or '').split()
    for master in masters:
        style = master.name.split()
        base_style = [s for s in style if s in base_style]
    base_style = ' '.join(base_style)
    return base_style


def is_instance_active(instance):
    # Glyphs.app recognizes both "exports=0" and "active=0" as a flag
    # to mark instances as inactive. Inactive instances should get ignored.
    # https://github.com/googlei18n/glyphsLib/issues/129
    return instance.exports and getattr(instance, 'active', True)


def interp(mapping, x):
    """Compute the piecewise linear interpolation given by mapping for input x.

    >>> _interp(((1, 1), (2, 4)), 1.5)
    2.5
    """
    mapping = sorted(mapping)
    if len(mapping) == 1:
        xa, ya = mapping[0]
        if xa == x:
            return ya
        return x
    for (xa, ya), (xb, yb) in zip(mapping[:-1], mapping[1:]):
        if xa <= x <= xb:
            return ya + float(x - xa) / (xb - xa) * (yb - ya)
    return x
