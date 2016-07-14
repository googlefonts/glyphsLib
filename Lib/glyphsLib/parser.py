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


from __future__ import (print_function, division, absolute_import,
                        unicode_literals)
from fontTools.misc.py23 import *

import collections
import re
import sys


class Parser:
    """Parses Python dictionaries from Glyphs source files."""

    def __init__(self):
        value_re = r'(".*?(?<!\\)"|[-_./$A-Za-z0-9]+)'
        self.start_dict_re = re.compile(r'\s*{')
        self.end_dict_re = re.compile(r'\s*}')
        self.dict_delim_re = re.compile(r'\s*;')
        self.start_list_re = re.compile(r'\s*\(')
        self.end_list_re = re.compile(r'\s*\)')
        self.list_delim_re = re.compile(r'\s*,')
        self.attr_re = re.compile(r'\s*%s\s*=' % value_re, re.DOTALL)
        self.value_re = re.compile(r'\s*%s' % value_re, re.DOTALL)

    def parse(self, text):
        """Do the parsing."""

        text = tounicode(text, encoding='utf-8')
        result, i = self._parse(text, 0)
        if text[i:].strip():
            self._fail('Unexpected trailing content', text, i)
        return result

    def _parse(self, text, i):
        """Recursive function to parse a single dictionary, list, or value."""

        m = self.start_dict_re.match(text, i)
        if m:
            parsed = m.group(0)
            i += len(parsed)
            return self._parse_dict(text, i)

        m = self.start_list_re.match(text, i)
        if m:
            parsed = m.group(0)
            i += len(parsed)
            return self._parse_list(text, i)

        m = self.value_re.match(text, i)
        if m:
            parsed, value = m.group(0), self._trim_value(m.group(1))
            i += len(parsed)
            return value, i

        else:
            self._fail('Unexpected content', text, i)

    def _parse_dict(self, text, i):
        """Parse a dictionary from source text starting at i."""

        res = collections.OrderedDict()
        end_match = self.end_dict_re.match(text, i)
        while not end_match:
            m = self.attr_re.match(text, i)
            if not m:
                self._fail('Unexpected dictionary content', text, i)
            parsed, name = m.group(0), self._trim_value(m.group(1))
            i += len(parsed)
            res[name], i = self._parse(text, i)

            m = self.dict_delim_re.match(text, i)
            if not m:
                self._fail('Missing delimiter in dictionary before content',
                            text, i)
            parsed = m.group(0)
            i += len(parsed)

            end_match = self.end_dict_re.match(text, i)

        parsed = end_match.group(0)
        i += len(parsed)
        return res, i

    def _parse_list(self, text, i):
        """Parse a list from source text starting at i."""

        res = []
        end_match = self.end_list_re.match(text, i)
        while not end_match:
            list_item, i = self._parse(text, i)
            res.append(list_item)

            end_match = self.end_list_re.match(text, i)

            if not end_match:
                m = self.list_delim_re.match(text, i)
                if not m:
                    self._fail('Missing delimiter in list before content',
                                text, i)
                parsed = m.group(0)
                i += len(parsed)

        parsed = end_match.group(0)
        i += len(parsed)
        return res, i

    # glyphs only supports octal escapes between \000 and \077 and hexadecimal
    # escapes between \U0000 and \UFFFF
    _unescape_re = re.compile(r'(\\0[0-7]{2})|(\\U[0-9a-fA-F]{4})')

    @staticmethod
    def _unescape_fn(m):
        if m.group(1):
            return unichr(int(m.group(1)[1:], 8))
        return unichr(int(m.group(2)[2:], 16))

    def _trim_value(self, value):
        """Trim double quotes off the ends of a value, un-escaping inner
        double quotes.
        Also convert escapes to unicode.
        """

        if value[0] == '"':
            assert value[-1] == '"'
            value = value[1:-1].replace('\\"', '"')
        return Parser._unescape_re.sub(Parser._unescape_fn, value)

    def _fail(self, message, text, i):
        """Raise an exception with given message and text at i."""

        raise ValueError('%s:\n%s' % (message, text[i:i + 79]))


class Writer(object):
    """Write parsed data back to flat file.  Normalizes quoting
    and indentation."""

    # ints and floats are unquoted, as are strings of letters/digits and
    # underscore with period or leading forward slash.  Everything else
    # is quoted.
    _sym_re = re.compile(
        r'^(?:-?\.[0-9]+|-?[0-9]+\.?[0-9]*|[_a-zA-Z0-9/\.][_a-zA-Z0-9\.]*)$')

    def __init__(self, out=sys.stdout, indent=0, reorder=False):
        self.out = out
        self.indent = indent
        self.reorder = reorder
        self.curindent = 0

    def write(self, data):
        self.curindent = 0
        self._write(data)
        self.out.write('\n')
        self.out.flush()

    def _write(self, data):
        if isinstance(data, dict):
            self._write_dict(data)
        elif isinstance(data, list):
            self._write_list(data)
        else:
            self._write_atom(data)

    def _write_dict(self, data):
        if self.reorder:
            keys = sorted(data.keys())
        else:
            keys = data.keys()
        self.curindent += self.indent
        pad = ' ' * self.curindent
        out = self.out
        out.write('{\n')
        for k in keys:
            out.write(pad)
            self._write_atom(k)
            out.write(' = ')
            self._write(data[k])
            out.write(';\n')
        self.curindent -= self.indent
        out.write(' ' * self.curindent)
        out.write('}')

    def _write_list(self, data):
        first = True
        self.curindent += self.indent
        pad = ' ' * self.curindent
        out = self.out
        out.write('(')
        for v in data:
            out.write('\n' if first else ',\n')
            out.write(pad)
            first = False
            self._write(v)
        self.curindent -= self.indent
        out.write('\n')
        out.write(' ' * self.curindent)
        out.write(')')

    _escape_re = re.compile('([^\u0020-\u007e])|"')

    @staticmethod
    def _escape_fn(m):
        if m.group(1):
            v = ord(m.group(1)[0])
            if v < 0x20:
                return r'\%03o' % v
            return '\\U%04X' % v
        return r'\"'

    def _write_atom(self, data):
      data = Writer._escape_re.sub(Writer._escape_fn, data)
      out = self.out
      if Writer._sym_re.match(data):
          out.write(data)
          return
      out.write('"')
      out.write(data)
      out.write('"')
