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
    cubicPointAtT,
    segmentPointAtT,
    splitCubicAtT,
)
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.misc.roundTools import otRound
from fontTools.misc.transform import Transform
from ufo2ft.filters import BaseFilter
from ufoLib2.objects import Glyph

from glyphsLib.builder.constants import HINTS_LIB_KEY, SHAPE_ORDER_LIB_KEY
from glyphsLib.filters.eraseOpenCorners import erase_open_corners_in_contour

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


def cubic_length(seg):
    """Measure a cubic the way Glyphs does, as ten chords at even steps of t."""
    points = [cubicPointAtT(*seg, i / 10) for i in range(11)]
    return sum(dist(a, b) for a, b in zip(points, points[1:]))


def cubic_t_for_distance(seg, distance):
    """Find the t at `distance` along `seg`.

    This tries to match the behaviour of Glyphs, so that our points land
    where its do:

    1. Start by assuming t = distance / L, where L is the whole curve's
       length.
    2. Measure the length l of the curve up to t.
    3. Move t halfway towards t * distance / l (where it would be if length
       grew linearly with t).
    4. Repeat steps 2-3, four times in all.

    Lengths come from `cubic_length`, which sums ten chords rather than
    measuring the curve exactly. On a straight cubic with its handles at
    thirds this is exact; on other curves it lands slightly off the true arc
    length.
    """
    length = cubic_length(seg)
    if distance >= length:
        return 1.0
    if distance <= 0:
        return 0.0
    t = distance / length
    for _ in range(4):
        t = t * (1 + distance / cubic_length(splitCubicAtT(*seg, t)[0])) / 2
    return t


def point_along_segment(seg, distance):
    """Find the point `distance` along `seg` from its start.

    The distance is measured along the curve. Past the end of a line, the
    point lies on the line's continuation; past the end of a curve, it is the
    curve's end.
    """
    if len(seg) == 2:
        length = dist(*seg)
        t = distance / length if length else 0
    else:
        t = cubic_t_for_distance(seg, distance)
    return segmentPointAtT(seg, t)


def distance_to_line(point, direction, origin, line_direction):
    """Find how far `point` must move along `direction` to land on a line.

    The line runs through `origin` along `line_direction`, unbounded both
    ways. The distance may be negative. Returns None if the line runs along
    `direction`.
    """
    denominator = cross(direction, line_direction)
    if math.isclose(denominator, 0, abs_tol=1e-9):
        return None
    offset = (origin[0] - point[0], origin[1] - point[1])
    return cross(offset, line_direction) / denominator


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


def angle_of(vector):
    return math.atan2(vector[1], vector[0])


def turn_towards(vector, direction):
    # The angle that turns `vector` to point along `direction`
    if direction == (0, 0):
        return 0
    return math.remainder(angle_of(direction) - angle_of(vector), math.tau)


