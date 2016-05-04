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


from __future__ import print_function, division, absolute_import

import unittest
from defcon import Font

from glyphsLib import builder
from glyphsLib.builder import set_redundant_data, build_style_name


_warnings = []


def _add_warning(message):
    global _warnings
    _warnings.append(message)


def _check_warnings():
    global _warnings
    checked = list(_warnings)
    _warnings = []
    return checked


class BuildStyleNameTest(unittest.TestCase):
    def _build(self, data, italic):
        return build_style_name(data, 'width', 'weight', 'custom', italic)

    def test_style_regular_weight(self):
        self.assertEquals(self._build({}, False), 'Regular')
        self.assertEquals(self._build({}, True), 'Italic')
        self.assertEquals(
            self._build({'weight': 'Regular'}, True), 'Italic')

    def test_style_nonregular_weight(self):
        self.assertEquals(
            self._build({'weight': 'Thin'}, False), 'Thin')
        self.assertEquals(
            self._build({'weight': 'Thin'}, True), 'Thin Italic')

    def test_style_nonregular_width(self):
        self.assertEquals(
            self._build({'width': 'Condensed'}, False), 'Condensed')
        self.assertEquals(
            self._build({'width': 'Condensed'}, True), 'Condensed Italic')
        self.assertEquals(
            self._build({'weight': 'Thin', 'width': 'Condensed'}, False),
            'Condensed Thin')
        self.assertEquals(
            self._build({'weight': 'Thin', 'width': 'Condensed'}, True),
            'Condensed Thin Italic')


class SetRedundantDataTest(unittest.TestCase):
    def _run_on_ufo(self, family_name, style_name):
        ufo = Font()
        ufo.info.familyName = family_name
        ufo.info.styleName = style_name
        set_redundant_data(ufo)
        return ufo

    def test_sets_regular_weight_class_for_missing_weight(self):
        reg_ufo = self._run_on_ufo('MyFont', 'Regular')
        italic_ufo = self._run_on_ufo('MyFont', 'Italic')
        self.assertEquals(
            reg_ufo.info.openTypeOS2WeightClass,
            italic_ufo.info.openTypeOS2WeightClass)

    def test_sets_weight_lib_entry_only_nonregular(self):
        reg_ufo = self._run_on_ufo('MyFont', 'Regular')
        italic_ufo = self._run_on_ufo('MyFont', 'Italic')
        thin_ufo = self._run_on_ufo('MyFont', 'Thin')
        self.assertFalse(reg_ufo.lib)
        self.assertFalse(italic_ufo.lib)
        self.assertTrue(thin_ufo.lib)

    def test_sets_width_lib_entry_only_condensed(self):
        reg_ufo = self._run_on_ufo('MyFont', 'Regular')
        italic_ufo = self._run_on_ufo('MyFont', 'Italic')
        cond_ufo = self._run_on_ufo('MyFont', 'Condensed')
        cond_italic_ufo = self._run_on_ufo('MyFont', 'Condensed Italic')
        self.assertFalse(reg_ufo.lib)
        self.assertFalse(italic_ufo.lib)
        self.assertTrue(cond_ufo.lib)
        self.assertTrue(cond_italic_ufo.lib)

    def _run_style_map_names_test(self, args):
        for family, style, expected_family, expected_style in args:
            ufo = self._run_on_ufo(family, style)
            self.assertEquals(ufo.info.styleMapFamilyName, expected_family)
            self.assertEquals(ufo.info.styleMapStyleName, expected_style)

    def test_sets_legal_style_map_names(self):
        self._run_style_map_names_test((
            ('MyFont', '', 'MyFont', 'regular'),
            ('MyFont', 'Regular', 'MyFont', 'regular'),
            ('MyFont', 'Bold', 'MyFont', 'bold'),
            ('MyFont', 'Italic', 'MyFont', 'italic'),
            ('MyFont', 'Bold Italic', 'MyFont', 'bold italic')))

    def test_moves_width_to_family(self):
        self._run_style_map_names_test((
            ('MyFont', 'Condensed', 'MyFont Condensed', 'regular'),
            ('MyFont', 'Condensed Bold', 'MyFont Condensed', 'bold'),
            ('MyFont', 'Condensed Italic', 'MyFont Condensed', 'italic'),
            ('MyFont', 'Condensed Bold Italic', 'MyFont Condensed',
             'bold italic')))

    def test_moves_nonbold_weight_to_family(self):
        self._run_style_map_names_test((
            ('MyFont', 'Thin', 'MyFont Thin', 'regular'),
            ('MyFont', 'Thin Italic', 'MyFont Thin', 'italic'),
            ('MyFont', 'Condensed Thin', 'MyFont Condensed Thin', 'regular'),
            ('MyFont', 'Condensed Thin Italic', 'MyFont Condensed Thin',
             'italic')))


if __name__ == '__main__':
    builder.warn = _add_warning
    unittest.main()
