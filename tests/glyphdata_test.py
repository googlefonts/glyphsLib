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
import unittest
import xml.etree.ElementTree

from glyphsLib.glyphdata import *

class GlyphDataTest(unittest.TestCase):
    
    def test_infoFromName(self):
        # all the test from Glyphsapp
        
        info = get_glyph("**ABC**")
        self.assertIsNone(info)

        info = get_glyph("sad-ar.medi.liga")
        self.assertEqual(info.name, "sad-ar.medi.liga")
        self.assertIsNone(info.unicodes)

        info = get_glyph("x_ringcomb")
        self.assertEqual(info.name, "x_ringcomb")
        self.assertEqual(info.production, "uni0078030A")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)
        self.assertEqual(info.case, "lower")

        '''
        # TODO: double lang tags
        info = get_glyph("a_voicedcomb-kana-hira")
        self.assertEqual(info.name, "a_voicedcomb-kana-hira")
        self.assertEqual(info.production, "uni30423099")

        info = get_glyph("a-hira_voicedcomb-kana")
        self.assertEqual(info.name, "a_voicedcomb-kana-hira")
        self.assertEqual(info.production, "uni30423099")
        '''

        info = get_glyph("歷.1")
        self.assertEqual(info.name, "uni6B77.1")
        self.assertIsNone(info.production)

        info = get_glyph("A")
        self.assertEqual(info.name, "A")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "latin")

        info = get_glyph("uni0041")
        self.assertEqual(info.name, "uni0041")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "latin")

        info = get_glyph("uni0041.01")
        self.assertEqual(info.name, "uni0041.01")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "latin")

        info = get_glyph("uni6B77.1")
        self.assertEqual(info.name, "uni6B77.1")
        self.assertIsNone(info.production)
        
        info = get_glyph("uni6B776B77")
        self.assertEqual(info.name, "uni6B776B77")

        '''
        # TODO: implement parsing those names
        info = get_glyph("dvKTa")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")
        self.assertEqual(info.production, "uni0915094D0924")

        info = get_glyph("dvKTa.ss01")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")
        self.assertEqual(info.production, "uni0915094D0924.ss01")
        '''

        info = get_glyph("k_ta-deva.ss01")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")
        self.assertEqual(info.production, "uni0915094D0924.ss01")

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
        # self.assertEqual(info.production, "Asuperior")
        self.assertEqual(info.case, GSMinor)
        self.assertIsNone(info.unicodes)

        info = get_glyph("Ainferior")
        self.assertEqual(info.name, "Ainferior")
        self.assertEqual(info.category, "Letter")
        # self.assertEqual(info.production, "Ainferior")
        self.assertEqual(info.case, GSMinor)
        self.assertIsNone(info.unicodes)

        info = get_glyph("ia-cy")
        self.assertEqual(info.name, "ya-cy")
        self.assertEqual(info.category, "Letter")
        
        info = get_glyph("ii_ia-cy.fina")
        self.assertEqual(info.name, "ii_ia-cy.fina") # ii_ya-cy.fina
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.production, "uni0438044F.fina")

        info = get_glyph("ia-cy.fina")
        self.assertEqual(info.production, "uni044F.fina")
        
        info = get_glyph("a_a-cy");
        self.assertEqual(info.subCategory, "Ligature")
        self.assertEqual(info.production, "uni04300430")
        self.assertIsNone(info.unicodes)

        info = get_glyph("one-ar.osf.001")
        self.assertEqual(info.name, "one-ar.osf.001")

        info = get_glyph("one-ar.osf.ss01")
        self.assertEqual(info.name, "one-ar.osf.ss01")

        info = get_glyph("f_i.liga")
        self.assertEqual(info.name, "f_i.liga")
        self.assertEqual(info.production, "f_i.liga")

        info = get_glyph("f_i.rlig")
        self.assertEqual(info.name, "f_i.rlig")
        self.assertEqual(info.production, "f_i.rlig")

        info = get_glyph("f_i.ss01_")
        self.assertEqual(info.name, "f_i.ss01_")
        self.assertEqual(info.production, "f_i.ss01_")

        info = get_glyph("f_i._ss01")
        self.assertEqual(info.name, "f_i._ss01")
        self.assertEqual(info.production, "f_i._ss01")

        info = get_glyph("f_i.ss02_ss01")
        self.assertEqual(info.name, "f_i.ss02_ss01")
        self.assertEqual(info.production, "f_i.ss02_ss01")

        info = get_glyph("f_i.ss02_ss01.ss03")
        self.assertEqual(info.name, "f_i.ss02_ss01.ss03")
        self.assertEqual(info.production, "f_i.ss02_ss01.ss03")

        info = get_glyph("uni4E08uE0101-JP")
        # self.assertEqual(info.name, "uni4E08.uv018") # fails NULL
        # self.assertIsNone(info.unicodes) # fails NULL

        info = get_glyph("𬀩")
        self.assertEqual(info.name, "u2C029")
        self.assertEqual(info.script, "Hani") # TODO: should be "han"

        info = get_glyph("o_f_f.fina")
        self.assertEqual(info.name, "o_f_f.fina")
        self.assertEqual(info.production, "o_f_f.fina")

        '''
        TODO: To preserve the "agl" name before the first period, we have a matching suffix ligature
        info = get_glyph("f.ss01_j.ss02")
        self.assertEqual(info.name, "f_j.ss01_ss02")
        self.assertEqual(info.production, "f_j.ss01_ss02")
        '''

        info = get_glyph("brevecomb")
        self.assertEqual(info.case, GSLowercase)

        info = get_glyph("brevecomb.case")
        self.assertEqual(info.case, GSUppercase)

        info = get_glyph("dieresiscomb_acutecomb.case")
        self.assertEqual(info.case, GSUppercase)

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
        self.assertEqual(info.production, "uni17D2179B")
        
        info = get_glyph("lo_uaMark-khmer.below_")
        self.assertEqual(info.name, "lo_uaMark-khmer.below_")
        self.assertEqual(info.script, "khmer")
        
        '''
        TODO: this is similar to the "f_j.ss01_ss02". The "below" belongs to the "lo-khmer". And "lo-khmer.below" is in glyphData. 
        self.assertEqual(info.production, "uni17D2179B17BD")
        '''

        info = get_glyph("_loop-lao")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "_loop-lao")
        self.assertEqual(info.script, "lao")

        info = get_glyph("unicode")
        self.assertIsNone(info)

        info = get_glyph("uniABCG")
        self.assertIsNone(info)

        info = get_glyph("uni0CCD0CB0")
        self.assertEqual(info.name, "ra-kannada.below")
        self.assertEqual(info.production, "uni0CCD0CB0")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing Combining")

        info = get_glyph("uni0CCD0C95")
        self.assertEqual(info.name, "ka-kannada.below")
        self.assertEqual(info.production, "uni0CCD0C95")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing")

        info = get_glyph("ddhi-kannada")
        self.assertEqual(info.production, "uni0CA20CBF")

        info = get_glyph("k-kannada")

        info = get_glyph("kha_rakar-deva")
        self.assertEqual(info.subCategory, "Composition")
        self.assertEqual(info.production, "uni0916094D0930")

        info = get_glyph("k_ssi-kannada")
        self.assertEqual(info.production, "uni0C950CCD0CB70CBF")

        info = get_glyph("d_dh_r_ya-deva")
        self.assertEqual(info.name, "d_dh_r_ya-deva") # d_dh_rakar_ya-deva
        self.assertEqual(info.subCategory, "Conjunct")
        '''
        TODO:
        self.assertEqual(info.production, "uni0926094D0927094D0930094D092F")
        '''
        
        info = get_glyph("uni0926094D0927094D0930094D092F")
        self.assertEqual(info.name, "uni0926094D0927094D0930094D092F") # d_dh_rakar_ya-deva
        self.assertEqual(info.subCategory, "Conjunct")
        '''
        TODO:
        self.assertEqual(info.production, "uni0926094D0927094D0930094D092F")
        '''

        info = get_glyph("germandbls.sc")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("one.sinf")
        self.assertEqual(info.case, GSMinor)

        info = get_glyph("a_idotaccent_a")
        self.assertEqual(info.production, "a_i_a.loclTRK")

        info = get_glyph("f_idotaccent")
        self.assertEqual(info.production, "f_i.loclTRK")

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

        info = get_glyph("brevecomb.case")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.production, "uni0306.case")

        info = get_glyph("brevecomb_acutecomb")
        self.assertEqual(info.subCategory, "Nonspacing")

        info = get_glyph("brevecomb_acutecomb.case")
        self.assertEqual(info.subCategory, "Nonspacing")
        self.assertEqual(info.production, "uni03060301.case")

        info = get_glyph("a_parallel.circled")
        self.assertEqual(info.name, "a_parallel.circled")
        self.assertEqual(info.production, "uni00612225.circled")

        info = get_glyph("a_parallel._circled")
        self.assertEqual(info.name, "a_parallel._circled")
        '''
        TODO:
        self.assertEqual(info.production, "uni006129B7")
        '''

        info = get_glyph("Dboldscript-math")
        self.assertEqual(info.production, "u1D4D3")

        info = get_glyph("a_Dboldscript-math")
        self.assertEqual(info.name, "a_Dboldscript-math")
        self.assertEqual(info.production, "a_u1D4D3")

        info = get_glyph("uni51CB.jp78")
        self.assertEqual(info.name, "uni51CB.jp78")
        # self.assertEqual(info.production, "uni51CB.jp78") # fails
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.script, "han")

        info = get_glyph("h.sc")
        self.assertEqual(info.case, GSSmallcaps)
        self.assertIsNone(info.subCategory)

        info = get_glyph("i.sc")
        self.assertIsNone(info.production)
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
        self.assertEqual(info.production, "uniA716")
            
        info = get_glyph("extraLowLeftStemToneBarmod_extraLowLeftStemToneBarmod_lowLeftStemToneBarmod")
        self.assertEqual(info.category, "Symbol")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertEqual(info.production, "uniA716A716A715")

        info = get_glyph("three")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")

        info = get_glyph("three.tosf")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")

        info = get_glyph("three.tosf.ss13")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")

        info = get_glyph("one.subs")
        self.assertEqual(info.case, GSMinor)

        info = get_glyph("a.subs")
        self.assertEqual(info.case, GSMinor)

        info = get_glyph("t_rakar-deva")
        self.assertEqual(info.production, "uni0924094D0930094D")

        info = get_glyph("ta_rakar-deva")
        self.assertEqual(info.production, "uni0924094D0930")

        info = get_glyph("t_reph-deva")
        self.assertEqual(info.script, "devanagari")

        info = get_glyph("A_acutecomb-cy")
        self.assertEqual(info.name, "A_acutecomb-cy")
        self.assertEqual(info.production, "uni04100301")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "cyrillic")

        info = get_glyph("Ie_acutecomb-cy")
        self.assertEqual(info.name, "Ie_acutecomb-cy")
        self.assertEqual(info.production, "uni04150301")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)
        self.assertEqual(info.case, GSUppercase)
        self.assertEqual(info.script, "cyrillic")

        info = get_glyph("i.head.sc")
        self.assertEqual(info.name, "i.head.sc")
        self.assertEqual(info.case, GSSmallcaps)

        info = get_glyph("ma-kannada.base")
        self.assertEqual(info.name, "ma-kannada.base")
        self.assertEqual(info.production, "uni0CAE.base")
        self.assertEqual(info.category, "Letter")
        self.assertIsNone(info.subCategory)

        info = get_glyph("ka-kannada.below")
        self.assertEqual(info.production, "uni0CCD0C95")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing")


        info = get_glyph("ka_ssa-kannada.below")
        self.assertEqual(info.category, "Mark")
        self.assertEqual(info.subCategory, "Spacing")
        self.assertEqual(info.production, "uni0CCD0C950CCD0CB7")

        info = get_glyph("i.latn_TRK.pcap")
        self.assertEqual(info.name, "i.latn_TRK.pcap")

        info = get_glyph("ga-deva")
        self.assertEqual(info.marks, ("aiMatra-deva", "anudatta-deva", "anusvara-deva", "candraBindu-deva", "eCandraMatra-deva", "eMatra-deva", "eShortMatra-deva", "halant-deva", "lVocalicMatra-deva", "nukta-deva", "oeMatra-deva", "rakar-deva", "reph-deva", "rVocalicMatra-deva", "udatta-deva", "ueMatra-deva", "uMatra-deva", "uuMatra-deva"))

        info = get_glyph("d_ga-deva")
        self.assertEqual(info.marks, ("aiMatra-deva", "anudatta-deva", "anusvara-deva", "candraBindu-deva", "eCandraMatra-deva", "eMatra-deva", "eShortMatra-deva", "halant-deva", "lVocalicMatra-deva", "nukta-deva", "oeMatra-deva", "rakar-deva", "reph-deva", "rVocalicMatra-deva", "udatta-deva", "ueMatra-deva", "uMatra-deva", "uuMatra-deva"))

        info = get_glyph("yehVinverted-farsi.medi")
        self.assertEqual(info.production, "uni063D.medi")

        info = get_glyph("less_d_u_a_l_s_h_o_c_k_three_d_greater.liga")
        self.assertEqual(info.production, "less_d_u_a_l_s_h_o_c_k_three_d_greater.liga")

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
        self.assertEqual(info.production, "uni277B")

        info = get_glyph("five_zero.blackCircled")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertEqual(info.production, "uni277A24FF")

        info = get_glyph("five_zero.blackCircled_blackCircled")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Ligature")
        self.assertEqual(info.production, "uni277A24FF")

        info = get_glyph("two_zero.blackCircled")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.subCategory, "Decimal Digit")
        self.assertEqual(info.production, "uni24F4")

        info = get_glyph("ka_ra-deva")
        self.assertEqual(info.name, "ka_ra-deva")
        self.assertEqual(info.production, "uni09150930")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Ligature")

        info = get_glyph("ka_r-deva")
        self.assertEqual(info.name, "ka_rakar-deva")
        self.assertEqual(info.production, "uni0915094D0930")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Composition")

        info = get_glyph("k_ra-deva") # does this even make sense?
        #self.assertEqual(info.name, "ka_rakar-deva")
        #self.assertEqual(info.production, "uni0915094D0930")
        #self.assertEqual(info.category, "Letter")
        #self.assertEqual(info.subCategory, "Composition")

        info = get_glyph("kh_na-deva")
        self.assertEqual(info.name, "kh_na-deva")
        self.assertEqual(info.production, "uni0916094D0928")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")

        info = get_glyph("nukta_rakar-deva")
        self.assertEqual(info.name, "nukta_rakar-deva")
        self.assertEqual(info.production, "uni093C094D0930")

        info = get_glyph("dd_dda-myanmar")
        self.assertEqual(info.name, "dd_dda-myanmar")
        self.assertEqual(info.production, "uni0916094D0928")
        self.assertEqual(info.category, "Letter")
        self.assertEqual(info.subCategory, "Conjunct")

        info = get_glyph("rakar-deva")
        self.assertEqual(info.name, "rakar-deva")
        self.assertEqual(info.production, "uni094D0930")

        info = get_glyph("k_rakar-deva")
        self.assertEqual(info.name, "k_rakar-deva")
        self.assertEqual(info.production, "uni0915094D0930094D")

        info = get_glyph("uni0915094D0930094D")
        self.assertEqual(info.name, "k_rakar-deva")
        self.assertEqual(info.production, "uni0915094D0930094D")

        info = get_glyph("uni0915094D")
        self.assertEqual(info.name, "k-deva")

        info = get_glyph("uni0915094D0930")
        self.assertEqual(info.name, "ka_rakar-deva")

        info = get_glyph("dvHNa")
        self.assertEqual(info.script, "devanagari")

        info = get_glyph("h_na-deva")
        self.assertEqual(info.script, "devanagari")

        info = get_glyph("reph-deva.imatra")
        self.assertEqual(info.production, "uni0930094D.imatra")

        info = get_glyph("iMatra-deva.01")

        info = get_glyph("iMatra-gujarati.01")

        info = get_glyph("iiMatra_reph-deva")
        self.assertEqual(info.production, "uni09400930094D")

        info = get_glyph("k_ss-deva")
        self.assertEqual(info.subCategory, "Conjunct")

        info = get_glyph("u1F1A.d")
        self.assertEqual(info.name, "Epsilonpsilivaria.d")

        info = get_glyph("eMatra_reph_anusvara-deva")
        self.assertEqual(info.production, "uni09470930094D0902")

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

        #pragma mark Arabic

        info = get_glyph("reh_lam-ar.fina")
        self.assertEqual(info.production, "uni06310644.fina")

        info = get_glyph("reh_lamVabove-ar.fina")
        self.assertEqual(info.production, "uni063106B5.fina")

        info = get_glyph("kaf_lamVabove-ar.fina")
        self.assertEqual(info.production, "uni064306B5.fina")

        info = get_glyph("lamVabove-ar.medi")
        self.assertEqual(info.production, "uni06B5.medi")

        info = get_glyph("kaf_lamVabove-ar.medi")
        self.assertEqual(info.production, "uni064306B5.medi")

        info = get_glyph("lam_yehHamzaabove_meem-ar")
        self.assertEqual(info.production, "uni064406260645")

        info = get_glyph("yehFarsi_noonghunna-ar.fina.rlig")
        self.assertEqual(info.script, "arabic")

        info = get_glyph("beh-ar.fina.ss01")
        self.assertEqual(info.script, "arabic")

        info = get_glyph("ain_ain-ar.fina")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.production, "uni06390639.fina")
        self.assertEqual(info.name, "ain_ain-ar.fina")

        info = get_glyph("ain_ain-ar.fina.ss01")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.production, "uni06390639.fina.ss01")
        self.assertEqual(info.name, "ain_ain-ar.fina.ss01")

        info = get_glyph("uniFECCFECA")
        self.assertEqual(info.name, "ain_ain-ar.fina")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.production, "uni06390639.fina")

        info = get_glyph("jeh_ain-ar.fina")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.production, "uni06980639.fina")
        self.assertEqual(info.name, "jeh_ain-ar.fina")

        info = get_glyph("kaf_yeh-farsi.fina")
        self.assertEqual(info.name, "kaf_yehFarsi-ar.fina")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.production, "uni064306CC.fina")

        info = get_glyph("kaf_yeh-farsi.fina.ss01")
        self.assertEqual(info.name, "kaf_yehFarsi-ar.fina.ss01")
        self.assertEqual(info.script, "arabic")
        self.assertEqual(info.production, "uni064306CC.fina.ss01")

        info = get_glyph("ain-ar.medi_zah-ar.medi_alef-ar.medi_noonghunna-ar.fina")
        self.assertEqual(info.name, "ain_zah_alef_noonghunna-ar.fina")
        self.assertEqual(info.production, "uni06390638062706BA.fina")

        info = get_glyph("ain-ar.medi_zah-ar.medi_alef-ar.medi_noonghunna-ar.medi")
        self.assertEqual(info.name, "ain_zah_alef_noonghunna-ar.medi")
        self.assertEqual(info.production, "uni06390638062706BA.medi")
        result = ("ain-ar.medi", "zah-ar.medi", "alef-ar.fina", "noonghunna-ar")

        info = get_glyph("ain_zah_alefMaksura_noonghunna-ar")
        self.assertEqual(info.name, "ain_zah_alefMaksura_noonghunna-ar")
        self.assertEqual(info.production, "uni06390638064906BA")

        info = get_glyph("ain_zah_alefMaksura_noonghunna-ar.fina")
        self.assertEqual(info.name, "ain_zah_alefMaksura_noonghunna-ar.fina")
        self.assertEqual(info.production, "uni06390638064906BA.fina")

        info = get_glyph("ain-ar.init_zah-ar.medi_alef-ar.medi_noonghunna-ar.fina")
        self.assertEqual(info.name, "ain_zah_alef_noonghunna-ar")
        self.assertEqual(info.production, "uni06390638062706BA")

        info = get_glyph("lam_alef-ar.fina")
        self.assertEqual(info.name, "lam_alef-ar.fina")
        self.assertEqual(info.production, "uni06440627.fina")

        info = get_glyph("lam-ar.init_alef-ar.fina")
        self.assertEqual(info.name, "lam_alef-ar")
        self.assertEqual(info.production, "uni06440627")

        info = get_glyph("beh-ar.fina")

        info = get_glyph("meemDotabove-ar.fina")

        info = get_glyph("lam_alef-ar")
        info = get_glyph("lam_alef-ar.fina")
        info = get_glyph("lam_alefWasla-ar")

        info = get_glyph("uniFEFB.fina")
        self.assertEqual(info.name, "lam_alef-ar.fina")
        self.assertEqual(info.production, "uni06440627.fina")

        info = get_glyph("tehMarbutagoal-ar.fina")
        self.assertEqual(info.name, "tehMarbutagoal-ar.fina")
        self.assertEqual(info.category, "Letter")

        info = get_glyph("meem_meem_meem-ar.fina.connMeemSecond")
        self.assertEqual(info.name, "meem_meem_meem-ar.fina.connMeemSecond")
        self.assertEqual(info.production, "uni064506450645.fina.connMeemSecond")

        info = get_glyph("meem-ar.fina.conn_meem_second")
        self.assertEqual(info.production, "uni0645.fina.conn_meem_second")

        info = get_glyph("meem-ar.medi.conn_meem_second")
        self.assertEqual(info.production, "uni0645.medi.conn_meem_second")

        info = get_glyph("one-ar")
        self.assertEqual(info.name, "one-ar")
        self.assertEqual(info.category, "Number")
        self.assertEqual(info.production, "uni0661")
        self.assertEqual(info.sortName, "ar3129")
        self.assertEqual(info.direction, GSWritingDirectionLeftToRight)

        info = get_glyph("dottedCircle_consonantk-lepcha")
        self.assertEqual(info.name, "dottedCircle_consonantk-lepcha")
        self.assertEqual(info.production, "uni25CC_consonantk-lepcha")

        info = get_glyph("dottedCircle_k-lepcha")
        self.assertEqual(info.name, "dottedCircle_k-lepcha")
        self.assertEqual(info.production, "uni25CC1C2D")

        info = get_glyph("uni25CC_ran-lepcha")
        self.assertEqual(info.name, "dottedCircle_ran-lepcha")
        self.assertEqual(info.production, "uni25CC1C36")

        info = get_glyph("uni25CC_ran-lepcha.ss01")
        self.assertEqual(info.name, "dottedCircle_ran-lepcha.ss01")
        self.assertEqual(info.production, "uni25CC1C36.ss01")

        info = get_glyph("uni00C3.ss01")
        self.assertEqual(info.name, "Atilde.ss01")

        info = get_glyph("uni00C300C3.ss01")
        self.assertEqual(info.name, "Atilde_Atilde.ss01")
        self.assertEqual(info.production, "Atilde_Atilde.ss01")

        info = get_glyph("t.initlo_t")
        XCTAssertNotNil(info)
        self.assertEqual(info.name, "t_t.initlo_")

        info = get_glyph("f_f_i")
        self.assertEqual(info.production, nil)

        info = get_glyph("f_h")
        self.assertEqual(info.production, "f_h")

        info = get_glyph("o_o.ss01")

        info = get_glyph("iMatra_reph-deva.12")
        self.assertEqual(info.subCategory, "Matra")
        self.assertEqual(info.production, "uni093F0930094D.12")

        info = get_glyph("iMatra_reph-deva")
        self.assertEqual(info.subCategory, "Matra")
        self.assertEqual(info.production, "uni093F0930094D")

        info = get_glyph("gcommaaccent")

    def test_production_name(self):
        # Our behavior differs from Glyphs, Glyphs 2.5.2 responses are in comments.
        def prod(n):
            return get_glyph(n).production

        self.assertEqual(prod(".notdef"), ".notdef")
        self.assertEqual(prod("eacute"), "eacute")
        self.assertEqual(prod("Abreveacute"), "uni1EAE")
        self.assertEqual(prod("C-fraktur"), "uni212D")
        self.assertEqual(prod("Dboldscript-math"), "u1D4D3")
        self.assertEqual(prod("fi"), "fi")
        self.assertEqual(prod("s_t"), "s_t")
        self.assertEqual(prod("Gcommaaccent"), "uni0122")
        self.assertEqual(prod("o_f_f_i.foo"), "o_f_f_i.foo")
        self.assertEqual(prod("ain_alefMaksura-ar.fina"), "uniFD13")
        self.assertEqual(prod("brevecomb"), "uni0306")
        self.assertEqual(prod("brevecomb.case"), "uni0306.case")
        self.assertEqual(prod("brevecomb_acutecomb"), "uni03060301")
        self.assertEqual(prod("brevecomb_acutecomb.case"), "uni03060301.case")
        self.assertEqual(prod("brevecomb_a_a_a"), "uni0306006100610061")
        self.assertEqual(prod("brevecomb_a_a_a.case"), "uni0306006100610061.case")
        self.assertEqual(prod("brevecomb_aaa.case"), "brevecomb_aaa.case")

        # brevecomb_Dboldscript-math
        self.assertEqual(prod("brevecomb_Dboldscript-math"), "uni0306_u1D4D3")

        # brevecomb_Dboldscript-math.f.r
        self.assertEqual(prod("brevecomb_Dboldscript-math.f.r"), "uni0306_u1D4D3.f.r")

        self.assertEqual(prod("Dboldscript-math_Dboldscript-math"), "u1D4D3_u1D4D3")
        self.assertEqual(prod("Dboldscript-math_Dboldscript-math.f"), "u1D4D3_u1D4D3.f")
        self.assertEqual(prod("Dboldscript-math_a"), "u1D4D3_a")

        # a_Dboldscript-math
        self.assertEqual(prod("a_Dboldscript-math"), "a_u1D4D3")

        # Dboldscript-math_a_aa
        self.assertEqual(prod("Dboldscript-math_a_aa"), "u1D4D3_a_uniA733")

        self.assertEqual(prod("Dboldscript-math_a_aaa"), "Dboldscriptmath_a_aaa")

        # brevecomb_Dboldscript-math
        self.assertEqual(prod("brevecomb_Dboldscript-math"), "uni0306_u1D4D3")

        # Dboldscript-math_brevecomb
        self.assertEqual(prod("Dboldscript-math_brevecomb"), "u1D4D3_uni0306")

        self.assertEqual(prod("idotaccent"), "i.loclTRK")
        self.assertEqual(prod("a_idotaccent"), "a_i.loclTRK")

        # a_i.loclTRK_a
        self.assertEqual(prod("a_idotaccent_a"), "a_idotaccent_a")

        self.assertEqual(prod("a_a_acutecomb"), "a_a_acutecomb")
        self.assertEqual(prod("a_a_dieresiscomb"), "uni006100610308")
        self.assertEqual(prod("brevecomb_acutecomb"), "uni03060301")
        self.assertEqual(prod("vaphalaa-malayalam"), "uni0D030D35.1")
        self.assertEqual(prod("onethird"), "uni2153")
        self.assertEqual(prod("Jacute"), "uni004A0301")

    '''
    def test_unicode(self):
        def uni(n):
            return get_glyph(n).unicode

        self.assertIsNone(uni(".notdef"))
        self.assertEqual(uni("eacute"), "00E9")
        self.assertEqual(uni("Abreveacute"), "1EAE")
        self.assertEqual(uni("C-fraktur"), "212D")
        self.assertEqual(uni("Dboldscript-math"), "1D4D3")
        self.assertEqual(uni("fi"), "FB01")
        self.assertEqual(uni("Gcommaaccent"), "0122")
        self.assertIsNone(uni("s_t"))
        self.assertIsNone(uni("o_f_f_i.foo"))
        self.assertEqual(uni("brevecomb"), "0306")
        self.assertIsNone(uni("brevecomb.case"))
        self.assertIsNone(uni("brevecomb_acutecomb"))
        self.assertIsNone(uni("brevecomb_acutecomb.case"))

    def test_category(self):
        def cat(n):
            return get_glyph(n).category, get_glyph(n).subCategory

        self.assertEqual(cat(".notdef"), ("Separator", None))
        self.assertEqual(cat("uni000D"), ("Separator", None))
        self.assertEqual(cat("boxHeavyUp"), ("Symbol", "Geometry"))
        self.assertEqual(cat("eacute"), ("Letter", "Lowercase"))
        self.assertEqual(cat("Abreveacute"), ("Letter", "Uppercase"))
        self.assertEqual(cat("C-fraktur"), ("Letter", "Uppercase"))
        self.assertEqual(cat("fi"), ("Letter", "Ligature"))
        self.assertEqual(cat("fi.alt"), ("Letter", "Ligature"))
        self.assertEqual(cat("hib-ko"), ("Letter", "Syllable"))
        self.assertEqual(cat("one.foo"), ("Number", "Decimal Digit"))
        self.assertEqual(cat("one_two.foo"), ("Number", "Ligature"))
        self.assertEqual(cat("o_f_f_i"), ("Letter", "Ligature"))
        self.assertEqual(cat("o_f_f_i.foo"), ("Letter", "Ligature"))
        self.assertEqual(cat("ain_alefMaksura-ar.fina"), ("Letter", "Ligature"))
        self.assertEqual(cat("brevecomb"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("brevecomb.case"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("brevecomb_acutecomb"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("brevecomb_acutecomb.case"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("caroncomb_dotaccentcomb"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("dieresiscomb_caroncomb"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("dieresiscomb_macroncomb"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("dotaccentcomb_macroncomb"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("macroncomb_dieresiscomb"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("dotaccentcomb_o"), ("Mark", "Nonspacing"))
        self.assertEqual(cat("macronlowmod_O"), ("Mark", "Modifier"))
        self.assertEqual(cat("O_o"), ("Letter", "Ligature"))
        self.assertEqual(cat("O_dotaccentcomb_o"), ("Letter", "Ligature"))
        self.assertEqual(cat("O_dotaccentcomb"), ("Letter", "Uppercase"))
        self.assertEqual(cat("O_period"), ("Letter", "Ligature"))
        self.assertEqual(cat("O_nbspace"), ("Letter", "Uppercase"))
        self.assertEqual(cat("_a"), (None, None))
        self.assertEqual(cat("_aaa"), (None, None))
        self.assertEqual(cat("dal_alef-ar"), ("Letter", "Ligature"))
        self.assertEqual(cat("dal_lam-ar.dlig"), ("Letter", "Ligature"))

    def test_category_buy_unicode(self):
        def cat(n, u):
            return (
                get_glyph(n, unicodes=u).category,
                get_glyph(n, unicodes=u).subCategory,
            )

        # "SignU.bn" is a non-standard name not defined in GlyphData.xml
        self.assertEqual(cat("SignU.bn", ["09C1"]), ("Mark", "Nonspacing"))

    def test_bug232(self):
        # https://github.com/googlefonts/glyphsLib/issues/232
        u, g = get_glyph("uni07F0"), get_glyph("longlowtonecomb-nko")
        self.assertEqual((u.category, g.category), ("Mark", "Mark"))
        self.assertEqual((u.subCategory, g.subCategory), ("Nonspacing", "Nonspacing"))
        self.assertEqual((u.production, g.production), ("uni07F0", "uni07F0"))
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
    '''

if __name__ == "__main__":
    tests = GlyphDataTest()
    #tests.test_infoFromName()
    unittest.main(exit=False, failfast=False)
