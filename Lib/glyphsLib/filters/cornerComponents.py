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
    segmentPointAtT,
    splitCubic,
)
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.misc.roundTools import otRound
from fontTools.misc.transform import Transform
from ufo2ft.filters import BaseFilter
from ufoLib2.objects import Glyph

from glyphsLib.builder.constants import HINTS_LIB_KEY, SHAPE_ORDER_LIB_KEY


try:
    from math import dist
except ImportError:

    def dist(p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


logger = logging.getLogger(__name__)


class Alignment(IntEnum):
    OUTSTROKE = 0  # Glyphs calls this "left" alignment
    INSTROKE = 1  # Glyphs calls this "right" alignment
    MIDDLE = 2
    UNUSED = 3
    UNALIGNED = 4


# Lots of boring curve math stuff...


def otRoundNode(node):
    node.x, node.y = otRound(node.x), otRound(node.y)
    return node


# We often have Points (of some unknown UFO class), but fontTools
# math stuff needs tuples.
def as_tuples(pts):
    return [(pt.x, pt.y) for pt in pts]


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


def closest_point_on_segment(seg, pt):
    # Everything here is a tuple
    if len(seg) == 2:
        return closest_point_on_line(seg, pt)
    return closest_point_on_cubic(seg, pt)


def closest_point_on_line(seg, pt):
    a, b = seg
    a_to_b = (b[0] - a[0], b[1] - a[1])
    a_to_pt = (pt[0] - a[0], pt[1] - a[1])
    mag = a_to_b[0] ** 2 + a_to_b[1] ** 2
    if mag == 0:
        return a
    atp_dot_atb = a_to_pt[0] * a_to_b[0] + a_to_pt[1] * a_to_b[1]
    t = atp_dot_atb / mag
    return (a[0] + a_to_b[0] * t, a[1] + a_to_b[1] * t)


def closest_point_on_cubic(bez, pt, start=0.0, end=1.0, iterations=5, slices=5):
    tick = (end - start) / slices
    best = 0
    best_dist = float("inf")
    t = start
    best_pt = pt
    while t < end:
        this_pt = cubicPointAtT(*bez, t)
        current_distance = dist(this_pt, pt)
        if current_distance <= best_dist:
            best_dist = current_distance
            best = t
            best_pt = this_pt
        t += tick
    if iterations < 1:
        return best_pt
    return closest_point_on_cubic(
        bez,
        pt,
        start=max(best - tick, 0),
        end=min(best + tick, 1),
        iterations=iterations - 1,
        slices=slices,
    )


def unbounded_seg_seg_intersection(seg1, seg2):
    if len(seg1) == 2 and len(seg2) == 2:
        aligned_seg1 = _alignment_transformation(seg1).transformPoints(seg2)
        if not math.isclose(aligned_seg1[0][1], aligned_seg1[1][1]):
            t = aligned_seg1[0][1] / (aligned_seg1[0][1] - aligned_seg1[1][1])
            return linePointAtT(*seg2, t)
        elif not math.isclose(aligned_seg1[0][0], aligned_seg1[1][0]):
            t = aligned_seg1[0][0] / (aligned_seg1[0][0] - aligned_seg1[1][0])
            return linePointAtT(*seg2, t)
        else:
            return None
    if len(seg1) == 4 and len(seg2) == 2:
        curve, line = seg1, seg2
    elif len(seg1) == 2 and len(seg2) == 4:
        line, curve = seg1, seg2
    aligned_curve = _alignment_transformation(line).transformPoints(curve)
    a, b, c, d = calcCubicParameters(*aligned_curve)
    intersections = solveCubic(a[1], b[1], c[1], d[1])
    real_intersections = [t for t in intersections if t >= 0 and t <= 1]
    if real_intersections:
        return cubicPointAtT(*curve, real_intersections[0])
    return None  # Needs bending


def point_on_seg_at_distance(seg, distance):
    aligned_seg = _alignment_transformation(seg).transformPoints(seg)
    if len(aligned_seg) == 4:
        a, b, c, d = calcCubicParameters(*aligned_seg)
        solutions = solveCubic(a[0], b[0], c[0], d[0] - (aligned_seg[0][0] + distance))
        solutions = sorted(t for t in solutions if 0 <= t < 1)
        if not solutions:
            return None
        return solutions[0]
    else:
        start, end = aligned_seg
        if math.isclose(end[0], start[0]):
            if math.isclose(end[1], start[1]):
                return 0
            return distance / (end[1] - start[1])
        else:
            return distance / (end[0] - start[0])


def split_cubic_at_point(seg, point, inward=True):
    # There's a horrible edge case here where the curve wraps around and
    # the ray hits twice, but I'm not worrying about it.
    if inward:
        new_cubic_1 = splitCubic(*seg, point[0], False)[0]
        new_cubic_2 = splitCubic(*seg, point[1], True)[0]
    else:
        new_cubic_1 = splitCubic(*seg, point[0], False)[-1]
        new_cubic_2 = splitCubic(*seg, point[1], True)[-1]
    if dist(new_cubic_1[-1], point) < dist(new_cubic_2[-1], point):
        return new_cubic_1
    else:
        return new_cubic_2


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
    effective_start: (int, int) = None
    effective_end: (int, int) = None
    scale: (int, int) = None
    left_x: int = 0
    right_x: int = 0
    outstroke_intersection_point: (int, int) = None

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
    def first_seg(self):
        return get_next_segment(self.corner_path, 0)

    @property
    def last_seg(self):
        return get_previous_segment(self.corner_path, len(self.corner_path) - 1)

    def apply(self):
        self.path = self.glyph[self.path_index]
        # Find where the target node lines in this path. This may have
        # changed, if we have applied a corner component in this path
        # already.
        for ix, node in enumerate(self.path):
            if node == self.target_node:
                self.target_node_ix = ix
        if self.target_node_ix is None:
            self.fail("Lost track of where the corner should be applied")

        if self.corner_path[0].x != self.origin[0]:
            self.fail(
                "Can't deal with offset instrokes yet; start corner components on axis",
                hard=False,
            )

        # This is for handling the left and right anchors and doesn't
        # quite work yet
        self.determine_start_and_end_vectors()

        # Align all paths to the "origin" anchor.
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = pt.x - self.origin[0], pt.y - self.origin[1]

        # Apply scaling. We are considered "flipped" if one or other
        # of the scale factors is negative, but not both. Being flipped
        # means that the corner path gets applied backwards.
        self.flipped = False
        if self.scale is not None:
            self.flipped = (self.scale[0] * self.scale[1]) < 0
            self.scale_paths()

        # Align and rotate the corner paths so that they fit onto
        # the host path
        (
            instroke_intersection_point,
            outstroke_intersection_point,
            correction,
        ) = self.align_my_path_to_main_path()

        # Keep hold of the original outstroke segment. Fitting the
        # instroke to the corner component will change the position
        # of the target node (since it's at the end of that segment)
        # so we need to recover it later.
        original_outstroke = as_tuples(self.outstroke)

        # If we are not aligned to the instroke, we need to re-fit the
        # instroke based on where we put the corner component, and
        # potentially stretch the corner component so that it meets the
        # instroke.
        if self.alignment != Alignment.INSTROKE and correction:
            instroke_intersection_point = self.recompute_instroke_intersection_point()
            # The instroke of the corner path may need stretching to fit...
            if len(self.first_seg) == 4:
                self.stretch_first_seg_to_fit(instroke_intersection_point)
        self.split_instroke(instroke_intersection_point)

        # Now we insert the aligned and rotated corner path into the host
        self.path[self.target_node_ix + 1 : self.target_node_ix + 1] = [
            otRoundNode(node) for node in self.corner_path[1:]
        ]

        # And fix up the outstroke
        outstroke_intersection_point = self.recompute_outstroke_intersection_point(
            original_outstroke
        )
        self.fixup_outstroke(original_outstroke, outstroke_intersection_point)

        # Last of all, if there are other paths in the corner component,
        # they just get copied into the glyph.
        self.insert_other_paths()

    def determine_start_and_end_vectors(self):
        # Left and right anchors provide an additional offset, depending
        # on their relationship with the start/end of the first/last points
        # of the corner seg
        if not self.effective_start:
            self.effective_start = (0, 0)
        else:
            self.effective_start = (
                self.corner_path[0].x - self.effective_start[0],
                self.corner_path[0].y - self.effective_start[1],
            )
            self.fail(
                "left and right anchors to corner components are"
                " not currently supported",
                hard=False,
            )

        if not self.effective_end:
            self.effective_end = (0, 0)
        else:
            self.effective_end = (
                self.corner_path[-1].x - self.effective_end[0],
                self.corner_path[-1].y - self.effective_end[1],
            )
            self.fail(
                "left and right anchors to corner components are"
                " not currently supported",
                hard=False,
            )

    def scale_paths(self):
        scaling = Transform().scale(*self.scale)
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = scaling.transformPoint((pt.x, pt.y))

    def align_my_path_to_main_path(self):
        # Work out my rotation (1): Rotation occurring due to corner paths
        angle = math.atan2(-self.corner_path[-1].y, self.corner_path[-1].x)

        # Work out my rotation (2): Rotation occurring due to host paths
        if self.flipped:
            angle += math.radians(90)

            self.reverse_corner_path()

        # To align along the outstroke, work out how much the end of the
        # corner pokes out, then find a point on the curve that distance
        # away. Use that as the vector
        distance = self.last_seg[-1].y if self.flipped else self.last_seg[-1].x
        t = point_on_seg_at_distance(as_tuples(self.outstroke), distance)
        outstroke_intersection_point = segmentPointAtT(as_tuples(self.outstroke), t)
        outstroke_angle = math.atan2(
            outstroke_intersection_point[1] - self.target_node.y,
            outstroke_intersection_point[0] - self.target_node.x,
        )

        # And the same for the instroke, determined by the Y value of
        # the first point on the corner component
        distance = -self.first_seg[0].x if self.flipped else self.first_seg[0].y
        t2 = point_on_seg_at_distance(as_tuples(self.instroke), distance)
        instroke_intersection_point = segmentPointAtT(
            as_tuples(reversed(self.instroke)), t2
        )
        correction = not (math.isclose(t2, 0.0) or math.isclose(t2, 1.0))
        instroke_angle = math.atan2(
            self.target_node.y - instroke_intersection_point[1],
            self.target_node.x - instroke_intersection_point[0],
        )
        instroke_angle += math.radians(90)

        if self.alignment == Alignment.OUTSTROKE:
            angle += outstroke_angle
        elif self.alignment == Alignment.INSTROKE:
            angle += instroke_angle
        elif self.alignment == Alignment.MIDDLE:
            angle += (instroke_angle + outstroke_angle) / 2
        else:  # Unaligned, do nothing
            pass

        # Rotate the paths around the origin and then align them
        # so that the origin of the corner starts on the target node
        rot = Transform().rotate(angle)
        translation = Transform().translate(
            self.target_node.x + self.effective_start[0], self.target_node.y
        )
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = translation.transform(rot).transformPoint((pt.x, pt.y))

        return instroke_intersection_point, outstroke_intersection_point, correction

    def recompute_instroke_intersection_point(self):
        return unbounded_seg_seg_intersection(
            as_tuples(self.first_seg[0:2]), as_tuples(self.instroke)
        )

    def recompute_outstroke_intersection_point(self, original_outstroke):
        if self.flipped:
            # Project it
            return unbounded_seg_seg_intersection(
                as_tuples(self.last_seg), original_outstroke
            )

        # Bend it
        return closest_point_on_segment(
            original_outstroke,
            (self.corner_path[-1].x, self.corner_path[-1].y),
        )

    def split_instroke(self, intersection):
        if len(self.instroke) == 2:
            # Splitting a line is easy...
            (
                self.path[self.target_node_ix].x,
                self.path[self.target_node_ix].y,
            ) = otRound(intersection[0]), otRound(intersection[1])
        else:
            new_cubic = split_cubic_at_point(
                as_tuples(self.instroke), intersection, inward=True
            )
            for new_pt, old in zip(new_cubic, self.instroke):
                old.x, old.y = otRound(new_pt[0]), otRound(new_pt[1])

    def fixup_outstroke(self, original_outstroke, intersection):
        # Split the outstroke at the nearest point to the intersection.
        # The outstroke has moved now, since we have inserted the path
        outstroke = get_next_segment(
            self.path,
            (self.target_node_ix + len(self.corner_path) - 1) % len(self.path),
        )

        if not intersection:
            # Something's probably wrong...
            return

        if len(outstroke) == 2:
            (outstroke[0].x, outstroke[0].y) = otRound(intersection[0]), otRound(
                intersection[1]
            )
        else:
            new_cubic = split_cubic_at_point(
                original_outstroke, intersection, inward=False
            )
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
            shape_index, node_idx = glyphs_cc["origin"]
            path_indices = {}
            if SHAPE_ORDER_LIB_KEY in glyph.lib:
                # Map between shape index and path index
                for ix, sign in enumerate(glyph.lib[SHAPE_ORDER_LIB_KEY]):
                    if sign == "P":
                        path_indices[ix] = len(path_indices.keys())
                if shape_index not in path_indices:
                    raise ValueError(
                        f"Could not find shape number {shape_index} in {glyph.name}"
                    )
            path_idx = path_indices.get(shape_index, shape_index)

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

            if "left" in cc_anchor_dict:
                cc_left = cc_anchor_dict["left"].x, cc_anchor_dict["left"].y
            else:
                cc_left = None

            if "right" in cc_anchor_dict:
                cc_right = cc_anchor_dict["right"].x, cc_anchor_dict["right"].y
            else:
                cc_right = None

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
                effective_start=cc_left,
                effective_end=cc_right,
                # We pass in the current starting node, because its
                # position may change if we apply more than one corner.
                target_node=glyph[path_idx][(node_idx + 1) % len(glyph[path_idx])],
            )
            todo_list.append(cc)

        for cc in todo_list:
            cc.apply()

        return True
