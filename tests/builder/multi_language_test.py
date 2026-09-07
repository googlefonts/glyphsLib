#
# Copyright 2026 Google Inc. All Rights Reserved.
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

import io
from textwrap import dedent

from fontTools.feaLib.parser import Parser

from glyphsLib import classes, to_glyphs, to_ufos
from glyphsLib.builder.multi_language import expand_multi_language_statements

GLYPH_NAMES = ["i", "idotaccent", "Scedilla", "Scommaaccent", "Lcommaaccent"]

LANGUAGE_SYSTEMS = "languagesystem DFLT dflt;\nlanguagesystem latn dflt;\n" + "".join(
    f"languagesystem latn {tag};\n"
    for tag in ("AZE", "CRT", "KAZ", "TAT", "TRK", "ROM", "MOL")
)


def parse(fea):
    """Parse the feature text, raising on anything feaLib does not accept."""
    feature_file = io.StringIO(LANGUAGE_SYSTEMS + fea)
    return Parser(feature_file, glyphNames=GLYPH_NAMES).parse()


def normalize(fea):
    """The text with every kind of line ending written as ``\\n``."""
    return fea.replace("\r\n", "\n").replace("\r", "\n")


# Every shape the expansion has to survive, well formed or not, gathered so
# that the invariants below run over all of them rather than over one example
# each. The individual tests above pin down what each one is expected to do.
AWKWARD_SOURCES = (
    # Well formed, and expanded.
    "feature locl {\nlanguage AZE CRT;\nsub i by idotaccent;\n} locl;\n",
    "feature locl {\nlanguage ROM MOL;\nlookup l {\nsub i by idotaccent;\n} l;\n"
    "@Ced = [Scedilla];\nsub @Ced by Scommaaccent;\n} locl;\n",
    # Line endings feaLib counts but a `\n` split does not.
    "feature locl {\r\nlanguage AZE CRT;\r\nsub i by idotaccent;\r\n} locl;\r\n",
    "feature locl {\rlanguage AZE CRT;\rsub i by idotaccent;\r} locl;\r",
    "feature locl {\nlanguage AZE CRT;\rsub i by idotaccent;\n} locl;\n",
    # Not the shorthand, or not classifiable: left untouched.
    "feature locl {\nlanguage dflt AZE;\nsub i by idotaccent;\n} locl;\n",
    "feature locl {\nlanguage TOOLONGTAG OTHER;\nsub i by idotaccent;\n} locl;\n",
    "feature locl {\nlanguage AZE CRT;\ninclude(other.fea);\n} locl;\n",
    "feature locl {\nlanguage AZE CRT;\nsub $[name] by idotaccent;\n} locl;\n",
    # A missing semicolon, at the end of the code and before a closing brace.
    "feature locl {\nlanguage AZE CRT;\nsub i by idotaccent\n",
    "feature locl {\nlanguage AZE CRT;\nsub i by idotaccent\n} locl;\n\n"
    "feature ccmp {\nsub Scedilla by Scommaaccent;\n} ccmp;\n",
    # Outside any block, where FEA does not allow `language` at all.
    "language AZE CRT;\nsub i by idotaccent;\n\nfeature locl {\n"
    "sub Scedilla by Scommaaccent;\n} locl;\n",
)


def check(source, expected):
    """Expand the source, assert the whole output, then parse it."""
    fea = expand_multi_language_statements(dedent(source))
    assert fea == dedent(expected)
    parse(fea)


def test_bare_rules_are_repeated():
    check(
        """\
        feature locl {
        script latn;
        language ROM MOL;
        sub Scedilla by Scommaaccent;
        } locl;
        """,
        """\
        feature locl {
        script latn;
        language ROM;
        sub Scedilla by Scommaaccent;
        language MOL;
        sub Scedilla by Scommaaccent;
        } locl;
        """,
    )


