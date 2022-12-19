from collections import defaultdict
from functools import partial
from typing import Any
import copy

from fontTools import designspaceLib
from fontTools.varLib import FEAVAR_FEATURETAG_LIB_KEY
from fontTools.varLib.featureVars import overlayFeatureVariations

from glyphsLib import util
from .constants import (
    BRACKET_GLYPH_TEMPLATE,
    GLYPHLIB_PREFIX,
)


def to_designspace_bracket_layers(self):
    """Extract bracket layers in a GSGlyph into free-standing UFO glyphs with
    Designspace substitution rules.
    """
    if not self._designspace.axes:
        raise ValueError(
            "Cannot apply bracket layers unless at least one axis is defined."
        )

    find_component_use(self)

    # At this stage we will naively emit a designspace rule for every layer.
    bracket_layer_map = defaultdict(partial(defaultdict, list))
    rules = []
    tag_to_name = {axis.tag: axis.name for axis in self._designspace.axes}
    for layer in self.bracket_layers:
        box_with_tag = layer._bracket_info(self._designspace.axes)
        glyph_name = layer.parent.name
        # It'd be nice to use tag for both glyph names and designspace
        # rules, but given designspace refers to axes by name, our hand
        # is forced. (We don't use axis names in glyph names because they
        # might have spaces in them.)
        box_with_name = {tag_to_name[k]: v for k, v in box_with_tag.items()}
        bracket_layer_map[glyph_name][util.freezedict(box_with_tag)].append(layer)
        rules.append(
            (
                [box_with_name],
                {glyph_name: _bracket_glyph_name(self, glyph_name, box_with_tag)},
            )
        )

    # overlayFeatureVariations does exactly what we need in terms of
    # splitting rules into non-overlapping boxes and consolidating
    # multiple substitutions into a single rule.
    for box, mappings in overlayFeatureVariations(rules):
        # Reduce the mappings to a single mapping
        mapping = {}
        for this_mapping in mappings:
            mapping.update(this_mapping)

        self._designspace.addRule(_make_designspace_rule(box, mapping))

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
        for frozenbox, bracket_layers in glyph_bracket_layers.items():
            box = dict(frozenbox)
            for missing_master_layer_id in master_ids.difference(
                bl.associatedMasterId for bl in bracket_layers
            ):
                master_layer = glyph.layers[missing_master_layer_id]
                bracket_layers.append(master_layer)
                implicit_bracket_layers.add(id(master_layer))

            bracket_glyphs.add(_bracket_glyph_name(self, glyph_name, box))

    for glyph_name, glyph_bracket_layers in bracket_layer_map.items():
        for frozenbox, layers in glyph_bracket_layers.items():
            box = dict(frozenbox)
            for layer in layers:
                layer_id = layer.associatedMasterId or layer.layerId
                ufo_font = self._sources[layer_id].font
                ufo_layer = ufo_font.layers.defaultLayer
                ufo_glyph_name = _bracket_glyph_name(self, glyph_name, box)
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
                    bracket_comp_name = _bracket_glyph_name(self, comp.baseGlyph, box)
                    if bracket_comp_name in bracket_glyphs:
                        comp.baseGlyph = bracket_comp_name
                # Update kerning groups and pairs, bracket glyphs inherit the
                # parent's kerning.
                _expand_kerning_to_brackets(glyph_name, ufo_glyph_name, ufo_font)


def _bracket_glyph_name(self, glyph_name, box):
    if box not in self.alternate_names_map[glyph_name]:
        self.alternate_names_map[glyph_name].append(box)
    description = "varAlt%02i" % (1 + self.alternate_names_map[glyph_name].index(box))
    return BRACKET_GLYPH_TEMPLATE.format(glyph_name=glyph_name, description=description)


def _make_designspace_rule(box, mapping):
    description = ".".join(
        f"{name}_{min}_{max}" for name, (min, max) in sorted(box.items())
    )
    rule = designspaceLib.RuleDescriptor()
    rule.name = "BRACKET." + description
    rule.conditionSets.append(
        [
            {"name": axis_name, "minimum": range_min, "maximum": range_max}
            for axis_name, (range_min, range_max) in box.items()
        ]
    )
    rule.subs = list(mapping.items())
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


