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


from __future__ import (print_function, division, absolute_import,
                        unicode_literals)
from fontTools.misc.py23 import *

import sys
sys.path.append("./Lib")
import io
import fontTools.agl
import json
import urllib
import textwrap
import xml.etree.ElementTree as etree

from collections import Counter, defaultdict, namedtuple
from glyphsLib.glyphdata import get_glyph, _get_unicode_category, _get_category


# Data tables which we put into the generated Python file.
# See comments in generate_python_source() below for documentation.
GlyphData = namedtuple('GlyphData', [
    'PRODUCTION_NAMES',
    'PRODUCTION_NAMES_REVERSED',
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


def fetch_all_glyphs():
    glyphs = {}
    for filename in ("GlyphData.xml", "GlyphData_Ideographs.xml"):
        for glyph in etree.fromstring(fetch(filename)).findall("glyph"):
            glyphName = glyph.attrib["name"]
            assert glyphName not in glyphs, "multiple entries for " + glyphName
            glyphs[glyphName] = glyph.attrib
    return glyphs


def load_file(filename):
    stream = open(filename, "r")
    content = stream.read()
    stream.close()
    return content


def load_all_glyphs_from_files(filenames):
    glyphs = {}
    for filename in filenames:
        for glyph in etree.fromstring(load_file(filename)).findall("glyph"):
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

    prodnames_rev = {agl: g for g, agl in prodnames.items()}

    return GlyphData(prodnames,
                     prodnames_rev,
                     irregular_unicode_strings,
                     missing_unicode_strings,
                     default_categories,
                     irregular_categories)


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
    data = GlyphData({}, {}, {}, set(), default_categories, irregular_categories)
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


def nonesorter(a):
    # Python 2 sorts None before any string (even empty string), while
    # Python 3 raises a TypeError when attempting to compare NoneType with str.
    # Here we emulate python 2 and return "" when an item to be sorted is None
    if isinstance(a, tuple):
        return tuple(nonesorter(e) for e in a)
    return "" if a is None else a


def generate_python_source(data, out):
    out.write(
        "# -*- coding: utf-8 -*-\n"
        "#\n"
        "# Please do not manually edit this file.\n"
        "#\n")
    if len(sys.argv) < 2:
        out.write(
            "# It has been generated by MetaTools/generate_glyphdata.py using\n"
            "# upstream data from https://github.com/schriftgestalt/GlyphsInfo/\n"
            "# taken at commit hash %s.\n"
            "#\n"
            % fetch_data_version())

        for paragraph in fetch("LICENSE").strip().split("\n\n"):
            out.write("#\n")
            for line in textwrap.wrap(paragraph):
                out.write("# ")
                out.write(line)
                out.write("\n")

    out.write("\nfrom __future__ import unicode_literals\n\n\n")
    out.write(
        "# Glyphs for which Glyphs.app uses production names that do not\n"
        "# comply with the Adobe Glyph List specification.\n")
    out.write("PRODUCTION_NAMES = {\n")
    for key, value in sorted(data.PRODUCTION_NAMES.items()):
        out.write('\t"%s":"%s",\n' % (key, value))
    out.write("}\n\n")

    out.write("PRODUCTION_NAMES_REVERSED = {\n"
              "\tagl: g for g, agl in PRODUCTION_NAMES.items()\n"
              "}\n\n")

    out.write(
        "# Glyphs for which Glyphs.app has a different Unicode string\n"
        "# than the string we would generate from the production name.\n")
    out.write("IRREGULAR_UNICODE_STRINGS = {\n")
    for key, value in sorted(data.IRREGULAR_UNICODE_STRINGS.items()):
        value_repr = value.encode("unicode-escape").decode('ascii')
        out.write('\t"%s":"%s",\n' % (key, value_repr))
    out.write("}\n\n")

    out.write(
        "# Glyphs for which Glyphs.app has no Unicode string.\n"
        "# For almost all these glyphs, one could derive a Unicode string\n"
        "# from the production glyph name, but Glyphs.app still has none\n"
        "# in its data. Many of these cases seem to be bugs in GlyphsData,\n"
        "# but we need to be compatible with Glyphs.\n")
    out.write("MISSING_UNICODE_STRINGS = {\n")
    for name in sorted(data.MISSING_UNICODE_STRINGS):
        out.write('\t"%s",\n' % name)
    out.write("}\n\n")

    out.write(
        "# From the first character of the Unicode string of a glyph,\n"
        "# one can compute the Unicode category. This Unicode category\n"
        "# can frequently be mapped to the Glyphs category and subCategory.\n"
        "DEFAULT_CATEGORIES = {\n")
    for ucat, glyphsCat in sorted(
            data.DEFAULT_CATEGORIES.items(), key=nonesorter):
        out.write('\t%s: %s,\n' %
                  ('"%s"' % ucat if ucat else 'None', glyphsCat))
    out.write("}\n\n")

    out.write(
        "# However, to some glyphs, Glyphs.app assigns a different category\n"
        "# or sub-category than Unicode. The following table contains these\n"
        "# exceptions.\n"
        "IRREGULAR_CATEGORIES = {\n")
    for glyphName, glyphsCat in sorted(
            data.IRREGULAR_CATEGORIES.items(), key=nonesorter):
        out.write('\t"%s": %s,\n' % (glyphName, glyphsCat))
    out.write("}\n\n")

    
if __name__ == "__main__":
    outpath = "Lib/glyphsLib/glyphdata_generated.py"
    glyphs = (
            load_all_glyphs_from_files(sys.argv[1:]) if len(sys.argv) >= 2
            else fetch_all_glyphs())
    data = build_data(glyphs)
    test_data(glyphs, data)
    with io.open(outpath, "w", encoding="utf-8") as out:
        generate_python_source(data, out)
