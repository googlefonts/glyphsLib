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

from __future__ import (print_function, division, absolute_import,
                        unicode_literals)


def to_ufo_draw_paths(self, pen, paths):
    """Draw .glyphs paths onto a pen."""

    for path in paths:
        pen.beginPath()
        nodes = list(path.nodes) # the list is changed below, otherwise you can't draw more than once per session.

        if not nodes:
            pen.endPath()
            continue
        if not path.closed:
            node = nodes.pop(0)
            assert node.type == 'line', 'Open path starts with off-curve points'
            pen.addPoint(tuple(node.position), segmentType='move')
        else:
            # In Glyphs.app, the starting node of a closed contour is always
            # stored at the end of the nodes list.
            nodes.insert(0, nodes.pop())
        for node in nodes:
            node_type = node.type
            if node_type not in ['line', 'curve', 'qcurve']:
                node_type = None
            pen.addPoint(tuple(node.position), segmentType=node_type, smooth=node.smooth)
        pen.endPath()
