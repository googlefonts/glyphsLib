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
# unittest.mock is only available for python 3+
from mock import patch
import mock

from defcon import Font
from fontTools.misc.loggingTools import CapturingLogHandler
from glyphsLib import builder
from glyphsLib.builder import build_style_name, set_custom_params,\
    set_redundant_data, to_ufos, GLYPHS_PREFIX, PUBLIC_PREFIX, \
    GLYPHLIB_PREFIX, draw_paths, set_default_params, UFO2FT_FILTERS_KEY, \
    parse_glyphs_filter


class BuildStyleNameTest(unittest.TestCase):
    def _build(self, data, italic):
        return build_style_name(data, 'width', 'weight', 'custom', italic)

    def test_style_regular_weight(self):
        self.assertEqual(self._build({}, False), 'Regular')
        self.assertEqual(self._build({}, True), 'Italic')
        self.assertEqual(
            self._build({'weight': 'Regular'}, True), 'Italic')

    def test_style_nonregular_weight(self):
        self.assertEqual(
            self._build({'weight': 'Thin'}, False), 'Thin')
        self.assertEqual(
            self._build({'weight': 'Thin'}, True), 'Thin Italic')

    def test_style_nonregular_width(self):
        self.assertEqual(
            self._build({'width': 'Condensed'}, False), 'Condensed')
        self.assertEqual(
            self._build({'width': 'Condensed'}, True), 'Condensed Italic')
        self.assertEqual(
            self._build({'weight': 'Thin', 'width': 'Condensed'}, False),
            'Condensed Thin')
        self.assertEqual(
            self._build({'weight': 'Thin', 'width': 'Condensed'}, True),
            'Condensed Thin Italic')


class SetCustomParamsTest(unittest.TestCase):
    def setUp(self):
        self.ufo = Font()

    def test_normalizes_curved_quotes_in_names(self):
        data = {'customParameters': (
            {'name': '‘bad’', 'value': 1},
            {'name': '“also bad”', 'value': 2})}
        set_custom_params(self.ufo, data=data)
        self.assertIn(GLYPHS_PREFIX + "'bad'", self.ufo.lib)
        self.assertIn(GLYPHS_PREFIX + '"also bad"', self.ufo.lib)

    def test_set_glyphOrder(self):
        set_custom_params(self.ufo, parsed=[('glyphOrder', ['A', 'B'])])
        self.assertEqual(self.ufo.lib[PUBLIC_PREFIX + 'glyphOrder'], ['A', 'B'])

    def test_set_fsSelection_flags(self):
        self.assertEqual(self.ufo.info.openTypeOS2Selection, None)

        set_custom_params(self.ufo, parsed=[('Has WWS Names', False)])
        self.assertEqual(self.ufo.info.openTypeOS2Selection, None)

        set_custom_params(self.ufo, parsed=[('Use Typo Metrics', True)])
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [7])

        self.ufo = Font()
        set_custom_params(self.ufo, parsed=[('Has WWS Names', True),
                                       ('Use Typo Metrics', True)])
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [8, 7])

    def test_underlinePosition(self):
        set_custom_params(self.ufo, parsed=[('underlinePosition', -2)])
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, -2)

        set_custom_params(self.ufo, parsed=[('underlinePosition', 1)])
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, 1)

    def test_underlineThickness(self):
        set_custom_params(self.ufo, parsed=[('underlineThickness', 100)])
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 100)

        set_custom_params(self.ufo, parsed=[('underlineThickness', 0)])
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 0)

    @patch('glyphsLib.builder.parse_glyphs_filter')
    def test_parse_glyphs_filter(self, mock_parse_glyphs_filter):
        filter1 = ('Filter', 'Transformations;OffsetX:40;OffsetY:60;include:uni0334,uni0335')
        filter2 = ('Filter', 'Transformations;OffsetX:10;OffsetY:-10;exclude:uni0334,uni0335')
        set_custom_params(self.ufo, parsed=[filter1, filter2])

        self.assertEqual(mock_parse_glyphs_filter.call_count, 2)
        self.assertEqual(mock_parse_glyphs_filter.call_args_list[0], mock.call(filter1[1]))
        self.assertEqual(mock_parse_glyphs_filter.call_args_list[1], mock.call(filter2[1]))

    def test_set_defaults(self):
        set_default_params(self.ufo)
        self.assertEqual(self.ufo.info.openTypeOS2Type, [3])
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, -100)
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 50)


