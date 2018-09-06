# Copyright 2015 Google Inc. All Rights Reserved.
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

import re
from textwrap import dedent

from fontTools.misc.py23 import round, unicode
from fontTools.misc.py23 import StringIO

from fontTools.feaLib import ast, parser

import re

import glyphsLib
from .constants import GLYPHLIB_PREFIX, PUBLIC_PREFIX


ANONYMOUS_FEATURE_PREFIX_NAME = "<anonymous>"
ORIGINAL_FEATURE_CODE_KEY = GLYPHLIB_PREFIX + "originalFeatureCode"


def autostr(automatic):
    return "# automatic\n" if automatic else ""


def to_ufo_features(self):
    for master_id, source in self._sources.items():
        master = self.font.masters[master_id]
        _to_ufo_features(self, master, source.font)


def _to_ufo_features(self, master, ufo):
    """Write an UFO's OpenType feature file."""

    # Recover the original feature code if it was stored in the user data
    original = master.userData[ORIGINAL_FEATURE_CODE_KEY]
    if original is not None:
        ufo.features.text = original
        return

    prefixes = []
    for prefix in self.font.featurePrefixes:
        strings = []
        if prefix.name != ANONYMOUS_FEATURE_PREFIX_NAME:
            strings.append("# Prefix: %s\n" % prefix.name)
        strings.append(autostr(prefix.automatic))
        strings.append(prefix.code)
        prefixes.append("".join(strings))

    prefix_str = "\n\n".join(prefixes)

    class_defs = []
    for class_ in self.font.classes:
        prefix = "@" if not class_.name.startswith("@") else ""
        name = prefix + class_.name
        class_defs.append(
            "{}{} = [ {} ];".format(autostr(class_.automatic), name, class_.code)
        )
    class_str = "\n\n".join(class_defs)

    feature_defs = []
    for feature in self.font.features:
        code = feature.code
        lines = ["feature %s {" % feature.name]
        if feature.notes:
            lines.append("# notes:")
            lines.extend("# " + line for line in feature.notes.splitlines())
        if feature.automatic:
            lines.append("# automatic")
        if feature.disabled:
            lines.append("# disabled")
            lines.extend("#" + line for line in code.splitlines())
        else:
            lines.append(code)
        lines.append("} %s;" % feature.name)
        feature_defs.append("\n".join(lines))
    fea_str = "\n\n".join(feature_defs)

    # Don't add a GDEF when planning to round-trip
    gdef_str = None
    if not self.minimize_glyphs_diffs:
        gdef_str = _build_gdef(ufo)

    # make sure feature text is a unicode string, for defcon
    full_text = (
        "\n\n".join(filter(None, [prefix_str, class_str, fea_str, gdef_str])) + "\n"
    )
    ufo.features.text = full_text if full_text.strip() else ""


