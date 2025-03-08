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
import logging
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple, Union, cast

from fontTools.varLib.models import piecewiseLinearMap
from fontTools.designspaceLib import DesignSpaceDocument, InstanceDescriptor
from ufoLib2 import Font as UFOFont
from glyphsLib.util import build_ufo_path
from glyphsLib.classes import (
    GSCustomParameter,
    GSInstance,
    InstanceType,
    # WEIGHT_CODES,
)

from .constants import (
    GLYPHS_PREFIX,
    UFO_FILENAME_CUSTOM_PARAM,
    EXPORT_KEY,
    # WIDTH_KEY,
    # WEIGHT_KEY,
    FULL_FILENAME_KEY,
    MANUAL_INTERPOLATION_KEY,
    INSTANCE_INTERPOLATIONS_KEY,
    CUSTOM_PARAMETERS_BLACKLIST,
    PROPERTIES_KEY,
)
from .names import build_stylemap_names
from .custom_params import to_ufo_custom_params, to_ufo_properties, InstanceDescriptorAsGSInstance

logger = logging.getLogger(__name__)


def to_designspace_instances(self) -> None:
    """Write instance data from self.font to self.designspace."""
    for instance in self.font.instances:
        if self.minimize_glyphs_diffs or (
            instance.exports and _is_instance_included_in_family(self, instance)
        ):
            if instance.type == InstanceType.VARIABLE:
                _to_designspace_varfont(self, instance)
            else:
                _to_designspace_instance(self, instance)


def _to_designspace_varfont(self, instance: GSInstance) -> None:
    from fontTools.designspaceLib import RangeAxisSubsetDescriptor
    from fontTools.ufoLib import fontInfoAttributesVersion3

    ds = self.designspace
    # unless the `fileName` custom parameter was explicitly set, do like Glyphs.app
    # and concatenate the family, instance (style) names and "VF" to form a filename;
    # the default 'Regular' is omitted by Glyphs.app.
    # https://github.com/googlefonts/glyphsLib/issues/981
    filename: str = instance.customParameters.get("fileName", "")
    if not filename:
        filename = self.font.familyName
        if instance.name != "Regular":
            filename += "-" + instance.name
        filename += "VF"
        filename = filename.replace(" ", "")

    ufo_varfont = self.designspace.addVariableFontDescriptor(
        name=instance.name,
        filename=filename,
        axisSubsets=[RangeAxisSubsetDescriptor(name=axis.name) for axis in ds.axes],
    )
    ufo = self.ufo_module.Font()
    to_ufo_properties(self, ufo, instance)
    to_ufo_custom_params(self, ufo, instance, "instance", set_default_params=False)

    info = {}
    for attr in fontInfoAttributesVersion3:
        if (value := getattr(ufo.info, attr, None)) is not None:
            info[attr] = value

    if info:
        ufo_varfont.lib["public.fontInfo"] = info

    for key in ufo.lib:
        ufo_varfont.lib[key] = ufo.lib[key]


