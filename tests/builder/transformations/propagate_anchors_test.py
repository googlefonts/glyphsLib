from __future__ import annotations

import math
import os.path

from copy import deepcopy
from typing import TYPE_CHECKING

from fontTools.misc.transform import Transform as Affine

from glyphsLib.classes import GSAnchor, GSFont, GSGlyph, GSLayer, GSComponent
from glyphsLib.glyphdata import get_glyph
from glyphsLib.types import Point, Transform
from glyphsLib.writer import dumps

from glyphsLib.builder.transformations.propagate_anchors import (
    get_xy_rotation,
    propagate_all_anchors,
    propagate_all_anchors_impl,
    depth_sorted_composite_glyphs,
)

if TYPE_CHECKING:
    from typing import Callable, Self

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


# Basically all the tests below are translated from:
# https://github.com/googlefonts/fontc/blob/ecc727d/glyphs-reader/src/propagate_anchors.rs#L423-L959
# This is to ensure that the Python implementation behaves the same way as the Rust one.


class GlyphSetBuilder:
    glyphs: dict[str, GSGlyph]

    def __init__(self):
        self.glyphs = {}

    def build(self) -> dict[str, GSGlyph]:
        return self.glyphs

    def add_glyph(self, name: str, build_fn: Callable[["GlyphBuilder"], None]) -> Self:
        glyph = GlyphBuilder(name)
        build_fn(glyph)
        self.glyphs[name] = glyph.build()
        return self


class GlyphBuilder:
    def __init__(self, name: str):
        info = get_glyph(name)
        self.glyph = glyph = GSGlyph()
        glyph.name = name
        glyph.unicode = info.unicode
        glyph.category = info.category
        glyph.subCategory = info.subCategory
        self.add_layer()

    def build(self) -> GSGlyph:
        return self.glyph

    def add_layer(self) -> Self:
        layer = GSLayer()
        layer.name = layer.layerId = layer.associatedMasterId = (
            f"layer-{len(self.glyph.layers)}"
        )
        self.glyph.layers.append(layer)
        return self

    def set_category(self, category: str) -> Self:
        self.glyph.category = category
        return self

    def set_subCategory(self, subCategory: str) -> Self:
        self.glyph.subCategory = subCategory
        return self

    def add_component(self, name: str, pos: tuple[float, float]) -> Self:
        component = GSComponent(name, offset=pos)
        self.glyph.layers[-1].components.append(component)
        return self

    def rotate_component(self, degrees: float) -> Self:
        # Set an explicit translate + rotation for the component
        component = self.glyph.layers[-1].components[-1]
        component.transform = Transform(
            *Affine(*component.transform).rotate(math.radians(degrees))
        )
        return self

    def add_component_anchor(self, name: str) -> Self:
        # add an explicit anchor to the last added component
        component = self.glyph.layers[-1].components[-1]
        component.anchor = name
        return self

    def add_anchor(self, name: str, pos: tuple[float, float]) -> Self:
        anchor = GSAnchor(name, Point(*pos))
        self.glyph.layers[-1].anchors.append(anchor)
        return self


def make_glyph(name: str, components: list[str]) -> GSGlyph:
    builder = GlyphBuilder(name)
    for comp in components:
        builder.add_component(comp, (0, 0))  # pos doesn't matter for this test
    return builder.build()


def test_components_by_depth():
    glyphs = {
        name: make_glyph(name, components)
        for name, components in [
            ("A", []),
            ("E", []),
            ("acutecomb", []),
            ("brevecomb", []),
            ("brevecomb_acutecomb", ["acutecomb", "brevecomb"]),
            ("AE", ["A", "E"]),
            ("Aacute", ["A", "acutecomb"]),
            ("Aacutebreve", ["A", "brevecomb_acutecomb"]),
            ("AEacutebreve", ["AE", "brevecomb_acutecomb"]),
        ]
    }

    assert depth_sorted_composite_glyphs(glyphs) == [
        "A",
        "E",
        "acutecomb",
        "brevecomb",
        "AE",
        "Aacute",
        "brevecomb_acutecomb",
        "AEacutebreve",
        "Aacutebreve",
    ]