def _build_gdef(ufo):
    """Build a table GDEF statement for ligature carets."""
    from glyphsLib import glyphdata  # Expensive import

    bases, ligatures, marks, carets = set(), set(), set(), {}
    category_key = GLYPHLIB_PREFIX + "category"
    subCategory_key = GLYPHLIB_PREFIX + "subCategory"
    for glyph in ufo:
        has_attaching_anchor = False
        for anchor in glyph.anchors:
            name = anchor.name
            if name and not name.startswith("_"):
                has_attaching_anchor = True
            if name and name.startswith("caret_") and "x" in anchor:
                carets.setdefault(glyph.name, []).append(round(anchor["x"]))
        lib = glyph.lib
        glyphinfo = glyphdata.get_glyph(glyph.name)
        # first check glyph.lib for category/subCategory overrides; else use
        # global values from GlyphData
        category = lib.get(category_key)
        if category is None:
            category = glyphinfo.category
        subCategory = lib.get(subCategory_key)
        if subCategory is None:
            subCategory = glyphinfo.subCategory

        # Glyphs.app assigns glyph classes like this:
        #
        # * Base: any glyph that has an attaching anchor
        #   (such as "top"; "_top" does not count) and is neither
        #   classified as Ligature nor Mark using the definitions below;
        #
        # * Ligature: if subCategory is "Ligature" and the glyph has
        #   at least one attaching anchor;
        #
        # * Mark: if category is "Mark" and subCategory is either
        #   "Nonspacing" or "Spacing Combining";
        #
        # * Compound: never assigned by Glyphs.app.
        #
        # https://github.com/googlei18n/glyphsLib/issues/85
        # https://github.com/googlei18n/glyphsLib/pull/100#issuecomment-275430289
        if subCategory == "Ligature" and has_attaching_anchor:
            ligatures.add(glyph.name)
        elif category == "Mark" and (
            subCategory == "Nonspacing" or subCategory == "Spacing Combining"
        ):
            marks.add(glyph.name)
        elif has_attaching_anchor:
            bases.add(glyph.name)
    if not any((bases, ligatures, marks, carets)):
        return None
    lines = ["table GDEF {", "  # automatic"]
    glyphOrder = ufo.lib[PUBLIC_PREFIX + "glyphOrder"]
    glyphIndex = lambda glyph: glyphOrder.index(glyph)
    fmt = lambda g: ("[%s]" % " ".join(sorted(g, key=glyphIndex))) if g else ""
    lines.extend(
        [
            "  GlyphClassDef",
            "    %s, # Base" % fmt(bases),
            "    %s, # Liga" % fmt(ligatures),
            "    %s, # Mark" % fmt(marks),
            "    ;",
        ]
    )
    for glyph, caretPos in sorted(carets.items()):
        lines.append(
            "  LigatureCaretByPos %s %s;"
            % (glyph, " ".join(unicode(p) for p in sorted(caretPos)))
        )
    lines.append("} GDEF;")
    return "\n".join(lines)


def replace_feature(tag, repl, features):
    if not repl.endswith("\n"):
        repl += "\n"
    return re.sub(
        r"(?<=^feature {tag} {{\n)(.*?)(?=^}} {tag};$)".format(tag=tag),
        repl,
        features,
        count=1,
        flags=re.DOTALL | re.MULTILINE,
    )


def to_glyphs_features(self):
    if not self.designspace.sources:
        # Needs at least one UFO
        return

    # Handle differing feature files between input UFOs
    # For now: switch to very simple strategy if there is any difference
    # TODO: (jany) later, use a merge-as-we-go strategy where all discovered
    #   features go into the GSFont's features, and custom parameters are used
    #   to disable features on masters that didn't have them originally.
    if _features_are_different_across_ufos(self):
        if self.minimize_ufo_diffs:
            self.logger.warning(
                "Feature files are different across UFOs. The produced Glyphs "
                "file will have no editable features."
            )
            # Do all UFOs, not only the first one
            _to_glyphs_features_basic(self)
            return
        self.logger.warning(
            "Feature files are different across UFOs. The produced Glyphs "
            "file will reflect only the features of the first UFO."
        )

    # Split the feature file of the first UFO into GSFeatures
    ufo = self.designspace.sources[0].font
    if ufo.features.text is None:
        return
    document = FeaDocument(ufo.features.text, ufo.keys())
    processor = FeatureFileProcessor(document, self.glyphs_module)
    processor.to_glyphs(self.font)


def _features_are_different_across_ufos(self):
    # FIXME: requires that features are in the same order in all feature files;
    #   the only allowed differences are whitespace
    reference = self.designspace.sources[0].font.features.text or ""
    reference = _normalize_whitespace(reference)
    for source in self.designspace.sources[1:]:
        other = _normalize_whitespace(source.font.features.text or "")
        if reference != other:
            return True
    return False


def _normalize_whitespace(text):
    # FIXME: does not take into account "significant" whitespace like
    # whitespace in a UI string
    return re.sub(r"\s+", " ", text)


