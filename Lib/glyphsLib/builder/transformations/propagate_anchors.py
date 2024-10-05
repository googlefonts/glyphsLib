"""Propagating anchors from components to their composites

Glyphs.app has a nice feature where anchors defined in the components
of composite glyphs are copied into the composites themselves. This feature
however is not very extensively documented.
The code here is based off the Rust implementation in fontc:

  https://github.com/googlefonts/fontc/blob/85795bf/glyphs-reader/src/propagate_anchors.rs

The latter is in turn based off the original Objective-C implementation, which was
shared with us privately.
"""

from __future__ import annotations

import logging
from collections import deque
from itertools import chain
from math import atan2, degrees, isinf
from typing import TYPE_CHECKING

from fontTools.misc.transform import Transform

from glyphsLib import glyphdata
from glyphsLib.classes import GSAnchor
from glyphsLib.types import Point


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from typing import Iterable
    from glyphsLib.classes import GSComponent, GSFont, GSGlyph, GSLayer


def propagate_all_anchors(
    font: GSFont, *, glyph_data: glyphdata.GlyphData | None = None
) -> None:
    """Copy anchors from component glyphs into their including composites.

    If a custom `glyph_data` is provided, it will be used to override the
    category and subCategory of glyphs.
    """
    glyphs = {glyph.name: glyph for glyph in font.glyphs}
    propagate_all_anchors_impl(glyphs, glyph_data=glyph_data)


# the actual implementation, easier to test and compare with the original Rust code
def propagate_all_anchors_impl(
    glyphs: dict[str, GSGlyph], *, glyph_data: glyphdata.GlyphData | None = None
) -> None:
    # the reference implementation does this recursively, but we opt to
    # implement it by pre-sorting the work to ensure we always process components
    # first.
    todo = depth_sorted_composite_glyphs(glyphs)
    num_base_glyphs: dict[(str, str), int] = {}
    # NOTE: there's an important detail here, which is that we need to call the
    # 'anchors_traversing_components' function on each glyph, and save the returned
    # anchors, but we only *set* those anchors on glyphs that have components.
    # to make this work, we write the anchors to a separate data structure, and
    # then only update the actual glyphs after we've done all the work.
    all_anchors: dict[str, dict[str, list[GSAnchor]]] = {}
    for name in todo:
        glyph = glyphs[name]
        for layer in _interesting_layers(glyph):
            anchors = anchors_traversing_components(
                glyph,
                layer,
                glyphs,
                all_anchors,
                num_base_glyphs,
                glyph_data,
            )
            maybe_log_new_anchors(anchors, glyph, layer)
            all_anchors.setdefault(name, {})[layer.layerId] = anchors

    # finally update our glyphs with the new anchors, where appropriate
    for name, layers in all_anchors.items():
        glyph = glyphs[name]
        if _has_components(glyph):
            for layer_id, layer_anchors in layers.items():
                glyph.layers[layer_id].anchors = layer_anchors


def maybe_log_new_anchors(
    anchors: list[GSAnchor], glyph: GSGlyph, layer: GSLayer
) -> None:
    if not _has_components(glyph) or not logger.isEnabledFor(logging.DEBUG):
        return
    prev_names = [a.name for a in layer.anchors]
    new_names = [a.name for a in anchors]
    if prev_names != new_names:
        logger.debug(
            "propagated anchors for ('%s': %s -> %s)",
            glyph.name,
            prev_names,
            new_names,
        )


def _interesting_layers(glyph):
    # only master layers are currently supported for anchor propagation:
    # https://github.com/googlefonts/glyphsLib/issues/1017
    return (
        l
        for l in glyph.layers
        if l._is_master_layer
        # or l._is_brace_layer
        # or l._is_bracket_layer
        # etc.
    )


def _has_components(glyph: GSGlyph) -> bool:
    return any(layer.components for layer in _interesting_layers(glyph))


def _get_category(
    glyph: GSGlyph,
    glyph_data: glyphdata.GlyphData | None = None,
) -> str:
    return (
        glyph.category
        or glyphdata.get_glyph(
            glyph.name, data=glyph_data, unicodes=glyph.unicodes
        ).category
    )


