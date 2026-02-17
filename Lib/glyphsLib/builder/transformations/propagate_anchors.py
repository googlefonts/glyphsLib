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
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.varLib.models import VariationModel, normalizeLocation

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
    propagate_all_anchors_impl(glyphs, font=font, glyph_data=glyph_data)


# the actual implementation, easier to test and compare with the original Rust code
def propagate_all_anchors_impl(
    glyphs: dict[str, GSGlyph],
    *,
    font: GSFont | None = None,
    glyph_data: glyphdata.GlyphData | None = None,
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

    # For brace layer interpolation: map layer_id -> design-space location
    if font and font.masters:
        from glyphsLib.builder.axes import get_axis_definitions, get_regular_master

        axis_defs = get_axis_definitions(font)
        default_master = get_regular_master(font)
        master_locations = {}
        for master in font.masters:
            master_locations[master.id] = {
                a.name: a.get_design_loc(master) for a in axis_defs
            }
        default_loc = master_locations[default_master.id]
        axes_triples = {}
        for axis_def in axis_defs:
            vals = [loc[axis_def.name] for loc in master_locations.values()]
            axes_triples[axis_def.name] = (
                min(vals), default_loc[axis_def.name], max(vals)
            )
    else:
        master_locations = {}
        axes_triples = {}
    layer_locations: dict[str, dict[str, float]] = {}
    variation_model_cache: dict = {}

    for name in todo:
        glyph = glyphs[name]
        for layer in _interesting_layers(glyph):
            # Record this layer's location before traversal so it's available
            # for interpolation of component anchors at brace layer locations
            loc = _get_layer_location(layer, master_locations)
            if loc is not None:
                layer_locations[layer.layerId] = loc
            anchors = anchors_traversing_components(
                glyph,
                layer,
                glyphs,
                all_anchors,
                num_base_glyphs,
                glyph_data,
                layer_locations=layer_locations,
                axes_triples=axes_triples,
                variation_model_cache=variation_model_cache,
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


def _is_master_layer(layer: GSLayer) -> bool:
    # Treat smart component layers as master layers
    return layer._is_master_layer or (
        layer.parent.smartComponentAxes and layer.smartComponentPoleMapping
    )


def _interesting_layers(glyph):
    return (
        l
        for l in glyph.layers
        if _is_master_layer(l) or l._is_bracket_layer() or l._is_brace_layer()
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


def _get_layer_location(
    layer: GSLayer,
    master_locations: dict[str, dict[str, float]],
) -> dict[str, float] | None:
    """Return the design-space coordinates for a layer as a dict.

    For master layers, this is the master's axis values.
    For brace (intermediate) layers, this is the brace coordinates, filled
    with the associated master's values for any missing trailing axes.
    Returns None for other layer types (bracket, backup, etc.).
    """
    if not master_locations:
        return None
    if layer._is_master_layer:
        return master_locations[layer.layerId]
    if layer._is_brace_layer():
        master_loc = master_locations.get(layer.associatedMasterId)
        if master_loc is None:
            return None
        axis_names = list(master_loc.keys())
        coords = layer._brace_coordinates()
        # Fill missing trailing axes with the associated master's values
        loc = {}
        for i, name in enumerate(axis_names):
            if i < len(coords):
                loc[name] = coords[i]
            else:
                loc[name] = master_loc[name]
        return loc
    return None


def _interpolate_component_anchors(
    component_name: str,
    target_location: dict[str, float],
    all_anchors: dict[str, dict[str, list[GSAnchor]]],
    layer_locations: dict[str, dict[str, float]],
    axes_triples: dict[str, tuple[float, float, float]],
    variation_model_cache: dict,
) -> list[GSAnchor] | None:
    """Interpolate a component's anchors at a location where it has no source.

    Collects all available (location, anchors) pairs for the component, builds
    a VariationModel from normalized locations, and interpolates each anchor
    independently. Models are cached by source location set.

    Returns None if the component has no entries in all_anchors or interpolation
    fails entirely.
    """
    comp_layers = all_anchors.get(component_name)
    if not comp_layers:
        return None

    # Collect (location, anchors) pairs, deduplicating by normalized location
    seen: dict[tuple[tuple[str, float], ...], list[GSAnchor]] = {}
    loc_dicts: list[dict[str, float]] = []
    for layer_id, layer_anchors in comp_layers.items():
        loc = layer_locations.get(layer_id)
        if loc is None:
            continue
        norm_loc = normalizeLocation(loc, axes_triples)
        key = tuple(sorted(norm_loc.items()))
        if key not in seen:
            seen[key] = layer_anchors
            loc_dicts.append(norm_loc)

    if not seen:
        return None

    per_location = list(seen.items())
    norm_target = normalizeLocation(target_location, axes_triples)

    # Get canonical anchor names from the first source
    anchor_names = [a.name for a in per_location[0][1]]
    if not anchor_names:
        return []

    # Build per-anchor {normalized_location: position} maps
    per_anchor: dict[str, list[tuple[dict[str, float], Point]]] = {}
    for (key, anchors), norm_loc in zip(per_location, loc_dicts):
        for anchor in anchors:
            if anchor.name in anchor_names:
                per_anchor.setdefault(anchor.name, []).append(
                    (norm_loc, anchor.position)
                )

    axis_order = list(axes_triples.keys())

    # Interpolate each anchor independently from its own set of source locations
    result = []
    for name in anchor_names:
        sources = per_anchor.get(name)
        if not sources:
            continue

        source_locs = [loc for loc, _ in sources]
        cache_key = frozenset(tuple(sorted(loc.items())) for loc in source_locs)
        if cache_key not in variation_model_cache:
            try:
                variation_model_cache[cache_key] = VariationModel(
                    source_locs, axisOrder=axis_order
                )
            except Exception as e:
                logger.warning(
                    "failed to build VariationModel for anchor '%s' on "
                    "component '%s': %s",
                    name,
                    component_name,
                    e,
                )
                continue

        model = variation_model_cache[cache_key]
        master_values = [
            GlyphCoordinates([(pos.x, pos.y)]) for _, pos in sources
        ]

        try:
            interpolated = model.interpolateFromMasters(norm_target, master_values)
        except Exception as e:
            logger.warning(
                "failed to interpolate anchor '%s' on component '%s': %s",
                name,
                component_name,
                e,
            )
            continue

        if interpolated:
            x, y = interpolated[0]
            result.append(
                GSAnchor(name=name, position=Point(round(x, 6), round(y, 6)))
            )

    return result if result else None


def _interpolate_smart_component_anchors(
    layer: GSLayer,
    component: GSComponent,
    glyphs: dict[str, GSGlyph],
    done_anchors: dict[str, dict[str, list[GSAnchor]]],
    anchors: list[GSAnchor],
) -> None:
    from ..smart_components import get_smart_component_variation_model

    model, location, masters = get_smart_component_variation_model(layer, component)
    if model is not None:
        coords = [
            GlyphCoordinates(
                [
                    anchor.position
                    for anchor in get_component_layer_anchors(
                        component, master, glyphs, done_anchors
                    )
                ]
            )
            for master in masters
        ]

        try:
            new_coords = model.interpolateFromMasters(location, coords)
        except Exception as e:
            raise ValueError(
                "Could not interpolate smart component %s used in %s"
                % (component.name, layer)
            ) from e

        for anchor, new_coord in zip(anchors, new_coords):
            anchor.position = Point(new_coord[0], new_coord[1])


def _get_base_glyph_count(
    base_glyph_counts: dict[(str, str), int],
    component_name: str,
    layer: GSLayer,
) -> int:
    """Look up the base glyph count for a component, handling bracket layers.

    Synthesized bracket layers on composites have different layerIds than their
    component's bracket layers. When the exact (name, layerId) lookup misses,
    fall back to the associated master's layer.
    """
    count = base_glyph_counts.get((component_name, layer.layerId))
    if count is not None:
        return count
    return base_glyph_counts.get((component_name, layer.associatedMasterId), 0)


def anchors_traversing_components(
    glyph: GSGlyph,
    layer: GSLayer,
    glyphs: dict[str, GSGlyph],
    done_anchors: dict[str, dict[str, list[GSAnchor]]],
    base_glyph_counts: dict[(str, str), int],
    glyph_data: glyphdata.GlyphData | None = None,
    layer_locations: dict[str, dict[str, float]] | None = None,
    axes_triples: dict[str, tuple[float, float, float]] | None = None,
    variation_model_cache: dict | None = None,
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
            # Component doesn't have an explicit source at this location (e.g. the
            # composite has a brace layer that its component doesn't). Try to
            # interpolate anchors from the component's available sources.
            if (
                layer._is_brace_layer()
                and layer_locations is not None
                and axes_triples
                and variation_model_cache is not None
            ):
                target_loc = layer_locations.get(layer.layerId)
                if target_loc is None:
                    logger.warning(
                        "brace layer '%s' of glyph '%s' has no known "
                        "design-space location; skipping anchor interpolation",
                        layer.name,
                        glyph.name,
                    )
                else:
                    anchors = _interpolate_component_anchors(
                        component.name,
                        target_loc,
                        done_anchors,
                        layer_locations,
                        axes_triples,
                        variation_model_cache,
                    )
            if anchors is None:
                logger.debug(
                    "could not get layer '%s' for component '%s' of glyph '%s'",
                    layer.layerId,
                    component.name,
                    glyph.name,
                )
                continue

        if component.component and component.component.smartComponentAxes:
            # If this is a smart component, we need to interpolate the anchors
            _interpolate_smart_component_anchors(
                layer, component, glyphs, done_anchors, anchors
            )

        # if this component has an explicitly set attachment anchor, use it
        if component_idx > 0 and component.anchor:
            maybe_rename_component_anchor(component.anchor, anchors)

        component_number_of_base_glyphs = _get_base_glyph_count(
            base_glyph_counts, component.name, layer
        )

        comb_has_underscore = any(
            len(a.name) >= 2 and a.name.startswith("_") for a in anchors
        )
        comb_has_exit = any(a.name.startswith("exit") for a in anchors)
        if not (comb_has_underscore or comb_has_exit):
            # delete exit anchors we may have taken from earlier components
            # (since a glyph should only have one exit anchor, and logically its
            # at the end)
            all_anchors = {
                n: a for n, a in all_anchors.items() if not n.startswith("exit")
            }

        component_transform = Transform(*component.transform)
        xscale, yscale = get_xy_rotation(component_transform)
        for anchor in anchors:
            new_has_underscore = anchor.name.startswith("_")
            if (component_idx > 0 or has_underscore) and new_has_underscore:
                continue
            # skip entry anchors on non-first glyphs
            if component_idx > 0 and anchor.name.startswith("entry"):
                continue

            new_anchor_name = rename_anchor_for_scale(anchor.name, xscale, yscale)
            if (
                is_ligature
                and component_number_of_base_glyphs > 0
                and not new_has_underscore
                and not (
                    new_anchor_name.startswith("exit")
                    or new_anchor_name.startswith("entry")
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

        number_of_base_glyphs += _get_base_glyph_count(
            base_glyph_counts, component.name, layer
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
            and not (name.startswith("exit") or name.startswith("entry"))
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
    if component.name not in anchors:
        return None  # nothing to propagate

    glyph = glyphs.get(component.name)
    if glyph is None:
        return None  # invalid component reference, skip

    layer_anchors = None

    parent_is_master = _is_master_layer(layer)
    parent_is_bracket = layer._is_bracket_layer()
    parent_is_brace = layer._is_brace_layer()
    parent_axis_rules = (
        [] if not parent_is_bracket else list(layer._bracket_axis_rules())
    )

    # Try matching: master layer (by layerId), bracket layer (by axis rules +
    # associated master), or brace layer (by coordinates + associated master).
    for comp_layer in _interesting_layers(glyph):
        if (
            parent_is_bracket
            and comp_layer._is_bracket_layer()
            and comp_layer.associatedMasterId == layer.associatedMasterId
            and (list(comp_layer._bracket_axis_rules()) == parent_axis_rules)
        ) or (parent_is_master and comp_layer.layerId == layer.layerId):
            layer_anchors = anchors[component.name][comp_layer.layerId]
            break
        if (
            parent_is_brace
            and comp_layer._is_brace_layer()
            and comp_layer._brace_coordinates() == layer._brace_coordinates()
            and comp_layer.layerId in anchors.get(component.name, {})
        ):
            layer_anchors = anchors[component.name][comp_layer.layerId]
            break

    # For brace layers, return None when no match is found so the caller can
    # try interpolation. For other layer types, fall back to the associated master.
    if layer_anchors is None and not parent_is_brace:
        layer_anchors = anchors[component.name][layer.associatedMasterId]

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
