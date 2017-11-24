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
import os.path
import tempfile
from collections import OrderedDict
from textwrap import dedent

import glyphsLib
from glyphsLib.designSpaceDocument import (DesignSpaceDocument,
                                           InMemoryDocWriter)
from glyphsLib.builder import to_glyphs, to_designspace
from glyphsLib.writer import Writer
from fontTools.misc.py23 import UnicodeIO


def write_to_lines(glyphs_object):
    """
    Use the Writer to write the given object to a UnicodeIO.
    Return an array of lines ready for diffing.
    """
    string = UnicodeIO()
    writer = Writer(string)
    writer.write(glyphs_object)
    return string.getvalue().splitlines()


class AssertLinesEqual(object):
    def assertLinesEqual(self, expected, actual, message):
        if actual != expected:
            if len(actual) < len(expected):
                sys.stderr.write(dedent("""\
                    WARNING: the actual text is shorter that the expected text.
                             Some information may be LOST!
                    """))
            for line in difflib.unified_diff(
                    expected, actual,
                    fromfile="<expected>", tofile="<actual>"):
                if not line.endswith("\n"):
                    line += "\n"
                sys.stderr.write(line)
            self.fail(message)


class AssertParseWriteRoundtrip(AssertLinesEqual):
    def assertParseWriteRoundtrip(self, filename):
        with open(filename) as f:
            expected = f.read().splitlines()
            f.seek(0, 0)
            font = glyphsLib.load(f)
        actual = write_to_lines(font)
        # Roundtrip again to check idempotence
        font = glyphsLib.loads("\n".join(actual))
        actual_idempotent = write_to_lines(font)
        with open('expected.txt', 'w') as f:
            f.write('\n'.join(expected))
        with open('actual.txt', 'w') as f:
            f.write('\n'.join(actual))
        with open('actual_indempotent.txt', 'w') as f:
            f.write('\n'.join(actual_idempotent))
        # Assert idempotence first, because if that fails it's a big issue
        self.assertLinesEqual(
            actual, actual_idempotent,
            "The parser/writer should be idempotent. BIG PROBLEM!")
        self.assertLinesEqual(
            expected, actual,
            "The writer should output exactly what the parser read")


class AssertUFORoundtrip(AssertLinesEqual):
    def _normalize(self, font):
        # Order the kerning OrderedDict alphabetically
        # (because the ordering from Glyphs.app is random and that would be
        # a bit silly to store it only for the purpose of nicer diffs in tests)
        font.kerning = OrderedDict(sorted(map(
            lambda i: (i[0], OrderedDict(sorted(map(
                lambda j: (j[0], OrderedDict(sorted(j[1].items()))),
                i[1].items())
            ))),
            font.kerning.items())))

    def assertUFORoundtrip(self, font):
        self._normalize(font)
        expected = write_to_lines(font)
        # Don't propagate anchors when intending to round-trip
        designspace = to_designspace(font, propagate_anchors=False)

        # Check that round-tripping in memory is the same as writing on disk
        roundtrip_in_mem = to_glyphs(designspace)
        self._normalize(roundtrip_in_mem)
        actual_in_mem = write_to_lines(roundtrip_in_mem)

        directory = tempfile.mkdtemp()
        path = os.path.join(directory, font.familyName + '.designspace')
        designspace.write(path)
        designspace_roundtrip = DesignSpaceDocument(
            writerClass=InMemoryDocWriter)
        designspace_roundtrip.read(path)
        roundtrip = to_glyphs(designspace_roundtrip)
        self._normalize(roundtrip)
        actual = write_to_lines(roundtrip)

        with open('expected.txt', 'w') as f:
            f.write('\n'.join(expected))
        with open('actual_in_mem.txt', 'w') as f:
            f.write('\n'.join(actual_in_mem))
        with open('actual.txt', 'w') as f:
            f.write('\n'.join(actual))
        self.assertLinesEqual(
            actual_in_mem, actual,
            "The round-trip in memory or written to disk should be equivalent")
        self.assertLinesEqual(
            expected, actual,
            "The font should not be modified by the roundtrip")


class AssertDesignspaceRoundtrip(object):
    def assertDesignspaceRoundtrip(self, designspace):
        font = to_glyphs(designspace)
        font.save('test_font.glyphs')
        # roundtrip_in_mem = to_designspace(font)
        # # TODO: tempdir
        # font.save('lol.glyphs')
        # font_rt = GSFont('lol.glyphs')
        # roundtrip = to_designspace(font_rt)
        # # TODO: assert designspace + UFOS are equal!
