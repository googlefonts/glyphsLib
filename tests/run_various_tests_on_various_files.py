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
import re

import glyphsLib
from glyphsLib.designSpaceDocument import DesignSpaceDocument
import test_helpers

# Kinds of tests that can be run


class GlyphsRT(unittest.TestCase, test_helpers.AssertParseWriteRoundtrip):
    """Test the parser & writer for .glyphs files only"""

    @classmethod
    def add_tests(cls, testable):
        files = glyphs_files(directory(testable))
        for index, filename in enumerate(sorted(files)):

            def test_method(self, filename=filename):
                self.assertParseWriteRoundtrip(filename)

            file_basename = os.path.basename(filename)
            test_name = "test_n{0:0>3d}_{1}_v{2}_{3}".format(
                index, testable['name'], app_version(filename),
                file_basename.replace(r'[^a-zA-Z]', ''))
            test_method.__name__ = test_name
            setattr(cls, test_name, test_method)


class GlyphsToDesignspaceRT(unittest.TestCase,
                            test_helpers.AssertUFORoundtrip):
    """Test the whole chain from .glyphs to designspace + UFOs and back"""

    @classmethod
    def add_tests(cls, testable):
        files = glyphs_files(directory(testable))
        for index, filename in enumerate(sorted(files)):

            def test_method(self, filename=filename):
                with open(filename) as f:
                    font = glyphsLib.load(f)
                self.assertUFORoundtrip(font)

            file_basename = os.path.basename(filename)
            test_name = "test_n{0:0>3d}_{1}_v{2}_{3}".format(
                index, testable['name'], app_version(filename),
                file_basename.replace(r'[^a-zA-Z]', ''))
            test_method.__name__ = test_name
            setattr(cls, test_name, test_method)


class DesignspaceToGlyphsRT(unittest.TestCase):
    """Test the whole chain from designspace + UFOs to .glyphs and back"""

    @classmethod
    def add_tests(cls, testable):
        files = designspace_files(directory(testable))
        for index, filename in enumerate(sorted(files)):

            def test_method(self, filename=filename):
                doc = DesignSpaceDocument()
                doc.read(filename)
                self.assertDesignspaceRoundtrip(doc)

            file_basename = os.path.basename(filename)
            test_name = "test_n{0:0>3d}_{1}_{2}".format(
                index, testable['name'],
                file_basename.replace(r'[^a-zA-Z]', ''))
            test_method.__name__ = test_name
            setattr(cls, test_name, test_method)


class UFOsToGlyphsRT(unittest.TestCase):
    """The the whole chain from a collection of UFOs to .glyphs and back"""

    @classmethod
    def add_tests(cls, testable):
        pass


TESTABLES = [
    # The following contain .glyphs files
    {
        'name': 'noto_moyogo',  # dirname inside `downloaded/`
        'git_url': 'https://github.com/moyogo/noto-source.git',
        'git_ref': 'normalized-1071',
        'classes': (GlyphsRT, GlyphsToDesignspaceRT),
    },
    {
        # https://github.com/googlei18n/glyphsLib/issues/238
        'name': 'montserrat',
        'git_url': 'https://github.com/JulietaUla/Montserrat',
        'git_ref': 'master',
        'classes': (GlyphsRT, GlyphsToDesignspaceRT),
    },
    {
        # https://github.com/googlei18n/glyphsLib/issues/282
        'name': 'cantarell_madig',
        'git_url': 'https://github.com/madig/cantarell-fonts/',
        'git_ref': 'f17124d041e6ee370a9fcddcc084aa6cbf3d5500',
        'classes': (GlyphsRT, GlyphsToDesignspaceRT),
    },
    # {
    #     # This one has truckloads of smart components
    #     'name': 'vt323',
    #     'git_url': 'https://github.com/phoikoi/VT323',
    #     'git_ref': 'master',
    #     'classes': (GlyphsRT, GlyphsToDesignspaceRT),
    # },
    {
        # This one has truckloads of smart components
        'name': 'vt323_jany',
        'git_url': 'https://github.com/belluzj/VT323',
        'git_ref': 'glyphs-1089',
        'classes': (GlyphsRT, GlyphsToDesignspaceRT),
    },
    # The following contain .designspace files
    {
        'name': 'spectral',
        'git_url': 'https://github.com/productiontype/Spectral',
        'git_ref': 'master',
        'classes': (DesignspaceToGlyphsRT, UFOsToGlyphsRT),
    },
    {
        'name': 'amstelvar',
        'git_url': 'https://github.com/TypeNetwork/fb-Amstelvar',
        'git_ref': 'master',
        'classes': (DesignspaceToGlyphsRT, UFOsToGlyphsRT),
    },
]


APP_VERSION_RE = re.compile('\\.appVersion = "(.*)"')


def glyphs_files(directory):
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.glyphs'):
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
            if filename.endswith('.designspace'):
                yield os.path.join(root, filename)


def directory(testable):
    return os.path.join(
        os.path.dirname(__file__), 'downloaded', testable['name'])


for testable in TESTABLES:
    print("#### Downloading ", testable['name'])
    if not os.path.exists(directory(testable)):
        subprocess.call(
            ["git", "clone", testable['git_url'], directory(testable)])
    subprocess.check_call(
        ["git", "-C", directory(testable), "checkout", testable['git_ref']])
    print()

for testable in TESTABLES:
    for cls in testable['classes']:
        cls.add_tests(testable)

if __name__ == '__main__':
    import sys
    # Run pytest.main because it's easier to filter tests, drop into PDB, etc.
    sys.exit(pytest.main([__file__, *sys.argv]))
