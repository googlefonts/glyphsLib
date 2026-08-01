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

from textwrap import dedent

import pytest

from glyphsLib import classes, to_ufos
from glyphsLib.builder.variable_features import VariableFeatureConverter

# tag -> (minimum, default, maximum), in design space
AXES = {
    "wght": (100, 400, 1000),
    "wdth": (40, 100, 100),
    "opsz": (8, 12, 28),
    "MSHQ": (0, 10, 100),
    "SPAC": (-100, 0, 100),
    "KASH": (0, 0, 100),
}


def make_font(axes=("wght",), masters=None, axis_locations=None, axis_mappings=None):
    if masters is None:
        # a master at every axis default, then one at each axis extreme
        defaults = tuple(AXES[tag][1] for tag in axes)
        positions = [defaults]
        for i, tag in enumerate(axes):
            minimum, _, maximum = AXES[tag]
            positions += [
                defaults[:i] + (value,) + defaults[i + 1 :]
                for value in (minimum, maximum)
            ]
        masters = list(dict.fromkeys(positions))
    font = classes.GSFont()
    font.axes = [classes.GSAxis(name=tag, tag=tag) for tag in axes]
    for i, pos in enumerate(masters):
        master = classes.GSFontMaster()
        master.axes = list(pos)
        if axis_locations:
            master.customParameters["Axis Location"] = [
                {"Axis": tag, "Location": loc}
                for tag, loc in zip(axes, axis_locations[i])
            ]
        font.masters.append(master)
    if axis_mappings:
        font.customParameters["Axis Mappings"] = axis_mappings
    return font


@pytest.fixture
def mapped_font():
    # wght design 100..1000 mapped to user 400..900
    return make_font(masters=((100,), (1000,)), axis_locations=((400,), (900,)))


def convert(fea, axes=("wght",), font=None):
    if font is None:
        font = make_font(axes)
    return VariableFeatureConverter(font).convert(fea)


