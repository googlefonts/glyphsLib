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

from collections import OrderedDict, namedtuple
import logging
import os
import xml.etree.ElementTree as etree

from glyphsLib.builder import set_redundant_data, set_custom_params,\
    set_default_params, GLYPHS_PREFIX
from glyphsLib.util import build_ufo_path, write_ufo, clean_ufo, clear_data

__all__ = [
    'interpolate', 'build_designspace', 'apply_instance_data'
]

logger = logging.getLogger(__name__)

# Glyphs.app's default values for the masters' {weight,width,custom}Value
# and for the instances' interpolation{Weight,Width,Custom} properties.
# When these values are set, they are omitted from the .glyphs source file.
DEFAULT_LOCS = {
    'weight': 100,
    'width': 100,
    'custom': 0,
}


def interpolate(ufos, master_dir, out_dir, instance_data, debug=False):
    """Create MutatorMath designspace and generate instances.
    Returns instance UFOs, or unused instance data if debug is True.
    """
    from mutatorMath.ufo import build

    designspace_path, instance_files = build_designspace(
        ufos, master_dir, out_dir, instance_data)

    logger.info('Building instances')
    for path, _ in instance_files:
        clean_ufo(path)
    build(designspace_path, outputUFOFormatVersion=3)

    instance_ufos = apply_instance_data(instance_files)
    if debug:
        return clear_data(instance_data)
    return instance_ufos


def build_designspace(masters, master_dir, out_dir, instance_data):
    """Just create MutatorMath designspace without generating instances.

    Returns the path of the resulting designspace document and a list of
    (instance_path, instance_data) tuples which map instance UFO filenames to
    Glyphs data for that instance.
    """
    from mutatorMath.ufo.document import DesignSpaceDocumentWriter

    for font in masters:
        write_ufo(font, master_dir)

    # needed so that added masters and instances have correct relative paths
    tmp_path = os.path.join(master_dir, 'tmp.designspace')
    writer = DesignSpaceDocumentWriter(tmp_path)

    instances = list(filter(is_instance_active, instance_data.get('data', [])))
    axes = get_axes(masters, instances)
    write_axes(axes, writer)
    base_family, base_style = add_masters_to_writer(masters, axes, writer)
    base_family = instance_data.get('defaultFamilyName', base_family)
    instance_files = add_instances_to_writer(
        writer, base_family, axes, instances, out_dir)

    basename = '%s%s.designspace' % (
        base_family, ('-' + base_style) if base_style else '')
    writer.path = os.path.join(master_dir, basename.replace(' ', ''))
    writer.save()
    return writer.path, instance_files


# TODO: Use AxisDescriptor from fonttools once designSpaceDocument has been
# made part of fonttools. https://github.com/fonttools/fonttools/issues/911
# https://github.com/LettError/designSpaceDocument#axisdescriptor-object
AxisDescriptor = namedtuple('AxisDescriptor', [
    'minimum', 'maximum', 'default', 'name', 'tag', 'labelNames', 'map'])


def get_axes(masters, instances):
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
    axes = OrderedDict()
    for name, tag, userLocParam, defaultUserLoc in (
            ('weight', 'wght', 'weightClass', 400),
            ('width', 'wdth', 'widthClass', 100),
            ('custom', 'XXXX', None, 0)):
        key = GLYPHS_PREFIX + name + 'Value'
        interpolLocKey = 'interpolation' + name.title()
        if any(key in master.lib for master in masters):
            labelNames = {"en": name.title()}
            mapping = []
            for instance in instances:
                interpolLoc = instance.get(interpolLocKey, DEFAULT_LOCS[name])
                userLoc = interpolLoc
                for param in instance.get('customParameters', []):
                    if param.get('name') == userLocParam:
                        userLoc = float(param.get('value', DEFAULT_LOCS[name]))
                        break
                mapping.append((userLoc, interpolLoc))
            mapping = sorted(set(mapping))  # avoid duplicates
            if mapping:
                minimum = min([userLoc for userLoc, _ in mapping])
                maximum = max([userLoc for userLoc, _ in mapping])
                default = min(maximum, max(minimum, defaultUserLoc))  # clamp
            else:
                minimum = maximum = default = defaultUserLoc
            axes[name] = AxisDescriptor(
                minimum=minimum, maximum=maximum, default=default,
                name=name, tag=tag, labelNames=labelNames, map=mapping)
    return axes


def is_instance_active(instance):
    # Glyphs.app recognizes both "exports=0" and "active=0" as a flag
    # to mark instances as inactive. Inactive instances should get ignored.
    # https://github.com/googlei18n/glyphsLib/issues/129
    return instance.get('exports', True) and instance.get('active', True)


