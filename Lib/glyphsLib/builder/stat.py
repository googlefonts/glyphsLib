# Copyright 2024 Google Inc. All Rights Reserved.
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

"""Reproduce Glyphs’ automatic STAT table generation.

Glyphs derives a STAT table from the exported instances: for every axis it
generates one AxisValue per distinct instance coordinate, named after the
instance style name, and it always appends a STAT-only “ital” axis.  This
module reproduces that by populating the DesignSpace v5 ``axis.axisLabels``.
"""

import re

from fontTools.designspaceLib import AxisLabelDescriptor, DiscreteAxisDescriptor

from glyphsLib.classes import InstanceType
from glyphsLib.builder.axes import get_axis_definitions, is_instance_active


def _is_italic(instance):
    # Glyphs uses the style name as well as the style-linking flag.
    return bool(instance.isItalic) or "italic" in instance.name.lower()


def _default_name(tag):
    return "Normal" if tag == "wdth" else "Regular"


def _stat_disabled(instance):
    export = instance.customParameters["Export STAT Table"]
    return export is not None and not export


def _is_elidable(instance, axis):
    return any(
        param.value == axis.tag
        for param in instance.customParameters
        if param.name == "Elidable STAT Axis Value Name"
    )


def _stat_entry_tags(instance):
    return [
        param.value
        for param in instance.customParameters
        if param.name == "Style Name as STAT entry"
    ]


def _set_axisLabels(axis, labels):
    if labels:
        axis.axisLabels = [
            AxisLabelDescriptor(name=name, userValue=value, elidable=elidable)
            for value, (name, elidable) in sorted(labels.items())
        ]


def to_designspace_stat(self):
    font = self.font
    designspace = self.designspace

    # Glyphs builds a STAT only for a variable font, which needs a Variable Font
    # Setting instance. Do the same here.
    variable = [i for i in font.instances if i.type == InstanceType.VARIABLE]
    if not variable:
        return

    # “Export STAT Table” = 0 turns the STAT off. Glyphs applies this per variable
    # font, but varLib builds the STAT from the document as a whole, so we can only
    # drop it when every variable-font instance turns it off.
    if all(_stat_disabled(instance) for instance in variable):
        return

    axis_defs = {ad.tag: ad for ad in get_axis_definitions(font)}
    axis_tags = {axis.tag for axis in designspace.axes}
    slope_tag = (
        "ital" if "ital" in axis_tags else "slnt" if "slnt" in axis_tags else None
    )

    instances = [
        instance
        for instance in font.instances
        if instance.type != InstanceType.VARIABLE and is_instance_active(instance)
    ]

    def user_loc(axis, instance):
        axis_def = axis_defs.get(axis.tag)
        return axis_def.get_user_loc(instance) if axis_def else None

    default_instance = next(
        (i for i in instances if _at_default(i, designspace.axes, user_loc)), None
    )

    italic = default_instance is not None and _is_italic(default_instance)
    # Glyphs drops the italic part of the names only when the default instance is
    # called nothing but “Italic”.
    plain_italic = italic and default_instance.name.strip().lower() == "italic"

    # “Style Name as STAT entry” on any instance switches the whole font to manual
    # mode.
    if any(_stat_entry_tags(instance) for instance in instances):
        _manual_labels(designspace, instances, user_loc)
    else:
        _automatic_labels(
            designspace, instances, user_loc, slope_tag, default_instance, plain_italic
        )

    designspace.elidedFallbackName = "Regular"

    # Glyphs always appends a STAT-only “ital” axis unless the font already has
    # an “ital” axis.
    if "ital" not in axis_tags:
        if italic:
            label = AxisLabelDescriptor(name="Italic", userValue=1, elidable=False)
        else:
            label = AxisLabelDescriptor(
                name="Roman", userValue=0, elidable=True, linkedUserValue=1
            )
        designspace.addAxis(
            DiscreteAxisDescriptor(
                tag="ital",
                name="Italic",
                values=[label.userValue],
                default=label.userValue,
                axisLabels=[label],
            )
        )


def _manual_labels(designspace, instances, user_loc):
    for axis in designspace.axes:
        labels = {}
        for instance in instances:
            if axis.tag in _stat_entry_tags(instance):
                loc = user_loc(axis, instance)
                if loc is not None and loc not in labels:
                    labels[loc] = (instance.name, _is_elidable(instance, axis))
        _set_axisLabels(axis, labels)


def _at_default(instance, axes, user_loc, skip=None):
    return all(
        user_loc(axis, instance) in (None, axis.default)
        for axis in axes
        if axis is not skip
    )


def _representative_instance(instances, axis, designspace, user_loc):
    # The instance at this value that is at the default on every other axis.
    # Fall back to the first instance when none qualifies.
    for instance in instances:
        if _at_default(instance, designspace.axes, user_loc, skip=axis):
            return instance
    return instances[0]


def _label_name(instance, default, plain_italic):
    name = instance.name
    if plain_italic:
        name = re.sub(r"\s*italic\s*", " ", name, flags=re.IGNORECASE).strip()
    return name or default


def _automatic_labels(
    designspace, instances, user_loc, slope_tag, default_instance, plain_italic=False
):
    # The default value of the first axis the instances vary on takes the
    # default instance’s name, every other default value elides to the
    # default name.
    first = next(
        (
            axis
            for axis in designspace.axes
            if len({user_loc(axis, i) for i in instances} - {None}) > 1
        ),
        None,
    )

    for axis in designspace.axes:
        default = _default_name(axis.tag)
        by_value = {}  # user value -> instances sitting there
        for instance in instances:
            loc = user_loc(axis, instance)
            if loc is not None:
                by_value.setdefault(loc, []).append(instance)

        labels = {}
        for loc, instances_at_loc in by_value.items():
            if loc != axis.default:
                instance = _representative_instance(
                    instances_at_loc, axis, designspace, user_loc
                )
            elif axis is first and default_instance is not None:
                instance = default_instance
            else:
                labels[loc] = (default, True)
                continue
            name = _label_name(instance, default, plain_italic)
            labels[loc] = (name, name == default or _is_elidable(instance, axis))
        _set_axisLabels(axis, labels)

    # The regular weight links to a style-linked bold wherever it sits on the
    # other axes.
    wght = next((a for a in designspace.axes if a.tag == "wght"), None)
    if wght is not None and _default_value_elides(wght):
        bold = next((i for i in instances if i.isBold), None)
        _set_linked_value(wght, user_loc(wght, bold) if bold else None)

    # On a real “ital” axis the upright value links to the italic value.
    if slope_tag == "ital":
        ital = next(a for a in designspace.axes if a.tag == "ital")
        _set_linked_value(
            ital, max((l.userValue for l in ital.axisLabels), default=ital.default)
        )


def _default_value_elides(axis):
    label = next(
        (l for l in axis.axisLabels or [] if l.userValue == axis.default), None
    )
    return label is not None and label.elidable


def _set_linked_value(axis, value):
    if value is None or value == axis.default:
        return
    default_label = next(
        (l for l in axis.axisLabels or [] if l.userValue == axis.default), None
    )
    if default_label is not None:
        default_label.linkedUserValue = value


def is_stat_only_ital(axis):
    # The axis this module appends carries a single value, 0 or 1.
    return axis.tag == "ital" and getattr(axis, "values", None) in ([0], [1])
