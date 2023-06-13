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


from glyphsLib.types import Point
import uuid

from glyphsLib.builder.constants import OBJECT_LIBS_KEY

__all__ = [
    "to_ufo_glyph_anchors",
    "to_glyphs_glyph_anchors",
]


def to_ufo_glyph_anchors(self, glyph, anchors):
    """Add .glyphs anchors to a glyph."""

    for anchor in anchors:
        x, y = anchor.position
        anchor_dict = {"name": anchor.name, "x": x, "y": y}
        if anchor.userData:
            identifier = str(uuid.uuid4()).upper()
            anchor_dict["identifier"] = identifier
            glyph.lib.setdefault(OBJECT_LIBS_KEY, {})[identifier] = dict(
                anchor.userData
            )
        glyph.appendAnchor(anchor_dict)


def to_glyphs_glyph_anchors(self, ufo_glyph, layer):
    """Add UFO glif anchors to a GSLayer."""
    for ufo_anchor in ufo_glyph.anchors:
        anchor = self.glyphs_module.GSAnchor()
        anchor.name = ufo_anchor.name
        anchor.position = Point(ufo_anchor.x, ufo_anchor.y)
        layer.anchors.append(anchor)