def aim_along(seg, distance):
    """Find the direction a corner end aims in along its stroke `seg`.

    The end aims from the start of `seg` at the point `distance` along it.
    An end at the origin would aim at the start itself, so it aims along the
    stroke as it leaves its start instead.
    """
    start = seg[0]
    if len(seg) == 2:
        # Along a line, that's just the line's own direction
        candidates = seg[1:]
    else:
        candidates = (point_along_segment(seg, distance), *seg[1:])
    for pt in candidates:
        if pt != start:
            return unit_vector((pt[0] - start[0], pt[1] - start[1]))
    # A stroke with no length points straight up
    return (0, 1)


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
        self.mirror = None
        self.axes = [(1, 0), (0, 1)]
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
        strokes = as_tuples(reversed(self.instroke)), as_tuples(self.outstroke)
        directions = [
            aim_along(strokes[0], math.hypot(first.x, first.y)),
            aim_along(strokes[1], math.hypot(last.x, last.y)),
        ]
        left = self.left or (first.x, first.y)
        right = self.right or (last.x, last.y)

        # If the corner turns the other way from the host path, Glyphs
        # mirrors it to fit. Unaligned, it isn't mirrored, but its ends turn
        # the other way instead. A host that runs straight on through the node
        # counts as turning clockwise, like an inside corner.
        host_turn = cross(*directions)
        if host_turn == 0 and dot(*directions) < 0:
            host_turn = 1
        # A corner with no vector for one end, because that end node or its
        # anchor is on the origin, counts as turning like an outside corner.
        corner_turn = cross(left, right)
        if (0, 0) in (left, right):
            corner_turn = -1
        turns_other_way = host_turn * corner_turn < 0
        if turns_other_way and self.alignment != Alignment.UNALIGNED:
            self.mirror_paths()
            turns_other_way = False
        self.sign = -1 if turns_other_way else 1
        self.ends = (
            self.left or (first.x, first.y),
            self.right or (last.x, last.y),
        )

        # Then each end aims again, the instroke's first, as far along
        # its stroke as fitting the corner to the strokes would leave that end
        # node from the origin. That makes a difference where an end is
        # sheared to fit a curved stroke.
        for index, end in enumerate((first, last)):
            fit = self.end_fit(index, directions, aiming=True)
            if fit is not None:
                distance = math.hypot(*fit.transformPoint((end.x, end.y)))
                directions[index] = aim_along(strokes[index], distance)

        rotation = self.rotation(directions)
        for index in range(2):
            fit = self.end_fit(index, directions)
            if fit is not None:
                for pt in self.end_points(index):
                    pt.x, pt.y = fit.transformPoint((pt.x, pt.y))

        # Curved strokes are cut as far along them as the fitted end nodes
        # are from the origin, before the corner slides into place
        cuts = [math.hypot(first.x, first.y), math.hypot(last.x, last.y)]

        # An end with no vector doesn't slide the corner along its stroke
        self.place(
            node,
            rotation,
            *(
                direction if end != (0, 0) else (0, 0)
                for direction, end in zip(directions, self.ends)
            ),
        )

        # Keep hold of the original outstroke segment. Fitting the
        # instroke to the corner component will change the position
        # of the target node (since it's at the end of that segment)
        # so we need to recover it later.
        original_outstroke = as_tuples(self.outstroke)

        # The corner's first node takes the place of the target node, and its
        # last node starts the outstroke.
        self.split_instroke((first.x, first.y), cuts[0])
        self.path[self.target_node_ix + 1 : self.target_node_ix + 1] = [
            otRoundNode(node) for node in self.corner_path[1:]
        ]
        self.fixup_outstroke(original_outstroke, cuts[1])

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
        mirror = self.mirror = Transform().rotate(angle).scale(1, -1).rotate(-angle)
        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = mirror.transformPoint((pt.x, pt.y))
        self.left, self.right = (
            None if pt is None else mirror.transformPoint(pt)
            for pt in (self.left, self.right)
        )
        # The corner's axes are mirrored with it
        self.axes = [mirror.transformPoint(axis) for axis in self.axes]

    def rotation(self, directions):
        """Find how far the corner turns as a whole to fit the strokes.

        `directions` are where the ends aim along the instroke and the
        outstroke.
        """
        # An end with no vector points along the corner's y axis, which is
        # mirrored with the corner
        turns = [
            turn_towards(end if end != (0, 0) else self.axes[1], direction)
            for end, direction in zip(self.ends, directions)
        ]
        if self.alignment == Alignment.OUTSTROKE:
            return turns[1]
        if self.alignment == Alignment.INSTROKE:
            return turns[0]
        if self.alignment == Alignment.MIDDLE and (0, 0) in self.ends:
            # Such a corner turns its x axis to the host's bisector
            in_angle, out_angle = (angle_of(d) for d in directions)
            return (
                in_angle
                + math.remainder(out_angle - in_angle, math.tau) / 2
                - angle_of(self.axes[0])
            )
        if self.alignment == Alignment.MIDDLE:
            return turns[0] + math.remainder(turns[1] - turns[0], math.tau) / 2
        return 0

    def end_points(self, index):
        """The end node at `index` (0 or 1) and, if it is a curve's, its handle."""
        if index == 0:
            end, neighbour = self.corner_path[0], self.corner_path[1]
        else:
            end, neighbour = self.corner_path[-1], self.corner_path[-2]
        return [end] if neighbour.segmentType else [end, neighbour]

    def end_fit(self, index, directions, aiming=False):
        """Find how one end of the corner path turns to fit its stroke.

        The corner as a whole turns to fit the strokes, which point along
        `directions`, and the end at `index` (0 or 1) does the rest of the
        turning. If the end's segment runs within 30 degrees of the line from
        the origin to the anchor (or without one, to the end node), as a
        bracketed serif leaving along its stem does, the end node turns
        around the anchor (or the origin), taking its handle with it. So does
        an end with no such line, on the origin.
        Otherwise the end is sheared instead, along whichever of the
        corner's axes is nearer that line: points keep their distance from
        the anchor along the axis, and the axis turns to fit.

        Returns None if the end doesn't move.
        """
        end = self.corner_path[0 if index == 0 else -1]
        neighbour = self.corner_path[1 if index == 0 else -2]
        anchor = (self.left, self.right)[index]
        pivot = anchor or (0, 0)
        towards = self.ends[index]
        segment = (neighbour.x - end.x, neighbour.y - end.y)
        if segment == (0, 0):
            return None
        if towards == (0, 0):
            # An end with no vector does all of its turning itself
            turn = turn_towards(self.axes[1], directions[index])
            along = True
        else:
            turned = Transform().rotate(self.rotation(directions))
            line, segment = (
                turned.transformPoint(unit_vector(v)) for v in (towards, segment)
            )
            if aiming and pivot != (0, 0):
                # A quirk of Glyphs 3.5 that we copy on purpose: when it aims an
                # end again, it turns the corner about the end's anchor rather
                # than the origin, and moves the unit vectors along the end's
                # line and segment with it as though they were points. It looks
                # like a bug, but it moves the corners of real fonts. The end
                # then turns as far as is left from
                # where the line's vector lands, seen from the origin, and
                # the two vectors are compared there too.
                dx, dy = self.anchor_turn_offset(turned, pivot)
                line = (line[0] + dx, line[1] + dy)
                segment = (segment[0] + dx, segment[1] + dy)
            turn = turn_towards(line, directions[index])
            along = abs(cross(line, segment)) < 0.5
        turn *= self.sign
        if along:
            fit = Transform().rotate(turn)
        elif math.isclose(math.cos(turn), 0, abs_tol=1e-4):
            # The axis would turn parallel to its stroke
            return None
        else:
            axis = max(self.axes, key=lambda axis: abs(dot(axis, towards)))
            fit = shear_across(axis, turn)
        return (
            Transform().translate(*pivot).transform(fit).translate(-pivot[0], -pivot[1])
        )

    def anchor_turn_offset(self, turned, anchor):
        """Return the offset that turning about `anchor` adds to `turned`.

        `turned` turns points about the origin. Turning a point about `anchor`
        instead puts it at `turned` of the point plus this offset, which is
        `anchor` minus `turned` of `anchor`.
        """
        if self.mirror is None:
            moved = turned.transformPoint(anchor)
            return (anchor[0] - moved[0], anchor[1] - moved[1])
        # For a mirrored corner, Glyphs takes the anchor from before the
        # mirror and adds it mirrored across the y axis and turned, instead of
        # subtracting the turned anchor
        anchor = self.mirror.transformPoint(anchor)
        moved = turned.transform(self.mirror).transformPoint((-anchor[0], anchor[1]))
        return (anchor[0] + moved[0], anchor[1] + moved[1])

    def place(self, node, rotation, instroke_direction, outstroke_direction):
        # Rotate the paths around the origin and then align them
        # so that the origin of the corner starts on the target node
        transform = Transform().translate(*node).rotate(rotation)

        # Glyphs then slides the corner along the stroke it is aligned to,
        # until its left anchor sits on the instroke, or its right anchor on
        # the outstroke. It takes the other stroke to run straight from the
        # node towards where that end aims, even when it's curved.
        anchor = None
        if self.alignment == Alignment.OUTSTROKE and self.left is not None:
            anchor, along, onto = self.left, outstroke_direction, instroke_direction
        elif self.alignment == Alignment.INSTROKE and self.right is not None:
            anchor, along, onto = self.right, instroke_direction, outstroke_direction
        if anchor is not None and along != (0, 0):
            distance = distance_to_line(
                transform.transformPoint(anchor), along, node, onto
            )
            if distance is not None:
                transform = (
                    Transform()
                    .translate(along[0] * distance, along[1] * distance)
                    .transform(transform)
                )

        for path in [self.corner_path] + self.other_paths:
            for pt in path:
                pt.x, pt.y = transform.transformPoint((pt.x, pt.y))

    def split_instroke(self, first, distance):
        """Cut the instroke where the corner starts.

        A line ends at the corner's first node. A curve is cut `distance`
        along it from the target node, and the corner starts there.
        """
        if len(self.instroke) == 2:
            (
                self.path[self.target_node_ix].x,
                self.path[self.target_node_ix].y,
            ) = otRound(first[0]), otRound(first[1])
        else:
            instroke = as_tuples(self.instroke)
            t = cubic_t_for_distance(instroke[::-1], distance)
            new_cubic = splitCubicAtT(*instroke, 1 - t)[0]
            for new_pt, old in zip(new_cubic, self.instroke):
                old.x, old.y = otRound(new_pt[0]), otRound(new_pt[1])

    def fixup_outstroke(self, original_outstroke, distance):
        """Cut the outstroke where the corner ends.

        The outstroke starts at the corner's last node. A curve keeps the
        handles of what's left of it, once it's cut `distance` along from
        the target node.
        """
        # The outstroke has moved now, since we have inserted the path
        outstroke = get_next_segment(
            self.path,
            (self.target_node_ix + len(self.corner_path) - 1) % len(self.path),
        )
        if len(outstroke) == 4:
            t = cubic_t_for_distance(original_outstroke, distance)
            new_cubic = splitCubicAtT(*original_outstroke, t)[-1]
            for new_pt, old in zip(new_cubic[1:3], outstroke[1:3]):
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

        # Glyphs erases the open corners in a glyph before it applies its
        # corners. A corner on the node that ends an open corner's line goes
        # with that node.
        if todo_list:
            for contour in glyph:
                if not contour.open:
                    erase_open_corners_in_contour(contour)
        for cc in todo_list:
            if not any(pt is cc.target_node for pt in glyph[cc.path_index]):
                logger.warning(
                    "Ignoring corner component %s in %s: its node was removed "
                    "with an open corner",
                    cc.corner_name,
                    glyph.name,
                )
                continue
            cc.apply()

        return True