def _to_designspace_instance(self, instance: GSInstance) -> None:
    ufo_instance = self.designspace.newInstanceDescriptor()

    # FIXME: (jany) most of these customParameters are actually attributes,
    # at least according to https://docu.glyphsapp.com/#fontName

    # Read either from properties or custom parameters or the font
    ufo_instance.familyName = instance.familyName
    ufo_instance.styleName = instance.name
    ufo_instance.postScriptFontName = (
        instance.properties.get("postscriptFontName")
        or instance.customParameters["postscriptFontName"]
    )
    ufo_instance.filename = _to_filename(self, instance, ufo_instance)

    designspace_axis_tags: set[Any] = {a.tag for a in self.designspace.axes}
    location: dict = {}
    for axis_def in self.font.axes:
        # Only write locations along defined axes
        if axis_def.axisTag in designspace_axis_tags:
            location[axis_def.name] = instance.internalAxesValues[axis_def.axisId]
    ufo_instance.location = location

    # FIXME: (jany) should be the responsibility of ufo2ft?
    # Anyway, only generate the styleMap names if the Glyphs instance already
    # has a linkStyle set up, or if we're not round-tripping (i.e. generating
    # UFOs for fontmake, the traditional use-case of glyphsLib.)
    if instance.linkStyle or not self.minimize_glyphs_diffs or instance.isBold or instance.isItalic:
        styleMapFamilyName, styleMapStyleName = build_stylemap_names(
            family_name=ufo_instance.familyName,
            style_name=ufo_instance.styleName,
            is_bold=instance.isBold,
            is_italic=instance.isItalic,
            linked_style=instance.linkStyle,
        )
        ufo_instance.styleMapFamilyName = styleMapFamilyName
        ufo_instance.styleMapStyleName = styleMapStyleName
    smfm = instance.styleMapFamilyName
    if smfm:
        ufo_instance.styleMapFamilyName = smfm
    smsm = instance.styleMapStyleName
    if smsm:
        ufo_instance.styleMapStyleName = smsm

    ufo_instance.name = " ".join(
        (ufo_instance.familyName or "", ufo_instance.styleName or "")
    )

    ufo_instance.lib["openTypeOS2WidthClass"] = instance.widthClass
    ufo_instance.lib["openTypeOS2WeightClass"] = instance.weightClass

    uniqueID = instance.properties["uniqueID"]
    if uniqueID:
        ufo_instance.lib["openTypeNameUniqueID"] = uniqueID

    if self.minimize_glyphs_diffs:
        if not instance.exports:
            ufo_instance.lib[EXPORT_KEY] = False
        if instance.instanceInterpolations:
            ufo_instance.lib[
                INSTANCE_INTERPOLATIONS_KEY
            ] = instance.instanceInterpolations
        if instance.manualInterpolation:
            ufo_instance.lib[MANUAL_INTERPOLATION_KEY] = instance.manualInterpolation

    # Dump selected custom parameters and properties into the instance
    # descriptor. Later, when using `apply_instance_data`, we will dig out those
    # custom parameters and apply them to the UFO instance.
    parameters = _to_custom_parameters(instance)
    if parameters:
        ufo_instance.lib[GLYPHS_PREFIX + "customParameters"] = parameters
    properties = _to_properties(instance)
    if properties:
        ufo_instance.lib[PROPERTIES_KEY] = properties

    self.designspace.addInstance(ufo_instance)


def _to_custom_parameters(instance: GSInstance) -> List[Tuple[str, Any]]:
    """Extract custom parameters from an instance."""
    return [
        (item.name, item.value)
        for item in instance.customParameters
        if item.name not in CUSTOM_PARAMETERS_BLACKLIST
    ]


def _to_filename(self, instance: GSInstance, ufo_instance: InstanceDescriptor) -> str:
    filename = (
        instance.customParameters[UFO_FILENAME_CUSTOM_PARAM]
        or instance.customParameters[FULL_FILENAME_KEY]
    )
    if filename:
        if self.instance_dir:
            filename = os.path.basename(filename)
            filename = os.path.join(self.instance_dir, filename)
        return filename
    filename = instance.customParameters["fileName"]
    if filename:
        filename = f"{filename}.ufo"
        if self.instance_dir:
            filename = os.path.join(self.instance_dir, filename)
        return filename
    return build_ufo_path(
        self.instance_dir or "instance_ufos",
        ufo_instance.familyName,
        ufo_instance.styleName,
    )


def _to_properties(instance: GSInstance):
    return [
        (item.name, item.value if item.value else item.values)
        for item in instance.properties
        if item.name not in CUSTOM_PARAMETERS_BLACKLIST
    ]


def _is_instance_included_in_family(self, instance: GSInstance):
    if not self._do_filter_instances_by_family:
        return True
    return instance.familyName == self.family_name


