import copy
from dataclasses import dataclass
from enum import IntEnum
import logging
import math

from fontTools.misc.bezierTools import (
    _alignment_transformation,
    calcCubicParameters,
    solveCubic,
    cubicPointAtT,
    linePointAtT,
    splitCubic,
)
from fontTools.misc.roundTools import otRound
from ufo2ft.filters import BaseFilter

from glyphsLib.builder.constants import HINTS_LIB_KEY
from glyphsLib.affine import Affine


logger = logging.getLogger(__name__)

# Notes on corner components:
# Insertion index may be path,node,path,node - overlap component
# Left and right anchors are swapped when flipped
# Simple case: start at X=0, end at Y=0
# If start X!=0 or end Y !=0, offset is applied to host path start/end
#  nodes
# left is instroke, right is angle
# Y of "left" anchor is "thickness"
# X of "left" is offset from host path
# left computes origin and also sets offset from host path
# Divides curve at top of the corner
# It's only the first and last segments of the corner component that
# are fitted to the curve


def otRoundNode(node):
    node.x, node.y = otRound(node.x), otRound(node.y)
    return node


def get_next_segment(path, index):
    seg = [path[index]]
    index = (index + 1) % len(path)
    seg.append(path[index])
    if not seg[-1].type:
        index = (index + 1) % len(path)
        seg.append(path[index])
        index = (index + 1) % len(path)
        seg.append(path[index])
    return seg


def get_previous_segment(path, index):
    seg = [path[index]]
    index = (index - 1) % len(path)
    seg.append(path[index])
    if not seg[-1].type:
        index = (index - 1) % len(path)
        seg.append(path[index])
        index = (index - 1) % len(path)
        seg.append(path[index])
    return list(reversed(seg))


def apply_fonttools_transform(transform, seg):
    newseg = copy.deepcopy(seg)
    for pt in newseg:
        pt.x, pt.y = transform.transformPoint((pt.x, pt.y))
    return newseg


class Alignment(IntEnum):
    LEFT = 0
    MIDDLE = 1
    RIGHT = 2
    UNUSED = 3
    UNALIGNED = 4


