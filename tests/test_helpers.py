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
import inspect
import os.path
import re
import subprocess
import sys
import tempfile
import shutil
from collections import OrderedDict
from io import StringIO
from textwrap import dedent

import glyphsLib
from glyphsLib import classes, util
from fontTools.designspaceLib import DesignSpaceDocument
from glyphsLib.builder import to_glyphs, to_designspace, to_ufos
from glyphsLib.writer import Writer
from ufonormalizer import normalizeUFO


def write_to_lines(glyphs_object, format_version=2):
    """
    Use the Writer to write the given object to a StringIO.
    Return an array of lines ready for diffing.
    """
    string = StringIO()
    writer = Writer(string, format_version=format_version)
    writer.write(glyphs_object)
    return string.getvalue().splitlines()


class AssertLinesEqual:
    def assertLinesEqual(self, expected, actual, message):
        if actual != expected:
            if len(actual) < len(expected):
                sys.stderr.write(
                    dedent(
                        """\
                    WARNING: the actual text is shorter that the expected text.
                             Some information may be LOST!
                    """
                    )
                )
            for line in difflib.unified_diff(
                expected, actual, fromfile="<expected>", tofile="<actual>"
            ):
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
        with open("expected.txt", "w") as f:
            f.write("\n".join(expected))
        with open("actual.txt", "w") as f:
            f.write("\n".join(actual))
        with open("actual_indempotent.txt", "w") as f:
            f.write("\n".join(actual_idempotent))
        # Assert idempotence first, because if that fails it's a big issue
        self.assertLinesEqual(
            actual,
            actual_idempotent,
            "The parser/writer should be idempotent. BIG PROBLEM!",
        )
        self.assertLinesEqual(
            expected, actual, "The writer should output exactly what the parser read"
        )


class ParametrizedUfoModuleTestMixin(object):

    ufo_module = None  # subclasses must override this

    def to_ufos(self, *args, **kwargs):
        kwargs["ufo_module"] = self.ufo_module
        return to_ufos(*args, **kwargs)

    def to_designspace(self, *args, **kwargs):
        kwargs["ufo_module"] = self.ufo_module
        return to_designspace(*args, **kwargs)


class AssertUFORoundtrip(AssertLinesEqual, ParametrizedUfoModuleTestMixin):
    """Check .glyphs -> UFOs + designspace -> .glyphs"""

    def _normalize(self, font):
        # Order the kerning OrderedDict alphabetically
        # (because the ordering from Glyphs.app is random and that would be
        # a bit silly to store it only for the purpose of nicer diffs in tests)
        font.kerning = OrderedDict(
            sorted(
                map(
                    lambda i: (
                        i[0],
                        OrderedDict(
                            sorted(
                                map(
                                    lambda j: (j[0], OrderedDict(sorted(j[1].items()))),
                                    i[1].items(),
                                )
                            )
                        ),
                    ),
                    font.kerning.items(),
                )
            )
        )

    def assertUFORoundtrip(self, font):
        self._normalize(font)
        expected = write_to_lines(font)
        # Don't propagate anchors nor generate GDEF when intending to round-trip
        designspace = self.to_designspace(
            font,
            propagate_anchors=False,
            minimize_glyphs_diffs=True,
            generate_GDEF=False,
        )

        # Check that round-tripping in memory is the same as writing on disk
        roundtrip_in_mem = to_glyphs(designspace, ufo_module=self.ufo_module)
        self._normalize(roundtrip_in_mem)
        actual_in_mem = write_to_lines(roundtrip_in_mem)

        directory = tempfile.mkdtemp()
        path = os.path.join(directory, font.familyName + ".designspace")
        write_designspace_and_UFOs(designspace, path)
        designspace_roundtrip = DesignSpaceDocument()
        designspace_roundtrip.read(path)
        roundtrip = to_glyphs(designspace_roundtrip, ufo_module=self.ufo_module)
        self._normalize(roundtrip)
        actual = write_to_lines(roundtrip)

        with open("expected.txt", "w") as f:
            f.write("\n".join(expected))
        with open("actual_in_mem.txt", "w") as f:
            f.write("\n".join(actual_in_mem))
        with open("actual.txt", "w") as f:
            f.write("\n".join(actual))
        self.assertLinesEqual(
            actual_in_mem,
            actual,
            "The round-trip in memory or written to disk should be equivalent",
        )
        self.assertLinesEqual(
            expected, actual, "The font should not be modified by the roundtrip"
        )


def _save_overwrite_ufo(font, path):
    if "overwrite" in inspect.getfullargspec(font.save).args:
        font.save(path, formatVersion=3, overwrite=True)  # ufoLib2
    else:
        font.save(path, formatVersion=3)  # defcon


