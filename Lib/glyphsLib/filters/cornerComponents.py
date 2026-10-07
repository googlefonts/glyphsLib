"""Apply Glyphs' corner components to UFO glyphs.

The rules for fitting a corner to its host path follow the output of Glyphs
3.5, quirks included. Comments name Glyphs where we copy a quirk on purpose,
or deliberately differ.
"""

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


def point_along_segment(seg, distance):
    """Find the point `distance` along `seg` from its start.

    The distance is measured along the curve. Past the end of a line, the
    point lies on the line's continuation; past the end of a curve, it is the
    curve's end.
    """
    if len(seg) == 2:
        length = dist(*seg)
        t = distance / length if length else 0
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
    return segmentPointAtT(seg, t)


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


def unit_vector(vector):
    length = math.hypot(*vector)
    return (vector[0] / length, vector[1] / length)


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def shear_across(axis, angle):
    """Shear points across the unit vector `axis`, so that it turns by `angle`.

    Points keep their distance along the axis.
    """
    x, y = axis
    k = math.tan(angle)
    return Transform(1 - k * x * y, k * x * x, -k * y * y, 1 + k * x * y, 0, 0)


def turn_towards(vector, origin, target):
    # The angle that turns `vector` to point from `origin` towards `target`
    return math.remainder(
        math.atan2(target[1] - origin[1], target[0] - origin[0])
        - math.atan2(vector[1], vector[0]),
        math.tau,
    )


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
        # left and right anchors trade places. The other paths are reversed
        # too, so that they keep their direction.
        self.flipped = False
        if self.scale is not None:
            self.flipped = (self.scale[0] * self.scale[1]) < 0
            self.scale_paths()
        if self.flipped:
            self.reverse_paths()
            self.left, self.right = self.right, self.left

        # Each end of the corner points at the point as far along its
        # stroke as the end node is from the origin, measuring both strokes
        # from the target node. Where the corner has a left anchor, that's
        # what it points along the instroke, and likewise a right anchor
        # along the outstroke.
        first, last = self.corner_path[0], self.corner_path[-1]
        node = (self.target_node.x, self.target_node.y)
        instroke_target = point_along_segment(
            as_tuples(reversed(self.instroke)), math.hypot(first.x, first.y)
        )
        outstroke_target = point_along_segment(
            as_tuples(self.outstroke), math.hypot(last.x, last.y)
        )

        # If the corner turns the other way from the host path, Glyphs
        # mirrors it to fit. Unaligned, it isn't mirrored, but its ends turn
        # the other way instead.
        host_turn = cross(
            (instroke_target[0] - node[0], instroke_target[1] - node[1]),
            (outstroke_target[0] - node[0], outstroke_target[1] - node[1]),
        )
        corner_turn = cross(
            self.left or (first.x, first.y), self.right or (last.x, last.y)
        )
        turns_other_way = host_turn * corner_turn < 0
        if turns_other_way and self.alignment != Alignment.UNALIGNED:
            self.mirror_paths()
            turns_other_way = False
        instroke_turn = turn_towards(
            self.left or (first.x, first.y), node, instroke_target
        )
        outstroke_turn = turn_towards(
            self.right or (last.x, last.y), node, outstroke_target
        )

        # The corner as a whole turns to fit the stroke it's aligned to
        if self.alignment == Alignment.OUTSTROKE:
            rotation = outstroke_turn
        elif self.alignment == Alignment.INSTROKE:
            rotation = instroke_turn
        elif self.alignment == Alignment.MIDDLE:
            rotation = (
                instroke_turn
                + math.remainder(outstroke_turn - instroke_turn, math.tau) / 2
            )
        else:
            rotation = 0

        # The ends of the corner do the rest of the turning
        sign = -1 if turns_other_way else 1
        self.fit_end(0, sign * (instroke_turn - rotation), self.left)
        self.fit_end(-1, sign * (outstroke_turn - rotation), self.right)

        self.place(node, rotation, instroke_target, outstroke_target)

        # Keep hold of the original outstroke segment. Fitting the
        # instroke to the corner component will change the position
        # of the target node (since it's at the end of that segment)
        # so we need to recover it later.
        original_outstroke = as_tuples(self.outstroke)

        # The corner's first node takes the place of the target node, and its
        # last node starts the outstroke.
        self.split_instroke((first.x, first.y))
        self.path[self.target_node_ix + 1 : self.target_node_ix + 1] = [
            otRoundNode(node) for node in self.corner_path[1:]
        ]
        self.fixup_outstroke(original_outstroke, (last.x, last.y))

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

    def fit_end(self, index, turn, anchor):
        """Turn one end of the corner path by `turn`, to fit it to its stroke.

        If the end's segment runs within 30 degrees of the line from the
        origin to the anchor (or without one, to the end node), as a
        bracketed serif leaving along its stem does, the end node turns
        around the anchor (or the origin), taking its handle with it.
        Otherwise the end is sheared instead, along whichever of the
        corner's axes is nearer that line: points keep their distance from
        the anchor along the axis, and the axis turns by `turn`.
        """
        end = self.corner_path[index]
        neighbour = self.corner_path[1 if index == 0 else -2]
        moving = [end] if neighbour.segmentType else [end, neighbour]
        pivot = anchor or (0, 0)
        towards = anchor or (end.x, end.y)
        segment = (neighbour.x - end.x, neighbour.y - end.y)
        if segment == (0, 0) or towards == (0, 0):
            return
        if abs(cross(unit_vector(segment), unit_vector(towards))) < 0.5:
            fit = Transform().rotate(turn)
        elif math.isclose(math.cos(turn), 0, abs_tol=1e-4):
            # The axis would turn parallel to its stroke
            return
        else:
            axis = max([(1, 0), (0, 1)], key=lambda axis: abs(dot(axis, towards)))
            fit = shear_across(axis, turn)
        transform = (
            Transform().translate(*pivot).transform(fit).translate(-pivot[0], -pivot[1])
        )
        for pt in moving:
            pt.x, pt.y = transform.transformPoint((pt.x, pt.y))

    def place(self, node, rotation, instroke_target, outstroke_target):
        # Rotate the paths around the origin and then align them
        # so that the origin of the corner starts on the target node
        transform = Transform().translate(*node).rotate(rotation)

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

    def reverse_paths(self):
        for path in [self.corner_path] + self.other_paths:
            new_glyph = Glyph()
            path.draw(ReverseContourPen(new_glyph.getPen()))
            path[:] = new_glyph[0]

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
            path = glyph[path_idx]
            target_node = path[(node_idx + 1) % len(path)]
            # Glyphs ignores a corner on an off-curve point too
            if target_node.segmentType is None:
                logger.warning(
                    "Ignoring corner component %s in %s: node %d of shape %d is "
                    "an off-curve point",
                    glyphs_cc["name"],
                    glyph.name,
                    node_idx,
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
                target_node=target_node,
            )
            todo_list.append(cc)

        for cc in todo_list:
            cc.apply()

        return True
