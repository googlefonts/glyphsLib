import copy
import logging
from collections import defaultdict


logger = logging.getLogger(__name__)


def align_alternate_layers(font, glyph_data=None):
    """Ensure composites have the same alternate layers as their components.

    If a glyph uses a component which has alternate (aka 'bracket') layers, that
    glyph also must have the same alternate layers or else it will not correctly swap
    when these are converted GSUB FeatureVariations.
    We copy the layer locations from the component into the glyph which uses it.
    """
    # First let's put all the layers in a sensible order so we can
    # query them efficiently
    master_layers = defaultdict(dict)
    alternate_layers = defaultdict(lambda: defaultdict(list))
    master_ids = set(master.id for master in font.masters)

    for glyph in font.glyphs:
        for layer in glyph.layers:
            if layer.layerId in master_ids:
                master_layers[layer.layerId][glyph.name] = layer
            elif layer.associatedMasterId in master_ids and layer._is_bracket_layer():
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
                my_bracket_layers = {
                    tuple(layer._bracket_axis_rules())
                    for layer in alternate_layers[master][glyph_name]
                }
                for comp in layer.components:
                    # Check our alternate layer set-up agrees with theirs
                    components_bracket_layers = {
                        tuple(layer._bracket_axis_rules())
                        for layer in alternate_layers[master][comp.name]
                    }
                    if my_bracket_layers != components_bracket_layers:
                        # Find what we need to add
                        needed = components_bracket_layers - my_bracket_layers
                        if needed:
                            problematic_glyphs[(glyph_name, master)] |= needed

        if not problematic_glyphs:
            break

        # And now, fix the problem.
        for (glyph_name, master), needed_brackets in problematic_glyphs.items():
            my_bracket_layers = [
                tuple(layer._bracket_axis_rules())
                for layer in alternate_layers[master][glyph_name]
            ]
            if my_bracket_layers:
                # We have some bracket layers, but they're not the ones we
                # expect. Do the wrong thing, because doing the right thing
                # requires major investment.
                master_name = font.masters[master].name
                logger.warning(
                    f"Glyph {glyph_name} in master {master_name} has different "
                    "alternate layers to components that it uses. We don't "
                    "currently support this case, so some alternate layers will "
                    "not be applied. Consider fixing the source instead."
                )
            # Just copy the master layer for each thing we need.
            # Insert the new layers in a predictable, deterministic order based on
            # the bracket layers' axis values.
            for axis_rules in sorted(
                needed_brackets,
                key=lambda rules: tuple(
                    (
                        float("-inf") if r[0] is None else r[0],
                        float("inf") if r[1] is None else r[1],
                    )
                    for r in rules
                ),
            ):
                new_layer = synthesize_bracket_layer(
                    master_layers[master][glyph_name], axis_rules
                )
                font.glyphs[glyph_name].layers.append(new_layer)
                alternate_layers[master][glyph_name].append(new_layer)


def synthesize_bracket_layer(old_layer, axis_rules):
    new_layer = copy.copy(old_layer)  # We don't need a deep copy of everything
    new_layer.layerId = ""
    new_layer.associatedMasterId = old_layer.layerId

    if new_layer.parent.parent.format_version == 2:
        bottom, top = next(iter(axis_rules))
        if bottom is None:
            new_layer.name = old_layer.name + f" ]{top}]"
        elif top is None:
            new_layer.name = old_layer.name + f" [{bottom}]"
        else:
            raise AssertionError(f"either {bottom} or {top} must be None")
    else:
        new_layer.attributes = dict(
            new_layer.attributes
        )  # But we do need our own version of this
        new_layer.attributes["axisRules"] = [
            {"min": bottom, "max": top} for (bottom, top) in axis_rules
        ]

    assert tuple(new_layer._bracket_axis_rules()) == axis_rules
    return new_layer
