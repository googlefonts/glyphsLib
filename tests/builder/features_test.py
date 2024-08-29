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
from textwrap import dedent

from glyphsLib import to_glyphs, to_ufos, classes, to_designspace
from glyphsLib.builder.features import _build_public_opentype_categories

from fontTools.designspaceLib import DesignSpaceDocument
import pytest


def roundtrip(ufo, tmpdir, ufo_module):
    font = to_glyphs([ufo], minimize_ufo_diffs=True)
    filename = os.path.join(str(tmpdir), "font.glyphs")
    font.save(filename)
    font = classes.GSFont(filename)
    (ufo,) = to_ufos(font, ufo_module=ufo_module)
    return font, ufo


def test_blank(tmpdir, ufo_module):
    ufo = ufo_module.Font()

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert not font.features
    assert not font.featurePrefixes
    assert not rtufo.features.text


def test_comment(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        # Test
        # Lol
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert not font.features
    assert len(font.featurePrefixes) == 1
    fp = font.featurePrefixes[0]
    assert fp.code.strip() == ufo.features.text.strip()
    assert not fp.automatic

    assert rtufo.features.text == ufo.features.text


def test_languagesystems(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    # The sample has messed-up spacing because there was a problem with that
    ufo.features.text = dedent(
        """\
        # Blah
          languagesystem DFLT dflt; #Default
        languagesystem latn dflt;\t# Latin
        \tlanguagesystem arab URD; #\tUrdu
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert not font.features
    assert len(font.featurePrefixes) == 1
    fp = font.featurePrefixes[0]
    assert fp.code == ufo.features.text[:-1]  # Except newline
    assert not fp.automatic

    assert rtufo.features.text == ufo.features.text


def test_classes(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    # FIXME: (jany) no whitespace is preserved in this section
    ufo.features.text = dedent(
        """\
        @lc = [ a b
        ];

        @UC = [ A B
        ];

        @all = [ @lc @UC zero one
        ];

        @more = [ dot @UC colon @lc paren
        ];
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert len(font.classes) == 4
    assert font.classes["lc"].code == "a b"
    assert font.classes["UC"].code == "A B"
    assert font.classes["all"].code == "@lc @UC zero one"
    assert font.classes["more"].code == "dot @UC colon @lc paren"

    assert rtufo.features.text == ufo.features.text


def test_class_synonym(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        @lc = [ a b
        ];

        @lower = @lc;
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert len(font.classes) == 2
    assert font.classes["lc"].code == "a b"
    assert font.classes["lower"].code == "@lc"

    # FIXME: (jany) should roundtrip
    assert rtufo.features.text == dedent(
        """\
        @lc = [ a b
        ];

        @lower = [ @lc
        ];
    """
    )


def test_feature_names(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        feature ss01 {
        featureNames {
          name "Alternate g";
        };
        # automatic
        sub g by g.ss01;

        } ss01;
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    # Check code in Glyphs font
    gs_feature = font.features[0]
    assert gs_feature.automatic
    assert gs_feature.code.strip() == "sub g by g.ss01;"
    assert gs_feature.notes.strip() == "Name: Alternate g"

    assert rtufo.features.text == dedent(
        """\
        feature ss01 {
        featureNames {
          name "Alternate g";
        };
        # automatic
        sub g by g.ss01;

        } ss01;
    """
    )


def test_feature_names_notes(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        feature ss01 {
        # notes:
        # foo
        featureNames {
          name "Alternate g";
        };
        # automatic
        sub g by g.ss01;

        } ss01;
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    # Check code in Glyphs font
    gs_feature = font.features[0]
    assert gs_feature.automatic
    assert gs_feature.code.strip() == "sub g by g.ss01;"
    assert gs_feature.notes.strip() == "Name: Alternate g\nfoo"

    assert rtufo.features.text == dedent(
        """\
        feature ss01 {
        # notes:
        # foo
        featureNames {
          name "Alternate g";
        };
        # automatic
        sub g by g.ss01;

        } ss01;
    """
    )


def test_feature_names_full(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        feature ss01 {
        featureNames {
          name 1 "Alternate g";
        };
        # automatic
        sub g by g.ss01;

        } ss01;
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    # Check code in Glyphs font
    gs_feature = font.features[0]
    assert gs_feature.automatic
    assert gs_feature.code.strip() == "sub g by g.ss01;"
    assert gs_feature.notes.strip() == dedent(
        """\
        featureNames {
            name 1 "Alternate g";
        };"""
    )

    assert rtufo.features.text == dedent(
        """\
        feature ss01 {
        featureNames {
            name 1 "Alternate g";
        };
        # automatic
        sub g by g.ss01;

        } ss01;
    """
    )


def test_feature_names_multi(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        feature ss01 {
        featureNames {
          name "Alternate g";
          name 1 "Alternate g";
        };
        # automatic
        sub g by g.ss01;

        } ss01;
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    # Check code in Glyphs font
    gs_feature = font.features[0]
    assert gs_feature.automatic
    assert gs_feature.code.strip() == "sub g by g.ss01;"
    assert gs_feature.notes.strip() == dedent(
        """\
        featureNames {
            name "Alternate g";
            name 1 "Alternate g";
        };"""
    )

    assert rtufo.features.text == dedent(
        """\
        feature ss01 {
        featureNames {
            name "Alternate g";
            name 1 "Alternate g";
        };
        # automatic
        sub g by g.ss01;

        } ss01;
    """
    )


def test_include(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        include(../family.fea);
        # Blah
        include(../fractions.fea);
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert len(font.featurePrefixes) == 1
    assert font.featurePrefixes[0].code.strip() == ufo.features.text.strip()

    assert rtufo.features.text == ufo.features.text


def test_include_no_semicolon(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        include(../family.fea)
    """
    )

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert len(font.featurePrefixes) == 1
    assert font.featurePrefixes[0].code.strip() == ufo.features.text.strip()

    assert rtufo.features.text == ufo.features.text


def test_to_glyphs_expand_includes(tmp_path, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        include(family.fea);
        """
    )
    ufo.save(str(tmp_path / "font.ufo"))

    included_path = tmp_path / "family.fea"
    included_path.write_text("# hello from family.fea")
    assert included_path.exists()

    font = to_glyphs([ufo], minimize_ufo_diffs=True, expand_includes=True)

    assert len(font.featurePrefixes) == 1
    assert font.featurePrefixes[0].code.strip() == "# hello from family.fea"


def test_to_ufos_expand_includes(tmp_path, ufo_module):
    font = classes.GSFont()
    font.masters.append(classes.GSFontMaster())

    feature_prefix = classes.GSFeaturePrefix()
    feature_prefix.name = "include"
    feature_prefix.code = dedent(
        """\
        include(family.fea);
        """
    )
    font.featurePrefixes.append(feature_prefix)

    font.filepath = str(tmp_path / "font.glyphs")
    font.save()

    included_path = tmp_path / "family.fea"
    included_path.write_text("# hello from family.fea")
    assert included_path.exists()

    (ufo,) = to_ufos(font, ufo_module=ufo_module, expand_includes=True)

    assert ufo.features.text == ("# Prefix: include\n# hello from family.fea")


def test_standalone_lookup(tmpdir, ufo_module):
    ufo = ufo_module.Font()
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

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert len(font.featurePrefixes) == 1
    assert font.featurePrefixes[0].code.strip() == ufo.features.text.strip()

    assert rtufo.features.text == ufo.features.text


def test_feature(tmpdir, ufo_module):
    ufo = ufo_module.Font()
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

    font, rtufo = roundtrip(ufo, tmpdir, ufo_module)

    assert len(font.features) == 1
    # Strip "feature liga {} liga;"
    code = ufo.features.text.splitlines()[1:-1]
    assert font.features[0].code.strip() == "\n".join(code)

    assert rtufo.features.text.strip() == ufo.features.text.strip()


def test_different_features_in_different_UFOS(tmpdir, ufo_module):
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
    ufo1 = ufo_module.Font()
    ufo1.features.text = dedent(
        """\
        include('../family.fea');
    """
    )
    ufo2 = ufo_module.Font()
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
    ufo1rt, ufo2rt = to_ufos(font, ufo_module=ufo_module)

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


def test_roundtrip_disabled_feature(ufo_module):
    font = to_glyphs([ufo_module.Font()])
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

    (ufo,) = to_ufos(font, ufo_module=ufo_module)
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

    font_rr = to_glyphs(to_ufos(font_r, ufo_module=ufo_module))
    assert len(font_rr.features) == 1
    feature_rr = font_rr.features[0]
    assert feature_rr.name == "ccmp"
    assert feature_rr.code == feature.code
    assert feature_rr.disabled is True


def test_roundtrip_automatic_feature(ufo_module):
    font = to_glyphs([ufo_module.Font()])
    feature = classes.GSFeature(name="ccmp")
    feature.code = "sub c by c.ss03;"
    feature.automatic = True
    font.features.append(feature)

    (ufo,) = to_ufos(font, ufo_module=ufo_module)
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


def test_roundtrip_feature_prefix_with_only_a_comment(ufo_module):
    font = to_glyphs([ufo_module.Font()])
    prefix = classes.GSFeaturePrefix(name="include")
    # Contents: just a comment
    prefix.code = "#include(../family.fea)"
    font.featurePrefixes.append(prefix)

    (ufo,) = to_ufos(font, ufo_module=ufo_module)

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


def test_drop_disabled_class(ufo_module):
    font = to_glyphs([ufo_module.Font()])
    class_ = classes.GSClass(name="Class1", code="a b")
    class_.disabled = True
    font.classes.append(class_)

    class_ = classes.GSClass(name="Class2", code="c d")
    font.classes.append(class_)

    (ufo,) = to_ufos(font, ufo_module=ufo_module, minimal=True)
    assert ufo.features.text == dedent(
        """\
        @Class2 = [ c d
        ];
    """
    )


def test_drop_disabled_prefix(ufo_module):
    font = to_glyphs([ufo_module.Font()])
    prefix = classes.GSFeaturePrefix(name="Prefix1", code="# test 1")
    prefix.disabled = True
    font.featurePrefixes.append(prefix)

    prefix = classes.GSFeaturePrefix(name="Prefix2", code="# test 2")
    font.featurePrefixes.append(prefix)

    (ufo,) = to_ufos(font, ufo_module=ufo_module, minimal=True)
    assert ufo.features.text == dedent(
        """\
        # Prefix: Prefix2
        # test 2
    """
    )


def test_drop_disabled_feature(ufo_module):
    font = to_glyphs([ufo_module.Font()])
    feature = classes.GSFeature(name="ccmp", code="sub a by a.ccmp1 a.ccmp2;")
    feature.disabled = True
    font.features.append(feature)

    feature = classes.GSFeature(name="liga", code="sub f i by f_i;")
    font.features.append(feature)

    (ufo,) = to_ufos(font, ufo_module=ufo_module, minimal=True)
    assert ufo.features.text == dedent(
        """\
        feature liga {
        sub f i by f_i;
        } liga;
    """
    )


@pytest.fixture
def ufo_with_GDEF(ufo_module):
    ufo = ufo_module.Font()
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
    return ufo, gdef, ufo_module


def test_roundtrip_existing_GDEF(tmpdir, ufo_with_GDEF):
    """Test that an existing GDEF table in UFO is preserved unchanged and
    no extra GDEF table is generated upon roundtripping to UFO when
    `generate_GDEF` is False.
    """
    ufo, gdef, ufo_module = ufo_with_GDEF
    font = to_glyphs([ufo])
    filename = os.path.join(str(tmpdir), "font.glyphs")
    font.save(filename)
    font = classes.GSFont(filename)
    (rtufo,) = to_ufos(font, generate_GDEF=False, ufo_module=ufo_module)

    assert rtufo.features.text == gdef


def test_groups_remain_at_top(tmpdir, ufo_module):
    ufo = ufo_module.Font()
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
    (rtufo,) = to_ufos(font, ufo_module=ufo_module)

    fea_rt = rtufo.features.text
    assert fea_rt.index("@FIG_DFLT") < fea_rt.index("lookup") < fea_rt.index("feature")


def test_roundtrip_empty_feature(ufo_module):
    # https://github.com/googlefonts/glyphsLib/issues/562
    font = to_glyphs([ufo_module.Font()])
    feature = classes.GSFeature(name="dlig")
    feature.code = ""
    font.features.append(feature)

    (ufo,) = to_ufos(font, ufo_module=ufo_module)
    assert ufo.features.text == dedent(
        """\
        feature dlig {

        } dlig;
    """
    )

    font_r = to_glyphs([ufo])
    assert len(font_r.features) == 1
    feature_r = font_r.features[0]
    assert feature_r.name == "dlig"
    assert feature_r.code == ""


def test_build_GDEF_incomplete_glyphOrder():
    import ufoLib2

    font = ufoLib2.Font()
    font.lib["public.glyphOrder"] = ["b", "c"]
    for name in ("d", "c", "b", "a"):
        glyph = font.newGlyph(name)
        glyph.appendAnchor({"name": "top", "x": 0, "y": 0})

    categories = _build_public_opentype_categories(font)
    assert categories == {"a": "base", "b": "base", "c": "base", "d": "base"}


def test_comments_in_classes(ufo_module):
    filename = os.path.join(os.path.dirname(__file__), "../data/CommentedClass.glyphs")
    font = classes.GSFont(filename)
    (ufo,) = to_ufos(font)
    assert ufo.features.text == dedent(
        """\
            @Test = [ A
            # B
            ];
"""
    )


def test_mark_class_used_as_glyph_class(tmpdir, ufo_module):
    ufo = ufo_module.Font()
    ufo.features.text = dedent(
        """\
        markClass CombBreve_Macron <anchor -700 1000> @_U;
        markClass CombGraphemeJoiner <anchor 0 0> @_U;
        @c_u_diacs = @_U;
        """
    )

    font = to_glyphs([ufo], minimize_ufo_diffs=True)

    assert (
        font.featurePrefixes[0].code
        == dedent(
            """\
            markClass CombBreve_Macron <anchor -700 1000> @_U;
            markClass CombGraphemeJoiner <anchor 0 0> @_U;
            """
        ).strip()
    )
    assert font.classes[0].name == "c_u_diacs"
    assert font.classes[0].code == "@_U"

    (rtufo,) = to_ufos(font, ufo_module=ufo_module)

    # After roundtrip glyph classes are always placed before the mark classes
    # hence the following assertion would fail...
    # https://github.com/googlefonts/glyphsLib/issues/694#issuecomment-1117204523
    # assert rtufo.features.text == ufo.features.text


def test_automatic_added_to_manual_kern(tmpdir, ufo_module):
    """Test that when a Glyphs file has a manual kern feature,
    automatic markers are added so that the source kerning also
    gets applied.
    """
    font = classes.GSFont()
    font.masters.append(classes.GSFontMaster())

    (ufo,) = to_ufos(font)

    assert "# Automatic Code" not in ufo.features.text

    kern = classes.GSFeature(name="kern", code="pos a b 100;")
    font.features.append(kern)
    (ufo,) = to_ufos(font)

    assert "# Automatic Code" in ufo.features.text

    designspace = to_designspace(font, ufo_module=ufo_module)
    path = str(tmpdir / "test.designspace")
    designspace.write(path)
    for source in designspace.sources:
        source.font.save(str(tmpdir / source.filename))

    designspace2 = DesignSpaceDocument.fromfile(path)
    font2 = to_glyphs(designspace2, ufo_module=ufo_module)

    assert len([f for f in font2.features if f.name == "kern"]) == 1
