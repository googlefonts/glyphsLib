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

from __future__ import (print_function, division, absolute_import,
                        unicode_literals)

import unittest
import subprocess
import os

import test_helpers


class MainTest(unittest.TestCase, test_helpers.AssertLinesEqual):
    def test_parser_main(self):
        """This is both a test for the "main" functionality of glyphsLib.parser
        and for the round-trip of GlyphsUnitTestSans.glyphs.
        """
        filename = os.path.join(
            os.path.dirname(__file__), 'data/GlyphsUnitTestSans.glyphs')
        with open(filename) as f:
            expected = f.read()
        out = subprocess.check_output(
            ['python', '-m', 'glyphsLib.parser', filename],
            universal_newlines=True)  # Windows gives \r\n otherwise
        self.assertLinesEqual(
            str(expected.splitlines()),
            str(out.splitlines()),
            'The roundtrip should output the .glyphs file unmodified.')
