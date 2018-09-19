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

from __future__ import print_function, division, absolute_import, unicode_literals

import os
from textwrap import dedent

import defcon

from glyphsLib import to_glyphs, to_ufos, classes

import pytest


def make_font(features):
    ufo = defcon.Font()
    ufo.features = dedent(features)
    return ufo


def roundtrip(ufo, tmpdir):
    font = to_glyphs([ufo], minimize_ufo_diffs=True)
    filename = os.path.join(str(tmpdir), "font.glyphs")
    font.save(filename)
    font = classes.GSFont(filename)
    ufo, = to_ufos(font)
    return font, ufo


def test_blank(tmpdir):
    ufo = defcon.Font()

    font, rtufo = roundtrip(ufo, tmpdir)

    assert not font.features
    assert not font.featurePrefixes
    assert not rtufo.features.text


def test_comment(tmpdir):
    ufo = defcon.Font()
    ufo.features.text = dedent(
        """\
        # Test
        # Lol
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir)

    assert not font.features
    assert len(font.featurePrefixes) == 1
    fp = font.featurePrefixes[0]
    assert fp.code.strip() == ufo.features.text.strip()
    assert not fp.automatic

    assert rtufo.features.text == ufo.features.text


def test_languagesystems(tmpdir):
    ufo = defcon.Font()
    # The sample has messed-up spacing because there was a problem with that
    ufo.features.text = dedent(
        """\
        # Blah
          languagesystem DFLT dflt; #Default
        languagesystem latn dflt;\t# Latin
        \tlanguagesystem arab URD; #\tUrdu
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir)

    assert not font.features
    assert len(font.featurePrefixes) == 1
    fp = font.featurePrefixes[0]
    assert fp.code == ufo.features.text[:-1]  # Except newline
    assert not fp.automatic

    assert rtufo.features.text == ufo.features.text


def test_classes(tmpdir):
    ufo = defcon.Font()
    # FIXME: (jany) no whitespace is preserved in this section
    ufo.features.text = dedent(
        """\
        @lc = [ a b ];

        @UC = [ A B ];

        @all = [ @lc @UC zero one ];

        @more = [ dot @UC colon @lc paren ];
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir)

    assert len(font.classes) == 4
    assert font.classes["lc"].code == "a b"
    assert font.classes["UC"].code == "A B"
    assert font.classes["all"].code == "@lc @UC zero one"
    assert font.classes["more"].code == "dot @UC colon @lc paren"

    assert rtufo.features.text == ufo.features.text


def test_class_synonym(tmpdir):
    ufo = defcon.Font()
    ufo.features.text = dedent(
        """\
        @lc = [ a b ];

        @lower = @lc;
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir)

    assert len(font.classes) == 2
    assert font.classes["lc"].code == "a b"
    assert font.classes["lower"].code == "@lc"

    # FIXME: (jany) should roundtrip
    assert rtufo.features.text == dedent(
        """\
        @lc = [ a b ];

        @lower = [ @lc ];
    """
    )


def test_include(tmpdir):
    ufo = defcon.Font()
    ufo.features.text = dedent(
        """\
        include(../family.fea);
        # Blah
        include(../fractions.fea);
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir)

    assert len(font.featurePrefixes) == 1
    assert font.featurePrefixes[0].code.strip() == ufo.features.text.strip()

    assert rtufo.features.text == ufo.features.text


def test_include_no_semicolon(tmpdir):
    ufo = defcon.Font()
    ufo.features.text = dedent(
        """\
        include(../family.fea)
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir)

    assert len(font.featurePrefixes) == 1
    assert font.featurePrefixes[0].code.strip() == ufo.features.text.strip()

    assert rtufo.features.text == ufo.features.text


