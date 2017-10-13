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

from collections import OrderedDict


class GlyphsToUFOContext(object):
    """Builder context for Glyphs to UFO + designspace."""

    def __init__(self, font, defcon):
        """Create a context for the Glyphs to UFO + designspace builder.

        Keyword arguments:
        font -- The GSFont object to transform into UFOs
        defcon -- The defcon module to use to build UFO objects (you can pass
                  a custom module that has the same classes as the official
                  defcon to get instances of your own classes)
        """
        self.font = font
        self.defcon = defcon

        self.ufos = OrderedDict()
        """
        The set of UFOs (= defcon.Font objects) that will be built,
        indexed by master ID, the same order as masters in the source GSFont.
        """

        self.designspace = None
        """The MutatorMath Designspace object that will be built."""


class UFOToGlyphsContext(object):
    """Builder context for UFO + designspace to Glyphs."""

    def __init__(self, ufos, designspace, classes):
        """Create a context for the UFO + designspace to Glyphs builder.

        Keyword arguments:
        ufos -- The list of UFOs to combine into a GSFont
        designspace -- A MutatorMath Designspace to use for the GSFont
        classes -- The glyphsLib.classes module to use to build glyphsLib
                   classes (you can pass a custom module with the same classes
                   as the official glyphsLib.classes to get instances of your
                   own classes)
        """
        self.ufos = ufos
        self.designspace = designspace
        self.classes = classes

        self.font = None
        """The GSFont that will be built."""
