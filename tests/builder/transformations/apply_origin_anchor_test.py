from __future__ import annotations

from glyphsLib.classes import (
    GSAnchor,
    GSComponent,
    GSFont,
    GSFontMaster,
    GSGlyph,
    GSLayer,
    GSNode,
    GSPath,
)
from glyphsLib.builder.transformations.apply_origin_anchor import apply_origin_anchor
from glyphsLib.types import Point


def _add_master(font):
    master = GSFontMaster()
    master.id = "m01"
    font.masters.append(master)
    return master


def _square():
    path = GSPath()
    path.nodes = [
        GSNode(position=(100, 0), nodetype="line"),
        GSNode(position=(300, 0), nodetype="line"),
        GSNode(position=(300, 200), nodetype="line"),
        GSNode(position=(100, 200), nodetype="line"),
    ]
    path.closed = True
    return path


def _glyph(font, name):
    glyph = GSGlyph()
    glyph.name = name
    layer = GSLayer()
    layer.layerId = layer.associatedMasterId = "m01"
    layer.width = 400
    glyph.layers.append(layer)
    font.glyphs.append(glyph)
    return glyph.layers[0]


def _origin(x, y):
    anchor = GSAnchor()
    anchor.name = "*origin"
    anchor.position = Point(x, y)
    return anchor


def test_apply_origin_anchor_shifts_paths_and_removes_anchor():
    font = GSFont()
    _add_master(font)
    layer = _glyph(font, "markOrigin")
    layer.paths.append(_square())
    layer.anchors.append(_origin(250, 100))

    apply_origin_anchor(font)

    assert [(n.position.x, n.position.y) for n in layer.paths[0].nodes] == [
        (-150, -100),
        (50, -100),
        (50, 100),
        (-150, 100),
    ]
    assert [a.name for a in layer.anchors] == []
    assert layer.width == 400


def test_apply_origin_anchor_shifts_components_and_other_anchors():
    font = GSFont()
    _add_master(font)
    layer = _glyph(font, "compOrigin")
    layer.components.append(GSComponent("base"))  # at (0, 0)
    top = GSAnchor()
    top.name = "top"
    top.position = Point(200, 180)
    layer.anchors.append(top)
    layer.anchors.append(_origin(250, 0))

    apply_origin_anchor(font)

    assert (layer.components[0].position.x, layer.components[0].position.y) == (-250, 0)
    assert {a.name: (a.position.x, a.position.y) for a in layer.anchors} == {
        "top": (-50, 180)
    }


def test_apply_origin_anchor_leaves_glyphs_without_origin_untouched():
    font = GSFont()
    _add_master(font)
    layer = _glyph(font, "plain")
    layer.paths.append(_square())

    apply_origin_anchor(font)

    assert [(n.position.x, n.position.y) for n in layer.paths[0].nodes] == [
        (100, 0),
        (300, 0),
        (300, 200),
        (100, 200),
    ]
