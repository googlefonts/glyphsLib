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

"""Expand Glyphs' multiple languages syntax into plain FEA.

Glyphs lets a single ``language`` statement carry several tags and applies
everything that follows to each of them::

    language AZE CRT KAZ TAT TRK;
    lookup idotaccent {
        sub i by idotaccent;
    } idotaccent;

The FEA spec allows exactly one tag per statement, so feaLib rejects this with
``Expected ';'`` at the second tag. See
https://handbook.glyphsapp.com/layout/multiple-languages-syntax/,
https://github.com/googlefonts/glyphsLib/issues/1109 and, for the extension
written up as a spec proposal,
https://github.com/adobe-type-tools/feature_file_workshops/pull/8.

The scan runs on feaLib's own ``Lexer`` rather than on the text, because FEA
treats a line ending as ordinary whitespace: statements may share a line or
span several, and a brace or a semicolon inside a comment or a string is not
code. Tokenizing is what tells the three apart.
"""

import collections
import logging
import re

from fontTools.feaLib.error import FeatureLibError
from fontTools.feaLib.lexer import Lexer

logger = logging.getLogger(__name__)

# Keywords the FEA spec allows after the tag of a `language` statement.
_LANGUAGE_KEYWORDS = frozenset(("exclude_dflt", "include_dflt", "required"))

# A `language` or `script` statement closes the block opened by the previous one.
_BLOCK_DELIMITERS = frozenset(("language", "script"))

# An OpenType language system tag. Unlike a feature tag it may be shorter than
# four characters (`ROM`, `AZE`).
_TAG_LENGTH = 4

# What a statement inside the shorthand's scope is, and what happens to it when
# the scope is replayed for the second and every further tag:
#
#   _LOOKUP      `lookup NAME [useExtension] { ... } NAME;`
#                emitted once, replayed as the reference `lookup NAME;`
#   _DEFINITION  `@Class = ...;` or `markClass ...;`
#                emitted once, dropped from the replay
#   _INCLUDE     `include(...);`
#                unknown contents, so the shorthand is left for feaLib to reject
#   _PLAIN       anything else, `lookup NAME;` references included
#                repeated verbatim, which is what the shorthand means
_LOOKUP = "lookup"
_DEFINITION = "definition"
_INCLUDE = "include"
_PLAIN = "plain"

# `language` as a whole word. `languagesystem` does not match, which matters:
# the guard below would otherwise fire for nearly every font.
_language_re = re.compile(r"\blanguage\b")

_Token = collections.namedtuple("_Token", "kind value start")

_Item = collections.namedtuple("_Item", "kind name first last")


def expand_multi_language_statements(fea):
    """Rewrite multi-tag ``language`` statements into one tag per statement.

    The scope of the shorthand is emitted once for the first tag and then
    replayed for every remaining one, statement by statement; see the table
    above for what happens to each kind of statement. Named lookups cannot
    simply be duplicated -- that would redefine them -- so the replays
    reference the lookup defined under the first tag::

        language AZE;
        lookup idotaccent {
            sub i by idotaccent;
        } idotaccent;
        language CRT;
        lookup idotaccent;
        ...

    The emitted text is sliced out of ``fea`` by offset, so comments,
    indentation and blank lines survive the round trip untouched.

    A statement that is already spec-compliant, or that cannot be classified
    with confidence, is left exactly as it is: the shorthand is invalid FEA, so
    leaving it alone means feaLib reports it rather than glyphsLib emitting a
    silently wrong language mapping.
    """
    # Lexing is not free -- feaLib takes a few microseconds per token -- and
    # most feature code has no `language` statement at all. The keyword has to
    # be there as a word for the shorthand to exist, so this cannot skip work
    # that was needed; a match inside a comment only costs the lexing.
    if not _language_re.search(fea):
        return fea

    tokens = _tokenize(fea)
    if tokens is None:
        return fea

    out = []
    expanded = False
    # Offset in `fea` up to which `out` has been filled.
    consumed = 0
    i = 0
    while i < len(tokens):
        if not _is_name(tokens[i], "language"):
            i += 1
            continue

        end = _statement_end(tokens, i)
        tags, keywords = _split_language_tokens(tokens, i + 1, end)
        if not tags or len(tags) < 2:
            i = end
            continue

        items, scope_end = _scan_scope(tokens, end)
        if items is None:
            logger.warning(
                "'language %s;' governs an include() and was left unexpanded",
                " ".join(tags),
            )
            i = end
            continue

        # The semicolon of the shorthand, and the end of the scope it governs.
        semicolon = tokens[end - 1].start
        scope = _scope_end_offset(tokens, items, semicolon)
        indent = _indent(fea, tokens[i].start)

        out.append(fea[consumed : tokens[i].start])
        out.append(_language_statement(tags[0], keywords))
        # Everything from just after the semicolon (a trailing comment) to the
        # end of the scope is kept verbatim.
        out.append(fea[semicolon + 1 : scope])
        for tag in tags[1:]:
            out.append("\n" + indent + _language_statement(tag, keywords))
            out.extend(_replay(fea, tokens, items, indent))

        logger.debug("Expanded 'language %s;'", " ".join(tags))
        expanded = True
        consumed = scope
        i = scope_end

    if not expanded:
        return fea
    out.append(fea[consumed:])
    return "".join(out)