def test_named_lookup_is_defined_once_and_referenced():
    check(
        """\
        feature locl {
        script latn;
        language AZE CRT KAZ;
        lookup idotaccent {
            sub i by idotaccent;
        } idotaccent;
        } locl;
        """,
        """\
        feature locl {
        script latn;
        language AZE;
        lookup idotaccent {
            sub i by idotaccent;
        } idotaccent;
        language CRT;
        lookup idotaccent;
        language KAZ;
        lookup idotaccent;
        } locl;
        """,
    )


def test_lookup_with_use_extension_is_referenced():
    check(
        """\
        feature locl {
        language AZE CRT;
        lookup idot useExtension {
            sub i by idotaccent;
        } idot;
        } locl;
        """,
        """\
        feature locl {
        language AZE;
        lookup idot useExtension {
            sub i by idotaccent;
        } idot;
        language CRT;
        lookup idot;
        } locl;
        """,
    )


def test_lookup_with_brace_on_the_next_line_is_referenced():
    check(
        """\
        feature locl {
        language AZE CRT;
        lookup idot
        {
            sub i by idotaccent;
        } idot;
        } locl;
        """,
        """\
        feature locl {
        language AZE;
        lookup idot
        {
            sub i by idotaccent;
        } idot;
        language CRT;
        lookup idot;
        } locl;
        """,
    )


def test_glyph_class_is_not_redefined():
    check(
        """\
        feature locl {
        language ROM MOL;
        @Cedillas = [Scedilla];
        sub @Cedillas by Scommaaccent;
        } locl;
        """,
        """\
        feature locl {
        language ROM;
        @Cedillas = [Scedilla];
        sub @Cedillas by Scommaaccent;
        language MOL;
        sub @Cedillas by Scommaaccent;
        } locl;
        """,
    )


def test_multi_line_glyph_class_is_dropped_whole():
    check(
        """\
        feature locl {
        language ROM MOL;
        @Ced = [Scedilla
                Lcommaaccent];
        sub @Ced by Scommaaccent;
        } locl;
        """,
        """\
        feature locl {
        language ROM;
        @Ced = [Scedilla
                Lcommaaccent];
        sub @Ced by Scommaaccent;
        language MOL;
        sub @Ced by Scommaaccent;
        } locl;
        """,
    )


def test_mark_class_is_not_redefined():
    check(
        """\
        feature test {
        language ROM MOL;
        markClass [Scedilla] <anchor 0 0> @MC;
        pos base i <anchor 0 0> mark @MC;
        } test;
        """,
        """\
        feature test {
        language ROM;
        markClass [Scedilla] <anchor 0 0> @MC;
        pos base i <anchor 0 0> mark @MC;
        language MOL;
        pos base i <anchor 0 0> mark @MC;
        } test;
        """,
    )


def test_closing_brace_in_a_comment_does_not_truncate_the_body():
    """It would otherwise bind the rules to the last tag only.

    And parse cleanly while doing so. The comment itself is not a statement,
    so it stays where the author put it instead of being repeated.
    """
    check(
        """\
        feature locl {
        language AZE CRT;
        # see the } sign
        sub i by idotaccent;
        } locl;
        """,
        """\
        feature locl {
        language AZE;
        # see the } sign
        sub i by idotaccent;
        language CRT;
        sub i by idotaccent;
        } locl;
        """,
    )


def test_opening_brace_in_a_comment_does_not_swallow_the_closing_brace():
    check(
        """\
        feature locl {
        language AZE CRT;
        # an opening { sign
        sub i by idotaccent;
        } locl;
        """,
        """\
        feature locl {
        language AZE;
        # an opening { sign
        sub i by idotaccent;
        language CRT;
        sub i by idotaccent;
        } locl;
        """,
    )


def test_trailing_comment_on_a_delimiter_ends_the_body():
    check(
        """\
        feature locl {
        language AZE CRT;
        sub i by idotaccent;
        language TRK; # Turkish
        sub Scedilla by Scommaaccent;
        } locl;
        """,
        """\
        feature locl {
        language AZE;
        sub i by idotaccent;
        language CRT;
        sub i by idotaccent;
        language TRK; # Turkish
        sub Scedilla by Scommaaccent;
        } locl;
        """,
    )


