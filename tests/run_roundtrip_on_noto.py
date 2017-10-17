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
import re

import test_helpers

NOTO_DIRECTORY = os.path.join(os.path.dirname(__file__), 'noto-source-moyogo')
NOTO_GIT_URL = "https://github.com/moyogo/noto-source.git"
NOTO_GIT_BRANCH = "normalized-1071"

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


class NotoRoundtripTest(unittest.TestCase,
                        test_helpers.AssertParseWriteRoundtrip):
    pass


if __name__ == '__main__':
    print("Run with `pytest -c noto_pytest.ini`")
else:
    subprocess.call(["git", "clone", NOTO_GIT_URL, NOTO_DIRECTORY])
    subprocess.check_call(
        ["git", "-C", NOTO_DIRECTORY, "checkout", NOTO_GIT_BRANCH])

    for index, filename in enumerate(glyphs_files(NOTO_DIRECTORY)):
        def test_method(self, filename=filename):
            self.assertParseWriteRoundtrip(filename)
        file_basename = os.path.basename(filename)
        test_name = "test_n{0:0>3d}_v{1}_{2}".format(
            index,
            app_version(filename),
            file_basename.replace(r'[^a-zA-Z]', ''))
        test_method.__name__ = test_name
        setattr(NotoRoundtripTest, test_name, test_method)
