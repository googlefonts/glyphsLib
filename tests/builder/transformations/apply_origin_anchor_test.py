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
from glyphsLib.builder import preflight_glyphs
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


def test_preflight_does_not_apply_origin_twice_to_synthesized_bracket_layers():
    """A bracket layer synthesized from an origin-shifted master is not a new shift.

    ``align_alternate_layers`` deliberately uses a shallow copy when it creates
    a missing bracket layer. If ``apply_origin_anchor`` runs afterwards, both
    layers see the shared path and translate it. The master outline must still
    move only once.
    """
    font = GSFont()
    font.format_version = 3
    _add_master(font)

    component = GSGlyph()
    component.name = "A"
    component.category = "Letter"
    component.subCategory = "Uppercase"
    component_master = GSLayer()
    component_master.layerId = component_master.associatedMasterId = "m01"
    component.layers.append(component_master)
    component_bracket = GSLayer()
    component_bracket.layerId = "component-bracket"
    component_bracket.associatedMasterId = "m01"
    component_bracket.attributes["axisRules"] = [{"min": 500}]
    component.layers.append(component_bracket)
    font.glyphs.append(component)

    composite = GSGlyph()
    composite.name = "Aacute"
    composite.category = "Letter"
    composite.subCategory = "Uppercase"
    composite_master = GSLayer()
    composite_master.layerId = composite_master.associatedMasterId = "m01"
    composite_master.paths.append(_square())
    composite_master.components.append(GSComponent("A", offset=(300, 0)))
    composite_master.anchors.append(_origin(10, 0))
    composite_master.anchors.append(GSAnchor("top", Point(500, 700)))
    composite.layers.append(composite_master)
    font.glyphs.append(composite)

    preflight_glyphs(font)

    assert len([layer for layer in composite.layers if layer._is_bracket_layer()]) == 1
    assert [
        (node.position.x, node.position.y) for node in composite_master.paths[0].nodes
    ] == [
        (90, 0),
        (290, 0),
        (290, 200),
        (90, 200),
    ]
    # Components and anchors are shared with the synthesized layer as well.
    assert composite_master.components[0].position == Point(290, 0)
    assert composite_master.anchors["top"].position == Point(490, 700)