def test_trailing_comment_on_the_statement_is_kept():
    check(
        """\
        feature locl {
        script latn;
        language AZE CRT; # Turkic
        sub i by idotaccent;
        } locl;
        """,
        """\
        feature locl {
        script latn;
        language AZE; # Turkic
        sub i by idotaccent;
        language CRT;
        sub i by idotaccent;
        } locl;
        """,
    )


def test_keywords_are_kept_on_every_tag():
    check(
        """\
        feature locl {
        script latn;
        language ROM MOL exclude_dflt;
        sub Scedilla by Scommaaccent;
        } locl;
        """,
        """\
        feature locl {
        script latn;
        language ROM exclude_dflt;
        sub Scedilla by Scommaaccent;
        language MOL exclude_dflt;
        sub Scedilla by Scommaaccent;
        } locl;
        """,
    )


def test_single_tag_is_untouched():
    original = "script latn;\nlanguage TRK;\nsub i by idotaccent;\n"

    assert expand_multi_language_statements(original) == original


def test_unparseable_statement_is_untouched():
    """Leave it for feaLib to report rather than guess at it."""
    original = "language TOOLONGTAG OTHER;\nsub i by idotaccent;\n"

    assert expand_multi_language_statements(original) == original


def test_statement_sharing_the_line_with_the_shorthand_is_expanded():
    check(
        """\
        feature locl {
        script latn;
        language AZE CRT; sub i by idotaccent;
        } locl;
        """,
        """\
        feature locl {
        script latn;
        language AZE; sub i by idotaccent;
        language CRT;
        sub i by idotaccent;
        } locl;
        """,
    )


def test_lookup_closed_on_one_line_does_not_swallow_what_follows():
    """The braces open and close within the line.

    A line-wise nesting depth therefore never rises above zero, and the lookup
    used to be taken as running to the end of the scope -- dropping the rule
    after it from every repeat.
    """
    check(
        """\
        feature locl {
        script latn;
        language AZE CRT;
        lookup idot { sub i by idotaccent; } idot;
        sub Scedilla by Scommaaccent;
        } locl;
        """,
        """\
        feature locl {
        script latn;
        language AZE;
        lookup idot { sub i by idotaccent; } idot;
        sub Scedilla by Scommaaccent;
        language CRT;
        lookup idot;
        sub Scedilla by Scommaaccent;
        } locl;
        """,
    )


def test_definition_sharing_a_line_with_a_rule_replays_the_rule():
    """The whole line used to count as one definition.

    The rule on it was dropped from the repeats instead of being replayed.
    """
    check(
        """\
        feature locl {
        script latn;
        language AZE CRT;
        @Ced = [Scedilla]; sub @Ced by Scommaaccent;
        } locl;
        """,
        """\
        feature locl {
        script latn;
        language AZE;
        @Ced = [Scedilla]; sub @Ced by Scommaaccent;
        language CRT;
        sub @Ced by Scommaaccent;
        } locl;
        """,
    )


def test_line_break_after_lookup_keyword_is_still_a_definition():
    """A definition broken after the keyword used to go unrecognised.

    It was then repeated whole, which redefines the lookup.
    """
    check(
        """\
        feature locl {
        script latn;
        language AZE CRT;
        lookup
          idot { sub i by idotaccent; } idot;
        } locl;
        """,
        """\
        feature locl {
        script latn;
        language AZE;
        lookup
          idot { sub i by idotaccent; } idot;
        language CRT;
        lookup idot;
        } locl;
        """,
    )


def test_tab_indentation_survives_the_replay():
    """Statements are sliced out of the original by offset.

    The offsets come from feaLib's line/column locations. Glyphs indents
    feature code with tabs, so this pins down that a tab counts as one column
    and the slices do not drift.
    """
    check(
        "feature locl {\nscript latn;\nlanguage AZE CRT;\n"
        "\tsub i by idotaccent;\n} locl;\n",
        "feature locl {\nscript latn;\nlanguage AZE;\n"
        "\tsub i by idotaccent;\nlanguage CRT;\n"
        "sub i by idotaccent;\n} locl;\n",
    )


