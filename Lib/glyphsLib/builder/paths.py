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


import logging

from glyphsLib import GSPath, types
from glyphsLib.pens import (
    _drop_offcurves_before_lines,
    _to_glyphs_node_type,
    _to_ufo_node_type,
)

logger = logging.getLogger(__name__)


def to_ufo_paths(self, ufo_glyph, layer):
    """Draw paths and return old-to-new node indices for pruned contours."""
    pen = ufo_glyph.getPointPen()
    node_index_maps = {}

    # Hint references count components as well as paths in the shape index.
    for shape_index, path in enumerate(layer.shapes):
        if not isinstance(path, GSPath):
            continue
        # the list is changed below, otherwise you can't draw more than once
        # per session.
        nodes = list(path.nodes)

        pen.beginPath()

        if not nodes:
            pen.endPath()
            continue

        if not path.closed:
            assert nodes[0].type == "line", "Open path starts with off-curve points"

        kept = _drop_offcurves_before_lines(nodes, path.closed)
        node_indices = None
        if len(kept) != len(nodes):
            logger.warning(
                "Dropping off-curve points before line points "
                "in glyph '%s', layer '%s'",
                ufo_glyph.name,
                layer.layerId,
            )
            nodes = kept
            node_indices = {id(node): i for i, node in enumerate(nodes)}
            node_index_maps[shape_index] = {
                i: node_indices[id(node)]
                for i, node in enumerate(path.nodes)
                if id(node) in node_indices
            }

        if not path.closed:
            node = nodes.pop(0)
            pen.addPoint(
                tuple(node.position),
                segmentType="move",
                name=node.userData.get("name"),
                identifier=node.userData.get("UFO.identifier"),
            )
        else:
            # In Glyphs.app, the starting node of a closed contour is always
            # stored at the end of the nodes list.
            nodes.insert(0, nodes.pop())

        for node in nodes:
            node_type = _to_ufo_node_type(node.type)
            pen.addPoint(
                tuple(node.position),
                segmentType=node_type,
                smooth=node.smooth,
                name=node.userData.get("name"),
                identifier=node.userData.get("UFO.identifier"),
            )
            # NOTE: Can't do path_index, node_index through enumeration here because we
            # might have changed node order.
            # A node's name will be stored as a UFO point's name attribute, so filter
            # it from the Glyph node user data to avoid storing duplicate information.
            node_user_data = {
                k: v
                for k, v in node.userData.items()
                if k not in ("UFO.identifier", "name")
            }
            self.to_ufo_node_user_data(
                ufo_glyph,
                node,
                node_user_data,
                node_index=node_indices[id(node)] if node_indices else None,
            )
        pen.endPath()

    return node_index_maps


def to_glyphs_paths(self, ufo_glyph, layer):
    # Keep track of path and node numbers, otherwise to_glyphs_node_user_data must
    # call _indices on every single GSNode, which is a huge performance drain.
    for contour_index, contour in enumerate(ufo_glyph):
        path = self.glyphs_module.GSPath()
        for point in contour:
            node = self.glyphs_module.GSNode()
            node.position = types.Point(point.x, point.y)
            node.type = _to_glyphs_node_type(point.segmentType)
            node.smooth = point.smooth
            node.name = point.name
            if point.identifier is not None:
                node.userData["UFO.identifier"] = point.identifier
            path.nodes.append(node)
        path.closed = not contour.open
        if not contour.open:
            path.nodes.append(path.nodes.pop(0))
        layer.paths.append(path)

        for node_index, node in enumerate(path.nodes):
            self.to_glyphs_node_user_data(ufo_glyph, node, contour_index, node_index)
