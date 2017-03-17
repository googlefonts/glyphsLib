#!/usr/bin/python
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

from io import open
import logging

from glyphsLib import glyphdata_generated
from glyphsLib.builder import to_ufos
from glyphsLib.casting import cast_data
from glyphsLib.interpolation import interpolate, build_designspace
from glyphsLib.parser import Parser
from glyphsLib.util import fetch, write_ufo, fetch_all_glyphs, build_data, test_data, GlyphData


__version__ = "1.5.3.dev0"

__all__ = [
    "build_masters", "build_instances", "load_to_ufos", "load", "loads",
]

logger = logging.getLogger(__name__)


def load(fp):
    """Read a .glyphs file. 'fp' should be (readable) file object.
    Return the unpacked root object (an ordered dictionary).
    """
    return loads(fp.read())


def loads(value):
    """Read a .glyphs file from a bytes object.
    Return the unpacked root object (an ordered dictionary).
    """
    p = Parser()
    logger.info('Parsing .glyphs file')
    data = p.parse(value)
    logger.info('Casting parsed values')
    cast_data(data)
    return data


def load_glyph_data(data=glyphdata_generated, glyphs_source=None, custom_glyph_xml=None):
    """Load GlyphData.xml
    If a custom GlyphData.xml exists merge it with the default GlyphData.xml
    Two overrides are possible:
        1. Reading from a custom GlyphData.xml
        2. Manually changing the info in Glyphs app
    Args:
        data: pre-generated glyph data
        glyphs_source: unpacked .glyphs object
        custom_glyph_xml: Path to a custom GlyphData.xml file
    """
    glyph_dict = data.DEFAULT_GLYPH_DICT.copy()
    if custom_glyph_xml:
        custom_glyphs = {}
        lines = None
        with open(custom_glyph_xml, 'r') as f:
            lines = f.read()
        if lines:
            custom_glyphs = fetch_all_glyphs(paths=(lines,))
        glyph_dict.update(custom_glyphs)

    # Check the .glyphs file for any overrides
    if glyphs_source:
        for g in glyphs_source['glyphs']:
            name = g.get('glyphname')
            category = g.get('category')
            subCategory = g.get('subCategory')
            if g.get('category') is None and g.get('subCategory') is None:
                continue
            if name in glyph_dict:
                glyph_dict[name]['category'] = category
                glyph_dict[name]['subCategory'] = subCategory
            else:
                glyphs_gdef = {name: {}}
                glyphs_gdef[name]['category'] = category
                glyphs_gdef[name]['subCategory'] = subCategory
                glyph_dict.update(glyphs_gdef)

    glyph_data = build_data(glyph_dict)
    test_data(glyph_dict, glyph_data)
    logger.info('Loading custom GlyphData.xml')
    return glyph_data


def load_to_ufos(file_or_path, include_instances=False, family_name=None,
                 debug=False, custom_glyph_xml=None):
    """Load an unpacked .glyphs object to UFO objects."""

    if hasattr(file_or_path, 'read'):
        data = load(file_or_path)
    else:
        with open(file_or_path, 'r', encoding='utf-8') as ifile:
            data = load(ifile)

    glyph_data = load_glyph_data(glyphs_source=data, custom_glyph_xml=custom_glyph_xml)

    logger.info('Loading to UFOs')
    return to_ufos(data, include_instances=include_instances,
                   family_name=family_name, debug=debug, glyph_data=glyph_data)


def build_masters(filename, master_dir, designspace_instance_dir=None,
                  family_name=None, custom_glyph_xml=None):
    """Write and return UFOs from the masters defined in a .glyphs file.

    Args:
        master_dir: Directory where masters are written.
        designspace_instance_dir: If provided, a designspace document will be
            written alongside the master UFOs though no instances will be built.
        family_name: If provided, the master UFOs will be given this name and
            only instances with this name will be included in the designspace.
        custom_glyph_xml: Path to a custom GlyphData.xml file.

    Returns:
        A list of master UFOs, and if designspace_instance_dir is provided, a
        path to a designspace and a list of (path, data) tuples with instance
        paths from the designspace and respective data from the Glyphs source.
    """

    ufos, instance_data = load_to_ufos(
        filename, include_instances=True, family_name=family_name, custom_glyph_xml=custom_glyph_xml)
    if designspace_instance_dir is not None:
        designspace_path, instance_data = build_designspace(
            ufos, master_dir, designspace_instance_dir, instance_data)
        return ufos, designspace_path, instance_data
    else:
        for ufo in ufos:
            write_ufo(ufo, master_dir)
        return ufos


def build_instances(filename, master_dir, instance_dir, family_name=None, custom_glyph_xml=None):
    """Write and return UFOs from the instances defined in a .glyphs file.

    Args:
        master_dir: Directory where masters are written.
        instance_dir: Directory where instances are written.
        family_name: If provided, the master UFOs will be given this name and
            only instances with this name will be built.
        custom_glyph_xml: Path to a custom GlyphData.xml file.
    """

    master_ufos, instance_data = load_to_ufos(
        filename, include_instances=True, family_name=family_name, custom_glyph_xml=custom_glyph_xml)
    instance_ufos = interpolate(
        master_ufos, master_dir, instance_dir, instance_data)
    return instance_ufos
