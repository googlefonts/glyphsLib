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


from __future__ import print_function, division, absolute_import

import sys

from glyphsLib.builder import to_ufos, write_ufo
from glyphsLib.casting import cast_data
from glyphsLib.interpolation import interpolate, build_designspace
from glyphsLib.parser import Parser

__all__ = [
    "build_masters", "build_instances", "load_to_ufos", "load", "loads",
]


def load(fp, dict_type=dict):
    """Read a .glyphs file. 'fp' should be (readable) file object.
    Return the unpacked root object (which usually is a dictionary).
    """
    return loads(fp.read(), dict_type=dict_type)


def loads(value, dict_type=dict):
    """Read a .glyphs file from a bytes object.
    Return the unpacked root object (which usually is a dictionary).
    """
    p = Parser(dict_type=dict_type)
    print('>>> Parsing .glyphs file')
    data = p.parse(value)
    print('>>> Casting parsed values')
    cast_data(data)
    return data


def load_to_ufos(filename, include_instances=False, debug=False):
    """Load an unpacked .glyphs object to UFO objects."""

    with open(filename, 'rb') as ifile:
        data = load(ifile)
    print('>>> Loading to UFOs')
    return to_ufos(data, include_instances=include_instances, debug=debug)


def build_masters(filename, master_dir, designspace_instance_dir=None):
    """Write and return UFOs from the masters defined in a .glyphs file.

    If `designspace_instance_dir` is provided, a designspace document will be
    written alongside the master UFOs, though no instances will be built.
    """

    ufos, instance_data = load_to_ufos(filename, include_instances=True)
    if designspace_instance_dir is not None:
        build_designspace(ufos, master_dir, designspace_instance_dir,
                          instance_data)
    else:
        for ufo in ufos:
            write_ufo(ufo, master_dir)
    return ufos


def build_instances(filename, master_dir, instance_dir):
    """Write and return UFOs from the instances defined in a .glyphs file."""

    master_ufos, instance_data = load_to_ufos(
        filename, include_instances=True)
    instance_ufos = interpolate(
        master_ufos, master_dir, instance_dir, instance_data)
    return instance_ufos
