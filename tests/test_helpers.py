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
from textwrap import dedent

import glyphsLib
from glyphsLib.builder import to_glyphs, to_ufos
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
        # Assert idempotence first, because if that fails it's a big issue
        self.assertLinesEqual(
            actual, actual_idempotent,
            "The parser/writer should be idempotent. BIG PROBLEM!")
        self.assertLinesEqual(
            expected, actual,
            "The writer should output exactly what the parser read")

class AssertUFORoundtrip(AssertLinesEqual):
    def assertUFORoundtrip(self, font):
        expected = write_to_lines(font)
        roundtrip = to_glyphs(to_ufos(font))
        actual = write_to_lines(roundtrip)
        self.assertLinesEqual(
            expected, actual,
            "The font has been modified by the roundtrip")