# TODO: function is too complex (35), split it up
def to_glyphs_instances(self) -> None:  # noqa: C901
    if self.designspace is None:
        return

    for ufo_instance in self.designspace.instances:
        instance = self.glyphs_module.GSInstance()

        instance.active = ufo_instance.lib.get(EXPORT_KEY, True)
        instance.name = ufo_instance.styleName

        for axis_def in self.font.axes:
            design_loc = ufo_instance.location.get(axis_def.name)
            if design_loc is not None:
                instance.internalAxesValues[axis_def.axisId] = design_loc

            if axis_def.axisTag in ("wght", "wdth"):
                # Retrieve the user location (weightClass/widthClass)
                # Generic way: read the axis mapping backwards.
                user_loc = design_loc
                mapping = None
                for axis in self.designspace.axes:
                    if axis.tag == axis_def.axisTag:
                        mapping = axis.map
                if mapping:
                    reverse_mapping = {dl: ul for ul, dl in mapping}
                    user_loc = piecewiseLinearMap(design_loc, reverse_mapping)
                if user_loc is not None and user_loc != design_loc:
                    instance.externalAxesValues[axis_def.axisId] = user_loc

        instance.weightClass = ufo_instance.lib.get("openTypeOS2WeightClass", 400)
        instance.widthClass = ufo_instance.lib.get("openTypeOS2WidthClass", 5)

        if ufo_instance.familyName and ufo_instance.familyName != self.font.familyName:
            instance.familyName = ufo_instance.familyName

        smfn = ufo_instance.styleMapFamilyName
        if smfn:
            instance.styleMapFamilyName = smfn
            if smfn.startswith(ufo_instance.familyName):
                smfn = smfn[len(ufo_instance.familyName):].strip()
            instance.linkStyle = smfn

        smsn = ufo_instance.styleMapStyleName
        if smsn:
            instance.styleMapStyleName = smsn
            instance.isBold = "bold" in smsn
            instance.isItalic = "italic" in smsn

        if ufo_instance.postScriptFontName:
            instance.fontName = ufo_instance.postScriptFontName

        instance.manualInterpolation = ufo_instance.lib.get(MANUAL_INTERPOLATION_KEY, False)
        instance.instanceInterpolations = ufo_instance.lib.get(INSTANCE_INTERPOLATIONS_KEY, {})

        for name, value in ufo_instance.lib.get(GLYPHS_PREFIX + "customParameters", []):
            instance.customParameters.append(GSCustomParameter(name, value))

        if ufo_instance.filename and self.minimize_ufo_diffs:
            instance.customParameters[UFO_FILENAME_CUSTOM_PARAM] = ufo_instance.filename

        self.font.instances.append(instance)


def apply_instance_data(
    designspace: Union[str, Path, DesignSpaceDocument],
    include_filenames: Optional[Set[str]] = None,
    Font: Optional[UFOFont] = None
) -> List[UFOFont]:
    """Open UFO instances referenced by designspace, apply Glyphs instance
    data if present, re-save UFOs and return updated UFO Font objects.

    Args:
        designspace: DesignSpaceDocument object or path (str or PathLike) to
            a designspace file.
        include_filenames: Optional set of instance filenames (relative to
            the designspace path) to be included. By default all instances are
            processed.
        Font: A callable(path: str) -> Font, used to load a UFO, such as
            defcon.Font class (default: ufoLib2.Font.open).

    Returns:
        List of opened and updated instance UFOs.
    """
    from fontTools.designspaceLib import DesignSpaceDocument
    from os.path import normcase, normpath

    if Font is None:
        import ufoLib2

        Font = ufoLib2.Font.open  # type: ignore

    if hasattr(designspace, "__fspath__"):
        designspace = designspace.__fspath__()
    if isinstance(designspace, str):
        designspace = DesignSpaceDocument.fromfile(designspace)

    basedir = os.path.dirname(designspace.path or "")
    instance_ufos = []
    if include_filenames is not None:
        include_filenames = {normcase(normpath(p)) for p in include_filenames}

    for designspace_instance in designspace.instances:
        fname = designspace_instance.filename
        assert fname is not None, f"Instance {designspace_instance.name} missing required filename."

        if include_filenames is not None:
            fname = normcase(normpath(fname))
            if fname not in include_filenames:
                continue

        logger.debug("Applying instance data to %s", fname)
        # fontmake <= 1.4.0 compares the ufo paths returned from this function
        # to the keys of a dict of designspace locations that have been passed
        # through normpath (but not normcase). We do the same.
        ufo = Font(normpath(os.path.join(basedir, fname)))  # type: ignore

        apply_instance_data_to_ufo(ufo, designspace_instance, designspace)

        ufo.save()
        instance_ufos.append(ufo)
    return instance_ufos


def apply_instance_data_to_ufo(ufo: UFOFont, instance: InstanceDescriptor, designspace: DesignSpaceDocument) -> None:
    """Apply Glyphs instance data to a UFO object.

    Args:
        ufo: A defcon-like font object.
        instance: A fontTools.designspaceLib.InstanceDescriptor.
        designspace: A fontTools.designspaceLib.DesignSpaceDocument.
    """
    try:
        ufo.info.openTypeOS2WidthClass = instance.lib["openTypeOS2WidthClass"]
    except KeyError:
        pass
    try:
        ufo.info.openTypeOS2WeightClass = instance.lib["openTypeOS2WeightClass"]
    except KeyError:
        pass

    glyphs_instance: GSInstance = cast(GSInstance, InstanceDescriptorAsGSInstance(instance))
    to_ufo_properties(None, ufo, glyphs_instance)
    to_ufo_custom_params(None, ufo, glyphs_instance, "instance")