def _get_subCategory(
    glyph: GSGlyph,
    glyph_data: glyphdata.GlyphData | None = None,
) -> str:
    return (
        glyph.subCategory
        or glyphdata.get_glyph(
            glyph.name, data=glyph_data, unicodes=glyph.unicodes
        ).subCategory
    )


def anchors_traversing_components(
    glyph: GSGlyph,
    layer: GSLayer,
    glyphs: dict[str, GSGlyph],
    done_anchors: dict[str, dict[str, list[GSAnchor]]],
    base_glyph_counts: dict[(str, str), int],
    glyph_data: glyphdata.GlyphData | None = None,
) -> list[GSAnchor]:
    """Return the anchors for this glyph, including anchors from components

    This function is a reimplmentation of a similarly named function in glyphs.app.

    The logic for copying anchors from components into their containing composites
    is tricky. Anchors need to be adjusted in various ways:

    - a special "*origin" anchor may exist, which modifies the position of other anchors
    - if a component is flipped on the x or y axes, we rename "top" to "bottom"
      and/or "left" to "right"
    - we need to apply the transform from the component
    - we may need to rename an anchor when the component is part of a ligature glyph
    """
    if not layer.anchors and not layer.components:
        return []

    # if this is a mark and it has anchors, just return them
    # (as in, don't even look at the components)
    if layer.anchors and _get_category(glyph, glyph_data) == "Mark":
        return list(origin_adjusted_anchors(layer.anchors))

    is_ligature = _get_subCategory(glyph, glyph_data) == "Ligature"
    has_underscore = any(a.name.startswith("_") for a in layer.anchors)

    number_of_base_glyphs = 0
    all_anchors = {}

    for component_idx, component in enumerate(layer.components):
        # because we process dependencies first we know that all components
        # referenced have already been propagated
        anchors = get_component_layer_anchors(component, layer, glyphs, done_anchors)
        if anchors is None:
            logger.debug(
                "could not get layer '%s' for component '%s' of glyph '%s'",
                layer.layerId,
                component.name,
                glyph.name,
            )
            continue

        # if this component has an explicitly set attachment anchor, use it
        if component_idx > 0 and component.anchor:
            maybe_rename_component_anchor(component.anchor, anchors)

        component_number_of_base_glyphs = base_glyph_counts.get(
            (component.name, layer.layerId), 0
        )

        comb_has_underscore = any(
            len(a.name) >= 2 and a.name.startswith("_") for a in anchors
        )
        comb_has_exit = any(a.name.endswith("exit") for a in anchors)
        if not (comb_has_underscore or comb_has_exit):
            # delete exit anchors we may have taken from earlier components
            # (since a glyph should only have one exit anchor, and logically its
            # at the end)
            all_anchors = {
                n: a for n, a in all_anchors.items() if not n.endswith("exit")
            }

        component_transform = Transform(*component.transform)
        xscale, yscale = get_xy_rotation(component_transform)
        for anchor in anchors:
            new_has_underscore = anchor.name.startswith("_")
            if (component_idx > 0 or has_underscore) and new_has_underscore:
                continue
            # skip entry anchors on non-first glyphs
            if component_idx > 0 and anchor.name.endswith("entry"):
                continue

            new_anchor_name = rename_anchor_for_scale(anchor.name, xscale, yscale)
            if (
                is_ligature
                and component_number_of_base_glyphs > 0
                and not new_has_underscore
                and not (
                    new_anchor_name.endswith("exit")
                    or new_anchor_name.endswith("entry")
                )
            ):
                # dealing with marks like top_1 on a ligature
                new_anchor_name = make_liga_anchor_name(
                    new_anchor_name, number_of_base_glyphs
                )

            apply_transform_to_anchor(anchor, component_transform)
            anchor.name = new_anchor_name
            all_anchors[anchor.name] = anchor
            has_underscore |= new_has_underscore

        number_of_base_glyphs += base_glyph_counts.get(
            (component.name, layer.layerId), 0
        )

    # now we've handled all the anchors from components, so copy over anchors
    # that were explicitly defined on this layer:
    all_anchors.update((a.name, a) for a in origin_adjusted_anchors(layer.anchors))
    has_underscore_anchor = False
    has_mark_anchor = False
    component_count_from_anchors = 0

    # now we count how many components we have, based on our anchors
    for name in all_anchors.keys():
        has_underscore_anchor |= name.startswith("_")
        has_mark_anchor |= name[0].isalpha() and name[0].isascii() if name else False
        if (
            not is_ligature
            and number_of_base_glyphs == 0
            and not name.startswith("_")
            and not (name.endswith("exit") or name.endswith("entry"))
            and "_" in name
        ):
            suffix = name[name.index("_") + 1 :]
            # carets count space between components, so the last caret
            # is n_components - 1
            maybe_add_one = 1 if name.startswith("caret") else 0
            anchor_index = 0
            try:
                anchor_index = int(suffix) + maybe_add_one
            except ValueError:
                pass
            component_count_from_anchors = max(
                component_count_from_anchors, anchor_index
            )
    if not has_underscore_anchor and number_of_base_glyphs == 0 and has_mark_anchor:
        number_of_base_glyphs += 1
    number_of_base_glyphs = max(number_of_base_glyphs, component_count_from_anchors)

    if any(a.name == "_bottom" for a in layer.anchors):
        all_anchors.pop("top", None)
        all_anchors.pop("_top", None)
    if any(a.name == "_top" for a in layer.anchors):
        all_anchors.pop("bottom", None)
        all_anchors.pop("_bottom", None)

    base_glyph_counts[(glyph.name, layer.layerId)] = number_of_base_glyphs

    return list(all_anchors.values())


