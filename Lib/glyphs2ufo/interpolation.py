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

from defcon import Font
from mutatorMath.ufo import build
from mutatorMath.ufo.document import DesignSpaceDocumentWriter

from glyphs2ufo.builder import set_redundant_data, set_custom_params,\
    clear_data, build_family_name, build_style_name,\
    write_ufo, build_ufo_path, GLYPHS_PREFIX

__all__ = [
    'interpolate', 'build_designspace'
]


DEFAULT_LOC = 100


def interpolate(ufos, master_dir, out_dir, designspace_path,
                instance_data, italic=False, debug=False):
    """Create MutatorMath designspace and generate instances.
    Returns instance UFOs, or unused instance data if debug is True.
    """

    instance_files = build_designspace(
        designspace_path, ufos, master_dir, out_dir, instance_data, italic)

    print('>>> Building instances')
    build(designspace_path)

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


def build_designspace(designspace_path, masters, master_dir, out_dir,
                      instance_data, italic=False):
    """Just create MutatorMath designspace without generating instances.
    Returns a list of (instance_path, instance_data) tuples which map instance
    UFO filenames to Glyphs data for that instance.
    """

    for font in masters:
        write_ufo(font, master_dir)

    writer = DesignSpaceDocumentWriter(designspace_path)
    base_family = add_masters_to_writer(writer, masters)
    instance_files = add_instances_to_writer(
        writer, base_family, instance_data, italic, out_dir)
    writer.save()
    return instance_files


def add_masters_to_writer(writer, ufos):
    """Add master UFOs to a MutatorMath document writer.

    Returns the masters' base family name, as determined by taking the
    intersection of their individual family names."""

    master_data = []
    base_family = ''

    # build list of <path, family, style, weight, width> tuples for each master
    for font in ufos:
        family, style = font.info.familyName, font.info.styleName
        if family in base_family or not base_family:
            base_family = family
        elif base_family not in family:
            raise ValueError('Inconsistent family names for masters')
        master_data.append((
            font.path, family, style,
            font.lib.get(GLYPHS_PREFIX + 'weightValue', DEFAULT_LOC),
            font.lib.get(GLYPHS_PREFIX + 'widthValue', DEFAULT_LOC)))

    # add the masters to the writer in a separate loop, when we have a good
    # candidate to copy metadata from ([base_family] Regular|Italic)
    for path, family, style, weight, width in master_data:
        is_base = family == base_family and style in ['Regular', 'Italic']
        writer.addSource(
            path=path,
            name='%s %s' % (family, style),
            location={'weight': weight, 'width': width},
            copyFeatures=is_base, copyGroups=is_base, copyInfo=is_base)

    return base_family


def add_instances_to_writer(writer, base_family, instances, italic, out_dir):
    """Add instances from Glyphs data to a MutatorMath document writer.

    Returns a list of <ufo_path, font_data> pairs, corresponding to the
    instances which will be output by the document writer. The font data is the
    Glyphs data for this instance as a dict.
    """

    ofiles = []
    for instance in instances:

        # use family name in instance data if available
        instance_family = base_family
        custom_params = instance.get('customParameters', ())
        for i in range(len(custom_params)):
            if custom_params[i]['name'] == 'familyName':
                instance_family = custom_params[i]['value']
                del custom_params[i]
                break

        family_name = build_family_name(instance_family, instance, 'widthClass')
        style_name = build_style_name(instance, 'weightClass', italic)
        ufo_path = build_ufo_path(out_dir, family_name, style_name)
        ofiles.append((ufo_path, instance))

        writer.startInstance(
            name=instance.pop('name'),
            location={
                'weight': instance.pop('interpolationWeight', DEFAULT_LOC),
                'width': instance.pop('interpolationWidth', DEFAULT_LOC)},
            familyName=family_name,
            styleName=style_name,
            fileName=ufo_path)

        writer.writeInfo()
        writer.writeKerning()
        writer.endInstance()

    return ofiles