class ParseGlyphsFilterTest(unittest.TestCase):
    def test_complete_parameter(self):
        inputstr = 'Transformations;LSB:+23;RSB:-22;SlantCorrection:true;OffsetX:10;OffsetY:-10;Origin:0;exclude:uni0334,uni0335 uni0336'
        expected = {
            'name': 'Transformations',
            'kwargs': {
                'LSB': 23,
                'RSB': -22,
                'SlantCorrection': True,
                'OffsetX': 10,
                'OffsetY': -10,
                'Origin': 0,
            },
            'exclude': ['uni0334', 'uni0335', 'uni0336'],
        }
        result = parse_glyphs_filter(inputstr)
        self.assertEqual(result, expected)

    def test_positional_parameter(self):
        inputstr = 'Roughenizer;34;2;0;0.34'
        expected = {
            'name': 'Roughenizer',
            'args': [34, 2, 0, 0.34],
        }
        result = parse_glyphs_filter(inputstr)
        self.assertEqual(result, expected)

    def test_single_name(self):
        inputstr = 'AddExtremes'
        expected = {
            'name': 'AddExtremes',
        }
        result = parse_glyphs_filter(inputstr)
        self.assertEqual(result, expected)

    def test_empty_string(self):
        inputstr = ''
        with CapturingLogHandler(builder.logger, "ERROR") as captor:
            result = parse_glyphs_filter(inputstr)
        self.assertGreater(len([r for r in captor.records if 'Failed to parse glyphs filter' in r.msg]), 0,
            msg='Empty string should trigger an error message')

    def test_no_name(self):
        inputstr = ';OffsetX:2'
        with CapturingLogHandler(builder.logger, "ERROR") as captor:
            result = parse_glyphs_filter(inputstr)
        self.assertGreater(len([r for r in captor.records if 'Failed to parse glyphs filter' in r.msg]), 0,
            msg='Empty string with no filter name should trigger an error message')

    def test_duplicate_exclude_include(self):
        inputstr = 'thisisaname;34;-3.4;exclude:uni1111;include:uni0022;exclude:uni2222'
        expected = {
            'name': 'thisisaname',
            'args': [34, -3.4],
            'exclude': ['uni2222'],
        }
        with CapturingLogHandler(builder.logger, "ERROR") as captor:
            result = parse_glyphs_filter(inputstr)

        self.assertGreater(len([r for r in captor.records if 'can only present as the last argument' in r.msg]), 0,
            msg='The parse_glyphs_filter should warn user that the exclude/include should only be the last argument in the filter string.')
        self.assertEqual(result, expected)

    def test_empty_args_trailing_semicolon(self):
        inputstr = 'thisisaname;3;;a:b;;;'
        expected = {
            'name': 'thisisaname',
            'args': [3],
            'kwargs': {'a': 'b'}
        }
        result = parse_glyphs_filter(inputstr)
        self.assertEqual(result, expected)

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
        self.assertEqual(
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
            self.assertEqual(ufo.info.styleMapFamilyName, expected_family)
            self.assertEqual(ufo.info.styleMapStyleName, expected_style)

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

    def add_glyph(self, data, glyphname):
        glyph = {
            'glyphname': glyphname,
            'layers': [{'layerId': data['fontMaster'][0]['id'], 'width': 0}]
        }
        data['glyphs'].append(glyph)
        return glyph

    def add_anchor(self, data, glyphname, anchorname, x, y):
        for glyph in data['glyphs']:
            if glyph['glyphname'] == glyphname:
                for layer in glyph['layers']:
                    anchors = layer.setdefault('anchors', [])
                    anchors.append({'name': anchorname, 'position': (x, y)})

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

    def test_postscript_name_from_data(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'foo')['production'] = 'f_o_o.alt1'
        ufo = to_ufos(data)[0]
        postscriptNames = ufo.lib.get('public.postscriptNames')
        self.assertEqual(postscriptNames, {'foo': 'f_o_o.alt1'})

    def test_postscript_name_from_glyph_name(self):
        data = self.generate_minimal_data()
        # in GlyphData (and AGLFN) without a 'production' name
        self.add_glyph(data, 'A')
        # not in GlyphData, no production name
        self.add_glyph(data, 'foobar')
        # in GlyphData with a 'production' name
        self.add_glyph(data, 'C-fraktur')
        ufo = to_ufos(data)[0]
        postscriptNames = ufo.lib.get('public.postscriptNames')
        self.assertEqual(postscriptNames, {'C-fraktur': 'uni212D'})

    def test_category(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'foo')['category'] = 'Mark'
        self.add_glyph(data, 'bar')
        ufo = to_ufos(data)[0]
        category_key = GLYPHLIB_PREFIX + 'category'
        self.assertEqual(ufo['foo'].lib.get(category_key), 'Mark')
        self.assertFalse(category_key in ufo['bar'].lib)

    def test_subCategory(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'foo')['subCategory'] = 'Nonspacing'
        self.add_glyph(data, 'bar')
        ufo = to_ufos(data)[0]
        subCategory_key = GLYPHLIB_PREFIX + 'subCategory'
        self.assertEqual(ufo['foo'].lib.get(subCategory_key), 'Nonspacing')
        self.assertFalse(subCategory_key in ufo['bar'].lib)

    def test_mark_nonspacing_zero_width(self):
        data = self.generate_minimal_data()

        self.add_glyph(data, 'dieresiscomb')['layers'][0]['width'] = 100

        foo = self.add_glyph(data, 'foo')
        foo['category'] = 'Mark'
        foo['subCategory'] = 'Nonspacing'
        foo['layers'][0]['width'] = 200

        bar = self.add_glyph(data, 'bar')
        bar['category'] = 'Mark'
        bar['subCategory'] = 'Nonspacing'
        bar['layers'][0]['width'] = 0

        ufo = to_ufos(data)[0]

        originalWidth_key = GLYPHLIB_PREFIX + 'originalWidth'
        self.assertEqual(ufo['dieresiscomb'].width, 0)
        self.assertEqual(ufo['dieresiscomb'].lib.get(originalWidth_key), 100)
        self.assertEqual(ufo['foo'].width, 0)
        self.assertEqual(ufo['foo'].lib.get(originalWidth_key), 200)
        self.assertEqual(ufo['bar'].width, 0)
        self.assertFalse(originalWidth_key in ufo['bar'].lib)

    def test_weightClass_default(self):
        data = self.generate_minimal_data()
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.info.openTypeOS2WeightClass, 400)

    def test_weightClass_from_customParameter_weightClass(self):
        # In the test input, the weight is specified twice: once as weight,
        # once as customParameters.weightClass. We expect that the latter wins
        # because the Glyphs handbook documents that the weightClass value
        # overrides the setting in the Weight drop-down list.
        # https://glyphsapp.com/content/1-get-started/2-manuals/1-handbook-glyphs-2-0/Glyphs-Handbook-2.3.pdf#page=202
        data = self.generate_minimal_data()
        master = data['fontMaster'][0]
        master['weight'] = 'Bold'  # 700
        master['customParameters'] = ({'name': 'weightClass', 'value': 698},)
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.info.openTypeOS2WeightClass, 698)  # 698, not 700

    def test_weightClass_from_weight(self):
        data = self.generate_minimal_data()
        data['fontMaster'][0]['weight'] = 'Bold'
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.info.openTypeOS2WeightClass, 700)

    def test_widthClass_default(self):
        data = self.generate_minimal_data()
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 5)

    def test_widthClass_from_customParameter_widthClass(self):
        # In the test input, the width is specified twice: once as width,
        # once as customParameters.widthClass. We expect that the latter wins
        # because the Glyphs handbook documents that the widthClass value
        # overrides the setting in the Width drop-down list.
        # https://glyphsapp.com/content/1-get-started/2-manuals/1-handbook-glyphs-2-0/Glyphs-Handbook-2.3.pdf#page=203
        data = self.generate_minimal_data()
        master = data['fontMaster'][0]
        master['width'] = 'Extra Condensed'  # 2
        master['customParameters'] = ({'name': 'widthClass', 'value': 7},)
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 7)  # 7, not 2

    def test_widthClass_from_width(self):
        data = self.generate_minimal_data()
        data['fontMaster'][0]['width'] = 'Extra Condensed'
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 2)

    def test_GDEF(self):
        data = self.generate_minimal_data()
        for glyph in ('space', 'A', 'A.alt',
                      'wigglylinebelowcomb', 'wigglylinebelowcomb.alt',
                      'fi', 'fi.alt', 't_e_s_t', 't_e_s_t.alt'):
            self.add_glyph(data, glyph)
        self.add_anchor(data, 'A', 'bottom', 300, -10)
        self.add_anchor(data, 'wigglylinebelowcomb', '_bottom', 100, 40)
        self.add_anchor(data, 'fi', 'caret_1', 150, 0)
        self.add_anchor(data, 't_e_s_t.alt', 'caret_1', 200, 0)
        self.add_anchor(data, 't_e_s_t.alt', 'caret_2', 400, 0)
        self.add_anchor(data, 't_e_s_t.alt', 'caret_3', 600, 0)
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.features.text.splitlines(), [
            'table GDEF {',
            '  # automatic',
            '  GlyphClassDef',
            '    [A], # Base',
            '    [fi t_e_s_t.alt], # Liga',
            '    [wigglylinebelowcomb wigglylinebelowcomb.alt], # Mark',
            '    ;',
            '  LigatureCaretByPos fi 150;',
            '  LigatureCaretByPos t_e_s_t.alt 200 400 600;',
            '} GDEF;',
        ])

    def test_GDEF_base_with_attaching_anchor(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'A.alt')
        self.add_anchor(data, 'A.alt', 'top', 400, 1000)
        self.assertIn('[A.alt], # Base', to_ufos(data)[0].features.text)

    def test_GDEF_base_with_nonattaching_anchor(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'A.alt')
        self.add_anchor(data, 'A.alt', '_top', 400, 1000)
        self.assertEqual('', to_ufos(data)[0].features.text)

    def test_GDEF_ligature_with_attaching_anchor(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'fi')
        self.add_anchor(data, 'fi', 'top', 400, 1000)
        self.assertIn('[fi], # Liga', to_ufos(data)[0].features.text)

    def test_GDEF_ligature_with_nonattaching_anchor(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'fi')
        self.add_anchor(data, 'fi', '_top', 400, 1000)
        self.assertEqual('', to_ufos(data)[0].features.text)

    def test_GDEF_mark(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'eeMatra-gurmukhi')
        self.assertIn('[eeMatra-gurmukhi], # Mark',
                      to_ufos(data)[0].features.text)

    def test_GDEF_fractional_caret_position(self):
        # Some Glyphs sources happen to contain fractional caret positions.
        # In the Adobe feature file syntax (and binary OpenType GDEF tables),
        # caret positions must be integers.
        data = self.generate_minimal_data()
        self.add_glyph(data, 'fi')
        self.add_anchor(data, 'fi', 'caret_1', 499.9876, 0)
        self.assertIn('LigatureCaretByPos fi 500;',
                      to_ufos(data)[0].features.text)

    def test_GDEF_custom_category_subCategory(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'foo')['subCategory'] = 'Ligature'
        self.add_anchor(data, 'foo', 'top', 400, 1000)
        bar = self.add_glyph(data, 'bar')
        bar['category'], bar['subCategory'] = 'Mark', 'Nonspacing'
        baz = self.add_glyph(data, 'baz')
        baz['category'], baz['subCategory'] = 'Mark', 'Spacing Combining'
        features = to_ufos(data)[0].features.text
        self.assertIn('[foo], # Liga', features)
        self.assertIn('[bar baz], # Mark', features)

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

    def test_set_glyphOrder_no_custom_param(self):
        data = self.generate_minimal_data()
        self.add_glyph(data, 'C')
        self.add_glyph(data, 'B')
        self.add_glyph(data, 'A')
        self.add_glyph(data, 'Z')
        glyphOrder = to_ufos(data)[0].lib[PUBLIC_PREFIX + 'glyphOrder']
        self.assertEqual(glyphOrder, ['C', 'B', 'A', 'Z'])

    def test_set_glyphOrder_with_custom_param(self):
        data = self.generate_minimal_data()
        data['customParameters'] = (
            {'name': 'glyphOrder', 'value': ['A', 'B', 'C']},)
        self.add_glyph(data, 'C')
        self.add_glyph(data, 'B')
        self.add_glyph(data, 'A')
        # glyphs outside glyphOrder are appended at the end
        self.add_glyph(data, 'Z')
        glyphOrder = to_ufos(data)[0].lib[PUBLIC_PREFIX + 'glyphOrder']
        self.assertEqual(glyphOrder, ['A', 'B', 'C', 'Z'])

    def test_missing_date(self):
        data = self.generate_minimal_data()
        del data['date']
        ufo = to_ufos(data)[0]
        self.assertIsNone(ufo.info.openTypeHeadCreated)

    def test_variation_font_origin(self):
        data = self.generate_minimal_data()
        name = 'Variation Font Origin'
        value = 'Light'
        data['customParameters'] = (
            {'name': name, 'value': value},)

        ufos, instances = to_ufos(data, include_instances=True)

        for ufo in ufos:
            key = GLYPHS_PREFIX + name
            self.assertIn(key, ufo.lib)
            self.assertEqual(ufo.lib[key], value)
        self.assertIn(name, instances)
        self.assertEqual(instances[name], value)

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