@pytest.mark.parametrize(
    "fea, axes, expected",
    [
        (
            "feature cpsp { pos @Uppercase 10 (wdth:80) 20; } cpsp;",
            ("wdth",),
            "feature cpsp { pos @Uppercase (wdth=100:10 wdth=80.0:20); } cpsp;",
        ),
        # "There can be multiple alternative values and axes"
        (
            "feature cpsp { pos @Uppercase 10 (wdth:80) 20 (wdth:40 opsz:28) 30; }"
            " cpsp;",
            ("wdth", "opsz"),
            "feature cpsp { pos @Uppercase (wdth=100,opsz=12:10 wdth=80.0:20"
            " wdth=40.0,opsz=28.0:30); } cpsp;",
        ),
        # The handbook’s tab-indented four-value example.
        (
            dedent("""\
                feature test {
                pos @Digit colon' <10 50 20 0
                \t(wdth:80) 30 40 60 0
                \t(wdth:40 opsz:28) 5 10 10 0> @Digit;
                } test;"""),
            ("wdth", "opsz"),
            "feature test {\n"
            "pos @Digit colon' <(wdth=100,opsz=12:10 wdth=80.0:30"
            " wdth=40.0,opsz=28.0:5) (wdth=100,opsz=12:50 wdth=80.0:40"
            " wdth=40.0,opsz=28.0:10) (wdth=100,opsz=12:20 wdth=80.0:60"
            " wdth=40.0,opsz=28.0:10) 0> @Digit;\n"
            "} test;",
        ),
        # A component equal across all masters stays a plain number.
        (
            "feature kern { pos a b <10 0 5 0 (wght:900) 20 10 5 2>; } kern;",
            ("wght",),
            "feature kern { pos a b <(wght=400:10 wght=900.0:20)"
            " (wght=400:0 wght=900.0:10) 5 (wght=400:0 wght=900.0:2)>; } kern;",
        ),
        (
            "feature cpsp { pos a 10 (wdth:80) 20.5; } cpsp;",
            ("wdth",),
            "feature cpsp { pos a (wdth=100:10 wdth=80.0:21); } cpsp;",
        ),
        # Undocumented, but accepted by Glyphs.
        (
            "feature kern { pos a b -10 (MSHQ:100, SPAC:50) -30; } kern;",
            ("MSHQ", "SPAC"),
            "feature kern { pos a b (MSHQ=10,SPAC=0:-10 MSHQ=100.0,SPAC=50.0:-30); }"
            " kern;",
        ),
        # An unbounded side becomes the axis maximum.
        (
            "feature rlig {\ncondition 127 < wght;\nsub a by b;\n} rlig;",
            ("wght",),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wght 127.0 1000.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                } rlig;
                """),
        ),
        # An unbounded side becomes the axis minimum.
        (
            "feature rlig { condition wght < 900; sub a by b; } rlig;",
            ("wght",),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wght 100.0 900.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                } rlig;
                """),
        ),
        (
            "feature rlig { condition 600 < wght < 900; sub a by b; } rlig;",
            ("wght",),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wght 600.0 900.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                } rlig;
                """),
        ),
        # Comma is AND: both ranges in one condition set.
        (
            dedent("""\
                feature rlig {
                condition 600 < wght < 900, 70 < wdth < 90;
                sub a by b;
                } rlig;"""),
            ("wght", "wdth"),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wdth 70.0 90.0;
                    wght 600.0 900.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                } rlig;
                """),
        ),
        # The tutorial’s OR: identical rules under two conditions
        (
            dedent("""\
                feature rlig {
                condition 127 < wght;
                sub a by b;
                condition 105 < wght < 127, wdth < 90;
                sub a by b;
                } rlig;"""),
            ("wght", "wdth"),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wdth 40.0 90.0;
                    wght 105.0 127.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                } rlig;

                conditionset conditionset_2 {
                    wght 127.0 1000.0;
                } conditionset_2;

                variation rlig conditionset_2 {
                sub a by b;
                } rlig;
                """),
        ),
        # useExtension is kept on the feature block, not the variation blocks.
        (
            dedent("""\
                feature kern useExtension {
                pos a b -10;
                condition 600 < wght;
                pos a b 10 (wght:80) 20;
                } kern;"""),
            ("wght",),
            dedent("""\
                feature kern useExtension {
                pos a b -10;
                } kern;

                conditionset conditionset_1 {
                    wght 600.0 1000.0;
                } conditionset_1;

                variation kern conditionset_1 {
                pos a b (wght=400:10 wght=80.0:20);
                } kern;
                """),
        ),
        # The two conditions partially overlap.
        (
            dedent("""\
                feature rlig {
                condition KASH < 54;
                sub a by b;
                condition 53 < KASH;
                sub c by d;
                } rlig;"""),
            ("KASH",),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    KASH 53.0 54.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                sub c by d;
                } rlig;

                conditionset conditionset_2 {
                    KASH 53.0 100.0;
                } conditionset_2;

                variation rlig conditionset_2 {
                sub c by d;
                } rlig;

                conditionset conditionset_3 {
                    KASH 0.0 53.0;
                } conditionset_3;

                variation rlig conditionset_3 {
                sub a by b;
                } rlig;
                """),
        ),
        # Decimal bounds are kept as-is.
        (
            dedent("""\
                feature rclt {
                condition 10 < MSHQ < 10.001;
                sub a by b;
                condition 10.001 < MSHQ < 15;
                sub c by d;
                } rclt;
                """),
            ("MSHQ",),
            dedent("""\
                feature rclt {

                } rclt;

                conditionset conditionset_1 {
                    MSHQ 10.001 15.0;
                } conditionset_1;

                variation rclt conditionset_1 {
                sub c by d;
                } rclt;

                conditionset conditionset_2 {
                    MSHQ 10.0 10.001;
                } conditionset_2;

                variation rclt conditionset_2 {
                sub a by b;
                } rclt;

                """),
        ),
        # Mark anchors.
        (
            dedent("""\
                feature dist {
                markClass acutecomb <anchor 0 0> @TOP;
                pos base a <anchor 250 700 (wght:1000) 300 760> mark @TOP;
                } dist;"""),
            ("wght",),
            "feature dist {\n"
            "markClass acutecomb <anchor 0 0> @TOP;\n"
            "pos base a <anchor (wght=400:250 wght=1000.0:300)"
            " (wght=400:700 wght=1000.0:760)> mark @TOP;\n"
            "} dist;",
        ),
        # Cursive anchors,
        (
            dedent("""\
                feature dist {
                pos cursive a <anchor 100 200 (wght:1000) 150 260> <anchor NULL>;
                } dist;"""),
            ("wght",),
            "feature dist {\n"
            "pos cursive a <anchor (wght=400:100 wght=1000.0:150)"
            " (wght=400:200 wght=1000.0:260)> <anchor NULL>;\n"
            "} dist;",
        ),
        # A component equal across all masters stays a plain number.
        (
            dedent("""\
                feature dist {
                pos cursive a <anchor 100 700 (wght:1000) 150 700> <anchor NULL>;
                } dist;"""),
            ("wght",),
            "feature dist {\n"
            "pos cursive a <anchor (wght=400:100 wght=1000.0:150) 700>"
            " <anchor NULL>;\n"
            "} dist;",
        ),
        # Variable anchors: multi-axis location.
        (
            "feature dist {\n"
            "pos cursive a <anchor 100 200 (wght:1000 wdth:80) 150 260>"
            " <anchor NULL>;\n"
            "} dist;",
            ("wght", "wdth"),
            "feature dist {\n"
            "pos cursive a <anchor (wght=400,wdth=100:100"
            " wght=1000.0,wdth=80.0:150) (wght=400,wdth=100:200"
            " wght=1000.0,wdth=80.0:260)> <anchor NULL>;\n"
            "} dist;",
        ),
        # sub c by d is unconditional again and stays in the feature block
        (
            dedent("""\
                feature rlig {
                condition 600 < wght;
                sub a by b;
                condition;
                sub c by d;
                } rlig;"""),
            ("wght",),
            dedent("""\
                feature rlig {
                sub c by d;
                } rlig;

                conditionset conditionset_1 {
                    wght 600.0 1000.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                } rlig;
                """),
        ),
        # Non-overlapping regions, most specific first.
        (
            dedent("""\
                feature rlig {
                condition 600 < wght;
                sub a by b;
                condition 800 < wght;
                sub c by d;
                } rlig;"""),
            ("wght",),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wght 800.0 1000.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                sub c by d;
                } rlig;

                conditionset conditionset_2 {
                    wght 600.0 800.0;
                } conditionset_2;

                variation rlig conditionset_2 {
                sub a by b;
                } rlig;
                """),
        ),
        # The pinned region precedes its container and carries the union of
        # both regions rules.
        (
            dedent("""\
                feature rlig {
                condition 600 < wght < 600;
                sub a by b;
                condition 400 < wght;
                sub c by d;
                } rlig;"""),
            ("wght",),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wght 600.0 600.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                sub c by d;
                } rlig;

                conditionset conditionset_2 {
                    wght 400.0 1000.0;
                } conditionset_2;

                variation rlig conditionset_2 {
                sub c by d;
                } rlig;
                """),
        ),
        # Duplicate conditions merge into one variation block, keeping source
        # order.
        (
            dedent("""\
                feature rlig {
                condition 600 < wght;
                sub a' b by c;
                condition 600 < wght;
                sub a by d;
                } rlig;"""),
            ("wght",),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wght 600.0 1000.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a' b by c;
                sub a by d;
                } rlig;
                """),
        ),
        # Identical conditions across features reuse the condition set.
        (
            dedent("""\
                feature rlig { condition 600 < wght; sub a by b; } rlig;
                feature liga { condition 600 < wght; sub c by d; } liga;"""),
            ("wght",),
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wght 600.0 1000.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                } rlig;

                feature liga {

                } liga;

                variation liga conditionset_1 {
                sub c by d;
                } liga;
                """),
        ),
        # The #ifndef block is stripped.
        (
            dedent("""\
                feature rlig {
                sub a by b;
                #ifndef VARIABLE
                sub c by d;
                #endif
                sub e by f;
                } rlig;"""),
            ("wght",),
            "feature rlig {\nsub a by b;\nsub e by f;\n} rlig;",
        ),
        # The #ifdef markers are kept as comments.
        (
            "feature rlig {\n#ifdef VARIABLE\nsub a by b;\n#endif\n} rlig;",
            ("wght",),
            "feature rlig {\n#ifdef VARIABLE\nsub a by b;\n#endif\n} rlig;",
        ),
        # An unterminated #ifndef runs to the feature’s end.
        (
            "feature rlig {\nsub a by b;\n#ifndef VARIABLE\nsub c by d;\n} rlig;",
            ("wght",),
            "feature rlig {\nsub a by b;\n} rlig;",
        ),
        # Rules after #endif but before the next condition are still
        # conditional.
        (
            dedent("""\
                feature rlig {
                sub x by y;
                #ifdef VARIABLE
                condition 600 < wght;
                sub a by b;
                #endif
                sub p by q;
                } rlig;"""),
            ("wght",),
            dedent("""\
                feature rlig {
                sub x by y;
                #ifdef VARIABLE
                } rlig;

                conditionset conditionset_1 {
                    wght 600.0 1000.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                #endif
                sub p by q;
                } rlig;
                """),
        ),
    ],
)
def test_convert(fea, axes, expected):
    assert convert(fea, axes) == expected


