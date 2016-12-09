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
import datetime
import unittest

from defcon import Font

from fontTools.misc.loggingTools import CapturingLogHandler

from glyphsLib import builder
from glyphsLib.builder import build_style_name, set_custom_params,\
    set_redundant_data, to_ufos, GLYPHS_PREFIX, draw_paths


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


class SetCustomParamsTest(unittest.TestCase):
    def test_normalizes_curved_quotes_in_names(self):
        ufo = Font()
        data = {'customParameters': (
            {'name': '‘bad’', 'value': 1},
            {'name': '“also bad”', 'value': 2})}
        set_custom_params(ufo, data=data)
        self.assertIn(GLYPHS_PREFIX + "'bad'", ufo.lib)
        self.assertIn(GLYPHS_PREFIX + '"also bad"', ufo.lib)


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


class ToUfosTest(unittest.TestCase):
    def generate_minimal_data(self):
        return {
            '.appVersion': 895,
            'date': datetime.datetime.today(),
            'familyName': 'MyFont',
            'fontMaster': [{
                'ascender': 0,
                'capHeight': 0,
                'descender': 0,
                'id': 'id',
                'xHeight': 0,
            }],
            'glyphs': [],
            'unitsPerEm': 1000,
            'versionMajor': 1,
            'versionMinor': 0,
        }

    def test_minimal_data(self):
        """Test the minimal data that must be provided to generate UFOs, and in
        some cases that additional redundant data is not set.
        """

        data = self.generate_minimal_data()
        family_name = data['familyName']
        ufos = to_ufos(data)
        self.assertEqual(len(ufos), 1)

        ufo = ufos[0]
        self.assertEqual(len(ufo), 0)
        self.assertEqual(ufo.info.familyName, family_name)
        self.assertEqual(ufo.info.styleName, 'Regular')
        self.assertEqual(ufo.info.versionMajor, 1)
        self.assertEqual(ufo.info.versionMinor, 0)
        self.assertIsNone(ufo.info.openTypeNameVersion)
        #TODO(jamesgk) try to generate minimally-populated UFOs in glyphsLib,
        # assert that more fields are empty here (especially in name table)

    def test_warn_no_version(self):
        """Test that a warning is printed when app version is missing."""

        data = self.generate_minimal_data()
        del data['.appVersion']
        with CapturingLogHandler(builder.logger, "WARNING") as captor:
            to_ufos(data)
        self.assertEqual(len([r for r in captor.records
                              if "outdated version" in r.msg]), 1)

    def test_load_kerning(self):
        """Test that kerning conflicts are resolved correctly.

        Correct resolution is defined as such: the last time a pair is found in
        a kerning rule, that rule is used for the pair.
        """

        data = self.generate_minimal_data()

        # generate classes 'A': ['A', 'a'] and 'V': ['V', 'v']
        for glyph_name in ('A', 'a', 'V', 'v'):
            data['glyphs'].append({
                'glyphname': glyph_name, 'layers': [],
                'rightKerningGroup': glyph_name.upper(),
                'leftKerningGroup': glyph_name.upper()})

        # classes are referenced in Glyphs kerning using old MMK names
        data['kerning'] = {
            data['fontMaster'][0]['id']: collections.OrderedDict((
                ('@MMK_L_A', collections.OrderedDict((
                    ('@MMK_R_V', -250),
                    ('v', -100),
                ))),
                ('a', collections.OrderedDict((
                    ('@MMK_R_V', 100),
                ))),
            ))}

        ufos = to_ufos(data)
        ufo = ufos[0]

        # these rules should be obvious
        self.assertEqual(ufo.kerning['public.kern1.A', 'public.kern2.V'], -250)
        self.assertEqual(ufo.kerning['a', 'public.kern2.V'], 100)

        # this rule results from breaking up (kern1.A, v, -100)
        # due to conflict with (a, kern2.V, 100)
        self.assertEqual(ufo.kerning['A', 'v'], -100)

    def test_propagate_anchors(self):
        """Test anchor propagation for some relatively complicated cases."""

        data = self.generate_minimal_data()

        glyphs = (
            ('sad', [], [('bottom', 50, -50), ('top', 50, 150)]),
            ('dotabove', [], [('top', 0, 150), ('_top', 0, 100)]),
            ('dotbelow', [], [('bottom', 0, -50), ('_bottom', 0, 0)]),
            ('dad', [('sad', 0, 0), ('dotabove', 50, 50)], []),
            ('dadDotbelow', [('dad', 0, 0), ('dotbelow', 50, -50)], []),
            ('yod', [], [('bottom', 50, -50)]),
            ('yodyod', [('yod', 0, 0), ('yod', 100, 0)], []),
        )
        for name, component_data, anchor_data in glyphs:
            anchors = [{'name': n, 'position': (x, y)}
                       for n, x, y in anchor_data]
            components = [{'name': n, 'transform': (1, 0, 0, 1, x, y)}
                          for n, x, y in component_data]
            data['glyphs'].append({
                'glyphname': name,
                'layers': [{'layerId': data['fontMaster'][0]['id'], 'width': 0,
                            'anchors': anchors, 'components': components}]})

        ufos = to_ufos(data)
        ufo = ufos[0]

        glyph = ufo['dadDotbelow']
        self.assertEqual(len(glyph.anchors), 2)
        for anchor in glyph.anchors:
            self.assertEqual(anchor.x, 50)
            if anchor.name == 'bottom':
                self.assertEqual(anchor.y, -100)
            else:
                self.assertEqual(anchor.name, 'top')
                self.assertEqual(anchor.y, 200)

        glyph = ufo['yodyod']
        self.assertEqual(len(glyph.anchors), 2)
        for anchor in glyph.anchors:
            self.assertEqual(anchor.y, -50)
            if anchor.name == 'bottom_1':
                self.assertEqual(anchor.x, 50)
            else:
                self.assertEqual(anchor.name, 'bottom_2')
                self.assertEqual(anchor.x, 150)

    def test_set_blue_values(self):
        """Test that blue values are set correctly from alignment zones."""

        data_in = [(500, 15), (400, -15), (0, -15), (-200, 15), (-300, -15)]
        expected_blue_values = [-200, -185, -15, 0, 500, 515]
        expected_other_blues = [-315, -300, 385, 400]

        data = self.generate_minimal_data()
        data['fontMaster'][0]['alignmentZones'] = data_in
        ufo = to_ufos(data)[0]

        self.assertEqual(ufo.info.postscriptBlueValues, expected_blue_values)
        self.assertEqual(ufo.info.postscriptOtherBlues, expected_other_blues)

    def _run_guideline_test(self, data_in, expected):
        data = self.generate_minimal_data()
        data['glyphs'].append({
            'glyphname': 'a',
            'layers': [{'layerId': data['fontMaster'][0]['id'], 'width': 0,
                        'guideLines': data_in}]})
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo['a'].guidelines, expected)

    #TODO enable these when we switch to loading UFO3 guidelines
    #def test_set_guidelines(self):
    #    """Test that guidelines are set correctly."""

    #    self._run_guideline_test(
    #        [{'position': (1, 2), 'angle': 270}],
    #        [{str('x'): 1, str('y'): 2, str('angle'): 90}])

    #def test_set_guidelines_duplicates(self):
    #    """Test that duplicate guidelines are accepted."""

    #    self._run_guideline_test(
    #        [{'position': (1, 2), 'angle': 270},
    #         {'position': (1, 2), 'angle': 270}],
    #        [{str('x'): 1, str('y'): 2, str('angle'): 90},
    #         {str('x'): 1, str('y'): 2, str('angle'): 90}])


