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

from glyphsLib.builder.builders import UFOBuilder
from glyphsLib.builder.custom_params import to_ufo_custom_params
from glyphsLib.builder.names import build_stylemap_names
from glyphsLib.builder.constants import GLYPHS_PREFIX
from glyphsLib.builder.instances import apply_instance_data, InstanceData

from glyphsLib.util import build_ufo_path, write_ufo, clean_ufo

__all__ = [
    'interpolate', 'build_designspace', 'apply_instance_data'
]

logger = logging.getLogger(__name__)


# DEPRECATED
def interpolate(ufos, master_dir, out_dir, instance_data, round_geometry=True):
    """Create MutatorMath designspace and generate instances.
    Returns instance UFOs.
    """
    # Problem with this function: should take a designspace explicitly.
    from mutatorMath.ufo import build

    designspace_path, instance_files = build_designspace(
        ufos, master_dir, out_dir, instance_data)

    logger.info('Building instances')
    for path, _ in instance_files:
        clean_ufo(path)
    build(designspace_path, outputUFOFormatVersion=3,
          roundGeometry=round_geometry)

    instance_ufos = apply_instance_data(instance_files)
    return instance_ufos


# DEPRECATED
def build_designspace(masters, master_dir, out_dir, instance_data):
    """Just create MutatorMath designspace without generating instances.

    Returns the path of the resulting designspace document and a list of
    (instance_path, instance_data) tuples which map instance UFO filenames to
    Glyphs data for that instance.
    """
    # TODO: (jany) check whether this function is still useful
    # No need to build a designspace, we should have it in "instance_data"
    designspace = instance_data['designspace']

    # Move masters and instances to the designated directories
    for font in masters:
        write_ufo(font, master_dir)
        for source in designspace.sources:
            if source.font is font:
                source.path = font.path
    for instance in designspace.instances:
        instance.path = os.path.join(out_dir,
                                     os.path.basename(instance.filename))

    designspace_path = os.path.join(master_dir, designspace.filename)
    designspace.write(designspace_path)

    return designspace_path, InstanceData(designspace)