@pytest.mark.parametrize(
    "fea, expected",
    [
        # GPOS locations are design-space and map to user-space.
        (
            "feature cpsp { pos a 10 (wght:1000) 20; } cpsp;",
            "feature cpsp { pos a (wght=400:10 wght=900.0:20); } cpsp;",
        ),
        # Condition bounds too: design 600 -> user 677.77777
        (
            "feature rlig { condition 600 < wght; sub a by b; } rlig;",
            dedent("""\
                feature rlig {

                } rlig;

                conditionset conditionset_1 {
                    wght 677.77777 900.0;
                } conditionset_1;

                variation rlig conditionset_1 {
                sub a by b;
                } rlig;
                """),
        ),
    ],
)
def test_mapped(mapped_font, fea, expected):
    # wght design 100..1000 mapped to user 400..900
    assert convert(fea, font=mapped_font) == expected


@pytest.mark.parametrize(
    "src",
    [
        # A plain feaLib value record with device tables is not Glyphs syntax.
        "feature kern { pos a b <10 0 5 0 <device 11 -2, 12 -1> "
        "<device NULL> <device NULL> <device NULL>>; } kern;",
        "feature rlig {\n# condition 600 < wght;\nsub a by b;\n} rlig;",
        "feature calt {\nsub a.condition by b;\n} calt;",
        "feature calt {\nsub condition.alt by b;\n} calt;",
        "feature calt {\nsub @mycondition by b;\n} calt;",
        'feature ss01 { featureNames { name "shift 10 (wght:80) 20"; };'
        " sub a by b; } ss01;",
        "feature dist {\npos cursive a <anchor 100 200> <anchor NULL>;\n} dist;",
        "feature dist {\npos cursive a <anchor NULL> <anchor NULL>;\n} dist;",
        dedent("""\
            feature dist {
            pos cursive a <anchor 100 200 contourpoint 5> <anchor NULL>;
            } dist;"""),
        # (wght=80) is not Glyphs syntax, it does not trigger conversion alone
        "feature kern { pos a b <10 0 5 0 (wght=80) 20 10 5 2>; } kern;",
        # Already feaLib variable syntax.
        "feature test { pos a b (wght=400:10 wght=900:20); } test;",
    ],
)
def test_untouched(src):
    assert convert(src) == src


