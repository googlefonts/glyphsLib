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


from __future__ import print_function, division, absolute_import, unicode_literals

from io import open
import collections
import os
import logging

from fontTools.misc.py23 import tostr

from glyphsLib.classes import __all__ as __all_classes__
from glyphsLib.classes import *
from glyphsLib.builder import to_ufos, to_designspace, to_glyphs
from glyphsLib.parser import load, loads
from glyphsLib.writer import dump, dumps
from glyphsLib.util import clean_ufo, ufo_create_background_layer_for_all_glyphs

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0+unknown"

# Doing `import *` from a module that uses unicode_literals, produces
# "TypeError: Item in ``from list'' must be str, not unicode" on Python 2.
# Thus we need to encode the unicode literals as ascii bytes.
# https://bugs.python.org/issue21720
__all__ = [
    tostr(s)
    for s in [
        "build_masters",
        "build_instances",
        "load_to_ufos",
        "load",
        "loads",
        "dump",
        "dumps",
    ]
    + __all_classes__
]

logger = logging.getLogger(__name__)

Masters = collections.namedtuple("Masters", ["ufos", "designspace_path"])


def load_to_ufos(
    file_or_path, include_instances=False, family_name=None, propagate_anchors=True
):
    """Load an unpacked .glyphs object to UFO objects."""

    if hasattr(file_or_path, "read"):
        font = load(file_or_path)
    else:
        with open(file_or_path, "r", encoding="utf-8") as ifile:
            font = load(ifile)
    logger.info("Loading to UFOs")
    return to_ufos(
        font,
        include_instances=include_instances,
        family_name=family_name,
        propagate_anchors=propagate_anchors,
    )


def build_masters(
    filename,
    master_dir,
    designspace_instance_dir=None,
    designspace_path=None,
    family_name=None,
    propagate_anchors=True,
    minimize_glyphs_diffs=False,
    normalize_ufos=False,
    create_background_layers=False,
):
    """Write and return UFOs from the masters and the designspace defined in a
    .glyphs file.

    Args:
        master_dir: Directory where masters are written.
        designspace_instance_dir: If provided, a designspace document will be
            written alongside the master UFOs though no instances will be built.
        family_name: If provided, the master UFOs will be given this name and
            only instances with this name will be included in the designspace.

    Returns:
        A named tuple of master UFOs (`ufos`) and the path to the designspace
        file (`designspace_path`).
    """

    font = GSFont(filename)

    if designspace_instance_dir is None:
        instance_dir = None
    else:
        instance_dir = os.path.relpath(designspace_instance_dir, master_dir)

    designspace = to_designspace(
        font,
        family_name=family_name,
        propagate_anchors=propagate_anchors,
        instance_dir=instance_dir,
        minimize_glyphs_diffs=minimize_glyphs_diffs,
    )

    ufos = []
    for source in designspace.sources:
        ufos.append(source.font)

        if create_background_layers:
            ufo_create_background_layer_for_all_glyphs(source.font)

        ufo_path = os.path.join(master_dir, source.filename)
        clean_ufo(ufo_path)
        source.font.save(ufo_path)

        if normalize_ufos:
            import ufonormalizer

            ufonormalizer.normalizeUFO(ufo_path, writeModTimes=False)

    if not designspace_path:
        designspace_path = os.path.join(master_dir, designspace.filename)
    designspace.write(designspace_path)

    return Masters(ufos, designspace_path)
