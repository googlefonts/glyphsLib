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
from glyphsLib.builder.instances import apply_instance_data

from glyphsLib.util import build_ufo_path, write_ufo, clean_ufo

__all__ = [
    'interpolate', 'build_designspace', 'apply_instance_data'
]

logger = logging.getLogger(__name__)


def interpolate(ufos, master_dir, out_dir, instance_data, round_geometry=True):
    """Create MutatorMath designspace and generate instances.
    Returns instance UFOs.
    """
    # TODO: (jany) This should not be in glyphsLib, but rather an instance
    #    method of the designspace document, or another thing like
    #    ufoProcessor/mutatorMath.build()
    #    GlyphsLib should put all that is necessary to interpolate into the
    #    InstanceDescriptor (lib if needed)
    #    All the logic like applying custom parameters and so on should be made
    #    glyphs-agnostic (because most of it should be relevant for other build
    #    systems as well?)
    #    or the logic that is really specific to Glyphs could be implemented as
    #    in apply_instance_data: InstanceDescriptor -> UFO of the instance.
    raise NotImplementedError


def build_designspace(masters, master_dir, out_dir, instance_data):
    """Just create MutatorMath designspace without generating instances.

    Returns the path of the resulting designspace document and a list of
    (instance_path, instance_data) tuples which map instance UFO filenames to
    Glyphs data for that instance.
    """
    # TODO: (jany) check whether this function is still useful
    raise NotImplementedError
