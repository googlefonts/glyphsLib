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

from __future__ import (print_function, division, absolute_import,
                        unicode_literals)

from fontTools.misc.py23 import round, unicode

import re

import glyphsLib
from .constants import GLYPHLIB_PREFIX, PUBLIC_PREFIX


def autostr(automatic):
    return '# automatic\n' if automatic else ''


def to_ufo_features(self, ufo):
    """Write an UFO's OpenType feature file."""

    prefix_str = '\n\n'.join('# Prefix: %s\n%s%s' %
                             (prefix.name, autostr(prefix.automatic),
                              prefix.code.strip())
                             for prefix in self.font.featurePrefixes)

    class_defs = []
    for class_ in self.font.classes:
        prefix = '@' if not class_.name.startswith('@') else ''
        name = prefix + class_.name
        class_defs.append('%s%s = [ %s ];' % (autostr(class_.automatic), name,
                                              class_.code))
    class_str = '\n\n'.join(class_defs)

    feature_defs = []
    for feature in self.font.features:
        code = feature.code.strip()
        lines = ['feature %s {' % feature.name]
        if feature.notes:
            lines.append('# notes:')
            lines.extend('# ' + line for line in feature.notes.splitlines())
        if feature.automatic:
            lines.append('# automatic')
        if feature.disabled:
            lines.append('# disabled')
            lines.extend('#' + line for line in code.splitlines())
        else:
            lines.append(code)
        lines.append('} %s;' % feature.name)
        feature_defs.append('\n'.join(lines))
    fea_str = '\n\n'.join(feature_defs)
    gdef_str = _build_gdef(ufo)

    # make sure feature text is a unicode string, for defcon
    full_text = '\n\n'.join(
        filter(None, [prefix_str, class_str, fea_str, gdef_str])) + '\n'
    ufo.features.text = full_text if full_text.strip() else ''


def _build_gdef(ufo):
    """Build a table GDEF statement for ligature carets."""
    from glyphsLib import glyphdata  # Expensive import

    bases, ligatures, marks, carets = set(), set(), set(), {}
    category_key = GLYPHLIB_PREFIX + 'category'
    subCategory_key = GLYPHLIB_PREFIX + 'subCategory'
    for glyph in ufo:
        has_attaching_anchor = False
        for anchor in glyph.anchors:
            name = anchor.name
            if name and not name.startswith('_'):
                has_attaching_anchor = True
            if name and name.startswith('caret_') and 'x' in anchor:
                carets.setdefault(glyph.name, []).append(round(anchor['x']))
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
        if subCategory == 'Ligature' and has_attaching_anchor:
            ligatures.add(glyph.name)
        elif category == 'Mark' and (subCategory == 'Nonspacing' or
                                     subCategory == 'Spacing Combining'):
            marks.add(glyph.name)
        elif has_attaching_anchor:
            bases.add(glyph.name)
    if not any((bases, ligatures, marks, carets)):
        return None
    lines = ['table GDEF {', '  # automatic']
    glyphOrder = ufo.lib[PUBLIC_PREFIX + 'glyphOrder']
    glyphIndex = lambda glyph: glyphOrder.index(glyph)
    fmt = lambda g: ('[%s]' % ' '.join(sorted(g, key=glyphIndex))) if g else ''
    lines.extend([
        '  GlyphClassDef',
        '    %s, # Base' % fmt(bases),
        '    %s, # Liga' % fmt(ligatures),
        '    %s, # Mark' % fmt(marks),
        '    ;'])
    for glyph, caretPos in sorted(carets.items()):
        lines.append('  LigatureCaretByPos %s %s;' %
                     (glyph, ' '.join(unicode(p) for p in sorted(caretPos))))
    lines.append('} GDEF;')
    return '\n'.join(lines)


def replace_feature(tag, repl, features):
    if not repl.endswith("\n"):
        repl += "\n"
    return re.sub(
        r"(?<=^feature %(tag)s {\n)(.*?)(?=^} %(tag)s;$)" % {"tag": tag},
        repl,
        features,
        count=1,
        flags=re.DOTALL | re.MULTILINE)