def test_include_in_the_scope_leaves_the_shorthand_alone():
    """An include cannot be replayed, because its contents are not visible.

    The shorthand is invalid FEA, so leaving it alone makes feaLib report it
    rather than glyphsLib emitting a silently wrong language mapping.
    """
    original = dedent("""\
        feature locl {
        language AZE CRT;
        include(other.fea);
        sub i by idotaccent;
        } locl;
        """)

    assert expand_multi_language_statements(original) == original


def test_dflt_alongside_other_tags_is_left_alone():
    """`dflt` has to be specified alone, so this is not the shorthand.

    Glyphs rejects it as well -- 4.0.1 (4004) and 3.4.1 both report
    `Expected ";" after language statement`. Expanding it would compile, but
    `language AZE;` implies `include_dflt`, so AZE would end up with the
    substitution twice: once inherited from `dflt` and once replayed, as two
    distinct lookups with identical content.
    """
    original = dedent("""\
        feature locl {
        script latn;
        language dflt AZE;
        sub i by idotaccent;
        } locl;
        """)

    assert expand_multi_language_statements(original) == original


def test_statement_without_a_semicolon_is_left_alone():
    """A missing semicolon leaves no way to tell where a statement stops.

    The scan would run to the end of the token stream and slice the first copy
    off mid-token. The code is invalid FEA either way, so it is handed to
    feaLib as it stands.
    """
    original = dedent("""\
        feature locl {
        language AZE CRT;
        sub i by idotaccent
        """)

    assert expand_multi_language_statements(original) == original


def test_statement_without_a_semicolon_does_not_escape_the_block():
    """The scan must not walk out through the brace that closes the block.

    Looking for the next semicolon regardless of depth would find the one
    ending `} locl;`, and the replay would then repeat the whole `ccmp`
    feature that follows.
    """
    original = dedent("""\
        feature locl {
        language AZE CRT;
        sub i by idotaccent
        } locl;

        feature ccmp {
        sub Scedilla by Scommaaccent;
        } ccmp;
        """)

    assert expand_multi_language_statements(original) == original


def test_shorthand_outside_a_block_is_left_alone():
    """FEA only allows `language` inside a feature block.

    Such a statement is invalid wherever it came from, and its scope has no
    enclosing brace to end at, so replaying it would swallow the block that
    follows.
    """
    original = dedent("""\
        language AZE CRT;
        sub i by idotaccent;

        feature locl {
        sub Scedilla by Scommaaccent;
        } locl;
        """)

    assert expand_multi_language_statements(original) == original


def test_glyphs_4_output_matches_what_glyphs_3_wrote():
    """The same source, saved by both versions, ends up as the same FEA.

    Modelled on a production source opened and saved in Glyphs 4: the
    automatic `locl` code nobody edited came back with the shorthand where
    Glyphs 3 had written one statement per tag. Expanding what Glyphs 4 saved
    gives back what Glyphs 3 saved, tabs and blank line included.
    """
    glyphs_4 = (
        "feature locl {\n"
        "script latn;\n"
        "language AZE CRT KAZ TAT TRK;\n"
        "lookup locl_latn_0 {\n"
        "\tsub i by idotaccent;\n"
        "} locl_latn_0;\n"
        "\n"
        "script latn;\n"
        "language ROM MOL;\n"
        "lookup locl_latn_1 {\n"
        "\tsub Scedilla by Scommaaccent;\n"
        "} locl_latn_1;\n"
        "} locl;\n"
    )
    glyphs_3 = (
        "feature locl {\n"
        "script latn;\n"
        "language AZE;\n"
        "lookup locl_latn_0 {\n"
        "\tsub i by idotaccent;\n"
        "} locl_latn_0;\n"
        "language CRT;\n"
        "lookup locl_latn_0;\n"
        "language KAZ;\n"
        "lookup locl_latn_0;\n"
        "language TAT;\n"
        "lookup locl_latn_0;\n"
        "language TRK;\n"
        "lookup locl_latn_0;\n"
        "\n"
        "script latn;\n"
        "language ROM;\n"
        "lookup locl_latn_1 {\n"
        "\tsub Scedilla by Scommaaccent;\n"
        "} locl_latn_1;\n"
        "language MOL;\n"
        "lookup locl_latn_1;\n"
        "} locl;\n"
    )

    assert expand_multi_language_statements(glyphs_4) == glyphs_3
    parse(glyphs_3)


