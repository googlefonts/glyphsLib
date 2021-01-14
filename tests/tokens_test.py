#
# Copyright 2021 Google Inc. All Rights Reserved.
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
import pytest
from glyphsLib.classes import GSFont
from glyphsLib.builder.tokens import TokenExpander
from glyphsLib.builder import to_ufos

TESTFONT = GSFont(
    os.path.join(os.path.dirname(__file__), os.path.join("data", "TokenTest.glyphs"))
)
master = TESTFONT.masters[1]
expander = TokenExpander(TESTFONT, master)


@pytest.mark.parametrize(
    "test_input,expected,throws",
    [
        ("sub a by b;", "sub a by b;", False),
        ("pos a $padding b;", "pos a 250 b;", False),
        (r"pos a ${padding} b;", "pos a 250 b;", False),
        (r"pos a ${padding * 2} b;", "pos a 500 b;", False),
        (r"pos a ${padding + padding} b;", "pos a 500 b;", False),
        (r"pos a ${padding + (padding/2)} b;", "pos a 375 b;", False),
        ("pos a $xxx b;", "", True),
        # Tests from Glyphs tutorial
        (
            "$[name endswith '.sc']",
            "A.sc",
            False,
        ),  # will expand to all glyph names that end in ".sc"
        ("$[not name endswith '.sc']", "A Sacute", False),
        ("$[name endswith '.sc' or not name endswith '.sc']", "A.sc A Sacute", False),
        ("$[name endswith '.sc' and not name endswith '.sc']", "", False),
        # ('$[layer0.width < 500]', "", False), # layer0 = first master
        # ('$[layers.count > 1]', "", False), # compare numbers with: == != <= >= < >
        # ('$[direction == 2]', "", False), # 0=LTR, 1=BiDi, 2=RTL
        # ('$[colorIndex == 5]', "", False),
        # ('$[case == smallCaps]', "", False),
        # predefined constants: noCase, upper, lower, smallCaps, minor, other
        (
            '$[name matches "S|s.*"]',
            "A.sc Sacute",
            False,
        ),  # "matches": regular expression
        # ('$[leftMetricsKey like "*"]', "", False), # "like": wildcard search
        # ('$[name like "*e*"]', "", False), # e anywhere in the glyph name
        ('$[script like "latin"]', "A", False),
        ('$[category like "Separator"]', "Sacute", False),
        ('$[leftKerningGroup like "H"]', "A", False),
        ('$[rightKerningGroup like "L"]', "A", False),
        ('$[unicode beginswith "41"]', "A", False),  # beginswith, endswith, contains
        ('$[note contains "love it"]', "A.sc", False),  # glyph note
        # ('$[countOfUnicodes > 1]', "", False),
        # ('$[countOfLayers > 1]', "", False),
        ('$[subCategory like "Arrow"]', "Sacute", False),
        # ('$[hasHints == 0]', "", False), # boolean: false, no, 0 versus true, yes, 1
        # ('$[isColorGlyph == true]', "", False),
        (
            '$[script == "latin"]',
            "A",
            False,
        ),  # connect multiple conditions with ORor AND
        # ('$[hasComponents == true and script == "latin"]', "", False),
        # connect multiple conditions with ORor AND
        # ('$[hasTrueTypeHints == false]', "", False),
        # ('$[hasAlignedWidth == true]', "", False),
        # ('$[hasPostScriptHints == true]', "", False),
        # ('$[hasAnnotations == true]', "", False),
        # ('$[hasCorners == true]', "", False), # corners = corner components
        # ('$[hasSpecialLayers == yes]', "", False),
        # special layers = color, brace and bracket layers
        # ('$[isHangulKeyGlyph == no]', "", False),
    ],
)
def test_token_expander(test_input, expected, throws):

    if throws:
        with pytest.raises(ValueError):
            expander.expand(test_input)
    else:
        output = expander.expand(test_input)
        assert output == expected


def test_end_to_end():
    ufos = to_ufos(TESTFONT)
    assert "@SmallCaps = [ A.sc" in ufos[0].features.text

    assert "pos A A.sc 100" in ufos[0].features.text
    assert "pos A A.sc 500" in ufos[1].features.text