def write_designspace_and_UFOs(designspace, path):
    for source in designspace.sources:
        basename = os.path.basename(source.filename)
        ufo_path = os.path.join(os.path.dirname(path), basename)
        source.filename = basename
        source.path = ufo_path
        _save_overwrite_ufo(source.font, ufo_path)

    designspace.write(path)


def deboolized(object):
    if isinstance(object, OrderedDict):
        return OrderedDict([(key, deboolized(value)) for key, value in object.items()])
    if isinstance(object, dict):
        return {key: deboolized(value) for key, value in object.items()}
    if isinstance(object, list):
        return [deboolized(value) for value in object]

    if isinstance(object, bool):
        return 1 if object else 0

    return object


def deboolize(lib):
    for key, value in lib.items():
        # Force dirtying the font, because value == deboolized(value)
        # since True == 1 in python, so defcon thinks nothing happens
        lib[key] = None
        lib[key] = deboolized(value)


def normalize_ufo_lib(path, ufo_module):
    """Go through each `lib` element recursively and transform `bools` into
    `int` because that's what's going to happen on round-trip with Glyphs.
    """
    font = util.open_ufo(path, ufo_module.Font)
    deboolize(font.lib)
    for layer in font.layers:
        deboolize(layer.lib)
        for glyph in layer:
            deboolize(glyph.lib)
    _save_overwrite_ufo(font, path)


class AssertDesignspaceRoundtrip(ParametrizedUfoModuleTestMixin):
    """Check UFOs + designspace -> .glyphs -> UFOs + designspace"""

    def assertDesignspacesEqual(self, expected, actual, message=""):
        directory = tempfile.mkdtemp()

        def git(*args):
            return subprocess.check_output(["git", "-C", directory] + list(args))

        def clean_git_folder():
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file() or entry.is_symlink():
                        os.remove(entry.path)
                    elif entry.is_dir() and entry.name != ".git":
                        shutil.rmtree(entry.path)

        # Strategy: init a git repo, dump expected, commit, dump actual, diff
        designspace_filename = os.path.join(directory, "test.designspace")
        git("init")
        write_designspace_and_UFOs(expected, designspace_filename)
        for source in expected.sources:
            normalize_ufo_lib(source.path)
            normalizeUFO(source.path, floatPrecision=3, writeModTimes=False)
        git("add", ".")
        git("commit", "-m", "expected")

        clean_git_folder()
        write_designspace_and_UFOs(actual, designspace_filename)
        for source in actual.sources:
            normalize_ufo_lib(source.path)
            normalizeUFO(source.path, floatPrecision=3, writeModTimes=False)
        git("add", ".")
        status = git("status")
        diff = git(
            "diff", "--staged", "--src-prefix= original/", "--dst-prefix=roundtrip/"
        )

        if diff:
            sys.stderr.write(status)
            sys.stderr.write(diff)

        self.assertEqual(0, len(diff), message)

    def assertDesignspaceRoundtrip(self, designspace):
        directory = tempfile.mkdtemp()
        font = to_glyphs(
            designspace, minimize_ufo_diffs=True, ufo_module=self.ufo_module
        )

        # Check that round-tripping in memory is the same as writing on disk
        roundtrip_in_mem = self.to_designspace(font, propagate_anchors=False)

        tmpfont_path = os.path.join(directory, "font.glyphs")
        font.save(tmpfont_path)
        font_rt = classes.GSFont(tmpfont_path)
        roundtrip = self.to_designspace(font_rt, propagate_anchors=False)

        font.save("intermediary.glyphs")

        write_designspace_and_UFOs(designspace, "expected/test.designspace")
        for source in designspace.sources:
            normalize_ufo_lib(source.path)
            normalizeUFO(source.path, floatPrecision=3, writeModTimes=False)
        write_designspace_and_UFOs(roundtrip, "actual/test.designspace")
        for source in roundtrip.sources:
            normalize_ufo_lib(source.path)
            normalizeUFO(source.path, floatPrecision=3, writeModTimes=False)
        self.assertDesignspacesEqual(
            roundtrip_in_mem,
            roundtrip,
            "The round-trip in memory or written to disk should be equivalent",
        )
        self.assertDesignspacesEqual(
            designspace, roundtrip, "The font should not be modified by the roundtrip"
        )


APP_VERSION_RE = re.compile('\\.appVersion = "(.*)"')


def glyphs_files(directory):
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".glyphs"):
                yield os.path.join(root, filename)


def app_version(filename):
    with open(filename) as fp:
        for line in fp:
            m = APP_VERSION_RE.match(line)
            if m:
                return m.group(1)
    return "no_version"


def designspace_files(directory):
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".designspace"):
                yield os.path.join(root, filename)