def test_shorthand_inside_a_lookup_block_repeats_the_rules():
    """Glyphs also writes the language statements inside the lookup block.

    The scope then ends at the block's own closing brace, and the rules are
    repeated where a reference would be wrong -- the lookup is the thing being
    defined. The single-tag form here is what Glyphs 3 wrote for a production
    source; the shorthand is that form collapsed by hand, since this is not a
    shape Glyphs 4 has been seen to emit.
    """
    glyphs_4 = (
        "feature locl {\n"
        "lookup locl_latn_0 {\n"
        "\tscript latn;\n"
        "\tlanguage AZE CRT KAZ;\n"
        "\tsub i by idotaccent;\n"
        "} locl_latn_0;\n"
        "} locl;\n"
    )
    glyphs_3 = (
        "feature locl {\n"
        "lookup locl_latn_0 {\n"
        "\tscript latn;\n"
        "\tlanguage AZE;\n"
        "\tsub i by idotaccent;\n"
        "\tlanguage CRT;\n"
        "\tsub i by idotaccent;\n"
        "\tlanguage KAZ;\n"
        "\tsub i by idotaccent;\n"
        "} locl_latn_0;\n"
        "} locl;\n"
    )

    assert expand_multi_language_statements(glyphs_4) == glyphs_3
    parse(glyphs_3)


def test_crlf_line_endings_do_not_shift_the_slices():
    """Offsets come from feaLib's line/column locations.

    feaLib counts a ``\r\n`` as one line ending, so the replayed slices have to
    stay in step with it on Windows-authored feature code.
    """
    source = (
        "feature locl {\r\nlanguage AZE CRT;\r\nsub i by idotaccent;\r\n} locl;\r\n"
    )

    assert expand_multi_language_statements(source) == (
        "feature locl {\r\nlanguage AZE;\r\nsub i by idotaccent;\n"
        "language CRT;\nsub i by idotaccent;\r\n} locl;\r\n"
    )


def test_lone_carriage_return_does_not_shift_the_slices():
    """feaLib ends a line at a bare ``\r`` too, not only at ``\r\n``.

    Counting lines by splitting on ``\n`` alone would leave every offset after
    the first carriage return one short per line, and since the emitted text
    is sliced out of the source by offset, the replay would silently lose the
    rules while still reading as valid FEA.
    """
    source = "feature locl {\rlanguage AZE CRT;\rsub i by idotaccent;\r} locl;\r"

    assert expand_multi_language_statements(source) == (
        "feature locl {\rlanguage AZE;\rsub i by idotaccent;\n"
        "language CRT;\nsub i by idotaccent;\r} locl;\r"
    )


def test_line_endings_do_not_change_what_is_expanded():
    """The same code expands the same way whichever line ending it uses.

    The replays are emitted with ``\n`` whatever went in, so the comparison is
    on the normalised text; what must not differ is which rules end up under
    which tag.
    """
    source = dedent("""\
        feature locl {
        script latn;
        language AZE CRT;
        lookup idotaccent {
            sub i by idotaccent;
        } idotaccent;
        sub Scedilla by Scommaaccent;
        } locl;
        """)
    expected = normalize(expand_multi_language_statements(source))

    for line_ending in ("\r\n", "\r"):
        rewritten = source.replace("\n", line_ending)

        assert normalize(expand_multi_language_statements(rewritten)) == expected


def test_code_that_does_not_lex_is_left_alone():
    """Feature text still holding Glyphs tokens cannot be classified.

    ``PassThruExpander`` leaves ``$[...]`` in place, and feaLib's lexer stops
    at the ``$``. Leaving the text untouched keeps the failure with feaLib
    rather than guessing at what the token stands for.
    """
    original = "language AZE CRT;\nsub $[name] by idotaccent;\n"

    assert expand_multi_language_statements(original) == original


