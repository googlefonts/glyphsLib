from collections import defaultdict
from functools import partial
from typing import Any

from fontTools import designspaceLib
from fontTools.varLib import FEAVAR_FEATURETAG_LIB_KEY

from glyphsLib import util
from .constants import (
    BRACKET_GLYPH_TEMPLATE,
    REVERSE_BRACKET_LABEL,
    GLYPHLIB_PREFIX,
)


def to_designspace_bracket_layers(self):
    """Extract bracket layers in a GSGlyph into free-standing UFO glyphs with
    Designspace substitution rules.

    As of Glyphs.app 2.6, only single axis bracket layers are supported, we
    assume the axis to be the first axis in the Designspace. Bracket layer
    backgrounds are not round-tripped.

    A glyph can have more than one bracket layer but Designspace
    rule/OpenType variation condition sets apply all substitutions in a rule
    in a range, so we have to potentially sort bracket layers into rule
    buckets. Example: if a glyph "x" has two bracket layers [300] and [600]
    and glyph "a" has bracket layer [300] and the bracket axis tops out at
    1000, we need the following Designspace rules:

    - BRACKET.300.600  # min 300, max 600 on the bracket axis.
      - x -> x.BRACKET.300
    - BRACKET.600.1000
      - x -> x.BRACKET.600
    - BRACKET.300.1000
      - a -> a.BRACKET.300
    """
    if not self._designspace.axes:
        raise ValueError(
            "Cannot apply bracket layers unless at least one axis is defined."
        )
    bracket_axis = self._designspace.axes[0]

    # Determine the axis scale in design space because crossovers/locations are
    # in design space (axis.default/minimum/maximum may be user space).
    if bracket_axis.map:
        axis_scale = [design_location for _, design_location in bracket_axis.map]
        bracket_axis_min = min(axis_scale)
        bracket_axis_max = max(axis_scale)
    else:  # No mapping means user and design space are the same.
        bracket_axis_min = bracket_axis.minimum
        bracket_axis_max = bracket_axis.maximum

    # Organize all bracket layers by glyph name and crossover value, so later we
    # can go through the layers by location and copy them to free-standing glyphs
    bracket_layer_map = defaultdict(partial(defaultdict, list))
    for layer in self.bracket_layers:
        bracket_axis_id, bracket_min, bracket_max = validate_bracket_info(
            self, layer, bracket_axis, bracket_axis_min, bracket_axis_max
        )
        if bracket_min is None and bracket_max is None:
            continue
        glyph_name = layer.parent.name
        bracket_layer_map[glyph_name][(bracket_min, bracket_max)].append(layer)

    # Sort crossovers into rule buckets, one for regular bracket layers (in which
    # the location represents the min value) and one for 'reverse' bracket layers
    # (in which the location is the max value).
    max_rule_bucket = defaultdict(list)
    min_rule_bucket = defaultdict(list)
    for glyph_name, glyph_bracket_layers in sorted(bracket_layer_map.items()):
        min_crossovers = set()
        max_crossovers = set()
        for bracket_min, bracket_max in glyph_bracket_layers.keys():
            if bracket_min is not None:
                min_crossovers.add(bracket_min)
            elif bracket_max is not None:
                max_crossovers.add(bracket_max)
        # reverse and non-reverse bracket layers with overlapping ranges are
        # tricky to implement as DS rules. They are relatively unlikely, and
        # can usually be rewritten so that they do not overlap. For laziness/
        # simplicity, where we simply warn that output may not be as expected.
        invalid_locs = [
            (mx, mn)
            for mx, mn in zip(sorted(max_crossovers), sorted(min_crossovers))
            if mx > mn
        ]
        if invalid_locs:
            self.logger.warning(
                "Bracket layers for glyph '%s' have overlapping ranges: %s",
                glyph_name,
                ", ".join("]{}] > [{}]".format(*values) for values in invalid_locs),
            )
        max_crossovers = list(sorted(max_crossovers))
        if bracket_axis_min not in max_crossovers:
            max_crossovers = [bracket_axis_min] + max_crossovers
        for crossover_min, crossover_max in util.pairwise(max_crossovers):
            max_rule_bucket[(int(crossover_min), int(crossover_max))].append(glyph_name)
        min_crossovers = list(sorted(min_crossovers))
        if bracket_axis_max not in min_crossovers:
            min_crossovers = min_crossovers + [bracket_axis_max]
        for crossover_min, crossover_max in util.pairwise(min_crossovers):
            min_rule_bucket[(int(crossover_min), int(crossover_max))].append(glyph_name)

    # Generate rules for the bracket layers.
    for reverse, rule_bucket in ((True, max_rule_bucket), (False, min_rule_bucket)):
        for (axis_range_min, axis_range_max), glyph_names in sorted(
            rule_bucket.items()
        ):
            rule = _make_designspace_rule(
                glyph_names,
                bracket_axis.name,
                axis_range_min,
                axis_range_max,
                reverse,
            )
            self._designspace.addRule(rule)

    # Set feature for rules
    feat = self.font.customParameters["Feature for Feature Variations"]
    if feat == "rclt":
        self._designspace.rulesProcessingLast = True
    elif feat and feat != "rvrn":
        self._designspace.lib[FEAVAR_FEATURETAG_LIB_KEY] = feat

    # Finally, copy bracket layers to their own glyphs.
    copy_bracket_layers_to_ufo_glyphs(self, bracket_layer_map)

    # re-generate the GDEF table since we have added new BRACKET glyphs, which may
    # also need to be included: https://github.com/googlefonts/glyphsLib/issues/578
    if self.generate_GDEF:
        self.regenerate_gdef()