# Using a class here is mild overkill but it allows us to store
# the information about the component in a slightly more readable
# manner.
@dataclass
class CornerComponentApplier:
    name: str  # For debugging
    alignment: Alignment
    path: object
    corner_path: object
    target_node_ix: int
    origin: (int, int) = (0, 0)
    left_x: int = 0
    right_x: int = 0

    @property
    def target_node(self):
        return self.path[self.target_node_ix]

    @property
    def instroke(self):
        return get_previous_segment(self.path, self.target_node_ix)

    @property
    def outstroke(self):
        return get_next_segment(self.path, self.target_node_ix)

    @property
    def first_seg(self):
        return get_next_segment(self.corner_path, 0)

    @property
    def last_seg(self):
        return get_previous_segment(self.corner_path, len(self.corner_path) - 1)

    def apply(self):
        if self.corner_path[0].x != self.origin[0]:
            raise ValueError(
                "Can't deal with offset instrokes yet; start corner components on axis"
            )
        if self.corner_path[-1].y != self.origin[1]:
            raise ValueError(
                "Can't deal with offset outstrokes yet; end corner components on axis"
            )
        self.align_my_path_to_main_path()

        # Find intersection between instroke and extended first_seg
        # Because this is potentially unbounded we can't use the stuff in
        # fontTools. If the first segment in the corner component is
        # a curve, we treat it as a line between the first node and first
        # offcurve
        first_seg_as_tuples = tuple((pt.x, pt.y) for pt in self.first_seg[0:2])
        instroke_as_tuples = tuple((pt.x, pt.y) for pt in self.instroke)
        aligned_curve = apply_fonttools_transform(
            _alignment_transformation(first_seg_as_tuples),
            self.instroke,
        )

        if len(aligned_curve) == 4:
            a, b, c, d = calcCubicParameters(*[(pt.x, pt.y) for pt in aligned_curve])
            intersections = solveCubic(a[1], b[1], c[1], d[1])
            intersection = cubicPointAtT(*instroke_as_tuples, intersections[0])
        elif not math.isclose(aligned_curve[0].y, aligned_curve[1].y):
            t = aligned_curve[0].y / (aligned_curve[0].y - aligned_curve[1].y)
            intersection = linePointAtT(*instroke_as_tuples, t)

        # Split the instroke at the intersection, fix up, and paste it in.
        if len(instroke_as_tuples) == 2:
            # Splitting a line is easy...
            (
                self.path[self.target_node_ix].x,
                self.path[self.target_node_ix].y,
            ) = otRound(intersection[0]), otRound(intersection[1])
        else:
            # There's a horrible edge case here where the curve wraps around and
            # the ray hits twice, but I'm not worrying about it.
            new_cubics_1 = splitCubic(*instroke_as_tuples, intersection[0], False)[0]
            new_cubics_2 = splitCubic(*instroke_as_tuples, intersection[1], True)[0]
            # Choose the one closest to the intersection point
            d1 = (new_cubics_1[-1][0] - intersection[0]) ** 2 + (
                new_cubics_1[-1][1] - intersection[1]
            ) ** 2
            d2 = (new_cubics_2[-1][0] - intersection[0]) ** 2 + (
                new_cubics_2[-1][1] - intersection[1]
            ) ** 2
            if d1 < d2:
                new_cubic = new_cubics_1
            else:
                new_cubic = new_cubics_2

            for new_pt, old in zip(new_cubic, self.instroke):
                old.x, old.y = otRound(new_pt[0]), otRound(new_pt[1])
        self.path[self.target_node_ix + 1 : self.target_node_ix + 1] = [
            otRoundNode(node) for node in self.corner_path[1:]
        ]

        # Fix up outstroke

    def align_my_path_to_main_path(self):
        # First align myself to the "origin" anchor.
        for pt in self.corner_path:
            pt.x, pt.y = pt.x - self.origin[0], pt.y + self.origin[1]

        # Work out my rotation
        if self.alignment == Alignment.LEFT:
            outstroke = self.outstroke
            outstroke_angle = math.atan2(
                outstroke[1].y - outstroke[0].y, outstroke[1].x - outstroke[0].x
            )
            rot = Affine.rotation(math.degrees(outstroke_angle))
            # Rotate the whole path around the origin
            for pt in self.corner_path:
                pt.x, pt.y = rot * (pt.x, pt.y)

        elif self.alignment == Alignment.MIDDLE:
            raise NotImplementedError
        elif self.alignment == Alignment.RIGHT:
            raise NotImplementedError
        elif self.alignment == Alignment.UNUSED:
            raise NotImplementedError
        elif self.alignment == Alignment.UNALIGNED:
            pass  # right?

        # Now position our path onto the point.
        for pt in self.corner_path:
            pt.x, pt.y = pt.x + self.target_node.x, pt.y + self.target_node.y


class CornerComponentsFilter(BaseFilter):
    def filter(self, glyph):
        if not len(glyph) or HINTS_LIB_KEY not in glyph.lib:
            return False

        corner_components = [
            hint
            for hint in glyph.lib[HINTS_LIB_KEY]
            if hint.get("type").upper() == "CORNER"
        ]

        if not corner_components:
            return False

        for glyphs_cc in corner_components:
            path_idx, node_idx = glyphs_cc["origin"]
            # We use font, not .glyphSet here because corner components
            # aren't normally exported
            if glyphs_cc["name"] not in self.context.font:
                logger.warn(
                    "Corner component %s in %s not found",
                    glyphs_cc["name"],
                    glyph.name,
                )
                continue
            layer = self.context.font[glyphs_cc["name"]]
            if len(layer) > 1:
                logger.warn(
                    "Corner components of more than one path (%s in %s) not supported",
                    glyphs_cc["name"],
                    glyph.name,
                )
                continue

            corner_path = copy.deepcopy(layer[0])
            if "scale" in glyphs_cc:
                scaling = Affine.scale(*glyphs_cc["scale"])
                for pt in corner_path:
                    pt.x, pt.y = scaling * (pt.x, pt.y)

            cc = CornerComponentApplier(
                name=glyph.name,
                alignment=Alignment(glyphs_cc.get("options", 0)),
                corner_path=corner_path,
                target_node_ix=(node_idx + 1) % len(glyph[path_idx]),
                path=glyph[path_idx],
            )
            cc.apply()

        return True
