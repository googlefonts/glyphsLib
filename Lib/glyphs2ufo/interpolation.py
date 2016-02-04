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

from mutatorMath.ufo import build
from mutatorMath.ufo.document import DesignSpaceDocumentWriter
from robofab.world import OpenFont

from glyphs2ufo.torf import set_redundant_data, clear_data, build_style_name, build_postscript_name

__all__ = [
    'interpolate'
]


def interpolate(rfonts, master_dir, out_dir, designspace_path,
                    instance_data, italic=False, debug=False):
    """Create MutatorMath designspace and generate instances.
    Returns instance UFOs, or unused instance data if debug is True.
    """

    print('>>> Writing masters')
    for font in rfonts:
        font.save(os.path.join(
            master_dir, font.info.postscriptFullName + '.ufo'))

    writer = DesignSpaceDocumentWriter(designspace_path)
    base_family = add_masters_to_writer(writer, rfonts)
    instance_files = add_instances_to_writer(
        writer, base_family, instance_data, italic, out_dir)
    writer.save()

    print('>>> Building instances')
    build(designspace_path)

    instance_ufos = []
    for path, data in instance_files:
        ufo = OpenFont(path)
        for attr in data:
            if attr.pop('name') == 'panose':
                ufo.info.openTypeOS2Panose = map(int, attr.pop('value'))
        set_redundant_data(ufo)
        instance_ufos.append(ufo)

    if debug:
        return clear_data(instance_data)
    return instance_ufos


def add_masters_to_writer(writer, rfonts):
    """Add master RFonts to a MutatorMath document writer.

    Returns the masters' base family name, as determined by taking the
    intersection of their individual family names."""

    master_data = []
    base_family = ''

    # build list of <path, family, style, weight, width> tuples for each master
    for font in rfonts:
        family, style = font.info.familyName, font.info.styleName
        if family in base_family or not base_family:
            base_family = family
        elif base_family not in family:
            raise ValueError('Inconsistent family names for masters')
        master_data.append((
            font.path, family, style,
            font.lib['com.google.glyphs2ufo.weightValue'],
            font.lib['com.google.glyphs2ufo.widthValue']))

    # add the masters to the writer in a separate loop, when we have a good
    # candidate to copy metadata from ([base_family] Regular)
    for path, family, style, weight, width in master_data:
        writer.addSource(
            path=path,
            name='%s %s' % (family, style),
            location={'weight': weight, 'width': width},
            copyInfo=(family == base_family and style == 'Regular'))

    return base_family


def add_instances_to_writer(writer, family_name, instances, italic, out_dir):
    """Add instances from Glyphs data to a MutatorMath document writer.

    Returns a list of <ufo_path, custom_font_data> pairs, corresponding to the
    instances which will be output by the document writer. The custom font data
    is Glyphs customParameters data (a list of <attr_name, value> pairs)."""

    ofiles = []
    for instance in instances:

        style_name = build_style_name(
            instance, 'widthClass', 'weightClass', italic)
        ufo_path = os.path.join(
            out_dir, build_postscript_name(family_name, style_name) + '.ufo')
        ofiles.append((ufo_path, instance['customParameters']))

        writer.startInstance(
            name=instance.pop('name'),
            location={'weight': instance.pop('interpolationWeight'),
                      'width': instance.pop('interpolationWidth')},
            familyName=family_name,
            styleName=style_name,
            fileName=ufo_path)

        writer.writeInfo()
        writer.writeKerning()
        writer.endInstance()

    return ofiles