def test_idempotent():
    src = dedent("""\
        feature cpsp { pos a 10 (wght:900) 20; } cpsp;
        feature rlig { condition 600 < wght; sub a by b; } rlig;""")
    once = convert(src)
    assert convert(once) == once


@pytest.mark.parametrize(
    "fea, axes, match",
    [
        # Glyphs: "Condition for axis wght already specified"
        (
            "feature rlig { condition 100 < wght, wght < 700; sub a by b; } rlig;",
            ("wght",),
            "already specified",
        ),
        (
            dedent("""\
                feature rlig {
                condition 600 < wght < 900 70 < wdth < 90;
                sub a by b;
                } rlig;"""),
            ("wght", "wdth"),
            "invalid condition axis range",
        ),
        (
            dedent("""\
                feature rlig {
                lookup L {
                condition 600 < wght;
                sub a by b;
                } L;
                } rlig;"""),
            ("wght",),
            "lookup",
        ),
        (
            "condition 600 < wght;\nsub a by b;",
            ("wght",),
            "outside feature blocks",
        ),
        (
            "feature rlig { condition 600 < opsz; sub a by b; } rlig;",
            ("wght",),
            "unknown axis",
        ),
        (
            "feature kern { pos a b <10 0 5 0 (wght:80) 30 40 60>; } kern;",
            ("wght", "opsz"),
            "value record",
        ),
        (
            "feature kern { pos a b <10 0 5 0 (wght:80) 1 2 (opsz:28) 4>; } kern;",
            ("wght", "opsz"),
            "value record",
        ),
        (
            dedent("""\
                feature kern { pos a b <10 0 5 0 (wght=80) 20 10 5 2>; } kern;
                feature cpsp { pos a 10 (wght:900) 20; } cpsp;"""),
            ("wght",),
            "value record",
        ),
        (
            dedent("""\
                feature dist {
                pos cursive a <anchor 100 200 (wght:1000) 150> <anchor NULL>;
                } dist;"""),
            ("wght",),
            "anchor",
        ),
    ],
)
def test_invalid_raises(fea, axes, match):
    with pytest.raises(ValueError, match=match):
        convert(fea, axes)