def _to_glyphs_features_basic(self):
    prefix = self.glyphs_module.GSFeaturePrefix()
    prefix.name = "WARNING"
    prefix.code = dedent(
        """\
        # Do not use Glyphs to edit features.
        #
        # This Glyphs file was made from several UFOs that had different
        # features. As a result, the features are not editable in Glyphs and
        # the original features will be restored when you go back to UFOs.
    """
    )
    self.font.featurePrefixes.append(prefix)
    for master_id, source in self._sources.items():
        master = self.font.masters[master_id]
        master.userData[ORIGINAL_FEATURE_CODE_KEY] = source.font.features.text


class FeaDocument(object):
    """Parse the string of a fea code into statements."""

    def __init__(self, text, glyph_set):
        feature_file = StringIO(text)
        parser_ = parser.Parser(feature_file, glyph_set, followIncludes=False)
        self._doc = parser_.parse()
        self.statements = self._doc.statements
        self._lines = text.splitlines(True)  # keepends=True
        self._build_end_locations()

    def text(self, statements):
        """Recover the original fea code of the given statements from the
        given block.
        """
        return "".join(self._statement_text(st) for st in statements)

    def _statement_text(self, statement):
        _, begin_line, begin_char = statement.location
        _, end_line, end_char = statement.end_location
        lines = self._lines[begin_line - 1 : end_line]
        if lines:
            # In case it's the same line, we need to trim the end first
            lines[-1] = lines[-1][:end_char]
            lines[0] = lines[0][begin_char - 1 :]
        return "".join(lines)

    def _build_end_locations(self):
        # The statements in the ast only have their start location, but we also
        # need the end location to find the text in between.
        # FIXME: (jany) maybe feaLib could provide that?
        # Add a fake statement at the end, it's the only one that won't get
        # a proper end_location, but its presence will help compute the
        # end_location of the real last statement(s).
        self._lines.append("#")  # Line corresponding to the fake statement
        fake_location = (None, len(self._lines), 1)
        self._doc.statements.append(
            ast.Comment(text="Sentinel", location=fake_location)
        )
        self._build_end_locations_rec(self._doc)
        # Remove the fake last statement
        self._lines.pop()
        self._doc.statements.pop()

    def _build_end_locations_rec(self, block):
        # To get the end location, we do a depth-first exploration of the ast:
        # When a new statement starts, it means that the previous one ended.
        # When a new statement starts outside of the current block, we must
        # remove the "end-of-block" string from the previous inner statement.
        previous = None
        previous_in_block = None
        for st in block.statements:
            if hasattr(st, "statements"):
                self._build_end_locations_rec(st)
            if previous is not None:
                _, line, char = st.location
                line, char = self._previous_char(line, char)
                previous.end_location = (None, line, char)
            if previous_in_block is not None:
                previous_in_block.end_location = self._in_block_end_location(previous)
                previous_in_block = None
            previous = st
            if hasattr(st, "statements"):
                previous_in_block = st.statements[-1]

    WHITESPACE_RE = re.compile("\\s")
    WHITESPACE_OR_NAME_RE = re.compile("\\w|\\s")

    def _previous_char(self, line, char):
        char -= 1
        while char == 0:
            line -= 1
            char = len(self._lines[line - 1])
        return (line, char)

    def _in_block_end_location(self, block):
        _, line, char = block.end_location

        def current_char(line, char):
            return self._lines[line - 1][char - 1]

        # Find the semicolon
        while current_char(line, char) != ";":
            assert self.WHITESPACE_RE.match(current_char(line, char))
            line, char = self._previous_char(line, char)
        # Skip it
        line, char = self._previous_char(line, char)
        # Skip the whitespace and table/feature name
        while self.WHITESPACE_OR_NAME_RE.match(current_char(line, char)):
            line, char = self._previous_char(line, char)
        # It should be the closing bracket
        assert current_char(line, char) == "}"
        # Skip it and we're done
        line, char = self._previous_char(line, char)

        return (None, line, char)


