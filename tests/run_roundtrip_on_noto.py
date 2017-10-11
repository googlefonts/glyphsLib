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

import test_helpers

import glyphsLib

NOTO_DIRECTORY = os.path.join(os.path.dirname(__file__), 'noto-source')

def glyphs_files(directory):
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.glyphs'):
                yield os.path.join(root, filename)


class NotoRoundtripTest(unittest.TestCase,
                        test_helpers.AssertParseWriteRoundtrip):
    pass


if __name__ == '__main__':
    subprocess.call([
        "git", "clone", "https://github.com/googlei18n/noto-source.git",
        NOTO_DIRECTORY])

    for index, filename in enumerate(glyphs_files(NOTO_DIRECTORY)):
        def test_method(self, filename=filename):
            self.assertParseWriteRoundtrip(filename)
        file_basename = os.path.basename(filename)
        test_name = "test_{0}".format(file_basename.replace(r'[^a-zA-Z]', ''))
        test_method.__name__ = test_name
        setattr(NotoRoundtripTest, test_name, test_method)

    unittest.main()
