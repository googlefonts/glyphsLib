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

from fontTools.varLib.models import piecewiseLinearMap

from glyphsLib.util import build_ufo_path
from glyphsLib.classes import (
    CustomParametersProxy,
    GSCustomParameter,
    GSInstance,
    InstanceType,
    PropertiesProxy,
    WEIGHT_CODES,
)
from .constants import (
    GLYPHS_PREFIX,
    UFO_FILENAME_CUSTOM_PARAM,
    EXPORT_KEY,
    WIDTH_KEY,
    WEIGHT_KEY,
    FULL_FILENAME_KEY,
    MANUAL_INTERPOLATION_KEY,
    INSTANCE_INTERPOLATIONS_KEY,
    CUSTOM_PARAMETERS_BLACKLIST,
    PROPERTIES_KEY,
)
from .names import build_stylemap_names


logger = logging.getLogger(__name__)


def to_designspace_instances(self):
    """Write instance data from self.font to self.designspace."""
    for instance in self.font.instances:
        if instance.type == InstanceType.VARIABLE:
            continue
        if self.minimize_glyphs_diffs or (
            instance.exports
            and _is_instance_included_in_family(self, instance)
        ):
            _to_designspace_instance(self, instance)


def _to_designspace_instance(self, instance):
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

    designspace_axis_tags = {a.tag for a in self.designspace.axes}
    location = {}
    for axis_def in self.font.axes:
        # Only write locations along defined axes
        if axis_def.axisTag in designspace_axis_tags:
            location[axis_def.name] = instance.internalAxesValues[axis_def.axisId]
    ufo_instance.location = location

    # FIXME: (jany) should be the responsibility of ufo2ft?
    # Anyway, only generate the styleMap names if the Glyphs instance already
    # has a linkStyle set up, or if we're not round-tripping (i.e. generating
    # UFOs for fontmake, the traditional use-case of glyphsLib.)
    if instance.linkStyle or not self.minimize_glyphs_diffs:
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

    uniqueID = instance.customParameters["uniqueID"]
    if uniqueID:
        ufo_instance.lib["openTypeNameUniqueID"] = uniqueID

    if self.minimize_glyphs_diffs:
        if not instance.exports:
            ufo_instance.lib[EXPORT_KEY] = False
        if instance.instanceInterpolations:
            ufo_instance.lib[INSTANCE_INTERPOLATIONS_KEY] = instance.instanceInterpolations
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


def _to_custom_parameters(instance):
    return [
        (item.name, item.value)
        for item in instance.customParameters
        if item.name not in CUSTOM_PARAMETERS_BLACKLIST
    ]


def _to_filename(self, instance, ufo_instance):
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


def _to_properties(instance):
    return [
        (item.name, item.value)
        for item in instance.properties
        if item.name not in CUSTOM_PARAMETERS_BLACKLIST
    ]


def _is_instance_included_in_family(self, instance: GSInstance):
    if not self._do_filter_instances_by_family:
        return True
    return instance.familyName == self.family_name


# TODO: function is too complex (35), split it up
def to_glyphs_instances(self):  # noqa: C901
    if self.designspace is None:
        return

    for ufo_instance in self.designspace.instances:
        instance = self.glyphs_module.GSInstance()

        try:
            instance.active = ufo_instance.lib[EXPORT_KEY]
        except KeyError:
            # If not specified, the default is to export all instances
            instance.active = True

        instance.name = ufo_instance.styleName

        for axis_def in self.font.axes:
            design_loc = None
            try:
                design_loc = ufo_instance.location[axis_def.name]
                instance.internalAxesValues[axis_def.axisId] = design_loc
            except KeyError:
                # The location does not have this axis?
                pass

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
                if user_loc is not None:
                    instance.externalAxesValues[axis_def.axisId] = user_loc

        try:
            # Restore the original weight name when there is an ambiguity based
            # on the value, e.g. Thin, ExtraLight, UltraLight all map to 250.
            # No problem with width, because 1:1 mapping in WIDTH_CODES.
            weight = ufo_instance.lib[WEIGHT_KEY]
            # Only use the lib value if:
            # 1. we don't have a weight for the instance already
            # 2. the value from lib is not "stale", i.e. it still maps to
            #    the current userLocation of the instance. This is in case the
            #    user changes the instance location of the instance by hand but
            #    does not update the weight value in lib.
            if (
                not instance.weightClass
                or WEIGHT_CODES[instance.weightClass] == WEIGHT_CODES[weight]
            ):
                instance.weightClass = weight
        except KeyError:
            # FIXME: what now
            pass

        try:
            if not instance.widthClass:
                instance.widthClass = ufo_instance.lib[WIDTH_KEY]
        except KeyError:
            # FIXME: what now
            pass

        if ufo_instance.familyName is not None:
            if ufo_instance.familyName != self.font.familyName:
                instance.familyName = ufo_instance.familyName

        smfn = ufo_instance.styleMapFamilyName
        if smfn is not None:
            instance.styleMapFamilyName = smfn
            if smfn.startswith(ufo_instance.familyName):
                smfn = smfn[len(ufo_instance.familyName) :].strip()
            instance.linkStyle = smfn

        smsn = ufo_instance.styleMapStyleName
        if smsn is not None:
            instance.styleMapStyleName = smsn
            instance.isBold = "bold" in smsn
            instance.isItalic = "italic" in smsn

        if ufo_instance.postScriptFontName is not None:
            instance.fontName = ufo_instance.postScriptFontName

        try:
            instance.manualInterpolation = ufo_instance.lib[MANUAL_INTERPOLATION_KEY]
        except KeyError:
            pass

        try:
            instance.instanceInterpolations = ufo_instance.lib[
                INSTANCE_INTERPOLATIONS_KEY
            ]
        except KeyError:
            # TODO: (jany) compute instanceInterpolations from the location
            # if instance.manualInterpolation: warn about data loss
            pass

        if GLYPHS_PREFIX + "customParameters" in ufo_instance.lib:
            for name, value in ufo_instance.lib[GLYPHS_PREFIX + "customParameters"]:
                instance.customParameters.append(GSCustomParameter(name, value))

        if ufo_instance.filename and self.minimize_ufo_diffs:
            instance.customParameters[UFO_FILENAME_CUSTOM_PARAM] = ufo_instance.filename

        # some info that needs to be in a instance in Glyphs is stored in the sources. So we try to find a matching source (FIXME: (georg) not nice
        for source in self.designspace.sources:
            if source.location == ufo_instance.location:
                instance.weightClass = source.font.info.openTypeOS2WeightClass or 400
                instance.widthClass = source.font.info.openTypeOS2WidthClass or 5
                if source.font.info.openTypeNameUniqueID:
                    instance.properties["uniqueID"] = source.font.info.openTypeNameUniqueID
        self.font.instances.append(instance)


