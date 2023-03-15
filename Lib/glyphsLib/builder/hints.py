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


from .constants import HINTS_LIB_KEY
from glyphsLib.types import IndexPath
from glyphsLib.types import Point


def to_ufo_hints(self, ufo_glyph, layer):
    if not hasattr(layer, "hints"):
        return
    hints = []
    for source in layer.hints:
        hint = {}
        for name in ["horizontal", "options", "stem", "type", "name"]:
            hint[name] = getattr(source, name, None)
        for name in ["origin", "other1", "other2", "target"]:
            index_path = getattr(source, name, None)
            if index_path:
                if name == "target" and index_path.value in (["up"], ["down"]):
                    hint[name] = index_path.value[0]
                elif not any(value is None for value in index_path):
                    hint[name] = index_path.value
        for name in ["place", "scale"]:
            point = getattr(source, name, None)
            if point and not any(value is None for value in point):
                hint[name] = point.value
        hints.append(hint)
    if hints:
        ufo_glyph.lib[HINTS_LIB_KEY] = hints


def to_glyphs_hints(self, ufo_glyph, layer):
    if HINTS_LIB_KEY not in ufo_glyph.lib:
        return
    for source in ufo_glyph.lib[HINTS_LIB_KEY]:
        hint = self.glyphs_module.GSHint()
        for name in ["horizontal", "options", "stem", "type", "name"]:
            setattr(hint, name, source[name])
        for name in ["origin", "other1", "other2", "target"]:
            if name in source:
                value = source[name]
                # https://github.com/googlefonts/glyphsLib/pull/613
                # handle target = ['u', 'p'] or ['d', 'o', 'w', 'n']
                if name == "target" and value in ([list("down")], [list("up")]):
                    value = ["".join(value)]
                setattr(hint, name, IndexPath(*value))
        for name in ["place", "scale"]:
            if name in source:
                setattr(hint, name, Point(*source[name]))
        layer.hints.append(hint)
