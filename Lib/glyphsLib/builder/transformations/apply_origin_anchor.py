"""Shift glyphs by the special “*origin” anchor.

On export, Glyphs.app shifts a glyph layer's outline (paths, components and
other anchors) by the negative of its “*origin” anchor position. This code
tries to do the same.
"""

from glyphsLib.types import Point


def apply_origin_anchor(font, *, glyph_data=None):
    """Shift each layer that has an "*origin" anchor and remove the anchor."""
    for glyph in font.glyphs:
        for layer in glyph.layers:
            origin = next((a for a in layer.anchors if a.name == "*origin"), None)
            if origin is None:
                continue

            dx, dy = -origin.position.x, -origin.position.y
            if dx or dy:
                for path in layer.paths:
                    path.applyTransform([1, 0, 0, 1, dx, dy])
                for component in layer.components:
                    pos = component.position
                    component.position = Point(pos.x + dx, pos.y + dy)
                for anchor in layer.anchors:
                    if anchor.name != "*origin":
                        pos = anchor.position
                        anchor.position = Point(pos.x + dx, pos.y + dy)

            # We already adjusted the anchors, if we keep “*origin” anchor,
            # propagate_anchors will double-adjust them. This makes “*origin”
            # anchor handling in propagate_anchors effectively dead, but lets
            # keep it for parity with Glyphs/fontc sources.
            layer.anchors = [a for a in layer.anchors if a.name != "*origin"]
