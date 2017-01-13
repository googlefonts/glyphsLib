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
    GLYPHS_PREFIX
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

    master_data = extract_master_data(masters)
    base_family = master_data['baseFamily']
    instance_data = extract_instance_data(instance_data, base_family, out_dir)

    add_masters_to_writer(
        writer, master_data['masters'], master_data['infoSource'])
    add_instances_to_writer(writer, instance_data['instances'])

    base_style = master_data['baseStyle']
    basename = '%s%s.designspace' % (
        base_family, ('-' + base_style) if base_style else '')
    writer.path = os.path.join(master_dir, basename.replace(' ', ''))
    writer.save()
    return writer.path, instance_data['files']


def extract_master_data(ufos):
    """Extract interpolation, family and style data from master UFOs.

    Returns data as a dictionary with four keys: "masters" which is a list of
    (path, family, style, location) tuples for each master, "baseFamily" which
    is the shared family name between masters, "baseStyle" which is the shared
    style between masters (could be an empty string), and "infoSource" which is
    the master from which non-interpolated info should be taken.
    """

    master_list = []
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
        master_list.append((font.path, family, style, {
            s: font.lib.get(GLYPHS_PREFIX + s + 'Value', DEFAULT_LOC)
            for s in dimension_names}))

    # pick a master to copy info, features, and groups from, trying to find the
    # master with a base style shared between all masters (or just Regular) and
    # defaulting to the first master if nothing is found
    base_style = ' '.join(base_style)
    info_source = 0
    for i, (path, family, style, location) in enumerate(master_list):
        if family == base_family and style == (base_style or 'Regular'):
            info_source = i
            break

    return {
        'masters': master_list,
        'baseFamily': base_family,
        'baseStyle': base_style,
        'infoSource': info_source,
    }


def add_masters_to_writer(writer, masters, info_source):
    """Add master UFOs to a MutatorMath document writer."""

    for i, (path, family, style, location) in enumerate(masters):
        is_base = (i == info_source)
        writer.addSource(
            path=path, name='%s %s' % (family, style),
            familyName=family, styleName=style, location=location,
            copyFeatures=is_base, copyGroups=is_base, copyInfo=is_base,
            copyLib=is_base)


def extract_instance_data(instance_data, master_family, out_dir):
    """Extract interpolation, family and style data from Glyphs instance data.

    Returns data as a dictionary with two keys: "instances" which is a list of
    (path, family, style, location) tuples for each instance, and "files" which
    is a list of (path, instance_data) tuples mapping the path of each instance
    to its original Glyphs instance data, for use in apply_instance_data.
    """

    default_family = instance_data.pop('defaultFamilyName')
    instance_data = instance_data.pop('data')

    # only write dimension elements if defined in at least one of the instances
    dimension_names = []
    for s in ('weight', 'width', 'custom'):
        key = 'interpolation' + s.title()
        if any(key in instance for instance in instance_data):
            dimension_names.append(s)

    instance_list = []
    files = []
    for instance in instance_data:
        if not instance.pop('active', True):
            continue

        # only use instances with the masters' family name
        family = default_family
        custom_params = instance.get('customParameters', ())
        for i in range(len(custom_params)):
            if custom_params[i]['name'] == 'familyName':
                family = custom_params[i]['value']
                del custom_params[i]
                break
        if family != master_family:
            continue

        style = instance.pop('name')
        path = build_ufo_path(out_dir, family, style)
        instance_list.append((path, family, style, {
            s: instance.pop('interpolation' + s.title(), DEFAULT_LOC)
            for s in dimension_names}))
        files.append((path, instance))

    return {
        'instances': instance_list,
        'files': files,
    }


def add_instances_to_writer(writer, instances):
    """Add instances from Glyphs data to a MutatorMath document writer."""

    for path, family, style, location in instances:
        writer.startInstance(
            name=' '.join((family, style)),
            location=location,
            familyName=family,
            styleName=style,
            fileName=path)

        writer.writeInfo()
        writer.writeKerning()
        writer.endInstance()


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
        set_redundant_data(ufo)
        ufo.save()
        instance_ufos.append(ufo)
    return instance_ufos
