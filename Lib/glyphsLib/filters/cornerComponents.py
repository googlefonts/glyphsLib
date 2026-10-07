import copy
from dataclasses import dataclass
from enum import IntEnum
import logging
import math

from fontTools.misc.bezierTools import (
    _alignment_transformation,
    calcCubicArcLength,
    calcCubicParameters,
    solveCubic,
    cubicPointAtT,
    linePointAtT,
    segmentPointAtT,
    splitCubic,
    splitCubicAtT,
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
            # The distance runs off one end of the segment
            return 1.0 if distance > 0 else 0.0
        return solutions[0]
    else:
        start, end = aligned_seg
        if math.isclose(end[0], start[0]):
            if math.isclose(end[1], start[1]):
                return 0
            return distance / (end[1] - start[1])
        else:
            return distance / (end[0] - start[0])


def point_along_segment(seg, distance):
    """Find the point `distance` along `seg` from its start.

    The distance is measured along the curve. Returns the point and the
    direction of the segment there, as a unit vector. Past the end of a line,
    the point lies on the line's continuation; past the end of a curve, it is
    the curve's end.
    """
    if len(seg) == 2:
        t = point_on_seg_at_distance(seg, distance)
    elif calcCubicArcLength(*seg) <= distance:
        t = 1.0
    else:
        low, high = 0.0, 1.0
        for _ in range(40):
            t = (low + high) / 2
            if calcCubicArcLength(*splitCubicAtT(*seg, t)[0]) < distance:
                low = t
            else:
                high = t
    point = segmentPointAtT(seg, t)
    direction = (seg[-1][0] - seg[0][0], seg[-1][1] - seg[0][1])
    if len(seg) == 4:
        derivative = tuple(
            3 * (1 - t) ** 2 * (seg[1][i] - seg[0][i])
            + 6 * (1 - t) * t * (seg[2][i] - seg[1][i])
            + 3 * t**2 * (seg[3][i] - seg[2][i])
            for i in range(2)
        )
        if derivative != (0, 0):
            direction = derivative
    return point, unit_vector(direction)


def is_on_segment(seg, pt, tolerance=0.5):
    # Unlike closest_point_on_segment, this doesn't extend lines past their
    # ends: as a cubic with its handles on its ends, a line stays put.
    if len(seg) == 2:
        seg = [seg[0], seg[0], seg[1], seg[1]]
    return dist(closest_point_on_cubic(seg, pt), pt) < tolerance


def runs_along_axis(end, neighbour):
    # Whether the segment from a corner's `end` node towards `neighbour`
    # runs along the line from that node to the origin.
    along = (end.x, end.y)
    leaving = (neighbour.x - end.x, neighbour.y - end.y)
    lengths = math.hypot(*along) * math.hypot(*leaving)
    if lengths == 0:
        return False
    return abs(cross(along, leaving)) / lengths < math.sin(math.radians(5))


def distance_to_segment(point, direction, seg):
    """Find how far `point` must move along `direction` to land on `seg`.

    `direction` must be a unit vector. Lines are treated as unbounded; a curve
    that the line misses is extended straight back from its start. The
    distance may be negative. Returns None if `direction` is parallel to
    `seg`.
    """
    aligned = _alignment_transformation(
        [point, (point[0] + direction[0], point[1] + direction[1])]
    )
    if len(seg) == 4:
        curve = aligned.transformPoints(seg)
        a, b, c, d = calcCubicParameters(*curve)
        hits = [
            cubicPointAtT(*curve, t)[0]
            for t in solveCubic(a[1], b[1], c[1], d[1])
            if 0 <= t <= 1
        ]
        if hits:
            return min(hits, key=abs)
        seg = [seg[0], seg[1] if seg[1] != seg[0] else seg[2]]
    (x0, y0), (x1, y1) = aligned.transformPoints(seg)
    if math.isclose(y0, y1):
        return None
    t = y0 / (y0 - y1)
    return x0 + (x1 - x0) * t


def has_length(seg):
    return any(pt != seg[0] for pt in seg[1:])


def aimable(stroke):
    """Return `stroke`, or if it has no length, a line running straight up.

    Glyphs aims a corner along a stroke with no length, such as one between
    two nodes in the same place, as if it ran straight up from the node.
    """
    if has_length(stroke):
        return stroke
    x, y = stroke[0]
    return [(x, y), (x, y + 1)]


def unit_vector(vector):
    length = math.hypot(*vector)
    return (vector[0] / length, vector[1] / length)


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def split_cubic_at_point(seg, point, inward=True):
    # When splitting inward we keep the first segment and want its end to be
    # at the point; when splitting outward we keep the last segment and want
    # its start to be at the point. The other end is the original segment
    # endpoint either way, so comparing that tells us nothing.
    if inward:
        new_cubic_1 = splitCubic(*seg, point[0], False)[0]
        new_cubic_2 = splitCubic(*seg, point[1], True)[0]
        split_end = -1
    else:
        new_cubic_1 = splitCubic(*seg, point[0], False)[-1]
        new_cubic_2 = splitCubic(*seg, point[1], True)[-1]
        split_end = 0
    if dist(new_cubic_1[split_end], point) < dist(new_cubic_2[split_end], point):
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
    left: (int, int) = None
    right: (int, int) = None
    scale: (int, int) = None
    outstroke_intersection_point: (int, int) = None

    def warn_about_unused_anchor(self):
        # We only use the left anchor of a corner aligned to the outstroke,
        # and the right anchor of one aligned to the instroke. Glyphs uses
        # them in other ways too.
        if self.alignment == Alignment.OUTSTROKE:
            unused = self.right
        elif self.alignment == Alignment.INSTROKE:
            unused = self.left
        else:
            unused = self.left or self.right
        if unused is not None:
            logger.warning(
                "Ignoring an anchor of corner %s in %s: left anchors are only"
                " supported with outstroke alignment, and right anchors with"
                " instroke alignment (the other way round when flipped)",
                self.corner_name,
                self.glyph_name,
            )

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
            if node is self.target_node:
                self.target_node_ix = ix
        if self.target_node_ix is None:
            self.fail("Lost track of where the corner should be applied")

        # Align all paths, and the anchors, to the "origin" anchor.
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = pt.x - self.origin[0], pt.y - self.origin[1]
        self.left, self.right = (
            None if pt is None else (pt[0] - self.origin[0], pt[1] - self.origin[1])
            for pt in (self.left, self.right)
        )

        # Apply scaling. We are considered "flipped" if one or other
        # of the scale factors is negative, but not both. Being flipped
        # means that the corner path gets applied backwards, and that the
        # left and right anchors trade places.
        self.flipped = False
        if self.scale is not None:
            self.flipped = (self.scale[0] * self.scale[1]) < 0
            self.scale_paths()
        if self.flipped:
            self.reverse_corner_path()
            self.left, self.right = self.right, self.left

        self.warn_about_unused_anchor()

        # The corner's first and last nodes may point any which way from
        # the origin; it is how far away they are that tells us where the
        # corner meets the host path.
        first, last = self.corner_path[0], self.corner_path[-1]
        instroke_distance = math.hypot(first.x, first.y)
        outstroke_distance = math.hypot(last.x, last.y)
        # Glyphs turns the corner towards points that far along each
        # stroke's chord, but where it puts a node on a curved stroke, it
        # measures along the curve. Both strokes are measured from the target
        # node, so the instroke is taken backwards, and the directions point
        # away from the node.
        instroke = aimable(as_tuples(reversed(self.instroke)))
        outstroke = aimable(as_tuples(self.outstroke))
        instroke_target = segmentPointAtT(
            instroke, point_on_seg_at_distance(instroke, instroke_distance)
        )
        outstroke_target = segmentPointAtT(
            outstroke, point_on_seg_at_distance(outstroke, outstroke_distance)
        )
        instroke_point, instroke_direction = point_along_segment(
            instroke, instroke_distance
        )
        outstroke_point, outstroke_direction = point_along_segment(
            outstroke, outstroke_distance
        )

        # If the corner turns the other way from the host path, Glyphs
        # mirrors it to fit, unless the corner is unaligned.
        node = (self.target_node.x, self.target_node.y)
        host_turn = cross(
            (instroke_target[0] - node[0], instroke_target[1] - node[1]),
            (outstroke_target[0] - node[0], outstroke_target[1] - node[1]),
        )
        if (
            self.alignment != Alignment.UNALIGNED
            and host_turn * cross((first.x, first.y), (last.x, last.y)) < 0
        ):
            self.mirror_paths()

        leaves_along_instroke = runs_along_axis(first, self.corner_path[1])
        arrives_along_outstroke = len(self.last_seg) == 4 and runs_along_axis(
            last, self.corner_path[-2]
        )
        left_on_first_seg = self.left is not None and is_on_segment(
            as_tuples(self.first_seg), self.left
        )

        # Align and rotate the corner paths so that they fit onto
        # the host path
        self.align_my_path_to_main_path(instroke_target, outstroke_target)

        # Keep hold of the original outstroke segment. Fitting the
        # instroke to the corner component will change the position
        # of the target node (since it's at the end of that segment)
        # so we need to recover it later.
        original_outstroke = as_tuples(self.outstroke)

        # Now fit the instroke to where we put the corner component. If we
        # are not aligned to the instroke, we may need to stretch the corner
        # component so that it meets the instroke.
        instroke_intersection_point = instroke_target
        if not has_length(as_tuples(self.instroke)):
            # There's no instroke to fit the first node to, so like Glyphs we
            # leave it where the corner put it
            instroke_intersection_point = (first.x, first.y)
        elif self.alignment == Alignment.INSTROKE:
            # Fit the first node to the instroke the way we fit the last
            # node to the outstroke below
            instroke_intersection_point = closest_point_on_segment(
                as_tuples(self.instroke), (first.x, first.y)
            )
        elif instroke_distance > 0:
            if leaves_along_instroke:
                # The corner's first segment runs along the instroke, so
                # there's no crossing to fit it to. Glyphs puts the first
                # node on the instroke instead, with its handle along it.
                instroke_intersection_point = instroke_point
                if len(self.first_seg) == 4:
                    self.move_end_onto_stroke(
                        first,
                        self.first_seg[1],
                        instroke_point,
                        (-instroke_direction[0], -instroke_direction[1]),
                    )
            else:
                # If the corner's first segment misses the instroke, keep the
                # point we found while aligning. If the left anchor is on the
                # first segment, that's where the corner already meets the
                # instroke, and Glyphs leaves the first node alone.
                recomputed = self.recompute_instroke_intersection_point()
                if left_on_first_seg:
                    instroke_intersection_point = (first.x, first.y)
                elif recomputed is not None:
                    instroke_intersection_point = recomputed
                # The instroke of the corner path may need stretching to fit...
                if len(self.first_seg) == 4:
                    self.stretch_first_seg_to_fit(instroke_intersection_point)
        self.split_instroke(instroke_intersection_point)

        # Aligned to the instroke, it's the other end of the corner that
        # needs fitting: a last segment that curves in along the outstroke
        # gets the same treatment as the first segment above.
        if self.alignment == Alignment.INSTROKE and arrives_along_outstroke:
            self.move_end_onto_stroke(
                last,
                self.last_seg[-2],
                outstroke_point,
                (-outstroke_direction[0], -outstroke_direction[1]),
            )

        # Now we insert the aligned and rotated corner path into the host
        self.path[self.target_node_ix + 1 : self.target_node_ix + 1] = [
            otRoundNode(node) for node in self.corner_path[1:]
        ]

        # And fix up the outstroke, if it has any length to fit the last node to
        if has_length(original_outstroke):
            outstroke_intersection_point = self.recompute_outstroke_intersection_point(
                original_outstroke
            )
            self.fixup_outstroke(original_outstroke, outstroke_intersection_point)

        # Last of all, if there are other paths in the corner component,
        # they just get copied into the glyph.
        self.insert_other_paths()

    def scale_paths(self):
        scaling = Transform().scale(*self.scale)
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = scaling.transformPoint((pt.x, pt.y))
        self.left, self.right = (
            None if pt is None else scaling.transformPoint(pt)
            for pt in (self.left, self.right)
        )

    def mirror_paths(self):
        # Reflect across the line from the origin to the first node, which
        # stays put. Unlike flipping with a negative scale, the path keeps
        # its direction.
        first = self.corner_path[0]
        angle = math.atan2(first.y, first.x)
        mirror = Transform().rotate(angle).scale(1, -1).rotate(-angle)
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = mirror.transformPoint((pt.x, pt.y))
        self.left, self.right = (
            None if pt is None else mirror.transformPoint(pt)
            for pt in (self.left, self.right)
        )

    def move_end_onto_stroke(self, end, handle, point, towards_node):
        # Put an end node of the corner path on the host path, at `point`,
        # and point its handle back along the host path, keeping its length.
        length = dist((end.x, end.y), (handle.x, handle.y))
        end.x, end.y = point
        handle.x = point[0] + towards_node[0] * length
        handle.y = point[1] + towards_node[1] * length

    def align_my_path_to_main_path(self, instroke_target, outstroke_target):
        # Turn the corner so that its first node points back along the
        # instroke, or its last node along the outstroke, or halfway between.
        node = (self.target_node.x, self.target_node.y)
        first, last = self.corner_path[0], self.corner_path[-1]
        instroke_angle = math.atan2(
            instroke_target[1] - node[1], instroke_target[0] - node[0]
        ) - math.atan2(first.y, first.x)
        outstroke_angle = math.atan2(
            outstroke_target[1] - node[1], outstroke_target[0] - node[0]
        ) - math.atan2(last.y, last.x)

        if self.alignment == Alignment.OUTSTROKE:
            angle = outstroke_angle
        elif self.alignment == Alignment.INSTROKE:
            angle = instroke_angle
        elif self.alignment == Alignment.MIDDLE:
            difference = math.remainder(outstroke_angle - instroke_angle, math.tau)
            angle = instroke_angle + difference / 2
        else:  # Unaligned, do nothing
            angle = 0

        # Rotate the paths around the origin and then align them
        # so that the origin of the corner starts on the target node
        transform = Transform().translate(*node).rotate(angle)

        # Glyphs then slides the corner along the stroke it is aligned to,
        # until its left anchor sits on the instroke, or its right anchor on
        # the outstroke
        anchor = None
        if self.alignment == Alignment.OUTSTROKE and self.left is not None:
            anchor, along, onto = self.left, outstroke_target, self.instroke
        elif self.alignment == Alignment.INSTROKE and self.right is not None:
            anchor, along, onto = self.right, instroke_target, self.outstroke[::-1]
        if anchor is not None and along != node:
            direction = unit_vector((along[0] - node[0], along[1] - node[1]))
            distance = distance_to_segment(
                transform.transformPoint(anchor), direction, as_tuples(onto)
            )
            if distance is not None:
                transform = (
                    Transform()
                    .translate(direction[0] * distance, direction[1] * distance)
                    .transform(transform)
                )

        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = transform.transformPoint((pt.x, pt.y))

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
            outstroke[0].x, outstroke[0].y = otRound(intersection[0]), otRound(
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
        corner_nodes = set()

        for glyphs_cc in corner_components:
            shape_index, node_idx = glyphs_cc["origin"]
            path_indices = {}
            if SHAPE_ORDER_LIB_KEY in glyph.lib:
                # Map between shape index and path index
                for ix, sign in enumerate(glyph.lib[SHAPE_ORDER_LIB_KEY]):
                    if sign == "P":
                        path_indices[ix] = len(path_indices.keys())
                path_idx = path_indices.get(shape_index)
            else:
                path_idx = shape_index
            # Glyphs ignores a corner on a component, or on a shape that isn't
            # there any more
            if path_idx is None or not 0 <= path_idx < len(glyph):
                logger.warning(
                    "Ignoring corner component %s in %s: shape %d is not a path",
                    glyphs_cc["name"],
                    glyph.name,
                    shape_index,
                )
                continue

            # We use font, not .glyphSet here because corner components
            # aren't normally exported
            if glyphs_cc["name"] not in self.context.font:
                logger.warn(
                    "Corner component %s in %s not found",
                    glyphs_cc["name"],
                    glyph.name,
                )
                continue

            # A corner replaces the node it is attached to, so like Glyphs we
            # only apply the first one on each node.
            if (path_idx, node_idx) in corner_nodes:
                logger.warning(
                    "Ignoring corner component %s in %s: there is already a "
                    "corner on that node",
                    glyphs_cc["name"],
                    glyph.name,
                )
                continue
            corner_nodes.add((path_idx, node_idx))
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
                left=cc_left,
                right=cc_right,
                # We pass in the current starting node, because its
                # position may change if we apply more than one corner.
                target_node=glyph[path_idx][(node_idx + 1) % len(glyph[path_idx])],
            )
            todo_list.append(cc)

        for cc in todo_list:
            cc.apply()

        return True
