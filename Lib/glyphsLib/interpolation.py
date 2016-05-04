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


from __future__ import print_function, division, absolute_import

import os

from glyphsLib.builder import set_redundant_data, set_custom_params,\
    clear_data, write_ufo, build_ufo_path, clean_ufo, GLYPHS_PREFIX

__all__ = [
    'interpolate', 'build_designspace'
]


DEFAULT_LOC = 100


def interpolate(ufos, master_dir, out_dir, instance_data, debug=False):
    """Create MutatorMath designspace and generate instances.
    Returns instance UFOs, or unused instance data if debug is True.
    """
    from defcon import Font
    from mutatorMath.ufo import build

    designspace_path, instance_files = build_designspace(
        ufos, master_dir, out_dir, instance_data)

    print('>>> Building instances')
    for path, _ in instance_files:
        clean_ufo(path)
    build(designspace_path, outputUFOFormatVersion=3)

    instance_ufos = []
    for path, data in instance_files:
        ufo = Font(path)
        set_custom_params(ufo, data=data)
        set_redundant_data(ufo)
        ufo.save()
        instance_ufos.append(ufo)

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

    base_family, base_style = add_masters_to_writer(writer, masters)
    instance_files = add_instances_to_writer(
        writer, base_family, instance_data, out_dir)

    basename = '%s%s.designspace' % (
        base_family, ('-' + base_style) if base_style else '')
    writer.path = os.path.join(master_dir, basename.replace(' ', ''))
    writer.save()
    return writer.path, instance_files


def add_masters_to_writer(writer, ufos):
    """Add master UFOs to a MutatorMath document writer.

    Returns the masters' base family and style names, as determined by taking
    the intersection of their individual family/style names. This is used for
    naming instances and the designspace path.
    """

    base_family = ''
    base_style = ''
    specify_info_source = True

    for font in ufos:
        family, style = font.info.familyName, font.info.styleName
        if family in base_family or not base_family:
            base_family = family
        elif base_family not in family:
            raise ValueError('Inconsistent family names for masters')
        if style in base_style or not base_style:
            base_style = style
        writer.addSource(
            path=font.path,
            name='%s %s' % (family, style),
            familyName=family, styleName=style,
            location={
                s: font.lib.get(GLYPHS_PREFIX + s + 'Value', DEFAULT_LOC)
                for s in ('weight', 'width', 'custom')},
            copyFeatures=specify_info_source, copyGroups=specify_info_source,
            copyInfo=specify_info_source)
        specify_info_source = False

    return base_family, base_style


def add_instances_to_writer(writer, family_name, instances, out_dir):
    """Add instances from Glyphs data to a MutatorMath document writer.

    Returns a list of <ufo_path, font_data> pairs, corresponding to the
    instances which will be output by the document writer. The font data is the
    Glyphs data for this instance as a dict.
    """

    ofiles = []
    for instance in instances:

        if not instance.pop('active', True):
            continue

        # use family name in instance data if available
        instance_family = family_name
        custom_params = instance.get('customParameters', ())
        for i in range(len(custom_params)):
            if custom_params[i]['name'] == 'familyName':
                instance_family = custom_params[i]['value']
                del custom_params[i]
                break

        style_name = instance.pop('name')
        ufo_path = build_ufo_path(out_dir, instance_family, style_name)
        ofiles.append((ufo_path, instance))

        writer.startInstance(
            name=' '.join((instance_family, style_name)),
            location={
                s: instance.pop('interpolation' + s.title(), DEFAULT_LOC)
                for s in ('weight', 'width', 'custom')},
            familyName=instance_family,
            styleName=style_name,
            fileName=ufo_path)

        writer.writeInfo()
        writer.writeKerning()
        writer.endInstance()

    return ofiles