class _PointDataPen(object):

    def __init__(self):
        self.contours = []

    def addPoint(self, pt, segmentType=None, smooth=False, **kwargs):
        self.contours[-1].append((pt[0], pt[1], segmentType, smooth))

    def beginPath(self):
        self.contours.append([])

    def endPath(self):
        if not self.contours[-1]:
            self.contours.pop()

    def addComponent(self, *args, **kwargs):
        pass


class DrawPathsTest(unittest.TestCase):

    def test_draw_paths_empty_nodes(self):
        contours = [{'nodes': []}]

        pen = _PointDataPen()
        draw_paths(pen, contours)

        self.assertEqual(pen.contours, [])

    def test_draw_paths_open(self):
        contours = [{
            'closed': False,
            'nodes': [
                (0, 0, 'line', False),
                (1, 1, 'offcurve', False),
                (2, 2, 'offcurve', False),
                (3, 3, 'curve', True),
            ]}]

        pen = _PointDataPen()
        draw_paths(pen, contours)

        self.assertEqual(pen.contours, [[
            (0, 0, 'move', False),
            (1, 1, None, False),
            (2, 2, None, False),
            (3, 3, 'curve', True),
        ]])

    def test_draw_paths_closed(self):
        contours = [{
            'closed': True,
            'nodes': [
                (0, 0, 'offcurve', False),
                (1, 1, 'offcurve', False),
                (2, 2, 'curve', True),
                (3, 3, 'offcurve', False),
                (4, 4, 'offcurve', False),
                (5, 5, 'curve', True),
            ]}]

        pen = _PointDataPen()
        draw_paths(pen, contours)

        points = pen.contours[0]

        first_x, first_y = points[0][:2]
        self.assertEqual((first_x, first_y), (5, 5))

        first_segment_type = points[0][2]
        self.assertEqual(first_segment_type, 'curve')


if __name__ == '__main__':
    unittest.main()
