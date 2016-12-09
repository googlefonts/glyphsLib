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


from __future__ import (print_function, division, absolute_import,
                        unicode_literals)

import collections
import unittest

from glyphsLib.parser import Parser


class ParserTest(unittest.TestCase):
    def run_test(self, text, expected):
        parser = Parser()
        self.assertEqual(parser.parse(text), collections.OrderedDict(expected))

    def test_parse(self):
        self.run_test(
            '{myval=1; mylist=(1,2,3);}',
            [('myval', '1'), ('mylist', ['1', '2', '3'])])

    def test_trim_value(self):
        self.run_test(
            '{mystr="a\\"s\\077d\\U2019f";}',
            [('mystr', 'a"s?d’f')])

    def test_trailing_content(self):
        with self.assertRaises(ValueError):
            self.run_test(
                '{myval=1;}trailing',
                [('myval', '1')])

    def test_unexpected_content(self):
        with self.assertRaises(ValueError):
            self.run_test(
                '{myval=@unexpected;}',
                [('myval', '@unexpected')])

    def test_with_utf8(self):
        self.run_test(
            b'{mystr="Don\xe2\x80\x99t crash";}',
            [('mystr', 'Don’t crash')])


if __name__ == '__main__':
    unittest.main()
