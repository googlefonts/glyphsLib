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


import logging

from glyphsLib.types import Transform

from .constants import GLYPHS_PREFIX, COMPONENT_INFO_KEY

logger = logging.getLogger(__name__)


def to_ufo_components(self, ufo_glyph, layer):
    """Draw .glyphs components onto a pen, adding them to the parent glyph."""
    pen = ufo_glyph.getPointPen()

    for index, component in enumerate(layer.components):
        pen.addComponent(component.name, component.transform)

        if not (component.anchor or component.alignment):
            continue

        component_info = {"name": component.name, "index": index}
        if component.anchor:
            component_info["anchor"] = component.anchor
        if component.alignment:
            component_info["alignment"] = component.alignment

        if COMPONENT_INFO_KEY not in ufo_glyph.lib:
            ufo_glyph.lib[COMPONENT_INFO_KEY] = []
        ufo_glyph.lib[COMPONENT_INFO_KEY].append(component_info)

    # data related to components that is not stored in ComponentInfo is
    # stored in lists of booleans. each list's elements correspond to the
    # components in order.
    for key in ["locked", "smartComponentValues"]:
        values = [getattr(c, key) for c in layer.components]
        if any(values):
            ufo_glyph.lib[_lib_key(key)] = values


def to_glyphs_components(self, ufo_glyph, layer):
    for comp in ufo_glyph.components:
        component = self.glyphs_module.GSComponent(comp.baseGlyph)
        component.transform = Transform(*comp.transformation)
        layer.components.append(component)

    for key in ["alignment", "locked", "smartComponentValues"]:
        if _lib_key(key) not in ufo_glyph.lib:
            continue
        # FIXME: (jany) move to using component identifiers for robustness
        # "alignment" is read, but not written for source backwards compatibility.
        values = ufo_glyph.lib[_lib_key(key)]
        for component, value in zip(layer.components, values):
            if value is not None:
                setattr(component, key, value)

    if COMPONENT_INFO_KEY in ufo_glyph.lib:
        for index, component_info in enumerate(ufo_glyph.lib[COMPONENT_INFO_KEY]):
            if "index" not in component_info or "name" not in component_info:
                logger.warning(
                    "Glyph %s, layer %s: The ComponentInfo at index %s is missing "
                    "index and/or name keys. Skipping, component properties will be "
                    "lost.",
                    ufo_glyph.name,
                    layer.name,
                    index,
                )
                continue

            component_index = component_info["index"]
            try:
                component = layer.components[component_index]
            except IndexError:
                logger.warning(
                    "Glyph %s, layer %s: The ComponentInfo at index %s is referencing "
                    "a component that does not exist. Skipping, component properties "
                    "will be lost.",
                    ufo_glyph.name,
                    layer.name,
                    index,
                )
                continue

            if component.name == component_info["name"]:
                if "anchor" in component_info:
                    component.anchor = component_info["anchor"]
                if "alignment" in component_info:
                    component.alignment = component_info["alignment"]
            else:
                logger.warning(
                    "Glyph %s, layer %s: The ComponentInfo at index %s says the "
                    "component at index %s is named '%s', but it is actually named "
                    "'%s'. Skipping, component properties will be lost.",
                    ufo_glyph.name,
                    layer.name,
                    index,
                    component_index,
                    component_info["name"],
                    component.name,
                )


def _lib_key(key):
    key = key[0].upper() + key[1:]
    return f"{GLYPHS_PREFIX}components{key}"


AXES_LIB_KEY = GLYPHS_PREFIX + "smartComponentAxes"


def to_ufo_smart_component_axes(self, ufo_glyph, glyph):
    def _to_ufo_axis(axis):
        return {
            "name": axis.name,
            "bottomName": axis.bottomName,
            "bottomValue": axis.bottomValue,
            "topName": axis.topName,
            "topValue": axis.topValue,
        }

    if glyph.smartComponentAxes:
        ufo_glyph.lib[AXES_LIB_KEY] = [
            _to_ufo_axis(a) for a in glyph.smartComponentAxes
        ]


def to_glyphs_smart_component_axes(self, ufo_glyph, glyph):
    def _to_glyphs_axis(axis):
        res = self.glyphs_module.GSSmartComponentAxis()
        res.name = axis["name"]
        res.bottomName = axis["bottomName"]
        res.bottomValue = axis["bottomValue"]
        res.topValue = axis["topValue"]
        res.topName = axis["topName"]
        return res

    if AXES_LIB_KEY in ufo_glyph.lib:
        glyph.smartComponentAxes = [
            _to_glyphs_axis(a) for a in ufo_glyph.lib[AXES_LIB_KEY]
        ]