class PeekableIterator(object):
    """Helper class to iterate and peek over a list."""

    def __init__(self, list):
        self.index = 0
        self.list = list

    def has_next(self, n=0):
        return (self.index + n) < len(self.list)

    def next(self):
        res = self.list[self.index]
        self.index += 1
        return res

    def peek(self, n=0):
        return self.list[self.index + n]


class FeatureFileProcessor(object):
    """Put fea statements into the correct fields of a GSFont."""

    def __init__(self, doc, glyphs_module):
        self.doc = doc
        self.glyphs_module = glyphs_module
        self.statements = PeekableIterator(doc.statements)
        self._font = None

    def to_glyphs(self, font):
        self._font = font
        self._font
        self._process_file()

    PREFIX_RE = re.compile("^# Prefix: (.*)$")
    AUTOMATIC_RE = re.compile("^# automatic$")
    DISABLED_RE = re.compile("^# disabled$")
    NOTES_RE = re.compile("^# notes:$")

    def _process_file(self):
        unhandled_root_elements = []
        while self.statements.has_next():
            if (
                self._process_prefix()
                or self._process_glyph_class_definition()
                or self._process_feature_block()
                or self._process_gdef_table_block()
            ):
                # Flush any unhandled root elements into an anonymous prefix
                if unhandled_root_elements:
                    prefix = self.glyphs_module.GSFeaturePrefix()
                    prefix.name = ANONYMOUS_FEATURE_PREFIX_NAME
                    prefix.code = self._rstrip_newlines(
                        self.doc.text(unhandled_root_elements)
                    )
                    self._font.featurePrefixes.append(prefix)
                    unhandled_root_elements.clear()
            else:
                # FIXME: (jany) Maybe print warning about unhandled fea block?
                unhandled_root_elements.append(self.statements.peek())
                self.statements.next()
        # Flush any unhandled root elements into an anonymous prefix
        if unhandled_root_elements:
            prefix = self.glyphs_module.GSFeaturePrefix()
            prefix.name = ANONYMOUS_FEATURE_PREFIX_NAME
            prefix.code = self._rstrip_newlines(self.doc.text(unhandled_root_elements))
            self._font.featurePrefixes.append(prefix)

    def _process_prefix(self):
        st = self.statements.peek()
        if not isinstance(st, ast.Comment):
            return False
        match = self.PREFIX_RE.match(st.text)
        if not match:
            return False
        self.statements.next()

        # Consume statements that are part of the feature prefix
        prefix_statements = []
        while self.statements.has_next():
            st = self.statements.peek()
            # Don't consume statements that are treated specially
            if isinstance(
                st, (ast.GlyphClassDefinition, ast.FeatureBlock, ast.TableBlock)
            ):
                break
            # Don't comsume a comment if it is the start of another prefix...
            if isinstance(st, ast.Comment):
                if self.PREFIX_RE.match(st.text):
                    break
                # ...or if it is the "automatic" comment just before a class
                if self.statements.has_next(1):
                    next_st = self.statements.peek(1)
                    if self.AUTOMATIC_RE.match(st.text) and isinstance(
                        next_st, ast.GlyphClassDefinition
                    ):
                        break
            prefix_statements.append(st)
            self.statements.next()

        prefix = self.glyphs_module.GSFeaturePrefix()
        prefix.name = match.group(1)
        automatic, prefix_statements = self._pop_comment(
            prefix_statements, self.AUTOMATIC_RE
        )
        prefix.automatic = bool(automatic)
        prefix.code = self._rstrip_newlines(self.doc.text(prefix_statements), 2)
        self._font.featurePrefixes.append(prefix)
        return True

    def _process_glyph_class_definition(self):
        automatic = False
        st = self.statements.peek()
        if isinstance(st, ast.Comment):
            if self.AUTOMATIC_RE.match(st.text):
                automatic = True
                st = self.statements.peek(1)
            else:
                return False
        if not isinstance(st, ast.GlyphClassDefinition):
            return False
        if automatic:
            self.statements.next()
        self.statements.next()
        glyph_class = self.glyphs_module.GSClass()
        glyph_class.name = st.name
        # Call st.glyphs.asFea() because it updates the 'original' field
        # However, we don't use the result of `asFea` because it expands
        # classes in a strange way
        # FIXME: (jany) maybe open an issue if feaLib?
        st.glyphs.asFea()
        elements = []
        try:
            if st.glyphs.original:
                for glyph in st.glyphs.original:
                    try:
                        # Class name (GlyphClassName object)
                        elements.append("@" + glyph.glyphclass.name)
                    except AttributeError:
                        try:
                            # Class name (GlyphClassDefinition object)
                            # FIXME: (jany) why not always the same type?
                            elements.append("@" + glyph.name)
                        except AttributeError:
                            # Glyph name
                            elements.append(glyph)
            else:
                elements = st.glyphSet()
        except AttributeError:
            # Single class
            elements.append("@" + st.glyphs.glyphclass.name)
        glyph_class.code = " ".join(elements)
        glyph_class.automatic = bool(automatic)
        self._font.classes.append(glyph_class)
        return True

    def _process_feature_block(self):
        st = self.statements.peek()
        if not isinstance(st, ast.FeatureBlock):
            return False
        self.statements.next()
        contents = st.statements
        automatic, contents = self._pop_comment(contents, self.AUTOMATIC_RE)
        disabled, disabled_text, contents = self._pop_comment_block(
            contents, self.DISABLED_RE
        )
        notes, notes_text, contents = self._pop_comment_block(contents, self.NOTES_RE)
        feature = self.glyphs_module.GSFeature()
        feature.name = st.name
        feature.automatic = bool(automatic)
        if notes:
            feature.notes = notes_text
        if disabled:
            feature.code = disabled_text
            feature.disabled = True
            # FIXME: (jany) check that the user has not added more new code
            #    after the disabled comment. Maybe start by checking whether
            #    the block is only made of comments
        else:
            feature.code = self._rstrip_newlines(self.doc.text(contents))
        self._font.features.append(feature)
        return True

    def _process_gdef_table_block(self):
        st = self.statements.peek()
        if not isinstance(st, ast.TableBlock) or st.name != "GDEF":
            return False
        # TODO: read an existing GDEF table and do something with it?
        # For now, this function returns False to say that it has not handled
        # the GDEF table, so it will be stored in Glyphs as a prefix with other
        # "unhandled root elements".
        return False

    def _pop_comment(self, statements, comment_re):
        """Look for the comment that matches the given regex.
        If it matches, return the regex match object and list of statements
        without the special one.
        """
        res = []
        match = None
        for st in statements:
            if match or not isinstance(st, ast.Comment):
                res.append(st)
                continue
            match = comment_re.match(st.text)
            if not match:
                res.append(st)
        return (match, res)

    def _pop_comment_block(self, statements, header_re):
        """Look for a series of comments that start with one that matches the
        regex. If the first comment is found, all subsequent comments are
        popped from statements, concatenated and dedented and returned.
        """
        res = []
        comments = []
        match = None
        st_iter = iter(statements)
        # Look for the header
        for st in st_iter:
            if isinstance(st, ast.Comment):
                match = header_re.match(st.text)
                if match:
                    # Drop this comment an move on to consuming the block
                    break
                else:
                    res.append(st)
            else:
                res.append(st)
        # Consume consecutive comments
        for st in st_iter:
            if isinstance(st, ast.Comment):
                comments.append(st)
            else:
                # The block is over, keep the rest of the statements
                res.append(st)
                break
        # Keep the rest of the statements
        res.extend(list(st_iter))
        # Inside the comment block, drop the pound sign and any common indent
        return (match, dedent("".join(c.text[1:] + "\n" for c in comments)), res)

    # Strip up to the given number of newlines from the right end of the string
    def _rstrip_newlines(self, string, number=1):
        for i in range(number):
            if string and string[-1] == "\n":
                string = string[:-1]
        return string