def test_standalone_lookup(tmpdir):
    ufo = defcon.Font()
    # FIXME: (jany) does not preserve whitespace before and after
    ufo.features.text = dedent(
        """\
        # start of default rules that are applied under all language systems.
        lookup HAS_I {
          sub f f i by f_f_i;
            sub f i by f_i;
        } HAS_I;
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir)

    assert len(font.featurePrefixes) == 1
    assert font.featurePrefixes[0].code.strip() == ufo.features.text.strip()

    assert rtufo.features.text == ufo.features.text


def test_feature(tmpdir):
    ufo = defcon.Font()
    # This sample is straight from the documentation at
    # http://www.adobe.com/devnet/opentype/afdko/topic_feature_file_syntax.html
    # FIXME: (jany) does not preserve whitespace before and after
    ufo.features.text = dedent(
        """\
        feature liga {
      # start of default rules that are applied under all language systems.
                lookup HAS_I {
                 sub f f i by f_f_i;
                 sub f i by f_i;
                } HAS_I;

                lookup NO_I {
                 sub f f l by f_f_l;
                 sub f f by f_f;
                } NO_I;

      # end of default rules that are applied under all language systems.

            script latn;
               language dflt;
      # default lookup for latn included under all languages for the latn script

                  sub f l by f_l;
               language DEU;
      # default lookups included under the DEU language..
                  sub s s by germandbls;   # This is also included.
               language TRK exclude_dflt;   # default lookups are excluded.
                lookup NO_I;             # Only this lookup is included
                                         # under the TRK language

            script cyrl;
               language SRB;
                  sub c t by c_t; # this rule will apply only under
                                  # script cyrl language SRB.
      } liga;
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir)

    assert len(font.features) == 1
    # Strip "feature liga {} liga;"
    code = ufo.features.text.splitlines()[1:-1]
    assert font.features[0].code.strip() == "\n".join(code)

    assert rtufo.features.text.strip() == ufo.features.text.strip()


def test_different_features_in_different_UFOS(tmpdir):
    # If the input UFOs have different features, Glyphs cannot model the
    # differences easily.
    #
    # TODO: (jany) A complex solution would be to put all the features that we
    # find across all the UFOS into the GSFont's features, and then add custom
    # parameters "Replace Features" and "Remove features" to the GSFontMasters
    # of the UFOs that didn't have the feature originally.
    #
    # What is done now: if feature files differ between the input UFOs, the
    # original text of each UFO's feature is stored in userData, and a single
    # GSFeaturePrefix is created just to warn the user that features were not
    # imported because of differences.
    ufo1 = defcon.Font()
    ufo1.features.text = dedent(
        """\
        include('../family.fea');
    """
    )
    ufo2 = defcon.Font()
    ufo2.features.text = dedent(
        """\
        include('../family.fea');

        feature ss03 {
            sub c by c.ss03;
        } ss03;
    """
    )

    font = to_glyphs([ufo1, ufo2], minimize_ufo_diffs=True)
    filename = os.path.join(str(tmpdir), "font.glyphs")
    font.save(filename)
    font = classes.GSFont(filename)
    ufo1rt, ufo2rt = to_ufos(font)

    assert len(font.features) == 0
    assert len(font.featurePrefixes) == 1
    assert font.featurePrefixes[0].code == dedent(
        """\
        # Do not use Glyphs to edit features.
        #
        # This Glyphs file was made from several UFOs that had different
        # features. As a result, the features are not editable in Glyphs and
        # the original features will be restored when you go back to UFOs.
    """
    )

    assert ufo1rt.features.text == ufo1.features.text
    assert ufo2rt.features.text == ufo2.features.text


def test_roundtrip_disabled_feature():
    font = to_glyphs([defcon.Font()])
    feature = classes.GSFeature(name="ccmp")
    feature.code = dedent(
        """\
        sub a by a.ss03;
        sub b by b.ss03;
        sub c by c.ss03;
    """
    )
    feature.disabled = True
    font.features.append(feature)

    ufo, = to_ufos(font)
    assert ufo.features.text == dedent(
        """\
        feature ccmp {
        # disabled
        #sub a by a.ss03;
        #sub b by b.ss03;
        #sub c by c.ss03;
        } ccmp;
    """
    )

    font_r = to_glyphs([ufo])
    assert len(font_r.features) == 1
    feature_r = font_r.features[0]
    assert feature_r.name == "ccmp"
    assert feature_r.code == feature.code
    assert feature_r.disabled is True

    font_rr = to_glyphs(to_ufos(font_r))
    assert len(font_rr.features) == 1
    feature_rr = font_rr.features[0]
    assert feature_rr.name == "ccmp"
    assert feature_rr.code == feature.code
    assert feature_rr.disabled is True


