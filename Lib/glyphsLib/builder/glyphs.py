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

from glyphsLib import classes

from .constants import GLYPHS_PREFIX

# def designspace_from_ufos(ufos):
#     pass

# def to_glyphs(designspace):
#     # For later
#     """Transform a MutatorMath designspace into a GSFont.

#     This should be the inverse function of `to_designspace` from `builder.py`,
#     so we should have to_glyphs(to_designspace(font)) == font
#     """
#     pass


def to_glyphs(ufos):
    """
    Take a list of UFOs and combine them into a single .glyphs file.

    This should be the inverse function of `to_ufos` from `builder.py`,
    so we should have to_glyphs(to_ufos(font)) == font
    """
    font = classes.GSFont()
    for ufo in ufos:
        master = to_glyphs_master(ufo)
        font.masters.insert(len(font.masters), master)
    return font


def to_glyphs_master(ufo):
    """
    Extract from the given UFO the data that goes into a GSFontMaster.
    """
    master = classes.GSFontMaster()
    master.id = ufo.lib[GLYPHS_PREFIX + 'fontMasterID']
    return master
