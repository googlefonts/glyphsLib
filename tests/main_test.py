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


import os
import glob

import glyphsLib.cli
import glyphsLib.parser


def test_glyphs_main_masters(tmpdir):
    """Tests the glyphs2ufo and ufo2glyphs of glyphsLib and also the
    `build_masters` function.
    """
    import fontTools.designspaceLib

    filename = os.path.join(os.path.dirname(__file__), "data/GlyphsUnitTestSans.glyphs")
    master_dir = os.path.join(str(tmpdir), "master_ufos_test")

    glyphsLib.cli.main(
        [
            "glyphs2ufo",
            filename,
            "-m",
            master_dir,
            "-n",
            os.path.join(master_dir, "hurf"),
        ]
    )

    assert glob.glob(master_dir + "/*.ufo")
    ds = glob.glob(master_dir + "/GlyphsUnitTestSans.designspace")
    assert ds
    designspace = fontTools.designspaceLib.DesignSpaceDocument()
    designspace.read(ds[0])
    for instance in designspace.instances:
        assert str(instance.filename).startswith("hurf")

    glyphs_file = os.path.join(master_dir, "GlyphsUnitTestSans.glyphs")
    glyphsLib.cli.main(["ufo2glyphs", ds[0], "--output-path", glyphs_file])
    assert os.path.isfile(glyphs_file)


def test_parser_main(capsys):
    """This is both a test for the "main" functionality of glyphsLib.parser
    and for the round-trip of GlyphsUnitTestSans.glyphs.
    """
    filename = os.path.join(os.path.dirname(__file__), "data/GlyphsUnitTestSans.glyphs")
    with open(filename) as f:
        expected = f.read()

    glyphsLib.parser.main([filename])
    out, _err = capsys.readouterr()
    assert expected == out, "The roundtrip should output the .glyphs file unmodified."


def test_parser_main_v3(capsys):
    """This is both a test for the "main" functionality of glyphsLib.parser
    and for the round-trip of GlyphsUnitTestSans.glyphs.
    """
    filename = os.path.join(
        os.path.dirname(__file__), "data/GlyphsUnitTestSans3.glyphs"
    )
    with open(filename) as f:
        expected = f.read()

    glyphsLib.parser.main([filename])
    out, _err = capsys.readouterr()
    assert expected == out, "The roundtrip should output the .glyphs file unmodified."


def test_parser_main_v3_upstream(capsys):
    filename = os.path.join(os.path.dirname(__file__), "data/GlyphsFileFormatv3.glyphs")
    with open(filename) as f:
        expected = f.read()

    glyphsLib.parser.main([filename])
    out, _err = capsys.readouterr()
    assert expected == out, "The roundtrip should output the .glyphs file unmodified."
