# coding=UTF-8
#
# Copyright 2016 Google Inc. All Rights Reserved.
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

import difflib
import sys

from glyphsLib.writer import GlyphsWriter
from fontTools.misc.py23 import StringIO


def write_to_lines(glyphs_object):
    """
    Use the Writer to write the given object to a StringIO.
    Return an array of lines ready for diffing.
    """
    string = StringIO()
    writer = GlyphsWriter(fp=string)
    writer.write(glyphs_object)
    return string.getvalue().splitlines()


class AssertLinesEqual(object):
    def assertLinesEqual(self, expected, actual, message):
        if actual != expected:
            for line in difflib.unified_diff(
                    expected, actual,
                    fromfile="<expected>", tofile="<actual>"):
                if not line.endswith("\n"):
                    line += "\n"
                sys.stderr.write(line)
            self.fail(message)