def assert_equal_gsobjects(object1, object2):
    # glyphsLib.classes objects don't implement __eq__, so we resort to compare
    # their serialized forms... Ugly but works :(
    assert dumps(object1) == dumps(object2)


def assert_equal_glyphsets(glyphs1, glyphs2):
    assert len(glyphs1) == len(glyphs2)
    assert glyphs1.keys() == glyphs2.keys()
    for name in glyphs1:
        assert_equal_gsobjects(glyphs1[name], glyphs2[name])


def assert_anchors(actual, expected):
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected):
        assert a.name == e[0]
        assert a.position == Point(*e[1])


def test_no_components_anchors_are_unchanged():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph(
            "A",
            lambda glyph: (
                glyph.add_anchor("bottom", (234, 0))
                .add_anchor("ogonek", (411, 0))
                .add_anchor("top", (234, 810))
            ),
        )
        .add_glyph(
            "acutecomb",
            lambda glyph: (
                glyph.add_anchor("_top", (0, 578)).add_anchor("top", (0, 810))
            ),
        )
        .build()
    )

    glyphs2 = deepcopy(glyphs)
    propagate_all_anchors_impl(glyphs2)
    # nothing should change here
    assert_equal_glyphsets(glyphs, glyphs2)


def test_basic_composite_anchor():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph(
            "A",
            lambda glyph: (
                glyph.add_anchor("bottom", (234, 0))
                .add_anchor("ogonek", (411, 0))
                .add_anchor("top", (234, 810))
            ),
        )
        .add_glyph(
            "acutecomb",
            lambda glyph: (
                glyph.add_anchor("_top", (0, 578)).add_anchor("top", (0, 810))
            ),
        )
        .add_glyph(
            "Aacute",
            lambda glyph: (
                glyph.add_component("A", (0, 0)).add_component("acutecomb", (234, 232))
            ),
        )
        .build()
    )
    propagate_all_anchors_impl(glyphs)

    new_glyph = glyphs["Aacute"]
    assert_anchors(
        new_glyph.layers[0].anchors,
        [
            ("bottom", (234, 0)),
            ("ogonek", (411, 0)),
            ("top", (234, 1042)),
        ],
    )


def test_propagate_ligature_anchors():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    # this is based on the IJ glyph in Oswald (ExtraLight)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph(
            "I",
            lambda glyph: (
                glyph.add_anchor("bottom", (103, 0))
                .add_anchor("ogonek", (103, 0))
                .add_anchor("top", (103, 810))
                .add_anchor("topleft", (20, 810))
            ),
        )
        .add_glyph(
            "J",
            lambda glyph: (
                glyph.add_anchor("bottom", (133, 0)).add_anchor("top", (163, 810))
            ),
        )
        .add_glyph(
            "IJ",
            lambda glyph: (
                glyph.set_subCategory("Ligature")
                .add_component("I", (0, 0))
                .add_component("J", (206, 0))
            ),
        )
        .build()
    )
    propagate_all_anchors_impl(glyphs)
    ij = glyphs["IJ"]
    # these were derived by running the built in glyphs.app propagate anchors
    # method from the macro panel
    assert_anchors(
        ij.layers[0].anchors,
        [
            ("bottom_1", (103, 0)),
            ("ogonek_1", (103, 0)),
            ("top_1", (103, 810)),
            ("topleft_1", (20, 810)),
            ("bottom_2", (339, 0)),
            ("top_2", (369, 810)),
        ],
    )


