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
from glyphsLib.glyphdata import get_glyph
import unittest


class GlyphDataTest(unittest.TestCase):
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
