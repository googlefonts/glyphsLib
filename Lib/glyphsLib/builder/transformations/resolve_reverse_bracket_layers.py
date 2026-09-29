"""Turn "reverse" bracket layers into ordinary ones, like Glyphs.app does.

In a reverse bracket setup, a master layer carries axis rules itself, and one
of its alternate (aka 'bracket') layers has blank axis rules, i.e. no bounds on
any axis (``[]`` in the Glyphs UI):

https://glyphsapp.com/learn/switching-shapes#reverse-bracket-layers

Glyphs.app exports the blank alternate as the glyph's design at that master,
and the master layer as the alternate for its rules. We swap the two layers,
which gives the equivalent ordinary bracket setup.

Outside that setup, a blank alternate is not exported as a substitution at
all. It loses its axis rules (so it is kept, like any other non-special layer,
e.g. as a backup layer), and so does a master layer with blank ones.
"""

import logging

logger = logging.getLogger(__name__)


def _is_bounded(layer):
    return any(
        axis_min is not None or axis_max is not None
        for axis_min, axis_max in layer._bracket_axis_rules()
    )


def _is_blank_alternate(layer):
    # only plain alternates: not brace, color, smart component or other
    # special layers
    return (
        set(layer.attributes) == {"axisRules"}
        and not layer.partSelection
        and len(layer.attributes["axisRules"]) > 0
        and not _is_bounded(layer)
    )


def resolve_reverse_bracket_layers(font, *, glyph_data=None):
    if font.format_version < 3:
        return
    master_ids = {master.id for master in font.masters}
    for glyph in font.glyphs:
        layers = list(glyph.layers)
        swapped = {}
        master_layers = [l for l in layers if l.layerId in master_ids]
        for master_layer in master_layers:
            blanks = [
                layer
                for layer in layers
                if layer.layerId not in master_ids
                and layer.associatedMasterId == master_layer.layerId
                and _is_blank_alternate(layer)
            ]
            master_is_bounded = master_layer._is_bracket_layer() and _is_bounded(
                master_layer
            )
            if master_is_bounded and len(blanks) == 1:
                blank = blanks[0]
                swapped[id(master_layer)] = blank
                swapped[id(blank)] = master_layer
                master_id, blank_id = master_layer.layerId, blank.layerId
                logger.debug(
                    "Glyph '%s': using blank alternate layer '%s' as master '%s'",
                    glyph.name,
                    blank_id,
                    master_id,
                )
                # the old master keeps its axis rules and becomes the alternate
                master_layer.name = blank.name
                master_layer.layerId = blank_id
                master_layer.associatedMasterId = master_id
                del blank.attributes["axisRules"]
                blank.layerId = master_id
                blank.associatedMasterId = master_id
                continue
            for layer in blanks:
                logger.debug(
                    "Glyph '%s': ignoring blank alternate layer '%s'",
                    glyph.name,
                    layer.layerId,
                )
                del layer.attributes["axisRules"]
            if master_layer._is_bracket_layer() and not master_is_bounded:
                del master_layer.attributes["axisRules"]
        if not swapped:
            continue
        # Setting layerId above re-keys the glyph's layers and may drop one on
        # a key collision; rebuilding them from the saved list is what puts
        # both layers of each pair back, in each other's positions.
        glyph.layers = [swapped.get(id(layer), layer) for layer in layers]