def test_digraphs_arent_ligatures():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    # this is based on the IJ glyph in Oswald (ExtraLight)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph(
            "I",
            lambda glyph: (
                glyph.add_anchor("bottom", (103, 0))
                .add_anchor("ogonek", (103, 0))
                .add_anchor("top", (103, 810))
                .add_anchor("topleft", (20, 810))
            ),
        )
        .add_glyph(
            "J",
            lambda glyph: (
                glyph.add_anchor("bottom", (133, 0)).add_anchor("top", (163, 810))
            ),
        )
        .add_glyph(
            "IJ",
            lambda glyph: (
                glyph.add_component("I", (0, 0)).add_component("J", (206, 0))
            ),
        )
        .build()
    )
    propagate_all_anchors_impl(glyphs)
    ij = glyphs["IJ"]
    # these were derived by running the built in glyphs.app propagate anchors
    # method from the macro panel
    assert_anchors(
        ij.layers[0].anchors,
        # 'J' component comes last; the 'bottom' and 'top' anchors are from 'J'
        # shifted by the 'J' component's offset (206, 0).
        # 'ogonek' and 'topleft' are inherited from 'I', the first component, which
        # has (0, 0) offset hence the same anchor positions as the original 'I' glyph.
        [
            ("bottom", (339, 0)),
            ("ogonek", (103, 0)),
            ("top", (369, 810)),
            ("topleft", (20, 810)),
        ],
    )


def test_propagate_across_layers():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph(
            "A",
            lambda glyph: (
                glyph.add_anchor("bottom", (290, 10))
                .add_anchor("ogonek", (490, 3))
                .add_anchor("top", (290, 690))
                .add_layer()
                .add_anchor("bottom", (300, 0))
                .add_anchor("ogonek", (540, 10))
                .add_anchor("top", (300, 700))
            ),
        )
        .add_glyph(
            "acutecomb",
            lambda glyph: (
                glyph.add_anchor("_top", (335, 502))
                .add_anchor("top", (353, 721))
                .add_layer()
                .add_anchor("_top", (366, 500))
                .add_anchor("top", (366, 765))
            ),
        )
        .add_glyph(
            "Aacute",
            lambda glyph: (
                glyph.add_component("A", (0, 0))
                .add_component("acutecomb", (-45, 188))
                .add_layer()
                .add_component("A", (0, 0))
                .add_component("acutecomb", (-66, 200))
            ),
        )
        .build()
    )
    propagate_all_anchors_impl(glyphs)

    new_glyph = glyphs["Aacute"]
    assert_anchors(
        new_glyph.layers[0].anchors,
        [
            ("bottom", (290, 10)),
            ("ogonek", (490, 3)),
            ("top", (308, 909)),
        ],
    )

    assert_anchors(
        new_glyph.layers[1].anchors,
        [
            ("bottom", (300, 0)),
            ("ogonek", (540, 10)),
            ("top", (300, 965)),
        ],
    )


def test_remove_exit_anchor_on_component():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph("comma", lambda glyph: ())
        .add_glyph(
            "ain-ar.init",
            lambda glyph: (
                glyph.add_anchor("top", (294, 514)).add_anchor("exit", (0, 0))
            ),
        )
        .add_glyph(
            "ain-ar.init.alt",
            lambda glyph: (
                glyph.add_component("ain-ar.init", (0, 0)).add_component(
                    "comma", (0, 0)
                )
            ),
        )
        .build()
    )
    propagate_all_anchors_impl(glyphs)

    new_glyph = glyphs["ain-ar.init.alt"]
    assert_anchors(new_glyph.layers[0].anchors, [("top", (294, 514))])


def test_component_anchor():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph(
            "acutecomb",
            lambda glyph: (
                glyph.add_anchor("_top", (150, 580)).add_anchor("top", (170, 792))
            ),
        )
        .add_glyph(
            "aa",
            lambda glyph: (
                glyph.add_anchor("bottom_1", (218, 8))
                .add_anchor("bottom_2", (742, 7))
                .add_anchor("ogonek_1", (398, 9))
                .add_anchor("ogonek_2", (902, 9))
                .add_anchor("top_1", (227, 548))
                .add_anchor("top_2", (746, 548))
            ),
        )
        .add_glyph(
            "a_a",
            lambda glyph: glyph.add_component("aa", (0, 0)),
        )
        .add_glyph(
            "a_aacute",
            lambda glyph: (
                glyph.add_component("a_a", (0, 0))
                .add_component("acutecomb", (596, -32))
                .add_component_anchor("top_2")
            ),
        )
        .build()
    )
    propagate_all_anchors_impl(glyphs)

    new_glyph = glyphs["a_aacute"]
    assert_anchors(
        new_glyph.layers[0].anchors,
        [
            ("bottom_1", (218, 8)),
            ("bottom_2", (742, 7)),
            ("ogonek_1", (398, 9)),
            ("ogonek_2", (902, 9)),
            ("top_1", (227, 548)),
            ("top_2", (766, 760)),
        ],
    )


