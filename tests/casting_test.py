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
from glyphsLib.casting import cast_data


class GlyphsDatetimeTest(unittest.TestCase):
    def compare_parsed_date_string(self, string, expected):
        data = {'date': string}
        cast_data(data)
        dt = data['date']
        year, month, day, hour, minute, second = expected
        self.assertEqual(dt.year, year)
        self.assertEqual(dt.month, month)
        self.assertEqual(dt.day, day)
        self.assertEqual(dt.hour, hour)
        self.assertEqual(dt.minute, minute)
        self.assertEqual(dt.second, second)

    def test_without_offset(self):
        self.compare_parsed_date_string(
            '2001-02-03 04:05:06 +0000',
            (2001, 2, 3, 4, 5, 6))

    def test_with_offset(self):
        self.compare_parsed_date_string(
            '2001-02-03 04:05:06 +1100',
            (2001, 2, 3, 15, 5, 6))
        self.compare_parsed_date_string(
            '2001-02-03 04:05:06 +0011',
            (2001, 2, 3, 4, 16, 6))
        self.compare_parsed_date_string(
            '2001-02-03 04:05:06 +1010',
            (2001, 2, 3, 14, 15, 6))
        self.compare_parsed_date_string(
            '2001-02-03 14:15:06 -1010',
            (2001, 2, 3, 4, 5, 6))
        self.compare_parsed_date_string(
            '2001-02-03 00:05:06 -0010',
            (2001, 2, 2, 23, 55, 6))


if __name__ == '__main__':
    unittest.main()
