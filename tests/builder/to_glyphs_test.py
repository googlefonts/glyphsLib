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

import pytest
import datetime

import defcon

from glyphsLib.builder.constants import GLYPHS_COLORS, GLYPHLIB_PREFIX
from glyphsLib import to_glyphs, to_ufos

# TODO: (jany) think hard about the ordering and RTL/LTR
# TODO: (jany) make one generic test with data using pytest


@pytest.mark.skip
def test_anchors_with_same_name_correct_order_rtl():
    ufo = defcon.Font()
    g = ufo.newGlyph('laam_alif')
    # Append the anchors in the correct order
    g.appendAnchor(dict(x=50, y=600, name='top'))
    g.appendAnchor(dict(x=250, y=600, name='top'))

    font = to_glyphs([ufo])

    top1, top2 = font.glyphs['laam_alif'].layers[0].anchors

    assert top1.name == 'top_1'
    assert top1.x == 50
    assert top1.y == 600
    assert top2.name == 'top_2'
    assert top2.x == 250
    assert top2.y == 600


@pytest.mark.skip
def test_anchors_with_same_name_wrong_order_rtl():
    ufo = defcon.Font()
    g = ufo.newGlyph('laam_alif')
    # Append the anchors in the wrong order
    g.appendAnchor(dict(x=250, y=600, name='top'))
    g.appendAnchor(dict(x=50, y=600, name='top'))

    font = to_glyphs([ufo])

    top1, top2 = font.glyphs['laam_alif'].layers[0].anchors

    # FIXME: (jany) think hard about the ordering and LTR
    assert top1.name == 'top_1'
    assert top1.x == 50
    assert top1.y == 600
    assert top2.name == 'top_2'
    assert top2.x == 250
    assert top2.y == 600


@pytest.mark.skip
def test_anchors_with_same_name_correct_order_ltr():
    ufo = defcon.Font()
    g = ufo.newGlyph('laam_alif')
    # Append the anchors in the correct order
    g.appendAnchor(dict(x=50, y=600, name='top'))
    g.appendAnchor(dict(x=250, y=600, name='top'))

    font = to_glyphs([ufo])

    top1, top2 = font.glyphs['laam_alif'].layers[0].anchors

    # FIXME: (jany) think hard about the ordering and RTL/LTR
    assert top1.name == 'top_1'
    assert top1.x == 50
    assert top1.y == 600
    assert top2.name == 'top_2'
    assert top2.x == 250
    assert top2.y == 600


@pytest.mark.skip
def test_anchors_with_same_name_wrong_order_ltr():
    ufo = defcon.Font()
    g = ufo.newGlyph('laam_alif')
    # Append the anchors in the wrong order
    g.appendAnchor(dict(x=250, y=600, name='top'))
    g.appendAnchor(dict(x=50, y=600, name='top'))

    font = to_glyphs([ufo])

    top1, top2 = font.glyphs['laam_alif'].layers[0].anchors

    # FIXME: (jany) think hard about the ordering and LTR
    assert top1.name == 'top_1'
    assert top1.x == 50
    assert top1.y == 600
    assert top2.name == 'top_2'
    assert top2.x == 250
    assert top2.y == 600


def test_groups():
    ufo = defcon.Font()
    ufo.newGlyph('T')
    ufo.newGlyph('e')
    ufo.newGlyph('o')
    samekh = ufo.newGlyph('samekh-hb')
    samekh.unicode = 0x05E1
    resh = ufo.newGlyph('resh-hb')
    resh.unicode = 0x05E8
    ufo.groups['public.kern1.T'] = ['T']
    ufo.groups['public.kern2.oe'] = ['o', 'e']
    ufo.groups['com.whatever.Te'] = ['T', 'e']
    # Groups can contain glyphs that are not in the font and that should
    # be preserved as well
    ufo.groups['public.kern1.notInFont'] = ['L']
    ufo.groups['public.kern1.halfInFont'] = ['o', 'b', 'p']
    ufo.groups['com.whatever.notInFont'] = ['i', 'j']
    # Empty groups as well (found in the wild)
    ufo.groups['public.kern1.empty'] = []
    ufo.groups['com.whatever.empty'] = []
    # Groups for RTL glyphs. In a UFO RTL kerning pair, kern1 is for the glyph
    # on the left visually (the first that gets written when writing RTL)
    # The example below with Resh and Samekh comes from:
    # https://forum.glyphsapp.com/t/dramatic-bug-in-hebrew-kerning/4093
    ufo.groups['public.kern1.hebrewLikeT'] = ['resh-hb']
    ufo.groups['public.kern2.hebrewLikeO'] = ['samekh-hb']
    groups_dict = dict(ufo.groups)

    # TODO: add a test with 2 UFOs with conflicting data
    # TODO: add a test with with both UFO groups and feature file classes
    # TODO: add a test with UFO groups that conflict with feature file classes
    font = to_glyphs([ufo], minimize_ufo_diffs=True)

    # Kerning for existing glyphs is stored in GSGlyph.left/rightKerningGroup
    assert font.glyphs['T'].rightKerningGroup == 'T'
    assert font.glyphs['o'].leftKerningGroup == 'oe'
    assert font.glyphs['e'].leftKerningGroup == 'oe'
    # In Glyphs, rightKerningGroup and leftKerningGroup refer to the sides of
    # the glyph, they don't swap for RTL glyphs
    assert font.glyphs['resh-hb'].leftKerningGroup == 'hebrewLikeT'
    assert font.glyphs['samekh-hb'].rightKerningGroup == 'hebrewLikeO'

    # Non-kerning groups are stored as classes
    assert font.classes['com.whatever.Te'].code == 'T e'
    assert font.classes['com.whatever.notInFont'].code == 'i j'
    # Kerning groups with some characters not in the font are also saved
    # somehow, but we don't care how, that fact will be better tested by the
    # roundtrip test a few lines below

    ufo, = to_ufos(font)

    # Check that nothing has changed
    assert dict(ufo.groups) == groups_dict

    # Check that changing the `left/rightKerningGroup` fields in Glyphs
    # updates the UFO kerning groups
    font.glyphs['T'].rightKerningGroup = 'newNameT'
    font.glyphs['o'].rightKerningGroup = 'onItsOwnO'

    del groups_dict['public.kern1.T']
    groups_dict['public.kern1.newNameT'] = ['T']
    groups_dict['public.kern1.halfInFont'].remove('o')
    groups_dict['public.kern1.onItsOwnO'] = ['o']

    ufo, = to_ufos(font)

    assert dict(ufo.groups) == groups_dict


