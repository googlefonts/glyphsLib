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

from __future__ import print_function, division, absolute_import, unicode_literals

from glyphsLib import types
from glyphsLib import classes


def to_ufo_paths(self, ufo_glyph, layer):
    """Draw .glyphs paths onto a pen."""
    pen = ufo_glyph.getPointPen()

    for path in layer.paths:
        # the list is changed below, otherwise you can't draw more than once
        # per session.
        nodes = list(path.nodes)
        for node in nodes:
            self.to_ufo_node_user_data(ufo_glyph, node)

        pen.beginPath()
        if not nodes:
            pen.endPath()
            continue
        if not path.closed:
            node = nodes.pop(0)
            assert node.type == "line", "Open path starts with off-curve points"
            pen.addPoint(tuple(node.position), segmentType="move")
        else:
            # In Glyphs.app, the starting node of a closed contour is always
            # stored at the end of the nodes list.
            nodes.insert(0, nodes.pop())
        for node in nodes:
            node_type = _to_ufo_node_type(node.type)
            pen.addPoint(
                tuple(node.position), segmentType=node_type, smooth=node.smooth
            )
        pen.endPath()


def to_glyphs_paths(self, ufo_glyph, layer):
    for contour in ufo_glyph:
        path = self.glyphs_module.GSPath()
        for point in contour:
            node = self.glyphs_module.GSNode()
            node.position = types.Point(point.x, point.y)
            node.type = _to_glyphs_node_type(point.segmentType)
            node.smooth = point.smooth
            node.name = point.name
            path.nodes.append(node)
        path.closed = not contour.open
        if not contour.open:
            path.nodes.append(path.nodes.pop(0))
        layer.paths.append(path)

        for node in path.nodes:
            self.to_glyphs_node_user_data(ufo_glyph, node)


def _to_ufo_node_type(node_type):
    if node_type not in ["line", "curve", "qcurve"]:
        return None
    return node_type


def _to_glyphs_node_type(node_type):
    if node_type is None:
        return classes.OFFCURVE
    if node_type == "move":
        return classes.LINE
    return node_type
