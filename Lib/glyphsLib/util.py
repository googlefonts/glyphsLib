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


import json
import logging
import os
import shutil
import urllib
import xml.etree.ElementTree as etree

from collections import Counter, defaultdict, namedtuple
from glyphsLib.glyphdata import get_glyph, _get_unicode_category, _get_category

import fontTools.agl
from fontTools.misc.py23 import *


logger = logging.getLogger(__name__)

GlyphData = namedtuple('GlyphData', [
    'PRODUCTION_NAMES',
    'IRREGULAR_UNICODE_STRINGS',
    'MISSING_UNICODE_STRINGS',
    'DEFAULT_CATEGORIES',
    'IRREGULAR_CATEGORIES',
])


def fetch_url(url):
    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen
    stream = urlopen(url)
    content = stream.read()
    stream.close()
    return content.decode('utf-8')


def fetch(filename):
    return fetch_url(
        "https://raw.githubusercontent.com/schriftgestalt/GlyphsInfo/master/"
        + filename)


def fetch_data_version():
    last_commit_info = fetch_url(
        "https://api.github.com/repos/schriftgestalt/GlyphsInfo/commits/master")
    return json.loads(last_commit_info)["sha"]


def build_ufo_path(out_dir, family_name, style_name):
    """Build string to use as a UFO path."""

    return os.path.join(
        out_dir, '%s-%s.ufo' % (
            family_name.replace(' ', ''),
            style_name.replace(' ', '')))


def write_ufo(ufo, out_dir):
    """Write a UFO."""

    out_path = build_ufo_path(
        out_dir, ufo.info.familyName, ufo.info.styleName)

    logger.info('Writing %s' % out_path)
    clean_ufo(out_path)
    ufo.save(out_path)


def clean_ufo(path):
    """Make sure old UFO data is removed, as it may contain deleted glyphs."""

    if path.endswith('.ufo') and os.path.exists(path):
        shutil.rmtree(path)


def clear_data(data):
    """Clear empty list or dict attributes in data.

    This is used to determine what input data provided to to_ufos was not
    loaded into an UFO."""

    if isinstance(data, dict):
        for key, val in data.items():
            if not clear_data(val):
                del data[key]
        return data
    elif isinstance(data, list):
        i = 0
        while i < len(data):
            val = data[i]
            if not clear_data(val):
                del data[i]
            else:
                i += 1
        return data
    return True


def fetch_all_glyphs(paths=()):
    glyphs = {}
    for fileobj in paths:
        for glyph in etree.fromstring(fileobj).findall("glyph"):
            glyphName = glyph.attrib["name"]
            assert glyphName not in glyphs, "multiple entries for " + glyphName
            glyphs[glyphName] = glyph.attrib
    return glyphs


def build_data(glyphs):
    default_categories, irregular_categories = build_categories(glyphs)
    prodnames = {}
    irregular_unicode_strings = {}
    missing_unicode_strings = set()
    for name, glyph in glyphs.items():
        prodname = glyph.get("production", name)
        if prodname != name:
            prodnames[name] = prodname
        inferred_unistr = fontTools.agl.toUnicode(prodname)
        unistr = glyph.get("unicode")
        unistr = unichr(int(unistr, 16)) if unistr else None
        if unistr is None:
            missing_unicode_strings.add(name)
        elif unistr != inferred_unistr:
            irregular_unicode_strings[name] = unistr
    return GlyphData(prodnames,
                     irregular_unicode_strings,
                     missing_unicode_strings,
                     default_categories,
                     irregular_categories,
                     )


def build_categories(glyphs):
    counts = defaultdict(Counter)
    unicode_strings = {}
    for name, glyph in glyphs.items():
        prodname = glyph.get("production", name)
        unistr = unicode_strings[name] = fontTools.agl.toUnicode(prodname)
        unicode_category = _get_unicode_category(unistr)
        category = (glyph.get("category"), glyph.get("subCategory"))
        counts[unicode_category][category] += 1
    default_categories = {"Cc": ("Separator", None)}
    for key, value in counts.items():
        cat, _count = value.most_common(1)[0]
        default_categories[key] = cat

    # Find irregular categories. Whether it makes much sense for
    # Glyphs.app to disagree with Unicode about Unicode categories,
    # and whether it's a great idea to introduce inconsistencies (for
    # example, other than Unicode, Glyphs does not assign the same
    # category to "ampersand" and "ampersand.full"), is an entirely
    # moot question. Our goal here is to return the same properties as
    # encoded in GlyphsData.xml, so that glyphsLib produces the same
    # output as Glyphs.app.
    #
    # Changing the category of one glyph can affect the category of
    # others. To handle this correctly, we execute a simple fixed
    # point algorithm. Each iteration looks for glyphs whose category
    # is different from what we'd have inferred from the current data
    # tables; any irregularities get added to the irregular_categories
    # exception list. If the last iteration has discovered additional
    # irregularites, we do another round, trying to expand the exception
    # list until we cannot find any more.
    irregular_categories = {}
    data = GlyphData({}, {}, set(), default_categories, irregular_categories)
    changed = True
    while changed:
        changed = False
        for name, glyph in glyphs.items():
            inferred_category = _get_category(name, unicode_strings[name], data)
            category = (glyph.get("category"), glyph.get("subCategory"))
            if category != inferred_category:
                irregular_categories[name] = category
                changed = True
    return default_categories, irregular_categories


def test_data(glyphs, data):
    """Runs checks on the generated GlyphData

    Makes sure that the implementation of glyphsLib.glyphdata.get_glyph(),
    if it were to work on the generated GlyphData, will produce the exact
    same results as the original data files.
    """
    for _, glyph in sorted(glyphs.items()):
        name = glyph["name"]
        prod = glyph.get("production", name)
        unicode = glyph.get("unicode")
        unicode = unichr(int(unicode, 16)) if unicode else None
        category = glyph.get("category")
        subCategory = glyph.get("subCategory")
        g = get_glyph(name, data=data)
        assert name == g.name, (name, g.name)
        assert prod == g.production_name, (name, prod, g.production_name)
        assert unicode == g.unicode, (name, unicode, g.unicode)
        assert category == g.category, (name, category, g.category)
        assert subCategory == g.subCategory, (name, subCategory, g.subCategory)
