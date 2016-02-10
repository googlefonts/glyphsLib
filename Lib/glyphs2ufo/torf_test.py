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
from robofab.world import RFont

from glyphs2ufo import torf
from glyphs2ufo.torf import set_redundant_data, build_family_name, build_style_name, build_postscript_name


_warnings = []


def _add_warning(message):
    global _warnings
    _warnings.append(message)


def _check_warnings():
    global _warnings
    checked = list(_warnings)
    _warnings = []
    return checked


class BuildNameTest(unittest.TestCase):
    def test_family_regular_width(self):
        self.assertEquals(build_family_name('MyFont', {}, 'width'), 'MyFont')

    def test_family_nonregular_width(self):
        self.assertEquals(
            build_family_name('MyFont', {'width': 'Condensed'}, 'width'),
            'MyFont Condensed')

    def test_style_regular_weight(self):
        self.assertEquals(build_style_name({}, 'weight', False), 'Regular')
        self.assertEquals(build_style_name({}, 'weight', True), 'Italic')
        self.assertEquals(build_style_name(
            {'weight': 'Regular'}, 'weight', True), 'Italic')

    def test_style_nonregular_weight(self):
        self.assertEquals(
            build_style_name({'weight': 'Thin'}, 'weight', False), 'Thin')
        self.assertEquals(
            build_style_name({'weight': 'Thin'}, 'weight', True), 'Thin Italic')

    def test_postscript(self):
        self.assertEquals(
            build_postscript_name('MyFont', 'Regular'), 'MyFont-Regular')
        self.assertEquals(
            build_postscript_name('MyFont Condensed', 'Thin Italic'),
            'MyFontCondensed-ThinItalic')


class SetRedundantDataTest(unittest.TestCase):
    def _run_on_ufo(self, family_name, style_name):
        ufo = RFont()
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

    def test_sets_regular_weight_class_and_warns_for_unknown_weight(self):
        reg_ufo = self._run_on_ufo('MyFont', 'Regular')
        bogus_ufo = self._run_on_ufo('MyFont', 'abc123')
        self.assertEquals(
            reg_ufo.info.openTypeOS2WeightClass,
            bogus_ufo.info.openTypeOS2WeightClass)
        self.assertTrue(_check_warnings())

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
        cond_ufo = self._run_on_ufo('MyFont Condensed', 'Regular')
        semicond_ufo = self._run_on_ufo('MyFont SemiCondensed', 'Regular')
        self.assertFalse(reg_ufo.lib)
        self.assertFalse(italic_ufo.lib)
        self.assertTrue(cond_ufo.lib)
        self.assertTrue(semicond_ufo.lib)

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
            ('MyFont', 'Bold Italic', 'MyFont', 'bold italic'),
            ('MyFont Condensed', '', 'MyFont Condensed', 'regular'),
            ('MyFont Condensed', 'Regular', 'MyFont Condensed', 'regular'),
            ('MyFont Condensed', 'Bold', 'MyFont Condensed', 'bold'),
            ('MyFont Condensed', 'Italic', 'MyFont Condensed', 'italic'),
            ('MyFont Condensed', 'Bold Italic', 'MyFont Condensed',
             'bold italic')))

    def test_moves_nonbold_weight_to_family(self):
        self._run_style_map_names_test((
            ('MyFont', 'Thin', 'MyFont Thin', 'regular'),
            ('MyFont', 'Thin Italic', 'MyFont Thin', 'italic'),
            ('MyFont Condensed', 'Thin', 'MyFont Condensed Thin', 'regular'),
            ('MyFont Condensed', 'Thin Italic', 'MyFont Condensed Thin',
             'italic')))


if __name__ == '__main__':
    torf.warn = _add_warning
    unittest.main()