def test_expanding_twice_changes_nothing():
    """The output holds one tag per statement, so a second pass is a no-op."""
    once = expand_multi_language_statements(dedent("""\
            feature locl {
            script latn;
            language AZE CRT;
            lookup idot {
                sub i by idotaccent;
            } idot;
            } locl;
            """))

    assert expand_multi_language_statements(once) == once


def make_font():
    font = classes.GSFont()
    font.masters.append(classes.GSFontMaster())
    for name in ("i", "idotaccent"):
        glyph = classes.GSGlyph(name)
        glyph.layers.append(classes.GSLayer())
        glyph.layers[0].layerId = font.masters[0].id
        font.glyphs.append(glyph)

    prefix = classes.GSFeaturePrefix()
    prefix.name = "Languagesystems"
    prefix.code = "languagesystem latn AZE;\nlanguagesystem latn TRK;"
    font.featurePrefixes.append(prefix)

    feature = classes.GSFeature("locl")
    feature.code = dedent("""\
        script latn;
        language AZE TRK;
        lookup idotaccent {
            sub i by idotaccent;
        } idotaccent;""")
    font.features.append(feature)
    return font


def test_output_is_the_input_or_valid_fea():
    """The invariant the whole module rests on.

    Either a source is left exactly as it was, for feaLib to report, or what
    comes back compiles. Anything in between -- text sliced mid-token, a block
    replayed past its closing brace -- is the failure mode worth guarding
    against as a class, rather than one example at a time.
    """
    for source in AWKWARD_SOURCES:
        expanded = expand_multi_language_statements(source)
        if expanded == source:
            continue
        parse(expanded)


def test_expanding_anything_twice_changes_nothing():
    """The output holds one tag per statement, so a second pass is a no-op."""
    for source in AWKWARD_SOURCES:
        once = expand_multi_language_statements(source)

        assert expand_multi_language_statements(once) == once


def test_to_ufos_expands_feature_code(ufo_module):
    (ufo,) = to_ufos(make_font(), ufo_module=ufo_module)

    assert ufo.features.text == dedent("""\
        # Prefix: Languagesystems
        languagesystem latn AZE;
        languagesystem latn TRK;

        feature locl {
        script latn;
        language AZE;
        lookup idotaccent {
            sub i by idotaccent;
        } idotaccent;
        language TRK;
        lookup idotaccent;
        } locl;
        """)
    Parser(io.StringIO(ufo.features.text), glyphNames=GLYPH_NAMES).parse()


def test_conditional_block_is_resolved_before_the_expansion(ufo_module):
    """`#ifndef VARIABLE` blocks are stripped before the shorthand is expanded.

    The markers are comments, so they are not statements and are not replayed.
    Expanding first would therefore put the repeats *inside* the block -- the
    strip that follows would then take the second `language` statement with it
    and leave the rules bound to the first tag alone.
    """
    font = make_font()
    font.features[0].code = dedent("""\
        script latn;
        language AZE TRK;
        #ifndef VARIABLE
        sub i by idotaccent;
        #endif""")

    (ufo,) = to_ufos(font, ufo_module=ufo_module)

    assert ufo.features.text.endswith(dedent("""\
            feature locl {
            script latn;
            language AZE;
            language TRK;
            } locl;
            """))


def test_expansion_does_not_round_trip(ufo_module):
    """The expansion is one-way: the shorthand is not restored.

    Going back to Glyphs yields the expanded form rather than the original
    statement. UFO -> Glyphs -> UFO is unaffected, because the original
    feature text is recovered from ORIGINAL_FEATURE_CODE_KEY.
    """
    (ufo,) = to_ufos(make_font(), ufo_module=ufo_module)

    (feature,) = to_glyphs([ufo]).features
    assert feature.code == dedent("""\
        script latn;
        language AZE;
        lookup idotaccent {
            sub i by idotaccent;
        } idotaccent;
        language TRK;
        lookup idotaccent;""")
