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
from fontTools.misc.py23 import tounicode, unichr, unicode

from collections import OrderedDict
import re
import sys


class Parser:
    """Parses Python dictionaries from Glyphs source files."""

    def __init__(self, dict_type=OrderedDict):
        self.dict_type = dict_type
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

    def parse_into_object(self, res, text):
        """Do the parsing."""

        text = tounicode(text, encoding='utf-8')

        m = self.start_dict_re.match(text, 0)
        if m:
            i = self._parse_dict_into_object(res, text, 1)
        else:
            self._fail('not correct file format')
        if text[i:].strip():
            self._fail('Unexpected trailing content', text, i)
        return i

    def _guess_dict_type(self, parsed, value):
        if parsed[-1] != '"':
            try:
                float_val = float(value)
                if float_val.is_integer():
                    dict_type = int
                else:
                    dict_type = float
            except:
                dict_type = unicode
        else:
            dict_type = unicode
        return dict_type

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
            if hasattr(self.dict_type, "read"):
                reader = self.dict_type()
                value = reader.read(value)
                return value, i


            if self.dict_type is None:  # for custom parameters
                self.dict_type = self._guess_dict_type(parsed, value)

            if self.dict_type == bool:
                value = bool(int(value))  # bool(u'0') returns True
                return value, i

            if self.dict_type in (dict, OrderedDict):
                if not self.start_dict_re.match(value):
                    self.dict_type = self._guess_dict_type(parsed, value)

            value = self.dict_type(value)

            return value, i

        else:
            self._fail('Unexpected content', text, i)

    def _parse_dict(self, text, i):
        """Parse a dictionary from source text starting at i."""
        old_dict_type = self.dict_type
        new_type = self.dict_type
        if new_type is None:
            # customparameter.value needs to be set from the found value
            new_type = dict
        elif type(new_type) == list:
            new_type = new_type[0]
        res = new_type()
        i = self._parse_dict_into_object(res, text, i)
        self.dict_type = old_dict_type
        return res, i

    def _parse_dict_into_object(self, res, text, i):
        end_match = self.end_dict_re.match(text, i)
        while not end_match:
            old_dict_type = self.dict_type
            m = self.attr_re.match(text, i)
            if not m:
                self._fail('Unexpected dictionary content', text, i)
            parsed, name = m.group(0), self._trim_value(m.group(1))
            if hasattr(res, "classForName"):
                self.dict_type = res.classForName(name)
            i += len(parsed)
            result = self._parse(text, i)
            try:
                res[name], i = result
            except:
                res = {}  # ugly, this fixes nested dicts in customparameters
                res[name], i = result

            m = self.dict_delim_re.match(text, i)
            if not m:
                self._fail('Missing delimiter in dictionary before content',
                           text, i)
            parsed = m.group(0)
            i += len(parsed)

            end_match = self.end_dict_re.match(text, i)
            self.dict_type = old_dict_type
        parsed = end_match.group(0)
        i += len(parsed)
        return i

    def _parse_list(self, text, i):
        """Parse a list from source text starting at i."""

        res = []
        end_match = self.end_list_re.match(text, i)
        old_dict_type = self.dict_type
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
        self.dict_type = old_dict_type
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