def origin_adjusted_anchors(anchors: list[GSAnchor]) -> Iterable[GSAnchor]:
    """Iterate over anchors taking into account the special "*origin" anchor

    If that anchor is present it will be used to adjust the positions of other
    anchors, and will not be included in the output.
    """
    origin = next((a.position for a in anchors if a.name == "*origin"), Point(0, 0))
    return (
        GSAnchor(
            name=a.name,
            position=Point(a.position.x - origin.x, a.position.y - origin.y),
            userData=dict(a.userData),
        )
        for a in anchors
        if a.name != "*origin"
    )


def get_xy_rotation(xform: Transform) -> tuple[float, float]:
    """Returns (x, y) where a negative value indicates axis is flipped"""
    # this is based on examining the behaviour of glyphs via the macro panel
    # and careful testing.
    a, b = xform[:2]
    # first take the rotation
    angle = atan2(b, a)
    # then remove the rotation, and take the scale
    rotated = xform.rotate(-angle)
    xscale, yscale = (rotated[0], rotated[3])
    # then invert the scale if the rotation was >= 180°
    if abs(degrees(angle) - 180) < 0.001:
        xscale = -xscale
        yscale = -yscale

    return xscale, yscale


def apply_transform_to_anchor(anchor: GSAnchor, transform: Transform) -> None:
    """Apply the transform but also do some rounding.

    So we don't have anchors with points like (512, 302.000000006).
    """
    x, y = anchor.position
    pos = transform.transformPoint((x, y))
    anchor.position = Point(round(pos[0], 6), round(pos[1], 6))


def maybe_rename_component_anchor(comp_name: str, anchors: list[GSAnchor]) -> None:
    # e.g, go from 'top' to 'top_1'
    if "_" not in comp_name:
        return
    sub_name = comp_name[: comp_name.index("_")]
    mark_name = f"_{sub_name}"
    if any(a.name == sub_name for a in anchors) and any(
        a.name == mark_name for a in anchors
    ):
        comp_anchor = next(a for a in anchors if a.name == sub_name)
        comp_anchor.name = comp_name


def make_liga_anchor_name(name: str, base_number: int) -> str:
    if "_" in name:
        # if this anchor already has a number (like 'top_2') we want to consider that
        name, suffix = name.split("_", 1)
        try:
            num = int(suffix)
        except ValueError:
            num = 1
        return f"{name}_{base_number + num}"
    # otherwise we're turning 'top' into 'top_N'
    return f"{name}_{base_number + 1}"


