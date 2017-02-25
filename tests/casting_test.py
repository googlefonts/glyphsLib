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
from glyphsLib.casting import cast_data, num, custom_params
from copy import deepcopy


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

    def test_empty_string(self):
        data = {'date': ''}
        cast_data(data)
        self.assertEqual(data['date'], None)


class RWNumTest(unittest.TestCase):

    def test_read(self):
        self.assertEqual(num.read('1.0'), 1)
        self.assertEqual(num.read('-10.0'), -10)
        self.assertEqual(num.read('1.1'), 1.1)

    def test_write(self):
        self.assertEqual(num.write(1.0), '1')
        self.assertEqual(num.write(-10), '-10')
        self.assertEqual(num.write(1.1), '1.1')


class RWCustomParamsTest(unittest.TestCase):

    raw_params = [
        {'name': 'openTypeOS2WinAscent', 'value': '1000'},
        {'name': 'underlinePosition', 'value': '-77.5'},
        {'name': 'postscriptBlueScale', 'value': '0.039625'},
        {'name': 'isFixedPitch', 'value': '0'},
        {'name': 'Don\u2019t use Production Names', 'value': '1'},
        {'name': 'unicodeRanges', 'value': ['0', '1', '2']},
        {'name': 'weightClass', 'value': '650'},
        {'name': 'widthClass', 'value': '2'}
    ]

    cast_params = [
        {'name': 'openTypeOS2WinAscent', 'value': 1000},
        {'name': 'underlinePosition', 'value': -77.5},
        {'name': 'postscriptBlueScale', 'value': 0.039625},
        {'name': 'isFixedPitch', 'value': False},
        {'name': 'Don\u2019t use Production Names', 'value': True},
        {'name': 'unicodeRanges', 'value': [0, 1, 2]},
        {'name': 'weightClass', 'value': 650},
        {'name': 'widthClass', 'value': 2}
    ]

    def test_read(self):
        src = deepcopy(self.raw_params)
        expected = deepcopy(self.cast_params)
        self.assertEqual(custom_params.read(src), expected)

    def test_write(self):
        src = deepcopy(self.cast_params)
        expected = deepcopy(self.raw_params)
        self.assertEqual(custom_params.write(src), expected)


if __name__ == '__main__':
    unittest.main()