def test_roundtrip_automatic_feature():
    font = to_glyphs([defcon.Font()])
    feature = classes.GSFeature(name="ccmp")
    feature.code = "sub c by c.ss03;"
    feature.automatic = True
    font.features.append(feature)

    ufo, = to_ufos(font)
    assert ufo.features.text == dedent(
        """\
        feature ccmp {
        # automatic
        sub c by c.ss03;
        } ccmp;
    """
    )

    font_r = to_glyphs([ufo])
    assert len(font_r.features) == 1
    feature_r = font_r.features[0]
    assert feature_r.name == "ccmp"
    assert feature_r.code == "sub c by c.ss03;"
    assert feature_r.automatic is True


def test_roundtrip_feature_prefix_with_only_a_comment():
    font = to_glyphs([defcon.Font()])
    prefix = classes.GSFeaturePrefix(name="include")
    # Contents: just a comment
    prefix.code = "#include(../family.fea)"
    font.featurePrefixes.append(prefix)

    ufo, = to_ufos(font)

    assert ufo.features.text == dedent(
        """\
        # Prefix: include
        #include(../family.fea)
    """
    )

    font_r = to_glyphs([ufo])
    assert len(font_r.featurePrefixes) == 1
    prefix_r = font_r.featurePrefixes[0]
    assert prefix_r.name == "include"
    assert prefix_r.code == "#include(../family.fea)"


@pytest.fixture
def ufo_with_GDEF():
    ufo = defcon.Font()
    gdef = dedent(
        """\
        table GDEF {
        GlyphClassDef
            [A], # Base
            , # Liga
            [dieresiscomb], # Mark
            ;
        } GDEF;
        """
    )
    ufo.features.text = gdef
    return ufo, gdef


def test_roundtrip_existing_GDEF(tmpdir, ufo_with_GDEF):
    """Test that an existing GDEF table in UFO is preserved unchanged and
    no extra GDEF table is generated upon roundtripping to UFO when
    `generate_GDEF` is False.
    """
    ufo, gdef = ufo_with_GDEF
    font = to_glyphs([ufo])
    filename = os.path.join(str(tmpdir), "font.glyphs")
    font.save(filename)
    font = classes.GSFont(filename)
    rtufo, = to_ufos(font, generate_GDEF=False)

    assert rtufo.features.text == gdef


def test_generate_GDEF_already_exists(tmpdir, ufo_with_GDEF):
    ufo = ufo_with_GDEF[0]
    font = to_glyphs([ufo])
    filename = os.path.join(str(tmpdir), "font.glyphs")
    font.save(filename)
    font = classes.GSFont(filename)

    with pytest.raises(ValueError, match="features already contain a `table GDEF"):
        to_ufos(font, generate_GDEF=True)


def test_groups_remain_at_top(tmpdir):
    ufo = defcon.Font()
    ufo.newGlyph("zero")
    ufo.newGlyph("zero.alt")
    fea_example = dedent(
        """\
        @FIG_DFLT = [zero];
        @FIG_ALT = [zero.alt];

        lookup pnum_text {
            sub @FIG_DFLT by @FIG_ALT;
        } pnum_text;

        feature pnum {
            lookup pnum_text;
        } pnum;
        """
    )
    ufo.features.text = fea_example

    font = to_glyphs([ufo], minimize_ufo_diffs=True)
    filename = os.path.join(str(tmpdir), "font.glyphs")
    font.save(filename)
    font = classes.GSFont(filename)
    rtufo, = to_ufos(font)

    fea_rt = rtufo.features.text
    assert fea_rt.index("@FIG_DFLT") < fea_rt.index("lookup") < fea_rt.index("feature")
