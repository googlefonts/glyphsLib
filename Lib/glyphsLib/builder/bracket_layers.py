from collections import OrderedDict, defaultdict
from functools import partial
import re
from typing import Any, Dict

from fontTools import designspaceLib

from glyphsLib import util
from .constants import (
    GLYPHLIB_PREFIX,
)

BRACKET_GLYPH_TEMPLATE = "{glyph_name}.{rev}BRACKET.{location}"
REVERSE_BRACKET_LABEL = "REV_"
BRACKET_GLYPH_RE = re.compile(
    r"(?P<glyph_name>.+)\.(?P<rev>{})?BRACKET\.(?P<location>\d+)$".format(
        REVERSE_BRACKET_LABEL
    )
)
BRACKET_GLYPH_SUFFIX_RE = re.compile(r".*(\..*BRACKET\.\d+)$")


class Region(frozenset):
    def __lt__(self, other):
        # Most specific first
        if len(self) != len(other):
            return len(self) < len(other)
        d1 = self.as_dict()
        d2 = other.as_dict()
        for axis in set(d1.keys()) | set(d2.keys()):
            if axis in d1 and axis in d2:
                if d1[axis][0] != d2[axis][0]:
                    return d1[axis][0] < d2[axis][0]
                return d1[axis][1] < d2[axis][1]
        return list(d1.keys()) < list(d2.keys())

    def as_dict(self):
        d = {}
        for axis, bracket_min, bracket_max in self:
            d[axis.name] = (bracket_min, bracket_max)
        return d

    def find_crossovers(self, min_crossovers, max_crossovers):
        for axis, bracket_min, bracket_max in self:
            if bracket_min is not None:
                min_crossovers[axis.name].add(bracket_min)
            elif bracket_max is not None:
                max_crossovers[axis.name].add(bracket_max)

    def bracket_glyph_name(self, glyph_name, reverse=None):
        if len(self) > 1:
            locations = []
            for axis, bracket_min, bracket_max in self:
                this_location = axis.tag + "."
                if bracket_max is not None:
                    this_location += "REVERSE." + str(bracket_max)
                else:
                    this_location += str(bracket_min)
                locations.append(this_location)
            location = ".".join(locations)
            reverse = False
        else:
            (_, bracket_min, bracket_max) = list(self)[0]
            if reverse is None:
                reverse = bracket_max is not None
            if reverse:
                location = bracket_max
            else:
                location = bracket_min
        return BRACKET_GLYPH_TEMPLATE.format(
            glyph_name=glyph_name,
            rev=REVERSE_BRACKET_LABEL if reverse else "",
            location=location,
        )

    def rule_name(self):
        if len(self) == 1:
            (_, range_min, range_max) = list(self)[0]
            assert range_min and range_max
            return f"BRACKET.{range_min}.{range_max}"
        return "BRACKET." + ".".join(
            f"{axis.tag}.{range_min}.{range_max}" for (axis, range_min, range_max)
            in self
        )

    def condition_set(self):
        return [
            {"name": axis.name, "minimum": range_min, "maximum": range_max}
            for axis, range_min, range_max in self
        ]

def to_ufo_bracket_layers(self):
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

    # Organize all bracket layers by glyph name and crossover value, so later we
    # can go through the layers by region and copy them to free-standing glyphs
    bracket_layer_map = defaultdict(partial(defaultdict, list))
    for layer in self.bracket_layers:
        region = validate_bracket_info(self, layer)
        if region is None:
            continue
        glyph_name = layer.parent.name
        bracket_layer_map[glyph_name][region].append(layer)

    # Sort crossovers into rule buckets, one for regular bracket layers (in which
    # the location represents the min value) and one for 'reverse' bracket layers
    # (in which the location is the max value).
    max_rule_bucket = defaultdict(list)
    min_rule_bucket = defaultdict(list)
    for glyph_name, glyph_bracket_layers in sorted(bracket_layer_map.items()):
        add_to_rule_buckets(self, glyph_name, glyph_bracket_layers, min_rule_bucket, max_rule_bucket)

    # Generate rules for the bracket layers.
    for reverse, rule_bucket in ((True, max_rule_bucket), (False, min_rule_bucket)):
        for region, glyph_names in sorted(rule_bucket.items()):
            rule = _make_designspace_rule(
                glyph_names,
                region,
                reverse,
            )
            self._designspace.addRule(rule)

    # Finally, copy bracket layers to their own glyphs.
    _copy_bracket_layers_to_ufo_glyphs(self, bracket_layer_map)

    # re-generate the GDEF table since we have added new BRACKET glyphs, which may
    # also need to be included: https://github.com/googlefonts/glyphsLib/issues/578
    if self.generate_GDEF:
        self.regenerate_gdef()

