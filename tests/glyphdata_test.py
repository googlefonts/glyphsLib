# -*- coding=utf-8 -*-
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
from glyphsLib.glyphdata import get_glyph, _lookup_production_name
import unittest


class GlyphDataTest(unittest.TestCase):
    def test__lookup_production_name(self):
        # Our behavior differs from Glyphs, Glyphs 2.5.2 responses are in comments.
        lkup = lambda n: _lookup_production_name(n)
        self.assertEqual(lkup("a_a_acutecomb"), "a_a_acutecomb")
        self.assertEqual(lkup("a_a_dieresiscomb"), "uni006100610308")
        self.assertEqual(lkup("brevecomb_acutecomb"), "uni03060301")

        self.assertEqual(lkup("a_idotaccent"), "a_i.loclTRK")
        self.assertEqual(lkup("a_idotaccent_a"), None)  # "a_i.loclTRK_a"
        self.assertEqual(lkup("a_idotaccent_aaa"), None)
        self.assertEqual(lkup("a_idotaccent_dieresiscomb"), None)
        self.assertEqual(lkup("a_idotaccent_acutecomb"), None)  # "a_i.loclTRK_acutecomb"

        self.assertEqual(lkup("idotaccent"), "i.loclTRK")
        self.assertEqual(lkup("dieresiscomb"), "uni0308")
        self.assertEqual(lkup("idotaccent_dieresiscomb"), None)
        self.assertEqual(lkup("idotaccent_acutecomb"), None)  # "i.loclTRK_acutecomb"
        self.assertEqual(lkup("idotaccent_a"), None)  # "i.loclTRK_a"

        self.assertEqual(lkup("aa"), "uniA733")
        self.assertEqual(lkup("Dboldscript-math"), "u1D4D3")
        self.assertEqual(lkup("Dboldscript-math_Dboldscript-math"), "u1D4D3_u1D4D3")
        self.assertEqual(lkup("Dboldscript-math_a"), "u1D4D3_a")
        self.assertEqual(lkup("Dboldscript-math_a_aa"), "u1D4D3_a_uniA733")  # None
        self.assertEqual(lkup("Dboldscript-math_a_aaa"), None)
        self.assertEqual(lkup("a_Dboldscript-math"), "a_u1D4D3")  # None
        self.assertEqual(lkup("brevecomb_Dboldscript-math"), "uni0306_u1D4D3")  # None
        self.assertEqual(lkup("Dboldscript-math_brevecomb"), "u1D4D3_uni0306")  # None

        self.assertEqual(lkup("a_a_a_a_a_a_a"), "a_a_a_a_a_a_a")
        self.assertEqual(lkup("a_a_a_a_a_a_a_a_a_a_a_a_a_a_a_a"), "a_a_a_a_a_a_a_a_a_a_a_a_a_a_a_a")
        self.assertEqual(lkup("a_a_a_a_a_a_a_a_a_a_a_a_a_a_a_a_A"), None)  # ...

        # Made-up glyph names, should not have a distinct production name.
        self.assertEqual(lkup('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'), None)
        self.assertEqual(lkup('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'), None)

    def test_production_name(self):
        prod = lambda n: get_glyph(n).production_name
        self.assertEqual(prod(".notdef"), ".notdef")
        self.assertEqual(prod("eacute"), "eacute")
        self.assertEqual(prod("Abreveacute"), "uni1EAE")
        self.assertEqual(prod("C-fraktur"), "uni212D")
        self.assertEqual(prod("Dboldscript-math"), "u1D4D3")
        self.assertEqual(prod("fi"), "fi")
        self.assertEqual(prod("s_t"), "s_t")
        self.assertEqual(prod("Gcommaaccent"), "uni0122")
        self.assertEqual(prod("o_f_f_i.foo"), "o_f_f_i.foo")
        self.assertEqual(prod("brevecomb"), "uni0306")
        self.assertEqual(prod("brevecomb.case"), "uni0306.case")
        self.assertEqual(prod("brevecomb_acutecomb"), "uni03060301")
        self.assertEqual(prod("brevecomb_acutecomb.case"), "uni03060301.case")
        self.assertEqual(prod("brevecomb_a_a_a"), "uni0306006100610061")        
        self.assertEqual(prod("brevecomb_a_a_a.case"), "uni0306006100610061.case")
        self.assertEqual(prod("brevecomb_aaa.case"), "brevecomb_aaa.case")
        self.assertEqual(prod("brevecomb_Dboldscript-math"), "uni0306_u1D4D3")
        self.assertEqual(prod("brevecomb_Dboldscript-math.f.r"), "uni0306_u1D4D3.f.r")
        self.assertEqual(prod("ain_alefMaksura-ar.fina"), "uniFD13")

    def test_unicode(self):
        uni = lambda n: get_glyph(n).unicode
        self.assertIsNone(uni(".notdef"))
        self.assertEqual(uni("eacute"), "é")
        self.assertEqual(uni("Abreveacute"), "Ắ")
        self.assertEqual(uni("C-fraktur"), "ℭ")
        self.assertEqual(uni("Dboldscript-math"), "𝓓")
        self.assertEqual(uni("fi"), "ﬁ")
        self.assertIsNone(uni("s_t"))  # no 'unicode' in GlyphsData
        self.assertEqual(uni("Gcommaaccent"), "Ģ")
        self.assertEqual(uni("o_f_f_i.foo"), "offi")
        self.assertEqual(uni("brevecomb"), "̆")
        self.assertEqual(uni("brevecomb.case"), "̆")
        self.assertEqual(uni("brevecomb_acutecomb"), "̆́")
        self.assertEqual(uni("brevecomb_acutecomb.case"), "̆́")

    def test_category(self):
        cat = lambda n: (get_glyph(n).category, get_glyph(n).subCategory)
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

    def test_bug232(self):
        # https://github.com/googlei18n/glyphsLib/issues/232
        u, g = get_glyph("uni07F0"), get_glyph("longlowtonecomb-nko")
        self.assertEqual((u.category, g.category), ("Mark", "Mark"))
        self.assertEqual((u.subCategory, g.subCategory),
                         ("Nonspacing", "Nonspacing"))
        self.assertEqual((u.production_name, g.production_name),
                         ("uni07F0", "uni07F0"))
        self.assertEqual((u.unicode, g.unicode), ("\u07F0", "\u07F0"))


if __name__ == "__main__":
    unittest.main()