def _tokenize(fea):
    """Return ``fea`` as a list of ``_Token``s carrying absolute offsets.

    Comments are dropped. Returns ``None`` if feaLib cannot even tokenize the
    code -- there is nothing to expand with confidence then, and feaLib reports
    the problem itself once it compiles the UFO. Feature text still holding
    unexpanded Glyphs tokens (``$[...]``, ``${...}``) lands here as well, and
    is likewise left alone.
    """
    starts = _line_starts(fea)
    tokens = []
    try:
        for kind, value, (_, line, column) in Lexer(fea, "<features>"):
            if kind == Lexer.COMMENT:
                continue
            tokens.append(_Token(kind, value, starts[line - 1] + column - 1))
    except (FeatureLibError, IndexError):
        return None
    return tokens


def _line_starts(fea):
    """Offset of the first character of every line.

    feaLib counts a ``\\r\\n`` as one line ending, same as splitting on ``\\n``
    does.
    """
    starts = [0]
    for line in fea.split("\n"):
        starts.append(starts[-1] + len(line) + 1)
    return starts


def _is_name(token, value):
    return token.kind == Lexer.NAME and token.value == value


def _is_symbol(token, value):
    return token.kind == Lexer.SYMBOL and token.value == value


def _statement_end(tokens, i):
    """Index just past the token that ends the statement starting at ``i``.

    That is the first semicolon at nesting depth zero. A block statement
    (``lookup X { ... } X;``) therefore ends at the semicolon following its
    closing brace, wherever the braces happen to sit on the page.
    """
    depth = 0
    while i < len(tokens):
        token = tokens[i]
        if token.kind == Lexer.SYMBOL:
            if token.value == "{":
                depth += 1
            elif token.value == "}":
                depth -= 1
            elif token.value == ";" and depth <= 0:
                return i + 1
        i += 1
    return len(tokens)


def _split_language_tokens(tokens, start, end):
    """Split the inside of a ``language ...;`` statement.

    Returns ``(tags, keywords)``, or ``(None, None)`` for anything unexpected,
    so that the caller leaves the statement alone rather than guessing.
    """
    if end > len(tokens) or not _is_symbol(tokens[end - 1], ";"):
        return None, None
    tags = []
    keywords = []
    for token in tokens[start : end - 1]:
        if token.kind != Lexer.NAME:
            return None, None
        if token.value in _LANGUAGE_KEYWORDS:
            keywords.append(token.value)
        elif keywords or len(token.value) > _TAG_LENGTH:
            # A tag after a keyword, or a token that is not a tag at all.
            return None, None
        else:
            tags.append(token.value)
    return tags, keywords


def _scan_scope(tokens, start):
    """Split the statements governed by the shorthand into ``_Item``s.

    The scope runs to the next ``language``/``script`` statement or to the end
    of the enclosing block, whichever comes first. Returns ``(None, start)`` if
    the scope contains an ``include()``, whose contents cannot be seen and
    therefore cannot be replayed.
    """
    items = []
    i = start
    while i < len(tokens):
        token = tokens[i]
        if _is_symbol(token, "}"):
            # Closes the block the `language` statement itself sits in.
            break
        if token.kind == Lexer.NAME and token.value in _BLOCK_DELIMITERS:
            break
        end = _statement_end(tokens, i)
        kind, name = _classify(tokens, i, end)
        if kind == _INCLUDE:
            return None, i
        items.append(_Item(kind, name, i, end))
        i = end
    return items, i


def _classify(tokens, i, end):
    """Return ``(kind, name)`` for the statement between ``i`` and ``end``."""
    head = tokens[i]
    if head.kind == Lexer.GLYPHCLASS:
        # `@Class = ...` defines; a rule may start with a class as well.
        if i + 1 < end and _is_symbol(tokens[i + 1], "="):
            return _DEFINITION, None
        return _PLAIN, None
    if head.kind != Lexer.NAME:
        return _PLAIN, None
    if head.value == "markClass":
        return _DEFINITION, None
    if head.value == "include":
        return _INCLUDE, None
    if head.value == "lookup" and i + 1 < end:
        # A definition opens a block; `lookup NAME;` is a reference and is
        # repeated as it stands.
        if any(_is_symbol(token, "{") for token in tokens[i:end]):
            return _LOOKUP, tokens[i + 1].value
    return _PLAIN, None


def _scope_end_offset(tokens, items, semicolon):
    """Offset just past the last statement of the scope.

    Deliberately not the start of the next one: whatever sits between them
    (newlines, a comment) belongs to the untouched remainder of the code.
    """
    if not items:
        return semicolon + 1
    return tokens[items[-1].last - 1].start + 1


def _replay(fea, tokens, items, indent):
    """Render the scope again for a repeated tag.

    Each replayed statement is laid out at ``indent``, the indentation of the
    ``language`` statement itself, rather than its own.
    """
    out = []
    for item in items:
        if item.kind == _LOOKUP:
            out.append(f"\n{indent}lookup {item.name};")
        elif item.kind != _DEFINITION:
            statement = fea[tokens[item.first].start : tokens[item.last - 1].start + 1]
            out.append("\n" + indent + statement)
    return out


def _language_statement(tag, keywords):
    return "language %s;" % " ".join([tag] + keywords)


def _indent(fea, offset):
    """The whitespace the statement at ``offset`` is indented by.

    ``""`` if the statement is not the first thing on its line.
    """
    line_start = fea.rfind("\n", 0, offset) + 1
    indent = fea[line_start:offset]
    return indent if not indent.strip() else ""
