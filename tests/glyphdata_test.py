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

import pytest

from glyphsLib.glyphdata import get_glyph


class GlyphDataTest(unittest.TestCase):
    def test_production_name(self):
        # Our behavior differs from Glyphs, Glyphs 2.5.2 responses are in comments.
        def prod(n):
            return get_glyph(n).production_name

        self.assertEqual(prod(".notdef"), ".notdef")
        self.assertEqual(prod("eacute"), "eacute")
        self.assertEqual(prod("Abreveacute"), "uni1EAE")
        self.assertEqual(prod("C-fraktur"), "uni212D")
        self.assertEqual(prod("Dboldscript-math"), "u1D4D3")
        self.assertEqual(prod("fi"), "fi")
        self.assertEqual(prod("s_t"), "s_t")
        self.assertEqual(prod("Gcommaaccent"), "uni0122")
        self.assertEqual(prod("o_f_f_i.foo"), "o_f_f_i.foo")
        self.assertEqual(prod("ain_alefMaksura-ar.fina"), "uni06390649.fina")
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
        self.assertEqual(prod("Ech_Vew-arm.liga"), "uni0535054E.liga")

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
        self.assertEqual(cat("eacute"), ("Letter", None))
        self.assertEqual(cat("Abreveacute"), ("Letter", None))
        self.assertEqual(cat("C-fraktur"), ("Letter", None))
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
        self.assertEqual(cat("O_dotaccentcomb"), ("Letter", None))
        self.assertEqual(cat("O_period"), ("Letter", "Ligature"))
        self.assertEqual(cat("O_nbspace"), ("Letter", None))
        self.assertEqual(cat("_a"), (None, None))
        self.assertEqual(cat("_aaa"), (None, None))
        self.assertEqual(cat("dal_alef-ar"), ("Letter", "Ligature"))
        self.assertEqual(cat("dal_lam-ar.dlig"), ("Letter", "Ligature"))
        self.assertEqual(cat("po-khmer"), ("Letter", None))
        self.assertEqual(cat("po-khmer.below"), ("Mark", "Nonspacing"))
        # see https://github.com/googlefonts/glyphsLib/commit/68e4e9cf44c9919de
        # this glyph is not in the data, and we want fallback to find po-khmer.below
        # before po-khmer
        self.assertEqual(cat("po-khmer.below.ro"), ("Mark", "Nonspacing"))

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
        self.assertEqual((u.production_name, g.production_name), ("uni07F0", "uni07F0"))
        self.assertEqual((u.unicode, g.unicode), ("07F0", "07F0"))

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
        return get_glyph(n).production_name

    assert prod(test_input) == expected


if __name__ == "__main__":
    unittest.main()
