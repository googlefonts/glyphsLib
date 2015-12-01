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


from __future__ import print_function, division, absolute_import

import re


class Parser:
    """Parses Python dictionaries from Glyphs source files."""

    def __init__(self, dict_type):
        self.dict_type = dict_type
        value_re = r'(".*?(?<!\\)"|[-_./A-Za-z0-9]+)'
        self.start_dict_re = re.compile(r'\s*{')
        self.end_dict_re = re.compile(r'\s*}')
        self.dict_delim_re = re.compile(r'\s*;')
        self.start_list_re = re.compile(r'\s*\(')
        self.end_list_re = re.compile(r'\s*\)')
        self.list_delim_re = re.compile(r'\s*,')
        self.attr_re = re.compile(r'\s*%s\s*=' % value_re)
        self.value_re = re.compile(r'\s*%s' % value_re)

    def parse(self, text):
        """Do the parsing."""

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

        res = self.dict_type()
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

    def _trim_value(self, value):
        """Trim double quotes off the ends of a value, un-escaping inner
        double quotes.
        """

        if value[0] == '"':
            assert value[-1] == '"'
            return value[1:-1].replace('\\"', '"')
        return value

    def _fail(self, message, text, i):
        """Raise an exception with given message and text at i."""

        raise ValueError('%s:\n%s' % (message, text[i:i + 79]))