def test_inverted_range_warns_and_drops_rules(caplog):
    with caplog.at_level("WARNING"):
        out = convert("feature rlig { condition 900 < wght < 600; sub a by b; } rlig;")
    assert out == "feature rlig {\n\n} rlig;\n"
    assert "can never match" in caplog.text


def test_axis_info_identity():
    converter = VariableFeatureConverter(make_font())
    (axis,) = converter.axes.values()
    assert (axis.minimum, axis.default, axis.maximum) == (100, 400, 1000)
    assert not axis.map


def test_axis_info_axis_location(mapped_font):
    converter = VariableFeatureConverter(mapped_font)
    axis = converter.axes["wght"]
    assert (axis.minimum, axis.default, axis.maximum) == (400, 400, 900)
    assert axis.map == [(400, 100), (900, 1000)]


def test_axis_info_axis_mappings():
    converter = VariableFeatureConverter(
        make_font(
            masters=((100,), (1000,)), axis_mappings={"wght": {400: 100, 900: 1000}}
        )
    )
    axis = converter.axes["wght"]
    assert (axis.minimum, axis.default, axis.maximum) == (400, 400, 900)
    assert axis.map == [(400, 100), (900, 1000)]


def test_to_ufos_converts_condition_with_axis_location(mapped_font, ufo_module):
    mapped_font.features.append(
        classes.GSFeature("rlig", "condition 600 < wght;\nsub a by b;")
    )
    ufo = to_ufos(mapped_font, ufo_module=ufo_module)[0]
    text = ufo.features.text
    # design-space 600 mapped through Axis Location to user-space 677.77777
    assert "wght 677.77777 900.0" in text
    assert "variation rlig conditionset_1" in text


def test_to_ufos_plain_features_untouched(ufo_module):
    font = make_font()
    font.features.append(classes.GSFeature("liga", "sub a by b;"))
    ufo = to_ufos(font, ufo_module=ufo_module)[0]
    assert "sub a by b;" in ufo.features.text
    assert "conditionset" not in ufo.features.text
