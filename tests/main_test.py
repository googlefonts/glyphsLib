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
import glob

import glyphsLib.__main__
import glyphsLib.parser


def test_glyphs_main_masters(tmpdir):
    """Tests the main of glyphsLib and also the `build_masters` function
    that `fontmake` uses.
    """
    filename = os.path.join(
        os.path.dirname(__file__), 'data/GlyphsUnitTestSans.glyphs')
    master_dir = os.path.join(str(tmpdir), 'master_ufos_test')

    glyphsLib.__main__.main(['-g', filename, '-m', master_dir])

    assert glob.glob(master_dir + '/*.ufo')


def test_glyphs_main_instances(tmpdir):
    filename = os.path.join(
        os.path.dirname(__file__), 'data/GlyphsUnitTestSans.glyphs')
    master_dir = os.path.join(str(tmpdir), 'master_ufos_test')
    inst_dir = os.path.join(str(tmpdir), 'inst_ufos_test')

    glyphsLib.__main__.main(['-g', filename, '-m', master_dir, '-n', inst_dir])

    assert glob.glob(master_dir + '/*.ufo')
    assert glob.glob(inst_dir + '/*.ufo')


def test_glyphs_main_instances_relative_dir(tmpdir):
    filename = os.path.join(
        os.path.dirname(__file__), 'data/GlyphsUnitTestSans.glyphs')
    master_dir = 'master_ufos_test'
    inst_dir = 'inst_ufos_test'

    cwd = os.getcwd()
    try:
        os.chdir(str(tmpdir))
        glyphsLib.__main__.main(
            ['-g', filename, '-m', master_dir, '-n', inst_dir])

        assert glob.glob(master_dir + '/*.ufo')
        assert glob.glob(inst_dir + '/*.ufo')
    finally:
        os.chdir(cwd)


def test_parser_main(capsys):
    """This is both a test for the "main" functionality of glyphsLib.parser
    and for the round-trip of GlyphsUnitTestSans.glyphs.
    """
    filename = os.path.join(
        os.path.dirname(__file__), 'data/GlyphsUnitTestSans.glyphs')
    with open(filename) as f:
        expected = f.read()

    glyphsLib.parser.main([filename])
    out, _err = capsys.readouterr()
    assert expected == out, 'The roundtrip should output the .glyphs file unmodified.'
