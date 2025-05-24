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


import os
import xml
import unittest

import pytest

from glyphsLib.glyphdata import (
    GSGlyphInfo,
    GSLTR,
    GSRTL,
    GSUppercase,
    GSMinor,
    GSLowercase,
    GSSmallcaps,
)

from glyphsLib.glyphdata import get_glyph


class GlyphDataTest(unittest.TestCase):

    def test_infoFromName(self) -> None:
        # all the test from Glyphsapp

        info: GSGlyphInfo = get_glyph("sad-ar.medi.liga")
        self.assertEqual(info.name, "sad-ar.medi.liga")
        self.assertIsNone(info.unicodes)

        info = get_glyph("x_ringcomb")
        self.assertEqual(info.name, "x_ringcomb")
        self.assertEqual(info.productionName, "uni0078030A")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)
        self.assertEqual(info.case, "lower")

        """
        # TODO: double lang tags
        info = get_glyph("a_voicedcomb-kana-hira")
        self.assertEqual(info.name, "a_voicedcomb-kana-hira")
        self.assertEqual(info.productionName, "uni30423099")

        info = get_glyph("a-hira_voicedcomb-kana")
        self.assertEqual(info.name, "a_voicedcomb-kana-hira")
        self.assertEqual(info.productionName, "uni30423099")
        """

        info = get_glyph("A")
        self.assertEqual(info.name, "A")
        self.assertEqual(info.productionName, "A")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "latin")
        self.assertEqual(info.direction, GSLTR)

        info = get_glyph("uni0041")
        self.assertEqual(info.name, "A")
        self.assertEqual(info.productionName, "A")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "latin")
        self.assertEqual(info.direction, GSLTR)

        info = get_glyph("uni0041.01")
        self.assertEqual(info.name, "A.01")
        self.assertEqual(info.productionName, "A.01")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "latin")
        self.assertEqual(info.direction, GSLTR)

        info = get_glyph("uni6B77.1")
        self.assertEqual(info.name, "uni6B77.1")
        self.assertEqual(info.productionName, "uni6B77.1")

        info = get_glyph("uni6B776B77")
        self.assertEqual(info.name, "uni6B776B77")
        self.assertEqual(info.productionName, "uni6B776B77")
        self.assertEqual(info.script, "han")
        self.assertEqual(info.category, "Letter")

        info = get_glyph("u2000B_uni6B77")
        self.assertEqual(info.name, "u2000B_uni6B77")
        self.assertEqual(info.productionName, "u2000B_uni6B77")

        """
        # TODO: implement parsing those names
        info = get_glyph("dvKTa")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")
        self.assertEqual(info.productionName, "uni0915094D0924")

        info = get_glyph("dvKTa.ss01")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")
        self.assertEqual(info.productionName, "uni0915094D0924.ss01")

        info = get_glyph("dvHNa")
        self.assertEqual(info.script, "devanagari")
        """

        info = get_glyph("k_ta-deva.ss01")
        self.assertEqual(info.name, "k_ta-deva.ss01")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")
        self.assertEqual(info.productionName, "uni0915094D0924.ss01")

        info = get_glyph("_brush.abc")
        self.assertEqual(info.category, "Corner")

        info = get_glyph("_segment.abc")
        self.assertEqual(info.category, "Corner")

        info = get_glyph("_corner.abc")
        self.assertEqual(info.category, "Corner")

        info = get_glyph("_cap.abc")
        self.assertEqual(info.category, "Corner")

        info = get_glyph(".notdef")
        self.assertEqual(info.name, ".notdef")
        self.assertEqual(info.category, "Separator")
        self.assertIsNone(info.subCategory)
        self.assertIsNone(info.unicodes)

        info = get_glyph(".null")
        self.assertEqual(info.name, ".null")
        self.assertEqual(info.category, "Separator")
        self.assertIsNone(info.unicodes)

        info = get_glyph("NULL")
        self.assertEqual(info.name, "NULL")
        self.assertEqual(info.category, "Separator")
        self.assertIsNone(info.unicodes)

        info = get_glyph("zerosuperior")
        self.assertEqual(info.name, "zerosuperior")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.unicodes, "2070")

        info = get_glyph("Asuperior")
        self.assertEqual(info.name, "Asuperior")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.productionName, "Asuperior")
        self.assertEqual(info.case, GSMinor)
        self.assertIsNone(info.unicodes)

        info = get_glyph("Ainferior")
        self.assertEqual(info.name, "Ainferior")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.productionName, "Ainferior")
        self.assertEqual(info.case, GSMinor)
        self.assertIsNone(info.unicodes)

        info = get_glyph("ia-cy")
        self.assertEqual(info.name, "ya-cy")
        self.assertEqual(info.category, "Letter")

        info = get_glyph("ii_ia-cy.fina")
        self.assertEqual(info.name, "ii_ya-cy.fina")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.productionName, "uni0438044F.fina")

        info = get_glyph("ia-cy.fina")
        self.assertEqual(info.productionName, "uni044F.fina")

        info = get_glyph("a_a-cy")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertEqual(info.productionName, "uni04300430")
        self.assertIsNone(info.unicodes)

        info = get_glyph("one-ar.osf.001")
        self.assertEqual(info.name, "one-ar.osf.001")

        info = get_glyph("one-ar.osf.ss01")
        self.assertEqual(info.name, "one-ar.osf.ss01")

        info = get_glyph("f_i.liga")
        self.assertEqual(info.name, "f_i.liga")
        self.assertEqual(info.productionName, "f_i.liga")

        info = get_glyph("f_i.rlig")
        self.assertEqual(info.name, "f_i.rlig")
        self.assertEqual(info.productionName, "f_i.rlig")

        info = get_glyph("f_i.ss01_")
        self.assertEqual(info.name, "f_i.ss01_")
        self.assertEqual(info.productionName, "f_i.ss01_")

        info = get_glyph("f_i._ss01")
        self.assertEqual(info.name, "f_i._ss01")
        self.assertEqual(info.productionName, "f_i._ss01")

        info = get_glyph("f_i.ss02_ss01")
        self.assertEqual(info.name, "f_i.ss02_ss01")
        self.assertEqual(info.productionName, "f_i.ss02_ss01")

        info = get_glyph("f_i.ss02_ss01.ss03")
        self.assertEqual(info.name, "f_i.ss02_ss01.ss03")
        self.assertEqual(info.productionName, "f_i.ss02_ss01.ss03")

        info = get_glyph("uni4E08uE0101-JP")
        # self.assertEqual(info.name, "uni4E08.uv018") # fails NULL
        # self.assertIsNone(info.unicodes) # fails NULL

        info = get_glyph("𬀩")
        self.assertEqual(info.name, "u2C029")
        self.assertEqual(info.script, "Hani")  # TODO: should be "han"

        info = get_glyph("o_f_f.fina")
        self.assertEqual(info.name, "o_f_f.fina")
        self.assertEqual(info.productionName, "o_f_f.fina")

        """
        TODO: To preserve the "agl" name before the first period,
        we have a matching suffix ligature
        info = get_glyph("f.ss01_j.ss02")
        self.assertEqual(info.name, "f_j.ss01_ss02")
        self.assertEqual(info.productionName, "f_j.ss01_ss02")
        """

        info = get_glyph("two")
        self.assertEqual(info.name, "two")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.unicodes, "0032")

        info = get_glyph("one_two")
        self.assertEqual(info.name, "one_two")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("two.001")
        self.assertEqual(info.name, "two.001")
        self.assertEqual(info.category, "Number")
        self.assertIsNone(info.unicodes)

        info = get_glyph("two.lf")

        info = get_glyph("two.lf.001")

        info = get_glyph("uni3513")

        info = get_glyph("u2A1DE")

        info = get_glyph("u2000B")

        info = get_glyph("u2000B.uv018")

        info = get_glyph("beh-ar.fina.ss01")
        self.assertEqual(info.script, "arabic")

        info = get_glyph("e-cy.ss08")
        self.assertEqual(info.script, "cyrillic")

        info = get_glyph("lo-khmer.below")
        self.assertEqual(info.name, "lo-khmer.below")
        self.assertEqual(info.script, "khmer")
        self.assertEqual(info.productionName, "uni17D2179B")

        """
        TODO:
        info = get_glyph("lo_uaMark-khmer.below_")
        self.assertEqual(info.name, "lo_uaMark-khmer.below_")
        self.assertEqual(info.script, "khmer")
        """

        """
        TODO: this is similar to the "f_j.ss01_ss02". The "below" belongs
        to the "lo-khmer". And "lo-khmer.below" is in glyphData.
        self.assertEqual(info.productionName, "uni17D2179B17BD")
        """

        info = get_glyph("_loop-lao")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "_loop-lao")
        self.assertEqual(info.script, "lao")

        info = get_glyph("unicode")
        self.assertIsNone(info.category)  # is a fallback info object

        info = get_glyph("uniABCG")
        self.assertIsNone(info.category)  # is a fallback info object

        info = get_glyph("uni0CCD0CB0")
        self.assertEqual(info.name, "ra-kannada.below")
        self.assertEqual(info.productionName, "uni0CCD0CB0")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing Combining")

        info = get_glyph("uni0CCD0C95")
        self.assertEqual(info.name, "ka-kannada.below")
        self.assertEqual(info.productionName, "uni0CCD0C95")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing")

        info = get_glyph("ddhi-kannada")
        self.assertEqual(info.productionName, "uni0CA20CBF")

        info = get_glyph("k-kannada")

        info = get_glyph("kha_rakar-deva")
        self.assertEqual(info.subCategory, "Composition")
        self.assertEqual(info.productionName, "uni0916094D0930")

        info = get_glyph("k_ssi-kannada")
        self.assertEqual(info.productionName, "uni0C950CCD0CB70CBF")

        info = get_glyph("d_dh_r_ya-deva")
        self.assertEqual(info.name, "d_dh_rakar_ya-deva")
        self.assertEqual(info.subCategory, "Conjunct")
        self.assertEqual(info.productionName, "uni0926094D0927094D0930094D092F")

        info = get_glyph("uni0926094D0927094D0930094D092F")
        self.assertEqual(info.name, "d_dh_rakar_ya-deva")
        self.assertEqual(info.subCategory, "Conjunct")
        self.assertEqual(info.productionName, "uni0926094D0927094D0930094D092F")

        info = get_glyph("germandbls.sc")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("one.sinf")
        self.assertEqual(info.case, GSMinor)

        info = get_glyph("one.subs")
        self.assertEqual(info.case, GSMinor)

        info = get_glyph("one.foo")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")

        info = get_glyph("one_two.foo")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("a_idotaccent_a")
        self.assertEqual(info.productionName, "a_i_a.loclTRK")

        info = get_glyph("f_idotaccent")
        self.assertEqual(info.productionName, "f_i.loclTRK")

        info = get_glyph("acutecomb.sc")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("acutecomb.smcp")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("acutecomb.c2sc")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("brevecomb")
        self.assertEqual(info.case, GSLowercase)
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.unicodes, "0306")
        self.assertEqual(info.productionName, "uni0306")

        info = get_glyph("brevecomb.case")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.productionName, "uni0306.case")
        self.assertIsNone(info.unicodes)

        info = get_glyph("dieresiscomb_acutecomb.case")
        self.assertIsNone(info.unicodes)
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("wigglylinebelowcomb.alt")
        self.assertIsNone(info.unicodes)
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("brevecomb_acutecomb")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.productionName, "uni03060301")
        self.assertIsNone(info.unicodes)

        info = get_glyph("brevecomb_acutecomb.case")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.productionName, "uni03060301.case")
        self.assertIsNone(info.unicodes)

        info = get_glyph("brevecomb_a_a_a")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.productionName, "uni0306006100610061")

        info = get_glyph("brevecomb_a_a_a.case")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.productionName, "uni0306006100610061.case")

        info = get_glyph("brevecomb_aaa.case")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.productionName, "uni0306_aaa.case")

        info = get_glyph("a_parallel.circled")
        self.assertEqual(info.name, "a_parallel.circled")
        self.assertEqual(info.productionName, "uni00612225.circled")

        info = get_glyph("a_parallel._circled")
        self.assertEqual(info.name, "a_parallel._circled")
        self.assertEqual(info.productionName, "uni006129B7")

        info = get_glyph("uni51CB.jp78")
        self.assertEqual(info.name, "uni51CB.jp78")
        # self.assertEqual(info.productionName, "uni51CB.jp78") # fails
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.script, "han")

        info = get_glyph("h.sc")
        self.assertEqual(info.case, GSSmallcaps)
        self.assertIsNone(info.subCategory)

        info = get_glyph("i.sc")
        self.assertEqual(info.productionName, "i.sc")
        self.assertEqual(info.case, GSSmallcaps)
        self.assertIsNone(info.subCategory)

        info = get_glyph("jcaron.sc")
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("one_one")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("extraLowLeftStemToneBarmod")
        self.assertEqual(info.category, "Symbol")
        self.assertEqual(info.subCategory, "Modifier")
        self.assertEqual(info.productionName, "uniA716")

        name = (
            "extraLowLeftStemToneBarmod_"
            "extraLowLeftStemToneBarmod_"
            "lowLeftStemToneBarmod"
        )
        info = get_glyph(name)
        self.assertEqual(info.category, "Symbol")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertEqual(info.productionName, "uniA716A716A715")

        info = get_glyph("three")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")

        info = get_glyph("three.tosf")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")

        info = get_glyph("three.tosf.ss13")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")

        info = get_glyph("a.subs")
        self.assertEqual(info.case, GSMinor)

        info = get_glyph("t_rakar-deva")
        self.assertEqual(info.productionName, "uni0924094D0930094D")

        info = get_glyph("ta_rakar-deva")
        self.assertEqual(info.productionName, "uni0924094D0930")

        info = get_glyph("t_reph-deva")
        self.assertEqual(info.script, "devanagari")

        info = get_glyph("A_acutecomb-cy")
        self.assertEqual(info.name, "A_acutecomb-cy")
        self.assertEqual(info.productionName, "uni04100301")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "cyrillic")

        info = get_glyph("Ie_acutecomb-cy")
        self.assertEqual(info.name, "Ie_acutecomb-cy")
        self.assertEqual(info.productionName, "uni04150301")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "cyrillic")

        info = get_glyph("i.head.sc")
        self.assertEqual(info.name, "i.head.sc")
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("ma-kannada.base")
        self.assertEqual(info.name, "ma-kannada.base")
        self.assertEqual(info.productionName, "uni0CAE.base")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)

        info = get_glyph("ka-kannada.below")
        self.assertEqual(info.productionName, "uni0CCD0C95")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing")

        info = get_glyph("ka_ssa-kannada.below")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing")
        self.assertEqual(info.productionName, "uni0C950CB7.below")  # uni0CCD0C950CCD0CB7

        info = get_glyph("ka_ssa-kannada.below_below")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing")
        self.assertEqual(info.productionName, "uni0CCD0C950CCD0CB7")  # uni0CCD0C950CCD0CB7

        info = get_glyph("i.latn_TRK.pcap")
        self.assertEqual(info.name, "i.latn_TRK.pcap")

        info = get_glyph("yehVinverted-farsi.medi")
        self.assertEqual(info.productionName, "uni063D.medi")

        info = get_glyph("less_d_u_a_l_s_h_o_c_k_three_d_greater.liga")
        self.assertEqual(info.productionName, "less_d_u_a_l_s_h_o_c_k_three_d_greater.liga")

        info = get_glyph("Alphaprosgegrammeni")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "greek")

        info = get_glyph("Yr.sc")
        self.assertEqual(info.case, GSSmallcaps)
        self.assertEqual(info.script, "latin")

        info = get_glyph("a_a_b")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("horizontalbar_horizontalbar")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("a_kang-lepcha")
        self.assertEqual(info.subCategory, "Composition")
        info = get_glyph("a_iVowel-lepcha")
        self.assertEqual(info.subCategory, "Composition")

        info = get_glyph("six.blackCircled")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.productionName, "uni277B")

        info = get_glyph("five_zero.blackCircled")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Ligature")
        """
        TODO:
        self.assertEqual(info.productionName, "uni277A24FF")
        """

        info = get_glyph("five_zero.blackCircled_blackCircled")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Ligature")
        """
        TODO:
        self.assertEqual(info.productionName, "uni277A24FF")
        """

        info = get_glyph("two_zero.blackCircled")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")
        self.assertEqual(info.productionName, "uni24F4")

        info = get_glyph("ka_ra-deva")
        self.assertEqual(info.name, "ka_ra-deva")
        self.assertEqual(info.productionName, "uni09150930")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("ka_r-deva")
        self.assertEqual(info.name, "ka_rakar-deva")
        self.assertEqual(info.productionName, "uni0915094D0930")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Composition")

        info = get_glyph("k_ra-deva")  # does this even make sense?
        # self.assertEqual(info.name, "ka_rakar-deva")
        # self.assertEqual(info.productionName, "uni0915094D0930")
        # self.assertEqual(info.category, "Letter")
        # self.assertEqual(info.subCategory, "Composition")

        info = get_glyph("kh_na-deva")
        self.assertEqual(info.name, "kh_na-deva")
        self.assertEqual(info.productionName, "uni0916094D0928")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")

        info = get_glyph("nukta_rakar-deva")
        self.assertEqual(info.name, "nukta_rakar-deva")
        self.assertEqual(info.productionName, "uni093C094D0930")

        info = get_glyph("rakar-deva")
        self.assertEqual(info.name, "rakar-deva")
        self.assertEqual(info.productionName, "uni094D0930")

        info = get_glyph("k_rakar-deva")
        self.assertEqual(info.name, "k_rakar-deva")
        self.assertEqual(info.productionName, "uni0915094D0930094D")

        info = get_glyph("uni0915094D0930094D")
        self.assertEqual(info.name, "k_rakar-deva")
        self.assertEqual(info.productionName, "uni0915094D0930094D")

        info = get_glyph("uni0915094D")
        self.assertEqual(info.name, "k-deva")

        info = get_glyph("uni0915094D0930")
        self.assertEqual(info.name, "ka_rakar-deva")
        self.assertEqual(info.productionName, "uni0915094D0930")

        info = get_glyph("h_na-deva")
        self.assertEqual(info.productionName, "uni0939094D0928")
        self.assertEqual(info.script, "devanagari")

        info = get_glyph("reph-deva.imatra")
        self.assertEqual(info.productionName, "uni0930094D.imatra")

        info = get_glyph("iMatra-deva.01")

        info = get_glyph("iMatra-gujarati.01")

        info = get_glyph("iiMatra_reph-deva")
        self.assertEqual(info.productionName, "uni09400930094D")

        info = get_glyph("k_ss-deva")
        self.assertEqual(info.subCategory, "Conjunct")

        info = get_glyph("eMatra_reph_anusvara-deva")
        self.assertEqual(info.productionName, "uni09470930094D0902")

        info = get_glyph("dd_dda-myanmar")
        self.assertEqual(info.name, "dd_dda-myanmar")
        self.assertEqual(info.productionName, "uni100D1039100D")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")

        info = get_glyph("u1F1A.d")
        self.assertEqual(info.name, "u1F1A.d")  # !!Epsilonpsilivaria.d

        info = get_glyph("acute_circumflex")
        self.assertEqual(info.name, "acute_circumflex")
        self.assertEqual(info.category, "Mark")

        info = get_glyph("d.sc.ss01")
        self.assertEqual(info.name, "d.sc.ss01")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("d.c2sc.ss01")
        self.assertEqual(info.name, "d.c2sc.ss01")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.case, GSSmallcaps)

        # Arabic

        info = get_glyph("reh_lam-ar.fina")
        self.assertEqual(info.name, "reh_lam-ar.fina")
        self.assertEqual(info.productionName, "uni06310644.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("reh_lamVabove-ar.fina")
        self.assertEqual(info.productionName, "uni063106B5.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("kaf_lamVabove-ar.fina")
        self.assertEqual(info.productionName, "uni064306B5.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("lamVabove-ar.medi")
        self.assertEqual(info.productionName, "uni06B5.medi")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("kaf_lamVabove-ar.medi")
        self.assertEqual(info.productionName, "uni064306B5.medi")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("lam_yehHamzaabove_meem-ar")
        self.assertEqual(info.productionName, "uni064406260645")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("yehFarsi_noonghunna-ar.fina.rlig")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("beh-ar.fina.ss01")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("ain_ain-ar.fina")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.productionName, "uni06390639.fina")
        self.assertEqual(info.name, "ain_ain-ar.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("ain_ain-ar.fina.ss01")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.productionName, "uni06390639.fina.ss01")
        self.assertEqual(info.name, "ain_ain-ar.fina.ss01")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("uniFECCFECA")
        self.assertEqual(info.name, "ain_ain-ar.fina")  # ain_ain-ar.fina
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.productionName, "uni06390639.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("jeh_ain-ar.fina")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.productionName, "uni06980639.fina")
        self.assertEqual(info.name, "jeh_ain-ar.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("lam_alef-ar.short")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertEqual(info.direction, GSRTL)

        """
        TODO:
        info = get_glyph("kaf_yeh-farsi.fina")
        self.assertEqual(info.name, "kaf_yeh-farsi.fina") # kaf_yehFarsi-ar.fina
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.productionName, "uni064306CC.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("kaf_yeh-farsi.fina.ss01")
        self.assertEqual(info.name, "kaf_yehFarsi-ar.fina.ss01")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.productionName, "uni064306CC.fina.ss01")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("ain-ar.medi_zah-ar.medi_alef-ar.medi_noonghunna-ar.fina")
         # ain_zah_alef_noonghunna-ar.fina
        self.assertEqual(info.name,
           "ain-ar.medi_zah-ar.medi_alef-ar.medi_noonghunna-ar.fina")
        self.assertEqual(info.productionName, "uni06390638062706BA.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("ain-ar.medi_zah-ar.medi_alef-ar.medi_noonghunna-ar.medi")
        self.assertEqual(info.name, "ain_zah_alef_noonghunna-ar.medi")
        self.assertEqual(info.productionName, "uni06390638062706BA.medi")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("ain-ar.init_zah-ar.medi_alef-ar.medi_noonghunna-ar.fina")
        self.assertEqual(info.name, "ain_zah_alef_noonghunna-ar")
        self.assertEqual(info.productionName, "uni06390638062706BA")

        info = get_glyph("lam-ar.init_alef-ar.fina")
        self.assertEqual(info.name, "lam_alef-ar")
        self.assertEqual(info.productionName, "uni06440627")
        """

        info = get_glyph("ain_zah_alefMaksura_noonghunna-ar")
        self.assertEqual(info.name, "ain_zah_alefMaksura_noonghunna-ar")
        self.assertEqual(info.productionName, "uni06390638064906BA")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("ain_zah_alefMaksura_noonghunna-ar.fina")
        self.assertEqual(info.name, "ain_zah_alefMaksura_noonghunna-ar.fina")
        self.assertEqual(info.productionName, "uni06390638064906BA.fina")
        self.assertEqual(info.direction, GSRTL)

        info = get_glyph("lam_alef-ar.fina")
        self.assertEqual(info.name, "lam_alef-ar.fina")
        self.assertEqual(info.productionName, "uni06440627.fina")

        info = get_glyph("beh-ar.fina")

        info = get_glyph("meemDotabove-ar.fina")

        info = get_glyph("lam_alef-ar")
        info = get_glyph("lam_alef-ar.fina")
        info = get_glyph("lam_alefWasla-ar")

        info = get_glyph("uniFEFB.fina")
        self.assertEqual(info.name, "lam_alef-ar.fina")
        self.assertEqual(info.productionName, "uni06440627.fina")

        info = get_glyph("tehMarbutagoal-ar.fina")
        self.assertEqual(info.name, "tehMarbutagoal-ar.fina")
        self.assertEqual(info.category, "Letter")

        info = get_glyph("meem_meem_meem-ar.fina.connMeemSecond")
        self.assertEqual(info.name, "meem_meem_meem-ar.fina.connMeemSecond")
        self.assertEqual(info.productionName, "uni064506450645.fina.connMeemSecond")

        info = get_glyph("meem-ar.fina.conn_meem_second")
        self.assertEqual(info.productionName, "uni0645.fina.conn_meem_second")

        info = get_glyph("meem-ar.medi.conn_meem_second")
        self.assertEqual(info.productionName, "uni0645.medi.conn_meem_second")

        info = get_glyph("one-ar")
        self.assertEqual(info.name, "one-ar")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.productionName, "uni0661")
        self.assertEqual(info.direction, GSLTR)

        info = get_glyph("dottedCircle_consonantk-lepcha")
        self.assertEqual(info.name, "dottedCircle_consonantk-lepcha")
        self.assertEqual(info.productionName, "uni25CC_consonantklepcha")

        info = get_glyph("dottedCircle_k-lepcha")
        self.assertEqual(info.name, "dottedCircle_k-lepcha")
        self.assertEqual(info.productionName, "uni25CC1C2D")

        info = get_glyph("uni25CC_ran-lepcha")
        self.assertEqual(info.name, "dottedCircle_ran-lepcha")
        self.assertEqual(info.productionName, "uni25CC1C36")

        info = get_glyph("uni25CC_ran-lepcha.ss01")
        self.assertEqual(info.name, "dottedCircle_ran-lepcha.ss01")
        self.assertEqual(info.productionName, "uni25CC1C36.ss01")

        info = get_glyph("Atilde")
        self.assertEqual(info.name, "Atilde")
        self.assertEqual(info.productionName, "Atilde")

        info = get_glyph("uni00C3")
        self.assertEqual(info.name, "Atilde")
        self.assertEqual(info.productionName, "Atilde")

        info = get_glyph("uni00C3.ss01")
        self.assertEqual(info.name, "Atilde.ss01")

        info = get_glyph("uni00C300C3.ss01")
        self.assertEqual(info.name, "Atilde_Atilde.ss01")
        self.assertEqual(info.productionName, "Atilde_Atilde.ss01")

        info = get_glyph("t.initlo_t")
        self.assertEqual(info.name, "t.initlo_t")  # t_t.initlo_

        info = get_glyph("f_f_i")
        self.assertEqual(info.productionName, "f_f_i")

        info = get_glyph("f_h")
        self.assertEqual(info.productionName, "f_h")

        info = get_glyph("o_o.ss01")

        info = get_glyph("iMatra_reph-deva.12")
        self.assertEqual(info.subCategory, "Composition")  # Matra
        self.assertEqual(info.productionName, "uni093F0930094D.12")

        info = get_glyph("iMatra_reph-deva")
        self.assertEqual(info.subCategory, "Composition")  # Matra
        self.assertEqual(info.productionName, "uni093F0930094D")

        info = get_glyph("t_e_s_t.alt")
        self.assertEqual(info.subCategory, "Ligature")

        # old 'production' tests

        info = get_glyph(".notdef")
        self.assertIsNone(info.unicodes)
        self.assertEqual(info.productionName, ".notdef")

        info = get_glyph("eacute")
        self.assertEqual(info.productionName, "eacute")
        self.assertEqual(info.unicodes, "00E9")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)

        info = get_glyph("Abreveacute")
        self.assertEqual(info.productionName, "uni1EAE")
        self.assertEqual(info.unicodes, "1EAE")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)

        info = get_glyph("C-fraktur")
        self.assertEqual(info.productionName, "uni212D")
        self.assertEqual(info.unicodes, "212D")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, None)

        info = get_glyph("fi")
        self.assertEqual(info.productionName, "fi")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertEqual(info.unicodes, "FB01")

        info = get_glyph("fi.alt")
        self.assertEqual(info.productionName, "fi.alt")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertIsNone(info.unicodes)

        info = get_glyph("s_t")
        self.assertEqual(info.productionName, "s_t")
        self.assertIsNone(info.unicodes)

        info = get_glyph("Gcommaaccent")
        self.assertEqual(info.productionName, "uni0122")
        self.assertEqual(info.unicodes, "0122")

        # G2: uniFD13, G3: uni06390649.fina
        info = get_glyph("ain_alefMaksura-ar.fina")
        self.assertEqual(info.productionName, "uni06390649.fina")

        info = get_glyph("Dboldscript-math")
        self.assertEqual(info.productionName, "u1D4D3")
        self.assertEqual(info.unicodes, "1D4D3")

        info = get_glyph("a_Dboldscript-math")
        self.assertEqual(info.name, "a_Dboldscript-math")
        self.assertEqual(info.productionName, "a_u1D4D3")

        info = get_glyph("brevecomb_Dboldscript-math")
        self.assertEqual(info.productionName, "uni0306_u1D4D3")

        # brevecomb_Dboldscript-math.f.r
        info = get_glyph("brevecomb_Dboldscript-math.f.r")
        self.assertEqual(
            info.productionName, "uni0306_u1D4D3.f.r"
        )  # G3: uni0306_u1D4D3.f.r

        info = get_glyph("Dboldscript-math_Dboldscript-math")
        self.assertEqual(info.productionName, "u1D4D3_u1D4D3")

        info = get_glyph("Dboldscript-math_Dboldscript-math.f")
        self.assertEqual(info.productionName, "u1D4D3_u1D4D3.f")

        info = get_glyph("Dboldscript-math_a")
        self.assertEqual(info.productionName, "u1D4D3_a")

        # a_Dboldscript-math
        info = get_glyph("a_Dboldscript-math")
        self.assertEqual(info.productionName, "a_u1D4D3")

        # Dboldscript-math_a_aa
        info = get_glyph("Dboldscript-math_a_aa")
        self.assertEqual(info.productionName, "u1D4D3_a_uniA733")

        info = get_glyph("Dboldscript-math_a_aaa")
        self.assertEqual(
            info.productionName, "u1D4D3_a_aaa"
        )  # Dboldscriptmath_a_aaa G3: u1D4D3_a_aaa

        # brevecomb_Dboldscript-math
        info = get_glyph("brevecomb_Dboldscript-math")
        self.assertEqual(info.productionName, "uni0306_u1D4D3")

        # Dboldscript-math_brevecomb
        info = get_glyph("Dboldscript-math_brevecomb")
        self.assertEqual(info.productionName, "u1D4D3_uni0306")

        info = get_glyph("idotaccent")
        self.assertEqual(info.productionName, "i.loclTRK")

        info = get_glyph("a_idotaccent")
        self.assertEqual(info.productionName, "a_i.loclTRK")

        # a_i.loclTRK_a
        info = get_glyph("a_idotaccent_a")
        self.assertEqual(
            info.productionName, "a_i_a.loclTRK"
        )  # a_idotaccent_a G3: a_i_a.loclTRK

        info = get_glyph("a_a_acutecomb")
        self.assertEqual(info.productionName, "a_a_acutecomb")

        info = get_glyph("a_a_dieresiscomb")
        self.assertEqual(info.productionName, "uni006100610308")

        info = get_glyph("vaphalaa-malayalam")
        self.assertEqual(info.productionName, "uni0D030D35.1")

        info = get_glyph("onethird")
        self.assertEqual(info.productionName, "uni2153")

        info = get_glyph("Jacute")
        self.assertEqual(info.productionName, "uni004A0301")

    def test_infoFromChar(self):

        info = get_glyph("ä")
        self.assertEqual(info.name, "adieresis")
        self.assertEqual(info.productionName, "adieresis")

        info = get_glyph("歷")
        self.assertEqual(info.name, "uni6B77")
        self.assertEqual(info.productionName, "uni6B77")

        info = get_glyph("歷.1")
        self.assertEqual(info.name, "uni6B77.1")
        self.assertEqual(info.productionName, "uni6B77.1")

    def test_category(self):
        info = get_glyph("uni000D")
        self.assertEqual(info.name, "CR")
        self.assertEqual(info.productionName, "CR")
        self.assertEqual(info.category, "Separator")
        self.assertIsNone(info.subCategory)

        info = get_glyph("boxHeavyUp")
        self.assertEqual(info.category, "Symbol")
        self.assertEqual(info.subCategory, "Geometry")

        info = get_glyph("hib-ko")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Syllable")

        info = get_glyph("o_f_f_i")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("o_f_f_i.foo")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertIsNone(info.unicodes)
        self.assertEqual(info.productionName, "o_f_f_i.foo")

        info = get_glyph("ain_alefMaksura-ar.fina")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("brevecomb.case")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("brevecomb_acutecomb")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("caroncomb_dotaccentcomb")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("dieresiscomb_caroncomb")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("dieresiscomb_macroncomb")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("dotaccentcomb_macroncomb")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("macroncomb_dieresiscomb")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("dotaccentcomb_o")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("macronlowmod_O")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Modifier")

        info = get_glyph("O_o")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("O_dotaccentcomb_o")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("O_dotaccentcomb")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)

        info = get_glyph("O_period")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("O_nbspace")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)

        info = get_glyph("_a")
        self.assertEqual(info.category, None)
        self.assertIsNone(info.subCategory)

        info = get_glyph("_aaa")
        self.assertEqual(info.category, None)
        self.assertIsNone(info.subCategory)

        info = get_glyph("dal_alef-ar")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("dal_lam-ar.dlig")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

    def test_category_buy_unicode(self):
        # "SignU.bn" is a non-standard name not defined in GlyphData.xml
        info = get_glyph("SignU.bn", unicodes=["09C1"])
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Nonspacing")

    def test_bug232(self):
        # https://github.com/googlefonts/glyphsLib/issues/232
        u = get_glyph("uni07F0")
        g = get_glyph("longlowtonecomb-nko")
        self.assertEqual((u.category, g.category), ("Mark", "Mark"))
        self.assertEqual((u.category, g.category), ("Mark", "Mark"))
        self.assertEqual((u.subCategory, g.subCategory), ("Nonspacing", "Nonspacing"))
        self.assertEqual((u.productionName, g.productionName), ("uni07F0", "uni07F0"))
        self.assertEqual((u.unicodes, g.unicodes), ("07F0", "07F0"))

    def test_glyphdata_no_duplicates(self):
        import glyphsLib

        names = set()
        alt_names = set()
        production_names = set()

        xml_files = [
            os.path.join(os.path.dirname(glyphsLib.__file__), "data", "GlyphData.xml"),
            os.path.join(
                os.path.dirname(glyphsLib.__file__), "data", "GlyphData_Ideographs.xml"
            ),
        ]

        for glyphdata_file in xml_files:
            glyph_data = xml.etree.ElementTree.parse(glyphdata_file).getroot()
            for glyph in glyph_data:
                glyph_name = glyph.attrib["name"]
                glyph_name_alternatives = glyph.attrib.get("altNames")
                glyph_name_production = glyph.attrib.get("production")

                assert glyph_name not in names
                names.add(glyph_name)
                if glyph_name_alternatives:
                    alternatives = glyph_name_alternatives.replace(" ", "").split(",")
                    for glyph_name_alternative in alternatives:
                        assert glyph_name_alternative not in alt_names
                        alt_names.add(glyph_name_alternative)
                if glyph_name_production:
                    assert glyph_name_production not in production_names
                    production_names.add(glyph_name_production)


