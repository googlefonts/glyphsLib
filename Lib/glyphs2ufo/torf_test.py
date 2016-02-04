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
from glyphs2ufo.torf import set_redundant_data


_warnings = []


def _add_warning(message):
    global _warnings
    _warnings.append(message)


def _check_warnings():
    global _warnings
    checked = list(_warnings)
    _warnings = []
    return checked


class SetRedundantDataTest(unittest.TestCase):
    def run_on_ufo(self, family_name, style_name):
        ufo = RFont()
        ufo.info.familyName = family_name
        ufo.info.styleName = style_name
        set_redundant_data(ufo)
        return ufo

    def test_sets_regular_weight_class_for_missing_weight(self):
        reg_ufo = self.run_on_ufo('MyFont', 'Regular')
        cond_ufo = self.run_on_ufo('MyFont', 'Condensed')
        self.assertEquals(
            reg_ufo.info.openTypeOS2WeightClass,
            cond_ufo.info.openTypeOS2WeightClass)

    def test_sets_regular_weight_class_and_warns_for_unknown_weight(self):
        reg_ufo = self.run_on_ufo('MyFont', 'Regular')
        bogus_ufo = self.run_on_ufo('MyFont', 'abc123')
        self.assertEquals(
            reg_ufo.info.openTypeOS2WeightClass,
            bogus_ufo.info.openTypeOS2WeightClass)
        self.assertTrue(_check_warnings())

    def run_style_map_names_test(self, args):
        for family, style, expected_family, expected_style in args:
            ufo = self.run_on_ufo(family, style)
            self.assertEquals(ufo.info.styleMapFamilyName, expected_family)
            self.assertEquals(ufo.info.styleMapStyleName, expected_style)

    def test_sets_legal_style_map_names(self):
        self.run_style_map_names_test((
            ('MyFont', 'Regular', 'MyFont', 'regular'),
            ('MyFont', 'Bold', 'MyFont', 'bold'),
            ('MyFont', 'Italic', 'MyFont', 'italic'),
            ('MyFont', 'Bold Italic', 'MyFont', 'bold italic')))

    def test_moves_nonbold_weight_to_family(self):
        self.run_style_map_names_test((
            ('MyFont', 'Thin', 'MyFont Thin', 'regular'),
            ('MyFont', 'Thin Italic', 'MyFont Thin', 'italic')))

    def test_moves_width_to_family(self):
        self.run_style_map_names_test((
            ('MyFont', 'Condensed', 'MyFont Condensed', 'regular'),
            ('MyFont', 'Condensed Italic', 'MyFont Condensed', 'italic'),
            ('MyFont', 'Condensed Thin', 'MyFont Condensed Thin', 'regular'),
            ('MyFont', 'Condensed Thin Italic', 'MyFont Condensed Thin',
             'italic')))

    def test_moves_bold_weight_to_family_with_width(self):
        # this may be changed in the future, if needed
        self.run_style_map_names_test((
            ('MyFont', 'Condensed Bold', 'MyFont Condensed Bold', 'regular'),
            ('MyFont', 'Condensed Bold Italic', 'MyFont Condensed Bold',
             'italic')))


if __name__ == '__main__':
    torf.warn = _add_warning
    unittest.main()