def test_guidelines():
    ufo = defcon.Font()
    # Complete guideline
    ufo.appendGuideline(dict(
        x=10, y=20, angle=30, name="lc", color="1,0,0,1", identifier="lc1"))
    # Don't crash if a guideline misses information
    ufo.appendGuideline({})
    ufo.appendGuideline({'x': 10})
    ufo.appendGuideline({'y': 20})

    font = to_glyphs([ufo])

    assert len(font.masters[0].guides) == 4

    # We only care about the data in the first guideline
    # The others are here to prevent crashes when only half of the data is here
    g = font.masters[0].guides[0]

    assert g.position.x == 10
    assert g.position.y == 20
    assert g.angle == 330
    assert g.name == "lc [1,0,0,1] [#lc1]"

    ufo, = to_ufos(font)

    g = ufo.guidelines[0]

    assert g.x == 10
    assert g.y == 20
    assert g.angle == 30
    assert g.name == 'lc'
    assert g.color == '1,0,0,1'
    assert g.identifier == 'lc1'


def test_glyph_color():
    ufo = defcon.Font()
    a = ufo.newGlyph('a')
    a.markColor = GLYPHS_COLORS[3]
    b = ufo.newGlyph('b')
    b.markColor = '1,0.5,0,1'

    font = to_glyphs([ufo])

    assert font.glyphs['a'].color == 3
    assert font.glyphs['b'].color == [255, 127, 0, 255]

    ufo, = to_ufos(font)

    assert ufo['a'].markColor == GLYPHS_COLORS[3]
    # FIXME: (jany) rounding errors
    assert ufo['b'].markColor == '1,0.498,0,1'


def test_bad_ufo_date_format_in_glyph_lib():
    ufo = defcon.Font()
    a = ufo.newGlyph('a')
    a.lib[GLYPHLIB_PREFIX + 'lastChange'] = '2017-12-19 15:12:44 +0000'

    # Don't crash
    font = to_glyphs([ufo])

    assert (font.glyphs['a'].lastChange ==
            datetime.datetime(2017, 12, 19, 15, 12, 44))


def test_have_default_interpolation_values():
    """When no designspace is provided, make sure that the Glyphs file has some default "axis positions" for the masters.
    """
    thin = defcon.Font()
    thin.info.openTypeOS2WidthClass = 5
    thin.info.openTypeOS2WeightClass = 100
    regular = defcon.Font()
    regular.info.openTypeOS2WidthClass = 5
    regular.info.openTypeOS2WeightClass = 400
    bold = defcon.Font()
    bold.info.openTypeOS2WidthClass = 5
    bold.info.openTypeOS2WeightClass = 700
    thin_expanded = defcon.Font()
    thin_expanded.info.openTypeOS2WidthClass = 7
    thin_expanded.info.openTypeOS2WeightClass = 100
    bold_ultra_cond = defcon.Font()
    bold_ultra_cond.info.openTypeOS2WidthClass = 1
    bold_ultra_cond.info.openTypeOS2WeightClass = 700

    font = to_glyphs([thin, regular, bold, thin_expanded, bold_ultra_cond])

    gthin, greg, gbold, gthinex, gbolducond = font.masters

    # For weight, copy the WeightClass as-is
    assert gthin.weightValue == 100
    assert greg.weightValue == 400
    assert gbold.weightValue == 700
    assert gthinex.weightValue == 100
    assert gbolducond.weightValue == 700

    # For width, use the "% of normal" column from the spec
    # https://www.microsoft.com/typography/otspec/os2.htm#wdc
    assert gthin.widthValue == 100
    assert greg.widthValue == 100
    assert gbold.widthValue == 100
    assert gthinex.widthValue == 125
    assert gbolducond.widthValue == 50