def find_component_use(self):
    """If a glyph uses a component which has alternate layers, that
    glyph also must have the same alternate layers or else it will not
    correctly swap. We copy the layer locations from the component into
    the glyph which uses it."""
    # First let's put all the layers in a sensible order so we can
    # query them efficiently
    master_layers = defaultdict(dict)
    alternate_layers = defaultdict(lambda: defaultdict(list))
    master_ids = set(master.id for master in self.font.masters)

    for glyph in self.font.glyphs:
        for layer in glyph.layers:
            if layer.layerId in master_ids:
                master_layers[layer.layerId][glyph.name] = layer
            elif layer.associatedMasterId in master_ids:
                alternate_layers[layer.associatedMasterId][glyph.name].append(layer)

    # Now let's find those which have a problem: they use components,
    # the components have some alternate layers, but the layer doesn't
    # have the same.
    # Because of the possibility of deeply nested components, we need
    # to keep doing this, bubbling up fixes until there's nothing left
    # to do.
    while True:
        problematic_glyphs = defaultdict(set)
        for master, layers in master_layers.items():
            for glyph_name, layer in layers.items():
                my_bracket_layers = [
                    layer._bracket_info(self._designspace.axes)
                    for layer in alternate_layers[master][glyph_name]
                ]
                for comp in layer.components:
                    # Check our alternate layer set-up agrees with theirs
                    components_bracket_layers = [
                        layer._bracket_info(self._designspace.axes)
                        for layer in alternate_layers[master][comp.name]
                    ]
                    if my_bracket_layers != components_bracket_layers:
                        # Find what we need to add, and make them hashable
                        they_have = set(
                            tuple(x.items())
                            for x in components_bracket_layers
                            if x.items()
                        )
                        i_have = set(
                            tuple(x.items()) for x in my_bracket_layers if x.items()
                        )
                        needed = they_have - i_have
                        if needed:
                            problematic_glyphs[(glyph_name, master)] |= needed

        if not problematic_glyphs:
            break

        # And now, fix the problem.
        for (glyph_name, master), needed_brackets in problematic_glyphs.items():
            my_bracket_layers = [
                layer._bracket_info(self._designspace.axes)
                for layer in alternate_layers[master][glyph_name]
            ]
            if my_bracket_layers:
                # We have some bracket layers, but they're not the ones we
                # expect. Do the wrong thing, because doing the right thing
                # requires major investment.
                master_name = self.font.masters[master].name
                self.logger.warning(
                    f"Glyph {glyph_name} in master {master_name} has different "
                    "alternate layers to components that it uses. We don't "
                    "currently support this case, so some alternate layers will "
                    "not be applied. Consider fixing the source instead."
                )
            # Just copy the master layer for each thing we need.
            for box in needed_brackets:
                new_layer = synthesize_bracket_layer(
                    master_layers[master][glyph_name], dict(box), self._designspace.axes
                )
                self.font.glyphs[glyph_name].layers.append(new_layer)
                self.bracket_layers.append(new_layer)
                alternate_layers[master][glyph_name].append(new_layer)


def synthesize_bracket_layer(old_layer, box, axes):
    new_layer = copy.copy(old_layer)  # We don't need a deep copy of everything
    new_layer.layerId = ""
    new_layer.associatedMasterId = old_layer.layerId

    if new_layer.parent.parent.format_version == 2:
        axis, (bottom, top) = next(iter(box.items()))
        designspace_min, designspace_max = util.designspace_min_max(axes[0])
        if designspace_min == bottom:
            new_layer.name = old_layer.name + f" ]{top}]"
        else:
            new_layer.name = old_layer.name + f"[{bottom}]"
    else:
        new_layer.attributes = dict(
            new_layer.attributes
        )  # But we do need our own version of this
        new_layer.attributes["axisRules"] = []
        for axis in axes:
            if axis.tag in box:
                new_layer.attributes["axisRules"].append(
                    {
                        "min": box[axis.tag][0],
                        "max": box[axis.tag][1],
                    }
                )
            else:
                new_layer.attributes["axisRules"].append({})

    assert new_layer._bracket_info(axes) == box
    return new_layer
