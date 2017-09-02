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

from fontTools.misc.py23 import unicode, BytesIO, UnicodeIO

from glyphsLib.parser import Parser, Writer


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


class WriterTest(unittest.TestCase):

    SAMPLE_DATA = collections.OrderedDict([
        ('a', 'b'),
        (
            'c', {
                'd': 'e'
            }
        ),
        (
            'f', [
                'g',
                'h'
            ]
        ),
        ('i', 'j k l')
    ])

    def test_text_input_output(self):
        w = Writer(UnicodeIO())
        w.write(WriterTest.SAMPLE_DATA)
        result = w.file.getvalue()

        self.assertIsInstance(result, unicode)
        self.assertEqual(
            result.split('\n'),
            [
                '{',
                'a = b;',
                'c = {',
                'd = e;',
                '};',
                'f = (',
                'g,',
                'h',
                ');',
                'i = "j k l";',
                '}',
                ''
            ])

    def test_text_input_binary_output(self):
        w = Writer(BytesIO())
        w.write(WriterTest.SAMPLE_DATA)
        result = w.file.getvalue()

        self.assertIsInstance(result, bytes)
        self.assertEqual(
            result.split(b'\n'),
            [
                b'{',
                b'a = b;',
                b'c = {',
                b'd = e;',
                b'};',
                b'f = (',
                b'g,',
                b'h',
                b');',
                b'i = "j k l";',
                b'}',
                b''
            ])

    def test_binary_input_text_output(self):
        w = Writer(UnicodeIO())
        w.write({'name': b'\xc3\xbc'})
        result = w.file.getvalue()
        # XXX Glyphs.app writes non-ASCII strings unescaped as UTF-8, whereas
        # glyphsLib currently escapes all non ASCII characters with \\UXXXX.
        # self.assertEqual(result, '{\nname = "ü";\n}\n')
        self.assertEqual(result, '{\nname = "\\U00FC";\n}\n')

    def test_indent_0(self):
        w = Writer(UnicodeIO(), indent=0)
        w.write(WriterTest.SAMPLE_DATA)

        self.assertEqual(
            w.file.getvalue().split('\n'),
            [
                '{',
                'a = b;',
                'c = {',
                'd = e;',
                '};',
                'f = (',
                'g,',
                'h',
                ');',
                'i = "j k l";',
                '}',
                ''
            ])

    def test_indent_2(self):
        w = Writer(UnicodeIO(), indent=2)
        w.write(WriterTest.SAMPLE_DATA)

        self.assertEqual(
            w.file.getvalue().split('\n'),
            [
                '{',
                '  a = b;',
                '  c = {',
                '    d = e;',
                '  };',
                '  f = (',
                '    g,',
                '    h',
                '  );',
                '  i = "j k l";',
                '}',
                ''
            ])

    def test_indent_4(self):
        w = Writer(UnicodeIO(), indent=4)
        w.write(WriterTest.SAMPLE_DATA)

        self.assertEqual(
            w.file.getvalue().split('\n'),
            [
                '{',
                '    a = b;',
                '    c = {',
                '        d = e;',
                '    };',
                '    f = (',
                '        g,',
                '        h',
                '    );',
                '    i = "j k l";',
                '}',
                ''
            ])

    def test_indent_tab(self):
        w = Writer(UnicodeIO(), indent='\t')
        w.write(WriterTest.SAMPLE_DATA)

        self.assertEqual(
            w.file.getvalue().split('\n'),
            [
                '{',
                '\ta = b;',
                '\tc = {',
                '\t\td = e;',
                '\t};',
                '\tf = (',
                '\t\tg,',
                '\t\th',
                '\t);',
                '\ti = "j k l";',
                '}',
                ''
            ])

    def test_sort_keys(self):
        data = dict(WriterTest.SAMPLE_DATA)
        del data['a']
        data['b'] = 'a'

        w = Writer(UnicodeIO(), sort_keys=True)
        w.write(data)

        self.assertEqual(
            w.file.getvalue().split('\n'),
            [
                '{',
                'b = a;',
                'c = {',
                'd = e;',
                '};',
                'f = (',
                'g,',
                'h',
                ');',
                'i = "j k l";',
                '}',
                ''
            ])

    def test_escape_octal(self):
        w = Writer(UnicodeIO())
        w.write({'CR': '\u000D'})

        self.assertEqual(w.file.getvalue(), '{\nCR = "\\015";\n}\n')

    def test_escape_inner_quotes(self):
        w = Writer(UnicodeIO())
        w.write({'s': 'string with inner "quotes"'})

        self.assertEqual(
            w.file.getvalue(),
            '{\ns = "string with inner \\"quotes\\"";\n}\n')

    def test_no_escape(self):
        s = '"quoted string with escaped inner \\"quotes\\""'
        w = Writer(UnicodeIO(), escape=False)
        w.write({'s': s})

        self.assertEqual(w.file.getvalue(), '{\ns = %s;\n}\n' % s)


if __name__ == '__main__':
    unittest.main()