def rename_anchor_for_scale(name: str, xscale: float, yscale: float) -> str:
    """If a component is rotated, flip bottom/top, left/right, entry/exit"""

    def swap_pair(s: str, one: str, two: str) -> str:
        if one in s:
            return s.replace(one, two)
        elif two in s:
            return s.replace(two, one)
        return s

    if xscale < 0.0:
        name = swap_pair(name, "left", "right")
        name = swap_pair(name, "exit", "entry")
    if yscale < 0.0:
        name = swap_pair(name, "bottom", "top")

    return name


def get_component_layer_anchors(
    component: GSComponent,
    layer: GSLayer,
    glyphs: dict[str, GSGlyph],
    anchors: dict[str, dict[str, list[GSAnchor]]],
) -> list[GSAnchor] | None:
    glyph = glyphs.get(component.name)
    if glyph is None:
        return None
    # in Glyphs.app, the `componentLayer` property would synthesize a layer
    # if it is missing. glyphsLib does not have that yet, so for now we
    # only support the corresponding 'master' layer of a component's base glyph.
    layer_anchors = None
    for comp_layer in _interesting_layers(glyph):
        if comp_layer.layerId == layer.layerId and component.name in anchors:
            layer_anchors = anchors[component.name][comp_layer.layerId]
            break
    if layer_anchors is not None:
        # return a copy as they may be modified in place
        layer_anchors = [
            GSAnchor(
                name=a.name,
                position=Point(a.position.x, a.position.y),
                userData=dict(a.userData),
            )
            for a in layer_anchors
        ]
    return layer_anchors


def compute_max_component_depths(glyphs: dict[str, GSGlyph]) -> dict[str, float]:
    queue = deque()
    # Returns a map of the maximum component depth of each glyph.
    # - a glyph with no components has depth 0,
    # - a glyph with a component has depth 1,
    # - a glyph with a component that itself has a component has depth 2, etc
    # - a glyph with a cyclical component reference has infinite depth, which is
    #   technically a source error
    depths = {}

    # for cycle detection; anytime a glyph is waiting for components (and so is
    # pushed to the back of the queue) we record its name and the length of the queue.
    # If we process the same glyph twice without the queue having gotten smaller
    # (meaning we have gone through everything in the queue) that means we aren't
    # making progress, and have a cycle.
    waiting_for_components = {}

    for name, glyph in glyphs.items():
        if _has_components(glyph):
            queue.append(glyph)
        else:
            depths[name] = 0

    while queue:
        next_glyph = queue.popleft()
        comp_names = {
            comp.name
            for comp in chain.from_iterable(
                l.components for l in _interesting_layers(next_glyph)
            )
            if comp.name in glyphs  # ignore missing components
        }
        if all(comp in depths for comp in comp_names):
            depths[next_glyph.name] = (
                max((depths[c] for c in comp_names), default=-1) + 1
            )
            waiting_for_components.pop(next_glyph.name, None)
        else:
            # else push to the back to try again after we've done the rest
            # (including the currently missing components)
            last_queue_len = waiting_for_components.get(next_glyph.name)
            waiting_for_components[next_glyph.name] = len(queue)
            if last_queue_len != len(queue):
                logger.debug("glyph '%s' is waiting for components", next_glyph.name)
                queue.append(next_glyph)
            else:
                depths[next_glyph.name] = float("inf")
                waiting_for_components.pop(next_glyph.name, None)
                logger.warning("glyph '%s' has cyclical components", next_glyph.name)

    assert not waiting_for_components
    assert len(depths) == len(glyphs)

    return depths


def depth_sorted_composite_glyphs(glyphs: dict[str, GSGlyph]) -> list[str]:
    depths = compute_max_component_depths(glyphs)
    # skip glyphs with infinite depth (cyclic dependencies)
    by_depth = sorted(
        (depth, name) for name, depth in depths.items() if not isinf(depth)
    )
    return [name for _, name in by_depth]
