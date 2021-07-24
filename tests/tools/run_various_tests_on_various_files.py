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

import subprocess
import os
import unittest
import pytest

import defcon
import ufoLib2

import glyphsLib
from fontTools.designspaceLib import DesignSpaceDocument
import test_helpers


# Kinds of tests that can be run
class GlyphsRT(unittest.TestCase, test_helpers.AssertParseWriteRoundtrip):
    """Test the parser & writer for .glyphs files only"""

    @classmethod
    def add_tests(cls, testable):
        files = test_helpers.glyphs_files(directory(testable))
        for index, filename in enumerate(sorted(files)):

            def test_method(self, filename=filename):
                self.assertParseWriteRoundtrip(filename)

            file_basename = os.path.basename(filename)
            test_name = "test_n{:0>3d}_{}_v{}_{}".format(
                index,
                testable["name"],
                test_helpers.app_version(filename),
                file_basename.replace(r"[^a-zA-Z]", ""),
            )
            test_method.__name__ = test_name
            setattr(cls, test_name, test_method)


class GlyphsToDesignspaceRT(test_helpers.AssertUFORoundtrip):
    """Test the whole chain from .glyphs to designspace + UFOs and back"""

    @classmethod
    def add_tests(cls, testable):
        files = test_helpers.glyphs_files(directory(testable))
        for index, filename in enumerate(sorted(files)):

            def test_method(self, filename=filename):
                with open(filename) as f:
                    font = glyphsLib.load(f)
                self.assertUFORoundtrip(font)

            file_basename = os.path.basename(filename)
            test_name = "test_n{:0>3d}_{}_v{}_{}".format(
                index,
                testable["name"],
                test_helpers.app_version(filename),
                file_basename.replace(r"[^a-zA-Z]", ""),
            )
            test_method.__name__ = test_name
            setattr(cls, test_name, test_method)


class GlyphsToDesignspaceRTUfoLib2(unittest.TestCase, GlyphsToDesignspaceRT):
    ufo_module = ufoLib2


class GlyphsToDesignspaceRTDefcon(unittest.TestCase, GlyphsToDesignspaceRT):
    ufo_module = defcon


class DesignspaceToGlyphsRT(test_helpers.AssertDesignspaceRoundtrip):
    """Test the whole chain from designspace + UFOs to .glyphs and back"""

    @classmethod
    def add_tests(cls, testable):
        files = test_helpers.designspace_files(directory(testable))
        for index, filename in enumerate(sorted(files)):

            def test_method(self, filename=filename):
                doc = DesignSpaceDocument()
                doc.read(filename)
                self.assertDesignspaceRoundtrip(doc)

            file_basename = os.path.basename(filename)
            test_name = "test_n{:0>3d}_{}_{}".format(
                index, testable["name"], file_basename.replace(r"[^a-zA-Z]", "")
            )
            test_method.__name__ = test_name
            setattr(cls, test_name, test_method)
            print("adding test", test_name)


class DesignspaceToGlyphsRTUfoLib2(unittest.TestCase, DesignspaceToGlyphsRT):
    ufo_module = ufoLib2


class DesignspaceToGlyphsRTDefcon(unittest.TestCase, DesignspaceToGlyphsRT):
    ufo_module = defcon


TESTABLES = [
    # The following contain .glyphs files
    {
        "name": "noto_moyogo",  # dirname inside `downloaded/`
        "git_url": "https://github.com/moyogo/noto-source.git",
        "git_ref": "normalized-1071",
        "classes": (
            GlyphsRT,
            GlyphsToDesignspaceRTUfoLib2,
            GlyphsToDesignspaceRTDefcon,
        ),
    },
    {
        # https://github.com/googlefonts/glyphsLib/issues/238
        "name": "montserrat",
        "git_url": "https://github.com/JulietaUla/Montserrat",
        "git_ref": "master",
        "classes": (
            GlyphsRT,
            GlyphsToDesignspaceRTUfoLib2,
            GlyphsToDesignspaceRTDefcon,
        ),
    },
    {
        # https://github.com/googlefonts/glyphsLib/issues/282
        "name": "cantarell_madig",
        "git_url": "https://github.com/madig/cantarell-fonts/",
        "git_ref": "f17124d041e6ee370a9fcddcc084aa6cbf3d5500",
        "classes": (
            GlyphsRT,
            GlyphsToDesignspaceRTUfoLib2,
            GlyphsToDesignspaceRTDefcon,
        ),
    },
    # {
    #     # This one has truckloads of smart components
    #     'name': 'vt323',
    #     'git_url': 'https://github.com/phoikoi/VT323',
    #     'git_ref': 'master',
    #     'classes': (
    #         GlyphsRT, GlyphsToDesignspaceRTUfoLib2, GlyphsToDesignspaceRTDefcon
    #     ),
    # },
    {
        # This one has truckloads of smart components
        "name": "vt323_jany",
        "git_url": "https://github.com/belluzj/VT323",
        "git_ref": "glyphs-1089",
        "classes": (
            GlyphsRT,
            GlyphsToDesignspaceRTUfoLib2,
            GlyphsToDesignspaceRTDefcon,
        ),
    },
    # The following contain .designspace files
    {
        "name": "spectral",
        "git_url": "https://github.com/productiontype/Spectral",
        "git_ref": "master",
        "classes": (DesignspaceToGlyphsRTUfoLib2, DesignspaceToGlyphsRTDefcon),
    },
    {
        "name": "amstelvar",
        "git_url": "https://github.com/TypeNetwork/fb-Amstelvar",
        "git_ref": "master",
        "classes": (DesignspaceToGlyphsRTUfoLib2, DesignspaceToGlyphsRTDefcon),
    },
]


def directory(testable):
    return os.path.join(os.path.dirname(__file__), "downloaded", testable["name"])


for testable in TESTABLES:
    print("#### Downloading ", testable["name"])
    if not os.path.exists(directory(testable)):
        subprocess.call(["git", "clone", testable["git_url"], directory(testable)])
    subprocess.check_call(
        ["git", "-C", directory(testable), "checkout", testable["git_ref"]]
    )
    print()

for testable in TESTABLES:
    for cls in testable["classes"]:
        cls.add_tests(testable)


if __name__ == "__main__":
    import sys

    # Run pytest.main because it's easier to filter tests, drop into PDB, etc.
    sys.exit(pytest.main(sys.argv))
