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

from glyphsLib.builder import to_ufos
from glyphsLib.casting import cast_data
from glyphsLib.interpolation import interpolate, build_designspace
from glyphsLib.parser import Parser
from glyphsLib.util import write_ufo


__version__ = "1.2.0"

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


def load_to_ufos(file_or_path, include_instances=False, family_name=None,
                 debug=False):
    """Load an unpacked .glyphs object to UFO objects."""

    if hasattr(file_or_path, 'read'):
        data = load(file_or_path)
    else:
        with open(file_or_path, 'r', encoding='utf-8') as ifile:
            data = load(ifile)
    logger.info('Loading to UFOs')
    return to_ufos(data, include_instances=include_instances,
                   family_name=family_name, debug=debug)


def build_masters(filename, master_dir, designspace_instance_dir=None,
                  family_name=None):
    """Write and return UFOs from the masters defined in a .glyphs file.

    Args:
        master_dir: Directory where masters are written.
        designspace_instance_dir: If provided, a designspace document will be
            written alongside the master UFOs though no instances will be built.
        family_name: If provided, the master UFOs will be given this name and
            only instances with this name will be included in the designspace.

    Returns:
        A list of master UFOs, and if designspace_instance_dir is provided, a
        path to a designspace and a list of (path, data) tuples with instance
        paths from the designspace and respective data from the Glyphs source.
    """

    ufos, instance_data = load_to_ufos(
        filename, include_instances=True, family_name=family_name)
    if designspace_instance_dir is not None:
        designspace_path, instance_data = build_designspace(
            ufos, master_dir, designspace_instance_dir, instance_data)
        return ufos, designspace_path, instance_data
    else:
        for ufo in ufos:
            write_ufo(ufo, master_dir)
        return ufos


def build_instances(filename, master_dir, instance_dir, family_name=None):
    """Write and return UFOs from the instances defined in a .glyphs file.

    Args:
        master_dir: Directory where masters are written.
        instance_dir: Directory where instances are written.
        family_name: If provided, the master UFOs will be given this name and
            only instances with this name will be built.
    """

    master_ufos, instance_data = load_to_ufos(
        filename, include_instances=True, family_name=family_name)
    instance_ufos = interpolate(
        master_ufos, master_dir, instance_dir, instance_data)
    return instance_ufos