class InstanceDescriptorAsGSInstance:
    # FIXME: (georg) find a better way
    """Wraps a designspace InstanceDescriptor and makes it behave like a
    GSInstance, just enough to use the descriptor as a source of custom
    parameters for `to_ufo_custom_parameters`
    """

    def __init__(self, descriptor):
        self._descriptor = descriptor

        self.customParameters = CustomParametersProxy(self)
        if GLYPHS_PREFIX + "customParameters" in descriptor.lib:
            for name, value in descriptor.lib[GLYPHS_PREFIX + "customParameters"]:
                self.customParameters[name] = value
        self.properties = PropertiesProxy(self)
        if PROPERTIES_KEY in descriptor.lib:
            for name, value in descriptor.lib[PROPERTIES_KEY]:
                self.properties[name] = value


def apply_instance_data(designspace, include_filenames=None, Font=None):
    """Open UFO instances referenced by designspace, apply Glyphs instance
    data if present, re-save UFOs and return updated UFO Font objects.

    Args:
        designspace: DesignSpaceDocument object or path (str or PathLike) to
            a designspace file.
        include_filenames: optional set of instance filenames (relative to
            the designspace path) to be included. By default all instaces are
            processed.
        Font: a callable(path: str) -> Font, used to load a UFO, such as
            defcon.Font class (default: ufoLib2.Font.open).
    Returns:
        List of opened and updated instance UFOs.
    """
    from fontTools.designspaceLib import DesignSpaceDocument
    from os.path import normcase, normpath

    if Font is None:
        import ufoLib2

        Font = ufoLib2.Font.open

    if hasattr(designspace, "__fspath__"):
        designspace = designspace.__fspath__()
    if isinstance(designspace, str):
        designspace = DesignSpaceDocument.fromfile(designspace)

    basedir = os.path.dirname(designspace.path)
    instance_ufos = []
    if include_filenames is not None:
        include_filenames = {normcase(normpath(p)) for p in include_filenames}

    for designspace_instance in designspace.instances:
        fname = designspace_instance.filename
        assert fname is not None, "instance %r missing required filename" % getattr(
            designspace_instance, "name", designspace_instance
        )
        if include_filenames is not None:
            fname = normcase(normpath(fname))
            if fname not in include_filenames:
                continue

        logger.debug("Applying instance data to %s", fname)
        # fontmake <= 1.4.0 compares the ufo paths returned from this function
        # to the keys of a dict of designspace locations that have been passed
        # through normpath (but not normcase). We do the same.
        ufo = Font(normpath(os.path.join(basedir, fname)))

        apply_instance_data_to_ufo(ufo, designspace_instance, designspace)

        ufo.save()
        instance_ufos.append(ufo)
    return instance_ufos


def apply_instance_data_to_ufo(ufo, instance, designspace):
    """Apply Glyphs instance data to UFO object.

    Args:
        ufo: a defcon-like font object.
        instance: a fontTools.designspaceLib.InstanceDescriptor.
        designspace: a fontTools.designspaceLib.DesignSpaceDocument.
    Returns:
        None.
    """
    # Import here to prevent a cyclic import with custom_params
    from .custom_params import to_ufo_custom_params, to_ufo_properties

    try:
        ufo.info.openTypeOS2WidthClass = instance.lib["openTypeOS2WidthClass"]
    except KeyError:
        pass
    try:
        ufo.info.openTypeOS2WeightClass = instance.lib["openTypeOS2WeightClass"]
    except KeyError:
        pass

    glyphs_instance = InstanceDescriptorAsGSInstance(instance)
    to_ufo_properties(None, ufo, glyphs_instance)
    to_ufo_custom_params(None, ufo, glyphs_instance, "instance")