def test_origin_anchor():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph(
            "a",
            lambda glyph: (
                glyph.add_anchor("*origin", (-20, 0))
                .add_anchor("bottom", (242, 7))
                .add_anchor("ogonek", (402, 9))
                .add_anchor("top", (246, 548))
            ),
        )
        .add_glyph(
            "acutecomb",
            lambda glyph: (
                glyph.add_anchor("_top", (150, 580)).add_anchor("top", (170, 792))
            ),
        )
        .add_glyph(
            "aacute",
            lambda glyph: (
                glyph.add_component("a", (0, 0)).add_component("acutecomb", (116, -32))
            ),
        )
        .build()
    )
    propagate_all_anchors_impl(glyphs)

    new_glyph = glyphs["aacute"]
    assert_anchors(
        new_glyph.layers[0].anchors,
        [
            ("bottom", (262, 7)),
            ("ogonek", (422, 9)),
            ("top", (286, 760)),
        ],
    )


def test_invert_names_on_rotation():
    # derived from the observed behaviour of glyphs 3.2.2 (3259)
    glyphs = (
        GlyphSetBuilder()
        .add_glyph("comma", lambda glyph: ())
        .add_glyph(
            "commaaccentcomb",
            lambda glyph: (
                glyph.add_anchor("_bottom", (289, 0))
                .add_anchor("mybottom", (277, -308))
                .add_component("comma", (9, -164))
            ),
        )
        .add_glyph(
            "commaturnedabovecomb",
            lambda glyph: (
                glyph.add_component("commaaccentcomb", (589, 502)).rotate_component(180)
            ),
        )
        .build()
    )
    propagate_all_anchors_impl(glyphs)

    new_glyph = glyphs["commaturnedabovecomb"]
    assert_anchors(
        new_glyph.layers[0].anchors,
        [("_top", (300, 502)), ("mytop", (312, 810))],
    )


def test_affine_scale():
    assert get_xy_rotation(Affine().translate(589, 502).rotate(math.radians(180))) == (
        -1,
        -1,
    )
    assert get_xy_rotation(Affine().translate(10, 10)) == (1, 1)
    assert get_xy_rotation(Affine().scale(1, -1)) == (1, -1)
    assert get_xy_rotation(Affine().scale(-1, 1)) == (-1, 1)
    assert get_xy_rotation(
        Affine().translate(589, 502).rotate(math.radians(180)).scale(-1, 1)
    ) == (
        1,
        -1,
    )


def test_real_files():
    # the tricky parts of these files have been factored out into separate tests,
    # but we'll keep them in case there are other regressions lurking
    expected = GSFont(os.path.join(DATA, "PropagateAnchorsTest-propagated.glyphs"))
    font = GSFont(os.path.join(DATA, "PropagateAnchorsTest.glyphs"))

    propagate_all_anchors(font)

    assert len(font.glyphs) == len(expected.glyphs)
    assert [g.name for g in font.glyphs] == [g.name for g in expected.glyphs]
    for g1, g2 in zip(font.glyphs, expected.glyphs):
        assert len(g1.layers) == len(g2.layers)
        for l1, l2 in zip(g1.layers, g2.layers):
            assert [(a.name, tuple(a.position)) for a in l1.anchors] == [
                (a.name, tuple(a.position)) for a in l2.anchors
            ]