def validate_bracket_info(
    self, layer, bracket_axis, bracket_axis_min, bracket_axis_max
):
    bracket_axis_id, bracket_min, bracket_max = layer._bracket_info()

    if bracket_axis_id != 0:
        raise ValueError("For now, bracket layers can only apply to the first axis")

    # Convert [500<wght<(max)] to [500<wght], etc.
    if bracket_min == bracket_axis_min:
        bracket_min = None
    if bracket_max == bracket_axis_max:
        bracket_max = None

    if bracket_min is not None and bracket_max is not None:
        raise ValueError("Alternate rules with min and max range not yet supported")

    glyph_name = layer.parent.name

    if (
        bracket_min is not None
        and not bracket_axis_min <= bracket_min <= bracket_axis_max
    ) or (
        bracket_max is not None
        and not bracket_axis_min <= bracket_max <= bracket_axis_max
    ):
        raise ValueError(
            "Glyph {glyph_name}: Bracket layer {layer_name} must be within the "
            "design space bounds of the {bracket_axis_name} axis: minimum "
            "{bracket_axis_minimum}, maximum {bracket_axis_maximum}.".format(
                glyph_name=glyph_name,
                layer_name=layer.name,
                bracket_axis_name=bracket_axis.name,
                bracket_axis_minimum=bracket_axis_min,
                bracket_axis_maximum=bracket_axis_max,
            )
        )
    return bracket_axis_id, bracket_min, bracket_max