def write_axes(axes, writer):
    # TODO: MutatorMath's DesignSpaceDocumentWriter does not support
    # axis label names. Once DesignSpaceDocument has been made part
    # of fonttools, we can write them out in a less hacky way than here.
    # The current implementation is rather terrible, but it works;
    # extending the writer isn't worth the effort because we'll move away
    # from it as soon as DesignSpaceDocument has landed in fonttools.
    # https://github.com/fonttools/fonttools/issues/911
    for axis in axes.values():
        writer.addAxis(tag=axis.tag, name=axis.name,
                       minimum=axis.minimum, maximum=axis.maximum,
                       default=axis.default, warpMap=axis.map)
        axisElement = writer.root.findall('.axes/axis')[-1]
        for lang, name in sorted(axis.labelNames.items()):
            labelname = etree.Element('labelname')
            labelname.attrib['xml:lang'], labelname.text = lang, name
            axisElement.append(labelname)


def add_masters_to_writer(ufos, axes, writer):
    """Add master UFOs to a MutatorMath document writer.

    Returns the masters' family name and shared style names. These are used for
    naming instances and the designspace path.
    """
    master_data = []
    base_family = None
    base_style = None

    for font in ufos:
        family, style = font.info.familyName, font.info.styleName
        if base_family is None:
            base_family = family
        else:
            assert family == base_family, 'Masters must all have same family'
        if base_style is None:
            base_style = style.split()
        else:
            base_style = [s for s in style.split() if s in base_style]
        # MutatorMath.DesignSpaceDocumentWriter iterates over the location
        # dictionary, which is non-deterministic so it can cause test failures.
        # We therefore use an OrderedDict to which we insert in axis order.
        # Since glyphsLib will switch to DesignSpaceDocument once that is
        # integrated into fonttools, it's not worth fixing upstream.
        # https://github.com/googlei18n/glyphsLib/issues/165
        location = OrderedDict()
        for axis in axes:
            location[axis] = font.lib.get(
                GLYPHS_PREFIX + axis + 'Value', DEFAULT_LOCS[axis])
        master_data.append((font.path, family, style, location))

    # pick a master to copy info, features, and groups from, trying to find the
    # master with a base style shared between all masters (or just Regular) and
    # defaulting to the first master if nothing is found
    base_style = ' '.join(base_style)
    info_source = 0
    for i, (path, family, style, location) in enumerate(master_data):
        if family == base_family and style == (base_style or 'Regular'):
            info_source = i
            break

    for i, (path, family, style, location) in enumerate(master_data):
        is_base = (i == info_source)
        writer.addSource(
            path=path, name='%s %s' % (family, style),
            familyName=family, styleName=style, location=location,
            copyFeatures=is_base, copyGroups=is_base, copyInfo=is_base,
            copyLib=is_base)

    return base_family, base_style


def add_instances_to_writer(writer, family_name, axes, instances, out_dir):
    """Add instances from Glyphs data to a MutatorMath document writer.

    Returns a list of <ufo_path, font_data> pairs, corresponding to the
    instances which will be output by the document writer. The font data is the
    Glyphs data for this instance as a dict.
    """
    ofiles = []
    for instance in instances:
        familyName, postScriptFontName = family_name, None
        for p in instance.get('customParameters', ()):
            param, value = p['name'], p['value']
            if param == 'familyName':
                familyName = value
            elif param == 'postscriptFontName':
                # Glyphs uses "postscriptFontName", not "postScriptFontName"
                postScriptFontName = value
        if not familyName:
            continue

        styleName = instance.get('name')
        ufo_path = build_ufo_path(out_dir, familyName, styleName)
        ofiles.append((ufo_path, instance))
        # MutatorMath.DesignSpaceDocumentWriter iterates over the location
        # dictionary, which is non-deterministic so it can cause test failures.
        # We therefore use an OrderedDict to which we insert in axis order.
        # Since glyphsLib will switch to DesignSpaceDocument once that is
        # integrated into fonttools, it's not worth fixing upstream.
        # https://github.com/googlei18n/glyphsLib/issues/165
        location = OrderedDict()
        for axis in axes:
            location[axis] = instance.get(
                'interpolation' + axis.title(), DEFAULT_LOCS[axis])
        writer.startInstance(
            name=' '.join((familyName, styleName)),
            location=location,
            familyName=familyName,
            styleName=styleName,
            postScriptFontName=postScriptFontName,
            fileName=ufo_path)

        writer.writeInfo()
        writer.writeKerning()
        writer.endInstance()

    return ofiles


def apply_instance_data(instance_data):
    """Open instances, apply data, and re-save.

    Args:
        instance_data: List of (path, data) tuples, one for each instance.
        dst_ufo_list: List to add opened instances to.
    Returns:
        List of opened and updated instance UFOs.
    """
    from defcon import Font

    instance_ufos = []
    for path, data in instance_data:
        ufo = Font(path)
        set_custom_params(ufo, data=data)
        set_default_params(ufo)
        set_redundant_data(ufo)
        ufo.save()
        instance_ufos.append(ufo)
    return instance_ufos