def _designspace_axis_limits(self, axis):
    # Determine the axis scale in design space because crossovers/locations are
    # in design space (axis.default/minimum/maximum may be user space).
    if axis.map:
        axis_scale = [design_location for _, design_location in axis.map]
        return min(axis_scale), max(axis_scale)
    else:  # No mapping means user and design space are the same.
        return axis.minimum, axis.maximum

def validate_bracket_info(self, layer):
    bracket_info = layer._bracket_info()
    r = []
    for bracket_axis_id, bracket_axis in enumerate(self._designspace.axes):
        if bracket_axis_id not in bracket_info:
            continue
        bracket_min, bracket_max = bracket_info[bracket_axis_id]

        bracket_axis_min, bracket_axis_max = _designspace_axis_limits(self, bracket_axis)

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
        r.append( (bracket_axis, bracket_min, bracket_max) )
    if not r:
        return None
    return Region(r)


def add_to_rule_buckets(self, glyph_name, glyph_bracket_layers, min_rule_bucket, max_rule_bucket):
    min_crossovers = defaultdict(set)
    max_crossovers = defaultdict(set)
    for region in glyph_bracket_layers.keys():
        region.find_crossovers(min_crossovers, max_crossovers)

    check_for_overlapping_locations(self, glyph_name, min_crossovers, max_crossovers)

    bracket_axis = self._designspace.axes[0]
    bracket_axis_min, bracket_axis_max = _designspace_axis_limits(self, bracket_axis)

    # XXX
    max_crossovers = max_crossovers[bracket_axis.name]
    min_crossovers = min_crossovers[bracket_axis.name]

    max_crossovers = list(sorted(max_crossovers))
    if bracket_axis_min not in max_crossovers:
        max_crossovers = [bracket_axis_min] + max_crossovers
    for crossover_min, crossover_max in util.pairwise(max_crossovers):
        max_rule_bucket[Region( [(bracket_axis, int(crossover_min), int(crossover_max))] )].append(
            glyph_name
        )
    min_crossovers = list(sorted(min_crossovers))
    if bracket_axis_max not in min_crossovers:
        min_crossovers = min_crossovers + [bracket_axis_max]
    for crossover_min, crossover_max in util.pairwise(min_crossovers):
        min_rule_bucket[Region( [(bracket_axis, int(crossover_min), int(crossover_max) )] )].append(
            glyph_name
        )

# reverse and non-reverse bracket layers with overlapping ranges are tricky to
# implement as DS rules. They are relatively unlikely, and can usually be
# rewritten so that they do not overlap. For laziness/simplicity, where we
# simply warn that output may not be as expected.
def check_for_overlapping_locations(self, glyph_name, min_crossovers, max_crossovers):
    axis_names = [ax.name for ax in self._designspace.axes]
    for axis in axis_names:
        invalid_locs = [
            (mx, mn)
            for mx, mn in zip(sorted(max_crossovers[axis]), sorted(min_crossovers[axis]))
            if mx > mn
        ]
        if invalid_locs:
            self.logger.warning(
                "Bracket layers for glyph '%s' have overlapping ranges: %s",
                glyph_name,
                ", ".join("]{}] > [{}]".format(*values) for values in invalid_locs),
        )

def _copy_bracket_layers_to_ufo_glyphs(self, bracket_layer_map):
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
        for (region, bracket_layers) in glyph_bracket_layers.items():

            for missing_master_layer_id in master_ids.difference(
                bl.associatedMasterId for bl in bracket_layers
            ):
                master_layer = glyph.layers[missing_master_layer_id]
                bracket_layers.append(master_layer)
                implicit_bracket_layers.add(id(master_layer))

            bracket_glyphs.add(region.bracket_glyph_name(glyph_name))

    for glyph_name, glyph_bracket_layers in bracket_layer_map.items():
        for (region, layers) in glyph_bracket_layers.items():
            for layer in layers:
                layer_id = layer.associatedMasterId or layer.layerId
                ufo_font = self._sources[layer_id].font
                ufo_layer = ufo_font.layers.defaultLayer
                ufo_glyph_name = region.bracket_glyph_name(glyph_name)
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
                    bracket_comp_name = region.bracket_glyph_name(comp.baseGlyph)
                    if bracket_comp_name in bracket_glyphs:
                        comp.baseGlyph = bracket_comp_name
                # Update kerning groups and pairs, bracket glyphs inherit the
                # parent's kerning.
                _expand_kerning_to_brackets(glyph_name, ufo_glyph_name, ufo_font)


def _make_designspace_rule(glyph_names, region, reverse=False):
    rule = designspaceLib.RuleDescriptor()
    rule.name = region.rule_name()
    rule.conditionSets.append(region.condition_set())
    for glyph_name in glyph_names:
        sub_glyph_name = region.bracket_glyph_name(glyph_name, reverse)
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
