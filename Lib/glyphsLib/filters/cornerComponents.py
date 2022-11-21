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
    segmentSegmentIntersections,
)
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.misc.roundTools import otRound
from ufo2ft.filters import BaseFilter
from ufoLib2.objects import Glyph

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


def closest_point_on_segment(seg, pt):
    # Everything here is a tuple
    if len(seg) == 4:
        # Cheat, closest point on a bezier is a nightmare
        seg = seg[0:2]
    # Closest point on line
    a, b = seg
    a_to_b = (b[0] - a[0], b[1] - a[1])
    a_to_pt = (pt[0] - a[0], pt[1] - a[1])
    mag = a_to_b[0] ** 2 + a_to_b[1] ** 2
    if mag == 0:
        return a
    atp_dot_atb = a_to_pt[0] * a_to_b[0] + a_to_pt[1] * a_to_b[1]
    t = atp_dot_atb / mag
    return (a[0] + a_to_b[0] * t, a[1] + a_to_b[1] * t)


class Alignment(IntEnum):
    LEFT = 0
    RIGHT = 1
    MIDDLE = 2
    UNUSED = 3
    UNALIGNED = 4


# Using a class here is mild overkill but it allows us to store
# the information about the component in a slightly more readable
# manner.
@dataclass
class CornerComponentApplier:
    corner_name: str
    glyph_name: str
    alignment: Alignment
    glyph: object
    path_index: int
    corner_path: object
    other_paths: list
    target_node: object
    target_node_ix: int = None
    origin: (int, int) = (0, 0)
    scale: (int, int) = None
    left_x: int = 0
    right_x: int = 0

    def fail(self, msg, hard=True):
        full_msg = f"{msg} (corner {self.corner_name} in {self.glyph_name})"
        if hard:
            raise ValueError(full_msg)
        else:
            logger.error(full_msg)

    @property
    def instroke(self):
        return get_previous_segment(self.path, self.target_node_ix)

    @property
    def outstroke(self):
        return get_next_segment(self.path, self.target_node_ix)

    @property
    def outstroke_as_tuples(self):
        return tuple((pt.x, pt.y) for pt in self.outstroke)

    @property
    def first_seg(self):
        return get_next_segment(self.corner_path, 0)

    @property
    def last_seg(self):
        return get_previous_segment(self.corner_path, len(self.corner_path) - 1)

    @property
    def last_seg_as_tuples(self):
        return tuple((pt.x, pt.y) for pt in self.last_seg)

    def apply(self):
        self.path = self.glyph[self.path_index]
        # Find our selves in this path
        for ix, node in enumerate(self.path):
            if node == self.target_node:
                self.target_node_ix = ix
        if self.target_node_ix is None:
            self.fail("Lost track of where the corner should be applied")

        if self.corner_path[0].x != self.origin[0]:
            self.fail(
                "Can't deal with offset instrokes yet; start corner components on axis"
            )

        # Determine scale
        self.flipped = False
        if self.scale is not None:
            self.flipped = (self.scale[0] * self.scale[1]) < 0
            self.scale_paths()

        self.align_my_path_to_main_path()

        # Deal with instroke/firstseg
        intersection1 = self.find_instroke_intersection_point()
        intersection2 = self.find_outstroke_intersection_point()
        original_outstroke = self.outstroke_as_tuples

        self.split_instroke(intersection1)
        # The instroke of the corner path may need stretching to fit...
        if len(self.first_seg) == 4:
            self.stretch_first_seg_to_fit(intersection1)

        self.path[self.target_node_ix + 1 : self.target_node_ix + 1] = [
            otRoundNode(node) for node in self.corner_path[1:]
        ]
        self.fixup_outstroke(original_outstroke, intersection2)
        self.insert_other_paths()

    def scale_paths(self):
        scaling = Affine.scale(*self.scale)
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = scaling * (pt.x, pt.y)

    def align_my_path_to_main_path(self):
        # First align myself to the "origin" anchor.
        for pt in self.corner_path:
            pt.x, pt.y = pt.x - self.origin[0], pt.y - self.origin[1]

        # Work out my rotation (1): Rotation occurring due to corner paths
        angle = math.atan2(-self.corner_path[-1].y, self.corner_path[-1].x)

        if self.flipped:
            self.reverse_corner_path()
            angle += math.radians(90)

        # Work out my rotation (2): Rotation occurring due to host paths
        outstroke_angle = math.atan2(
            self.outstroke[1].y - self.outstroke[0].y,
            self.outstroke[1].x - self.outstroke[0].x,
        )
        instroke_angle = (
            math.atan2(
                self.instroke[1].y - self.instroke[0].y,
                self.instroke[1].x - self.instroke[0].x,
            )
            + math.radians(90)
        )

        if self.alignment == Alignment.LEFT:
            if len(self.outstroke) == 4:
                self.fail(
                    "Can't reliably compute rotation angle to fit corner to a curved outstroke",
                    hard=False,
                )
            angle += outstroke_angle
        elif self.alignment == Alignment.RIGHT:
            if len(self.instroke) == 4:
                self.fail(
                    "Can't reliably compute rotation angle to fit corner to a curved instroke",
                    hard=False,
                )
            angle += instroke_angle
        elif self.alignment == Alignment.MIDDLE:
            angle += (instroke_angle + outstroke_angle) / 2
        else:  # Unaligned, do nothing
            pass

        rot = Affine.rotation(math.degrees(angle))
        translation = Affine.translation(self.target_node.x, self.target_node.y)

        # Rotate the paths around the origin
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = (translation * rot) * (pt.x, pt.y)

    def find_instroke_intersection_point(self):
        # Find intersection between instroke and (extended) first_seg
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
        return self.solve_intersection(aligned_curve, instroke_as_tuples)

    def find_outstroke_intersection_point(self):
        if self.flipped:
            # Project it
            aligned_curve = apply_fonttools_transform(
                _alignment_transformation(self.last_seg_as_tuples),
                self.outstroke,
            )
            return self.solve_intersection(aligned_curve, self.outstroke_as_tuples)

        # Bend it
        return closest_point_on_segment(
            self.outstroke_as_tuples,
            (self.corner_path[-1].x, self.corner_path[-1].y),
        )

    def solve_intersection(self, aligned_curve, stroke_as_tuples):
        if len(aligned_curve) == 4:
            a, b, c, d = calcCubicParameters(*[(pt.x, pt.y) for pt in aligned_curve])
            intersections = solveCubic(a[1], b[1], c[1], d[1])
            intersection = cubicPointAtT(*stroke_as_tuples, intersections[0])
        elif not math.isclose(aligned_curve[0].y, aligned_curve[1].y):
            t = aligned_curve[0].y / (aligned_curve[0].y - aligned_curve[1].y)
            intersection = linePointAtT(*stroke_as_tuples, t)
        elif not math.isclose(aligned_curve[0].x, aligned_curve[1].x):
            t = aligned_curve[0].x / (aligned_curve[0].x - aligned_curve[1].x)
            intersection = linePointAtT(*stroke_as_tuples, t)
        else:
            self.fail("Couldn't solve for intersection")

        return intersection

    def split_instroke(self, intersection):
        # Split the instroke at the intersection.
        if len(self.instroke) == 2:
            # Splitting a line is easy...
            (
                self.path[self.target_node_ix].x,
                self.path[self.target_node_ix].y,
            ) = otRound(intersection[0]), otRound(intersection[1])
        else:
            # There's a horrible edge case here where the curve wraps around and
            # the ray hits twice, but I'm not worrying about it.
            instroke_as_tuples = tuple((pt.x, pt.y) for pt in self.instroke)
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

    def fixup_outstroke(self, original_outstroke, intersection):
        # Split the outstroke at the nearest point to the intersection.
        # The outstroke has moved now, since we have inserted the path
        outstroke = get_previous_segment(
            self.path, (self.target_node_ix + len(self.corner_path)) % len(self.path)
        )

        if len(outstroke) == 2:
            # Splitting a line is easy...
            (outstroke[0].x, outstroke[0].y) = otRound(intersection[0]), otRound(
                intersection[1]
            )
        else:
            # There's a horrible edge case here where the curve wraps around and
            # the ray hits twice, but I'm not worrying about it.
            new_cubics_1 = splitCubic(
                *self.outstroke_as_tuples, intersection[0], False
            )[0]
            new_cubics_2 = splitCubic(*self.outstroke_as_tuples, intersection[1], True)[
                0
            ]
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

            for new_pt, old in zip(new_cubic, outstroke):
                old.x, old.y = otRound(new_pt[0]), otRound(new_pt[1])

    def stretch_first_seg_to_fit(self, intersection):
        delta = (
            intersection[0] - self.first_seg[0].x,
            intersection[1] - self.first_seg[0].y,
        )
        self.first_seg[1].x += delta[0]
        self.first_seg[1].y += delta[1]

    def reverse_corner_path(self):
        new_glyph = Glyph()
        self.corner_path.draw(ReverseContourPen(new_glyph.getPen()))
        self.corner_path[:] = new_glyph[0]

    def insert_other_paths(self):
        for path in self.other_paths:
            for node in path:
                otRoundNode(node)
            self.glyph.contours.append(path)


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

        todo_list = []

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
            cc_anchor_dict = {anchor.name: anchor for anchor in layer.anchors}
            if "origin" in cc_anchor_dict:
                cc_origin = cc_anchor_dict["origin"].x, cc_anchor_dict["origin"].y
            else:
                cc_origin = (0, 0)

            corner_path = copy.deepcopy(layer[0])
            other_paths = [copy.deepcopy(path) for path in layer[1:]]

            cc = CornerComponentApplier(
                glyph_name=glyph.name,
                corner_name=glyphs_cc["name"],
                alignment=Alignment(glyphs_cc.get("options", 0)),
                scale=glyphs_cc.get("scale"),
                corner_path=corner_path,
                other_paths=other_paths,
                path_index=path_idx,
                glyph=glyph,
                origin=cc_origin,
                # We pass in the current starting node, because its
                # position may change if we apply more than one corner.
                target_node=glyph[path_idx][(node_idx + 1) % len(glyph[path_idx])],
            )
            todo_list.append(cc)

        for cc in todo_list:
            cc.apply()

        return True
