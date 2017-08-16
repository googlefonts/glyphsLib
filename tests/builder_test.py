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
    to_ufos, GLYPHS_PREFIX, PUBLIC_PREFIX, GLYPHLIB_PREFIX, draw_paths, \
    set_default_params, parse_glyphs_filter, build_stylemap_names


class BuildStyleNameTest(unittest.TestCase):

    def test_style_regular_weight(self):
        self.assertEqual(build_style_name(is_italic=False), 'Regular')
        self.assertEqual(build_style_name(is_italic=True), 'Italic')

    def test_style_nonregular_weight(self):
        self.assertEqual(
            build_style_name(weight='Thin', is_italic=False), 'Thin')
        self.assertEqual(
            build_style_name(weight='Thin', is_italic=True), 'Thin Italic')

    def test_style_nonregular_width(self):
        self.assertEqual(
            build_style_name(width='Condensed', is_italic=False), 'Condensed')
        self.assertEqual(
            build_style_name(width='Condensed', is_italic=True),
            'Condensed Italic')
        self.assertEqual(
            build_style_name(weight='Thin', width='Condensed',
                             is_italic=False),
            'Condensed Thin')
        self.assertEqual(
            build_style_name(weight='Thin', width='Condensed',
                             is_italic=True),
            'Condensed Thin Italic')

    def test_style_custom(self):
        self.assertEqual(
            build_style_name(custom='Text', is_italic=False), 'Text')
        self.assertEqual(
            build_style_name(weight='Text', is_italic=True), 'Text Italic')


