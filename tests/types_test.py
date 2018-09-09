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

from __future__ import print_function, division, absolute_import, unicode_literals

import datetime
import unittest

from glyphsLib.types import Transform, parse_datetime, parse_color


class GlyphsDateTimeTest(unittest.TestCase):
    def test_parsing_24hr_format(self):
        """Assert glyphs_datetime can parse 24 hour time formats"""
        string_24hrs = "2017-01-01 17:30:30 +0000"
        self.assertEqual(
            parse_datetime(string_24hrs), datetime.datetime(2017, 1, 1, 17, 30, 30)
        )

    def test_parsing_12hr_format(self):
        """Assert glyphs_datetime can parse 12 hour time format"""
        string_12hrs = "2017-01-01 5:30:30 PM +0000"
        self.assertEqual(
            parse_datetime(string_12hrs), datetime.datetime(2017, 1, 1, 17, 30, 30)
        )

    def test_parsing_timezone(self):
        """Assert glyphs_datetime can parse the (optional) timezone
        formatted as UTC offset. If it's not explicitly specified, then
        +0000 is assumed.
        """
        self.assertEqual(
            parse_datetime("2017-12-18 16:45:31 -0100"),
            datetime.datetime(2017, 12, 18, 15, 45, 31),
        )

        self.assertEqual(
            parse_datetime("2017-12-18 14:15:31 +0130"),
            datetime.datetime(2017, 12, 18, 15, 45, 31),
        )

        self.assertEqual(
            parse_datetime("2017-12-18 15:45:31"),
            datetime.datetime(2017, 12, 18, 15, 45, 31),
        )

        self.assertEqual(
            parse_datetime("2017-12-18 03:45:31 PM"),
            datetime.datetime(2017, 12, 18, 15, 45, 31),
        )

        self.assertEqual(
            parse_datetime("2017-12-18 09:45:31 AM"),
            datetime.datetime(2017, 12, 18, 9, 45, 31),
        )


class TransformTest(unittest.TestCase):
    def test_value_equality(self):
        assert Transform(1, 0, 0, 1, 0, 0) == Transform(1, 0, 0, 1, 0, 0)
        assert Transform(1, 0, 0, 1, 0, 0) == Transform(1.0, 0, 0, 1.0, 0, 0)


class ColorTest(unittest.TestCase):
    def test_color_parsing(self):
        good_color_data = {
            "(1, 2, 3, 4)": (1, 2, 3, 4),
            "(255, 255, 255, 255)": (255, 255, 255, 255),
        }

        for key, value in good_color_data.items():
            assert parse_color(key) == value

        bad_color_data = [
            "(300, 300, 3000, 300)",
            "(0.1, 2.1, 3.9)",
            "(100, 200)",
            "()",
            "(-1)",
        ]

        for value in bad_color_data:
            self.assertRaises(ValueError, parse_color, value)


if __name__ == "__main__":
    unittest.main()
