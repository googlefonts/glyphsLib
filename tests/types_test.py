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

from __future__ import (
    print_function, division, absolute_import, unicode_literals)

import datetime
import unittest

from glyphsLib.types import glyphs_datetime


class GlyphsDateTimeTest(unittest.TestCase):

    def test_parsing_24hr_format(self):
        """Assert glyphs_datetime can parse 24 hour time formats"""
        string_24hrs = '2017-01-01 17:30:30 +0000'
        test_time = glyphs_datetime()
        self.assertEqual(test_time.read(string_24hrs),
                         datetime.datetime(2017, 1, 1, 17, 30, 30))

    def test_parsing_12hr_format(self):
        """Assert glyphs_datetime can parse 12 hour time format"""
        string_12hrs = '2017-01-01 5:30:30 PM +0000'
        test_time = glyphs_datetime()
        self.assertEqual(test_time.read(string_12hrs),
                         datetime.datetime(2017, 1, 1, 17, 30, 30))


if __name__ == '__main__':
    unittest.main()