def copy_bracket_layers_to_ufo_glyphs(self, bracket_layer_map):
    font = self.font
    master_ids = {m.id for m in font.masters}
    # when a glyph master layer doesn't have an explicitly associated bracket layer
    # for any crosspoint locations, we assume the master layer itself will be
    # used implicitly as bracket layer for that location. See "Switching Only One
    # Master" paragraph in "Alternating Glyph Shapes" tutorial at:
    # https://glyphsapp.com/tutorials/alternating-glyph-shapes
    implicit_bracket_layers = set()
    # collect all bracket glyph names for resolving composite references
    bracket_glyphs = set()

    for glyph_name, glyph_bracket_layers in bracket_layer_map.items():
        glyph = font.glyphs[glyph_name]
        for (
            (bracket_min, bracket_max),
            bracket_layers,
        ) in glyph_bracket_layers.items():

            for missing_master_layer_id in master_ids.difference(
                bl.associatedMasterId for bl in bracket_layers
            ):
                master_layer = glyph.layers[missing_master_layer_id]
                bracket_layers.append(master_layer)
                implicit_bracket_layers.add(id(master_layer))

            if bracket_max is None:
                reverse = False
                location = bracket_min
            else:
                reverse = True
                location = bracket_max

            bracket_glyphs.add(_bracket_glyph_name(glyph_name, reverse, location))

    for glyph_name, glyph_bracket_layers in bracket_layer_map.items():
        for (bracket_min, bracket_max), layers in glyph_bracket_layers.items():
            if bracket_max is None:
                reverse = False
                location = bracket_min
            else:
                reverse = True
                location = bracket_max

            for layer in layers:
                layer_id = layer.associatedMasterId or layer.layerId
                ufo_font = self._sources[layer_id].font
                ufo_layer = ufo_font.layers.defaultLayer
                ufo_glyph_name = _bracket_glyph_name(glyph_name, reverse, location)
                ufo_glyph = ufo_layer.newGlyph(ufo_glyph_name)
                self.to_ufo_glyph(ufo_glyph, layer, layer.parent)
                ufo_glyph.unicodes = []  # Avoid cmap interference
                # implicit bracket layers have no distinct name, they are simply
                # references to master layers; the empty string is a signal when
                # roundtripping back to Glyphs to skip the duplicate layers.
                ufo_glyph.lib[GLYPHLIB_PREFIX + "_originalLayerName"] = (
                    "" if id(layer) in implicit_bracket_layers else layer.name
                )
                # swap components if base glyph contains matching bracket layers.
                for comp in ufo_glyph.components:
                    bracket_comp_name = _bracket_glyph_name(
                        comp.baseGlyph, reverse, location
                    )
                    if bracket_comp_name in bracket_glyphs:
                        comp.baseGlyph = bracket_comp_name
                # Update kerning groups and pairs, bracket glyphs inherit the
                # parent's kerning.
                _expand_kerning_to_brackets(glyph_name, ufo_glyph_name, ufo_font)


def _bracket_glyph_name(glyph_name, reverse, location):
    return BRACKET_GLYPH_TEMPLATE.format(
        glyph_name=glyph_name,
        rev=REVERSE_BRACKET_LABEL if reverse else "",
        location=location,
    )


def _make_designspace_rule(glyph_names, axis_name, range_min, range_max, reverse=False):
    rule_name = f"BRACKET.{range_min}.{range_max}"
    rule = designspaceLib.RuleDescriptor()
    rule.name = rule_name
    rule.conditionSets.append(
        [{"name": axis_name, "minimum": range_min, "maximum": range_max}]
    )
    location = range_max if reverse else range_min
    for glyph_name in glyph_names:
        sub_glyph_name = _bracket_glyph_name(glyph_name, reverse, location)
        rule.subs.append((glyph_name, sub_glyph_name))
    return rule


def _expand_kerning_to_brackets(
    glyph_name: str, ufo_glyph_name: str, ufo_font: Any
) -> None:
    """Ensures that bracket glyphs inherit their parents' kerning."""

    for group, names in ufo_font.groups.items():
        if not group.startswith(("public.kern1.", "public.kern2.")):
            continue
        name_set = set(names)
        if glyph_name in name_set and ufo_glyph_name not in name_set:
            names.append(ufo_glyph_name)

    bracket_kerning = {}
    for (first, second), value in ufo_font.kerning.items():
        first_match = first == glyph_name
        second_match = second == glyph_name
        if first_match and second_match:
            bracket_kerning[(ufo_glyph_name, ufo_glyph_name)] = value
        elif first_match:
            bracket_kerning[(ufo_glyph_name, second)] = value
        elif second_match:
            bracket_kerning[(first, ufo_glyph_name)] = value
    ufo_font.kerning.update(bracket_kerning)