# Testing more production names separately because parameterizing is easier.
PRODUCTION_NAMES = {
    # Our behavior differs from Glyphs, Glyphs 2.5.2 responses are in comments.
    ".notdef": ".notdef",
    "eacute": "eacute",
    "Abreveacute": "uni1EAE",
    "C-fraktur": "uni212D",
    "Dboldscript-math": "u1D4D3",
    "fi": "fi",
    "s_t": "s_t",
    "Gcommaaccent": "uni0122",
    "o_f_f_i.foo": "o_f_f_i.foo",
    "ain_alefMaksura-ar.fina": "uni06390649.fina",
    "brevecomb": "uni0306",
    "brevecomb.case": "uni0306.case",
    "brevecomb_acutecomb": "uni03060301",
    "brevecomb_acutecomb.case": "uni03060301.case",
    "brevecomb_a_a_a": "uni0306006100610061",
    "brevecomb_a_a_a.case": "uni0306006100610061.case",
    "brevecomb_aaa.case": "brevecomb_aaa.case",

    # brevecomb_Dboldscript-math
    "brevecomb_Dboldscript-math": "uni0306_u1D4D3",

    # brevecomb_Dboldscript-math.f.r
    "brevecomb_Dboldscript-math.f.r": "uni0306_u1D4D3.f.r",

    "Dboldscript-math_Dboldscript-math": "u1D4D3_u1D4D3",
    "Dboldscript-math_Dboldscript-math.f": "u1D4D3_u1D4D3.f",
    "Dboldscript-math_a": "u1D4D3_a",

    # a_Dboldscript-math
    "a_Dboldscript-math": "a_u1D4D3",

    # Dboldscript-math_a_aa
    "Dboldscript-math_a_aa": "u1D4D3_a_uniA733",

    "Dboldscript-math_a_aaa": "Dboldscriptmath_a_aaa",

    # brevecomb_Dboldscript-math
    "brevecomb_Dboldscript-math": "uni0306_u1D4D3",

    # Dboldscript-math_brevecomb
    "Dboldscript-math_brevecomb": "u1D4D3_uni0306",

    "idotaccent": "i.loclTRK",
    "a_idotaccent": "a_i.loclTRK",

    # a_i.loclTRK_a
    "a_idotaccent_a": "a_idotaccent_a",

    "a_a_acutecomb": "a_a_acutecomb",
    "a_a_dieresiscomb": "uni006100610308",
    "brevecomb_acutecomb": "uni03060301",
    "vaphalaa-malayalam": "uni0D030D35.1",
    "onethird": "uni2153",
    "Jacute": "uni004A0301",
    "Ech_Vew-arm.liga": "uni0535054E.liga",

    "Ech_Vew-arm.liga": "uni0535054E.liga",
    "Men_Ech-arm.liga": "uni05440535.liga",
    "Men_Ini-arm.liga": "uni0544053B.liga",
    "Men_Now-arm.liga": "uni05440546.liga",
    "Men_Xeh-arm.liga": "uni0544053D.liga",
    "Vew_Now-arm.liga": "uni054E0546.liga",
    "aiMatra_anusvara-deva": "uni09480902",
    "aiMatra_candraBindu-deva": "uni09480901",
    "aiMatra_reph-deva": "uni09480930094D",
    "aiMatra_reph_anusvara-deva": "uni09480930094D0902",
    "ca_iMatra-tamil": "uni0B9A0BBF",
    "ca_uMatra-tamil": "uni0B9A0BC1",
    "ca_uuMatra-tamil": "uni0B9A0BC2",
    "ch_ya-deva": "uni091B094D092F",
    "d_ba-deva": "uni0926094D092C",
    "d_bha-deva": "uni0926094D092D",
    "d_da-deva": "uni0926094D0926",
    "d_dh_ya-deva": "uni0926094D0927094D092F",
    "d_dha-deva": "uni0926094D0927",
    "d_ga-deva": "uni0926094D0917",
    "d_gha-deva": "uni0926094D0918",
    "d_ma-deva": "uni0926094D092E",
    "d_ra-deva": "uni0926094D0930",
    "d_va-deva": "uni0926094D0935",
    "d_ya-deva": "uni0926094D092F",
    "da-khmer.below.ro": "uni17D2178A.ro",
    "da_rVocalicMatra-deva": "uni09260943",
    "da_uMatra-deva": "uni09260941",
    "da_uuMatra-deva": "uni09260942",
    "dd_dda-deva": "uni0921094D0921",
    "dd_ddha-deva": "uni0921094D0922",
    "dd_ya-deva": "uni0921094D092F",
    "ddh_ddha-deva": "uni0922094D0922",
    "ddh_ya-deva": "uni0922094D092F",
    "eCandraMatra_anusvara-deva": "uni09450902",
    "eCandraMatra_reph-deva": "uni09450930094D",
    "eMatra_anusvara-deva": "uni09470902",
    "eMatra_candraBindu-deva": "uni09470901",
    "eMatra_reph-deva": "uni09470930094D",
    "eMatra_reph_anusvara-deva": "uni09470930094D0902",
    "eShortMatra_anusvara-deva": "uni09460902",
    "eShortMatra_candraBindu-deva": "uni09460901",
    "eShortMatra_reph-deva": "uni09460930094D",
    "eShortMatra_reph_anusvara-deva": "uni09460930094D0902",
    "ech_vew-arm.liga.sc": "uni0565057E.liga.sc",
    "finalkaf_qamats-hb": "uni05DA05B8",
    "finalkaf_sheva-hb": "uni05DA05B0",
    "finalkafdagesh_qamats-hb": "uniFB3A05B8",
    "finalkafdagesh_sheva-hb": "uniFB3A05B0",
    "h_la-deva": "uni0939094D0932",
    "h_ma-deva": "uni0939094D092E",
    "h_na-deva": "uni0939094D0928",
    "h_nna-deva": "uni0939094D0923",
    "h_ra-deva": "uni0939094D0930",
    "h_ra_uMatra-deva": "uni0939094D09300941",
    "h_ra_uuMatra-deva": "uni0939094D09300942",
    "h_va-deva": "uni0939094D0935",
    "h_ya-deva": "uni0939094D092F",
    "ha_iMatra-tamil": "uni0BB90BBF",
    "ha_iiMatra-tamil": "uni0BB90BC0",
    "ha_rVocalicMatra-deva": "uni09390943",
    "ha_rrVocalicMatra-deva": "uni09390944",
    "ha_uMatra-deva": "uni09390941",
    "ha_uMatra-tamil": "uni0BB90BC1",
    "ha_uuMatra-deva": "uni09390942",
    "ha_uuMatra-tamil": "uni0BB90BC2",
    "hatafpatah_siluqleft-hb": "uni05B205BD",
    "hatafqamats_siluqleft-hb": "uni05B305BD",
    "hatafsegol_siluqleft-hb": "uni05B105BD",
    "iMark_toandakhiat-khmer": "uni17B717CD",
    "iMark_toandakhiat-khmer.narrow": "uni17B717CD.narrow",
    "idotaccent.sc": "i.loclTRK.sc",  # i.sc.loclTRK
    "iiMatra_reph-deva": "uni09400930094D",
    "iiMatra_reph-deva.alt2": "uni09400930094D.alt2",
    "iiMatra_reph_anusvara-deva": "uni09400930094D0902",
    "iiMatra_reph_anusvara-deva.alt2": "uni09400930094D0902.alt2",
    "j_ny-deva": "uni091C094D091E094D",
    "j_ny-deva.alt2": "uni091C094D091E094D.alt2",
    "j_ny-deva.alt3": "uni091C094D091E094D.alt3",
    "j_ny-deva.alt4": "uni091C094D091E094D.alt4",
    "j_ny-deva.alt5": "uni091C094D091E094D.alt5",
    "j_ny-deva.alt6": "uni091C094D091E094D.alt6",
    "j_ny-deva.alt7": "uni091C094D091E094D.alt7",
    "j_ny-deva.alt8": "uni091C094D091E094D.alt8",
    "j_nya-deva": "uni091C094D091E",
    "ja_iMatra-tamil": "uni0B9C0BBF",
    "ja_iiMatra-tamil": "uni0B9C0BC0",
    "k_ss-deva": "uni0915094D0937094D",
    "k_ss-deva.alt2": "uni0915094D0937094D.alt2",
    "k_ss-deva.alt3": "uni0915094D0937094D.alt3",
    "k_ss-deva.alt4": "uni0915094D0937094D.alt4",
    "k_ss-deva.alt5": "uni0915094D0937094D.alt5",
    "k_ss-deva.alt6": "uni0915094D0937094D.alt6",
    "k_ss-deva.alt7": "uni0915094D0937094D.alt7",
    "k_ssa-deva": "uni0915094D0937",
    "k_ssa-tamil": "uni0B950BCD0BB7",
    "k_ssa_iMatra-tamil": "uni0B950BCD0BB70BBF",
    "k_ssa_iiMatra-tamil": "uni0B950BCD0BB70BC0",
    "k_ssa_uMatra-tamil": "uni0B950BCD0BB70BC1",
    "k_ssa_uuMatra-tamil": "uni0B950BCD0BB70BC2",
    "ka_iMatra-tamil": "uni0B950BBF",
    "ka_uMatra-tamil": "uni0B950BC1",
    "ka_uuMatra-tamil": "uni0B950BC2",
    "la_iMatra-tamil": "uni0BB20BBF",
    "la_iiMatra-tamil": "uni0BB20BC0",
    "la_uMatra-tamil": "uni0BB20BC1",
    "la_uuMatra-tamil": "uni0BB20BC2",
    "lamed_dagesh_holam-hb": "uni05DC05BC05B9",
    "lamed_holam-hb": "uni05DC05B9",
    "lla_uMatra-tamil": "uni0BB30BC1",
    "lla_uuMatra-tamil": "uni0BB30BC2",
    "llla_iMatra-tamil": "uni0BB40BBF",
    "llla_iiMatra-tamil": "uni0BB40BC0",
    "llla_uMatra-tamil": "uni0BB40BC1",
    "llla_uuMatra-tamil": "uni0BB40BC2",
    "ma_iMatra-tamil": "uni0BAE0BBF",
    "ma_iiMatra-tamil": "uni0BAE0BC0",
    "ma_uMatra-tamil": "uni0BAE0BC1",
    "ma_uuMatra-tamil": "uni0BAE0BC2",
    "mo-khmer.below.ro": "uni17D21798.ro",
    "moMa_underscore-thai": "uni0E21005F",  # uni0E21_uni005F
    "na_iMatra-tamil": "uni0BA80BBF",
    "na_uMatra-tamil": "uni0BA80BC1",
    "na_uuMatra-tamil": "uni0BA80BC2",
    "ng_ya-deva": "uni0919094D092F",
    "nga_uMatra-tamil": "uni0B990BC1",
    "nga_uuMatra-tamil": "uni0B990BC2",
    "ngoNgu_underscore-thai": "uni0E07005F",  # uni0E07_uni005F
    "niggahita_maiCatawa-lao": "uni0ECD0ECB",
    "niggahita_maiCatawa-lao.right": "uni0ECD0ECB.right",
    "niggahita_maiEk-lao": "uni0ECD0EC8",
    "niggahita_maiEk-lao.right": "uni0ECD0EC8.right",
    "niggahita_maiTho-lao": "uni0ECD0EC9",
    "niggahita_maiTho-lao.right": "uni0ECD0EC9.right",
    "niggahita_maiTi-lao": "uni0ECD0ECA",
    "niggahita_maiTi-lao.right": "uni0ECD0ECA.right",
    "nikhahit_maiChattawa-thai": "uni0E4D0E4B",
    "nikhahit_maiChattawa-thai.narrow": "uni0E4D0E4B.narrow",
    "nikhahit_maiEk-thai": "uni0E4D0E48",
    "nikhahit_maiEk-thai.narrow": "uni0E4D0E48.narrow",
    "nikhahit_maiTho-thai": "uni0E4D0E49",
    "nikhahit_maiTho-thai.narrow": "uni0E4D0E49.narrow",
    "nikhahit_maiTri-thai": "uni0E4D0E4A",
    "nikhahit_maiTri-thai.narrow": "uni0E4D0E4A.narrow",
    "nna_uMatra-tamil": "uni0BA30BC1",
    "nna_uuMatra-tamil": "uni0BA30BC2",
    "nnna_uMatra-tamil": "uni0BA90BC1",
    "nnna_uuMatra-tamil": "uni0BA90BC2",
    "nno-khmer.below.narrow1": "uni17D2178E.narrow1",
    "nno-khmer.below.narrow2": "uni17D2178E.narrow2",
    "noNu_underscore-thai": "uni0E19005F",  # uni0E19_uni005F
    "nya_iMatra-tamil": "uni0B9E0BBF",
    "nya_uMatra-tamil": "uni0B9E0BC1",
    "nya_uuMatra-tamil": "uni0B9E0BC2",
    "nyo-khmer.full.below.narrow": "uni17D21789.full.below.narrow",
    "p_ta-deva": "uni092A094D0924",
    "pa_uMatra-tamil": "uni0BAA0BC1",
    "pa_uuMatra-tamil": "uni0BAA0BC2",
    "pho-khmer.below.ro": "uni17D21797.ro",
    "po-khmer.below.ro": "uni17D21796.ro",
    "ra_uMatra-deva": "uni09300941",
    "ra_uMatra-tamil": "uni0BB00BC1",
    "ra_uuMatra-deva": "uni09300942",
    "ra_uuMatra-tamil": "uni0BB00BC2",
    "reph_anusvara-deva": "uni0930094D0902",
    "ro-khmer.pre.narrow": "uni17D2179A.narrow",
    "rra_iMatra-tamil": "uni0BB10BBF",
    "rra_iiMatra-tamil": "uni0BB10BC0",
    "rra_uMatra-tamil": "uni0BB10BC1",
    "rra_uuMatra-tamil": "uni0BB10BC2",
    "sa_iMatra-tamil": "uni0BB80BBF",
    "sa_iiMatra-tamil": "uni0BB80BC0",
    "sa_uMatra-tamil": "uni0BB80BC1",
    "sa_uuMatra-tamil": "uni0BB80BC2",
    "sh_r-deva": "uni0936094D094D0930",  # uni0936094D0930094D
    "sh_ra-deva": "uni0936094D0930",
    "sh_ra_iiMatra-tamil": "uni0BB60BCD0BB00BC0",
    "ss_tta-deva": "uni0937094D091F",
    "ss_ttha-deva": "uni0937094D0920",
    "ssa_iMatra-tamil": "uni0BB70BBF",
    "ssa_iiMatra-tamil": "uni0BB70BC0",
    "ssa_uMatra-tamil": "uni0BB70BC1",
    "ssa_uuMatra-tamil": "uni0BB70BC2",
    "t_r-deva": "uni0924094D094D0930",  # uni0924094D0930094D
    "t_ra-deva": "uni0924094D0930",
    "t_ta-deva": "uni0924094D0924",
    "ta-khmer.below.ro": "uni17D2178F.ro",
    "ta_iMatra-tamil": "uni0BA40BBF",
    "ta_uMatra-tamil": "uni0BA40BC1",
    "ta_uuMatra-tamil": "uni0BA40BC2",
    "tt_tta-deva": "uni091F094D091F",
    "tt_ttha-deva": "uni091F094D0920",
    "tt_ya-deva": "uni091F094D092F",
    "tta_iMatra-tamil": "uni0B9F0BBF",
    "tta_uMatra-tamil": "uni0B9F0BC1",
    "tta_uuMatra-tamil": "uni0B9F0BC2",
    "tth_ttha-deva": "uni0920094D0920",
    "tth_ya-deva": "uni0920094D092F",
    "va_uMatra-tamil": "uni0BB50BC1",
    "va_uuMatra-tamil": "uni0BB50BC2",
    "ya_uMatra-tamil": "uni0BAF0BC1",
    "ya_uuMatra-tamil": "uni0BAF0BC2",
    "yoYing_underscore-thai": "uni0E0D005F",  # uni0E0D_uni005F
}


@pytest.mark.parametrize("test_input,expected", PRODUCTION_NAMES.items())
def test_prod_names(test_input, expected):
    def prod(n):
        return get_glyph(n).production

    assert prod(test_input) == expected


if __name__ == "__main__":
    unittest.main()