class BuildStyleMapNamesTest(unittest.TestCase):

    def test_regular(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Regular",
            is_bold=False,
            is_italic=False,
            linked_style=None
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("regular", map_style)

    def test_regular_isBold(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Regular",
            is_bold=True,
            is_italic=False,
            linked_style=None
        )
        self.assertEqual("NotoSans Regular", map_family)
        self.assertEqual("bold", map_style)

    def test_regular_isItalic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Regular",
            is_bold=False,
            is_italic=True,
            linked_style=None
        )
        self.assertEqual("NotoSans Regular", map_family)
        self.assertEqual("italic", map_style)

    def test_non_regular(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="ExtraBold",
            is_bold=False,
            is_italic=False,
            linked_style=None
        )
        self.assertEqual("NotoSans ExtraBold", map_family)
        self.assertEqual("regular", map_style)

    def test_bold_no_style_link(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold",
            is_bold=False,  # not style-linked, despite the name
            is_italic=False,
            linked_style=None
        )
        self.assertEqual("NotoSans Bold", map_family)
        self.assertEqual("regular", map_style)

    def test_italic_no_style_link(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Italic",
            is_bold=False,
            is_italic=False,  # not style-linked, despite the name
            linked_style=None
        )
        self.assertEqual("NotoSans Italic", map_family)
        self.assertEqual("regular", map_style)

    def test_bold_italic_no_style_link(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold Italic",
            is_bold=False,    # not style-linked, despite the name
            is_italic=False,  # not style-linked, despite the name
            linked_style=None
        )
        self.assertEqual("NotoSans Bold Italic", map_family)
        self.assertEqual("regular", map_style)

    def test_bold(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold",
            is_bold=True,
            is_italic=False,
            linked_style=None
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold", map_style)

    def test_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Italic",
            is_bold=False,
            is_italic=True,
            linked_style=None
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("italic", map_style)

    def test_bold_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold Italic",
            is_bold=True,
            is_italic=True,
            linked_style=None
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold italic", map_style)

    def test_incomplete_bold_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Bold",  # will be stripped...
            is_bold=True,
            is_italic=True,
            linked_style=None
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold italic", map_style)

        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Italic",  # will be stripped...
            is_bold=True,
            is_italic=True,
            linked_style=None
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold italic", map_style)

    def test_italicbold_isBoldItalic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Italic Bold",  # reversed
            is_bold=True,
            is_italic=True,
            linked_style=None
        )
        self.assertEqual("NotoSans", map_family)
        self.assertEqual("bold italic", map_style)

    def test_linked_style_regular(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Condensed",
            is_bold=False,
            is_italic=False,
            linked_style="Cd"
        )
        self.assertEqual("NotoSans Cd", map_family)
        self.assertEqual("regular", map_style)

    def test_linked_style_bold(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Condensed Bold",
            is_bold=True,
            is_italic=False,
            linked_style="Cd"
        )
        self.assertEqual("NotoSans Cd", map_family)
        self.assertEqual("bold", map_style)

    def test_linked_style_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Condensed Italic",
            is_bold=False,
            is_italic=True,
            linked_style="Cd"
        )
        self.assertEqual("NotoSans Cd", map_family)
        self.assertEqual("italic", map_style)

    def test_linked_style_bold_italic(self):
        map_family, map_style = build_stylemap_names(
            family_name="NotoSans",
            style_name="Condensed Bold Italic",
            is_bold=True,
            is_italic=True,
            linked_style="Cd"
        )
        self.assertEqual("NotoSans Cd", map_family)
        self.assertEqual("bold italic", map_style)


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

    def test_set_codePageRanges(self):
        set_custom_params(self.ufo, parsed=[('codePageRanges', [1252, 1250])])
        self.assertEqual(self.ufo.info.openTypeOS2CodePageRanges, [0, 1])

    def test_set_openTypeOS2CodePageRanges(self):
        set_custom_params(self.ufo, parsed=[
            ('openTypeOS2CodePageRanges', [0, 1])])
        self.assertEqual(self.ufo.info.openTypeOS2CodePageRanges, [0, 1])

    def test_gasp_table(self):
        gasp_table = {'65535': '15',
                      '20': '7',
                      '8': '10'}
        set_custom_params(self.ufo, parsed=[('GASP Table', gasp_table)])

        ufo_range_records = self.ufo.info.openTypeGaspRangeRecords
        self.assertIsNotNone(ufo_range_records)
        self.assertEqual(len(ufo_range_records), 3)
        rec1, rec2, rec3 = ufo_range_records
        self.assertEqual(rec1['rangeMaxPPEM'], 8)
        self.assertEqual(rec1['rangeGaspBehavior'], [1, 3])
        self.assertEqual(rec2['rangeMaxPPEM'], 20)
        self.assertEqual(rec2['rangeGaspBehavior'], [0, 1, 2])
        self.assertEqual(rec3['rangeMaxPPEM'], 65535)
        self.assertEqual(rec3['rangeGaspBehavior'], [0, 1, 2, 3])


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
        # check propagated anchors are appended in a deterministic order
        self.assertEqual(
            [anchor.name for anchor in glyph.anchors],
            ['bottom', 'top']
        )
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

    def test_family_name_none(self):
        data = self.generate_minimal_data()
        data['instances'] = [
            {
                'name': 'Regular1'
            },
            {
                'name': 'Regular2',
                'customParameters': [
                    {
                        'name': 'familyName',
                        'value': 'CustomFamily'
                    },
                ]
            }
        ]
        # 'family_name' defaults to None
        ufos, instance_data = to_ufos(data, include_instances=True)
        instances = instance_data['data']

        # all instances are included, both with/without 'familyName' parameter
        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0]['name'], 'Regular1')
        self.assertEqual(instances[1]['name'], 'Regular2')
        self.assertTrue('customParameters' not in instances[0])
        self.assertTrue('customParameters' in instances[1])
        self.assertEqual(instances[1]['customParameters'][0]['value'], 'CustomFamily')

        # the masters' family name is unchanged
        for ufo in ufos:
            self.assertEqual(ufo.info.familyName, 'MyFont')

    def test_family_name_same_as_default(self):
        data = self.generate_minimal_data()
        data['instances'] = [
            {
                'name': 'Regular1'
            },
            {
                'name': 'Regular2',
                'customParameters': [
                    {
                        'name': 'familyName',
                        'value': 'CustomFamily'
                    },
                ]
            }
        ]
        # 'MyFont' is the source family name, as returned from
        # 'generate_minimal_data'
        ufos, instance_data = to_ufos(data,
                                      include_instances=True,
                                      family_name='MyFont')
        instances = instance_data['data']

        # only instances which don't have 'familyName' custom parameter
        # are included in returned list
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['name'], 'Regular1')
        self.assertTrue('customParameters' not in instances[0])

        # the masters' family name is unchanged
        for ufo in ufos:
            self.assertEqual(ufo.info.familyName, 'MyFont')

    def test_family_name_custom(self):
        data = self.generate_minimal_data()
        data['instances'] = [
            {
                'name': 'Regular1'
            },
            {
                'name': 'Regular2',
                'customParameters': [
                    {
                        'name': 'familyName',
                        'value': 'CustomFamily'
                    },
                ]
            }
        ]
        ufos, instance_data = to_ufos(data,
                                      include_instances=True,
                                      family_name='CustomFamily')
        instances = instance_data['data']

        # only instances with familyName='CustomFamily' are included
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['name'], 'Regular2')
        self.assertTrue('customParameters' in instances[0])
        self.assertEqual(instances[0]['customParameters'][0]['value'],
                         'CustomFamily')

        # the masters' family is also modified to use custom 'family_name'
        for ufo in ufos:
            self.assertEqual(ufo.info.familyName, 'CustomFamily')

    def test_lib_no_weight(self):
        data = self.generate_minimal_data()
        ufo = to_ufos(data)[0]
        self.assertFalse(GLYPHS_PREFIX + 'weight' in ufo.lib)

    def test_lib_weight(self):
        data = self.generate_minimal_data()
        data['fontMaster'][0]['weight'] = 'Bold'
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + 'weight'], 'Bold')

    def test_lib_no_width(self):
        data = self.generate_minimal_data()
        ufo = to_ufos(data)[0]
        self.assertFalse(GLYPHS_PREFIX + 'width' in ufo.lib)

    def test_lib_width(self):
        data = self.generate_minimal_data()
        data['fontMaster'][0]['width'] = 'Condensed'
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + 'width'], 'Condensed')

    def test_lib_no_custom(self):
        data = self.generate_minimal_data()
        ufo = to_ufos(data)[0]
        self.assertFalse(GLYPHS_PREFIX + 'custom' in ufo.lib)

    def test_lib_custom(self):
        data = self.generate_minimal_data()
        data['fontMaster'][0]['custom'] = 'FooBar'
        ufo = to_ufos(data)[0]
        self.assertEqual(ufo.lib[GLYPHS_PREFIX + 'custom'], 'FooBar')

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

    def test_draw_paths_qcurve(self):
        contours = [{
            'closed': True,
            'nodes': [
                (143, 695, 'offcurve', False),
                (37, 593, 'offcurve', False),
                (37, 434, 'offcurve', False),
                (143, 334, 'offcurve', False),
                (223, 334, 'qcurve', True),
            ]}]

        pen = _PointDataPen()
        draw_paths(pen, contours)

        points = pen.contours[0]

        first_x, first_y = points[0][:2]
        self.assertEqual((first_x, first_y), (223, 334))

        first_segment_type = points[0][2]
        self.assertEqual(first_segment_type, 'qcurve')


if __name__ == '__main__':
    unittest.main()
