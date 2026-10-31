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

from glyphsLib.util import pairs


def blues_from_alignment_zones(zones):
    """Return the blue values and other blues of Glyphs alignment zones:
    zones below the baseline are other blues."""

    # Glyphs ignores zero-height zones and emits each zone only once.
    alignment_zones = sorted(
        {(zone.position, zone.size) for zone in zones if zone.size}
    )
    blue_values = []
    other_blues = []
    for pos, size in alignment_zones:
        val_list = blue_values if pos == 0 or size >= 0 else other_blues
        val_list.extend(sorted((pos, pos + size)))
    return blue_values, other_blues


def to_ufo_blue_values(self, ufo, master):
    """Set postscript blue values from Glyphs alignment zones."""

    blue_values, other_blues = blues_from_alignment_zones(master.alignmentZones)
    if blue_values:
        ufo.info.postscriptBlueValues = blue_values
    if other_blues:
        ufo.info.postscriptOtherBlues = other_blues


def alignment_zones_from_blues(blue_values, other_blues):
    """Return the positions and sizes of the Glyphs alignment zones of blue
    values and other blues, from the top down."""

    zones = []
    for y1, y2 in pairs(blue_values or []):
        size = y2 - y1
        if y2 == 0:
            pos = 0
            size = -size
        else:
            pos = y1
        zones.append((pos, size))
    for y1, y2 in pairs(other_blues or []):
        zones.append((y2, y1 - y2))
    return sorted(zones, key=lambda zone: -zone[0])


def to_glyphs_blue_values(self, ufo, master):
    """Sets the GSFontMaster alignmentZones from the postscript blue values."""

    master.alignmentZones = [
        self.glyphs_module.GSAlignmentZone(pos, size)
        for pos, size in alignment_zones_from_blues(
            ufo.info.postscriptBlueValues, ufo.info.postscriptOtherBlues
        )
    ]
