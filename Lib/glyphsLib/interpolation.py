# coding: utf-8
#
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

import logging
import os

from glyphsLib.builder import set_redundant_data, set_custom_params,\
    set_default_params, GLYPHS_PREFIX
from glyphsLib.util import build_ufo_path, write_ufo, clean_ufo, clear_data

__all__ = [
    'interpolate', 'build_designspace', 'apply_instance_data'
]

logger = logging.getLogger(__name__)

DEFAULT_LOC = 100


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

    base_family, base_style, master_names = add_masters_to_writer(
        writer, masters)
    instance_files = add_instances_to_writer(
        writer, base_family, master_names, instance_data, out_dir)

    basename = '%s%s.designspace' % (
        base_family, ('-' + base_style) if base_style else '')
    writer.path = os.path.join(master_dir, basename.replace(' ', ''))
    writer.save()
    return writer.path, instance_files


def add_masters_to_writer(writer, ufos):
    """Add master UFOs to a MutatorMath document writer.

    Returns the masters' family name and shared style names. These are used for
    naming instances and the designspace path.
    """

    master_data = []
    base_family = None
    base_style = None

    # only write dimension elements if defined in at least one of the masters
    dimension_names = []
    for s in ('weight', 'width', 'custom'):
        key = GLYPHS_PREFIX + s + 'Value'
        if any(key in font.lib for font in ufos):
            dimension_names.append(s)

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
        master_data.append((font.path, family, style, {
            s: font.lib.get(GLYPHS_PREFIX + s + 'Value', DEFAULT_LOC)
            for s in dimension_names}))

    # pick a master to copy info, features, and groups from, trying to find the
    # master with a base style shared between all masters (or just Regular) and
    # defaulting to the first master if nothing is found
    base_style = ' '.join(base_style)
    info_source = 0
    for i, (path, family, style, location) in enumerate(master_data):
        if family == base_family and style == (base_style or 'Regular'):
            info_source = i
            break

    master_names = []
    for i, (path, family, style, location) in enumerate(master_data):
        is_base = (i == info_source)
        name = '%s %s' % (family, style)
        master_names.append(name)
        writer.addSource(
            path=path, name=name,
            familyName=family, styleName=style, location=location,
            copyFeatures=is_base, copyGroups=is_base, copyInfo=is_base,
            copyLib=is_base)

    return base_family, base_style, master_names


def add_instances_to_writer(writer, family_name, master_names,
                            instance_data, out_dir):
    """Add instances from Glyphs data to a MutatorMath document writer.

    Returns a list of <ufo_path, font_data> pairs, corresponding to the
    instances which will be output by the document writer. The font data is the
    Glyphs data for this instance as a dict.
    """

    default_family_name = instance_data.pop('defaultFamilyName')
    instance_data = instance_data.pop('data')
    ofiles = []

    # only write dimension elements if defined in at least one of the instances
    dimension_names = []
    for s in ('weight', 'width', 'custom'):
        key = 'interpolation' + s.title()
        if any(key in instance for instance in instance_data):
            dimension_names.append(s)

    for instance in instance_data:
        if not instance.pop('active', True):
            continue

        renamed_glyphs = _get_renamed_glyphs(instance)
        removed_glyphs = _get_removed_glyphs(instance)
        instance_family = default_family_name
        custom_params = instance.get('customParameters', ())
        for param in custom_params:
            param_name = param.get('name')
            if param_name == 'familyName':
                instance_family = param['value']
        if not instance_family:
            continue

        style_name = instance.pop('name')
        ufo_path = build_ufo_path(out_dir, instance_family, style_name)
        ofiles.append((ufo_path, instance))

        writer.startInstance(
            name=' '.join((instance_family, style_name)),
            location={
                s: instance.pop('interpolation' + s.title(), DEFAULT_LOC)
                for s in dimension_names},
            familyName=instance_family,
            styleName=style_name,
            fileName=ufo_path)

        writer.writeInfo()
        writer.writeKerning()

        # Rename glyphs [w]ill exchange the glyphs mentioned in the
        # value with each other. Takes a list of rename strings of the
        # form ‘oldname=newname’, e.g. ‘e.bold=e, g.alt=g’. The glyph
        # previously stored as newname will now be called oldname
        # and vice versa.
        # https://glyphsapp.com/content/1-get-started/2-manuals/1-handbook-glyphs-2-0/Glyphs-Handbook-2.3.pdf#page=194
        for oldName, newName in sorted(renamed_glyphs.items()):
            if oldName not in removed_glyphs:
                writer.writeGlyph(
                    name=oldName,
                    masters=[(newName, m, None) for m in master_names])
            if newName not in removed_glyphs:
                writer.writeGlyph(
                    name=newName,
                    masters=[(oldName, m, None) for m in master_names])

        for glyph in sorted(removed_glyphs):
            writer.writeGlyph(name=glyph, mute=True)

        writer.endInstance()

    return ofiles


def _get_renamed_glyphs(instance):
    """Returns a mapping from master to instance glyphs, eg. {"A.alt": "A"}."""
    result = {}
    if not instance.get("active", True):
        return result
    custom_params = instance.get("customParameters", ())
    for param in custom_params:
        param_name = param.get("name")
        if param_name == "Rename Glyphs":
            for val in param.get("value", []):
                from_glyph, to_glyph = val.split("=", 1)
                result[from_glyph] = to_glyph
    return result


def _get_removed_glyphs(instance):
    """Return the set of glyphs removed by an instance, eg. {"A", "B"}."""
    result = set()
    if not instance.get("active", True):
        return result
    custom_params = instance.get("customParameters", ())
    for param in custom_params:
        param_name = param.get("name")
        if param_name == "Remove Glyphs":
            result.update(param.get("value", []))
    return result


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
