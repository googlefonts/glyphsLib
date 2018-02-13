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

from fontTools.misc.py23 import tostr

from glyphsLib.builder import to_ufos
from glyphsLib.interpolation import interpolate, build_designspace
from glyphsLib.util import write_ufo

from glyphsLib.classes import __all__ as __all_classes__
from glyphsLib.classes import *

__version__ = "2.2.2.dev0"

# Doing `import *` from a module that uses unicode_literals, produces
# "TypeError: Item in ``from list'' must be str, not unicode" on Python 2.
# Thus we need to encode the unicode literals as ascii bytes.
# https://bugs.python.org/issue21720
__all__ = [tostr(s) for s in [
    "build_masters", "build_instances"
 ] + __all_classes__]

logger = logging.getLogger(__name__)

def build_masters(filename, master_dir, designspace_instance_dir=None,
                  family_name=None, propagate_anchors=True):
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
    font = GSFont(filename)
    ufos, instance_data = to_ufos(
        font, include_instances=True, family_name=family_name,
        propagate_anchors=propagate_anchors)
    if designspace_instance_dir is not None:
        designspace_path, instance_data = build_designspace(
            font, ufos, master_dir, designspace_instance_dir, instance_data)
        return ufos, designspace_path, instance_data
    else:
        for ufo in ufos:
            write_ufo(ufo, master_dir)
        return ufos


def build_instances(filename, master_dir, instance_dir, family_name=None,
                    propagate_anchors=True, round_geometry=True):
    """Write and return UFOs from the instances defined in a .glyphs file.

    Args:
        master_dir: Directory where masters are written.
        instance_dir: Directory where instances are written.
        family_name: If provided, the master UFOs will be given this name and
            only instances with this name will be built.
    """
    font = GSFont(filename)
    master_ufos, instance_data = to_ufos(
        font, include_instances=True, family_name=family_name,
        propagate_anchors=propagate_anchors)
    instance_ufos = interpolate(
        font, master_ufos, master_dir, instance_dir, instance_data,
        round_geometry=round_geometry)
    return instance_ufos
