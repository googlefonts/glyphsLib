import logging
import uuid

from fontTools.varLib.models import VariationModel, normalizeValue

from glyphsLib.classes import GSLayer, GSNode, GSPath
from glyphsLib.builder.axes import get_regular_master


logger = logging.getLogger(__name__)


def resolve_intermediate_components(font):
    for glyph in font.glyphs:
        for layer in glyph.layers:
            if layer._is_brace_layer():
                # First, let's find glyphs with intermediate layers
                # which have components which don't have intermediate layers
                for shape in layer.components:
                    ensure_component_has_sparse_layer(font, shape, layer)


def variation_model(font, locations):
    tags = [axis.axisTag for axis in font.axes]
    limits = {tag: (min(x), max(x)) for tag, x in zip(tags, (zip(*locations)))}
    master_locations = []
    default_location = get_regular_master(font).axes
    for loc in locations:
        this_loc = {}
        for ix, axisTag in enumerate(tags):
            axismin, axismax = limits[axisTag]
            this_loc[axisTag] = normalizeValue(
                loc[ix], (axismin, default_location[ix], axismax)
            )
        master_locations.append(this_loc)
    return VariationModel(master_locations, axisOrder=tags), limits


def ensure_component_has_sparse_layer(font, component, parent_layer):
    tags = [axis.axisTag for axis in font.axes]
    master_locations = [x.axes for x in font.masters]
    _, limits = variation_model(font, master_locations)
    location = tuple(parent_layer._brace_coordinates())
    default_location = get_regular_master(font).axes
    normalized_location = {
        axisTag: normalizeValue(
            location[ix], (limits[axisTag][0], default_location[ix], limits[axisTag][1])
        )
        for ix, axisTag in enumerate(tags)
    }
    componentglyph = component.component
    for layer in componentglyph.layers:
        if layer.layerId == parent_layer.layerId:
            return
        if "coordinates" in layer.attributes and layer._brace_coordinates() == location:
            return

    # We'll add the appropriate intermediate layer to the component, that'll fix it
    logger.info(
        "Adding intermediate layer to %s to support %s %s",
        componentglyph.name,
        parent_layer.parent.name,
        parent_layer.name,
    )
    layer = GSLayer()
    layer.attributes["coordinates"] = location
    layer.layerId = str(uuid.uuid4())
    layer.associatedMasterId = parent_layer.associatedMasterId
    layer.name = parent_layer.name
    # Create a glyph-level variation model for the component glyph,
    # including any intermediate layers
    interpolatable_layers = []
    locations = []
    for l in componentglyph.layers:
        if l._is_brace_layer():
            locations.append(l.attributes["coordinates"])
            interpolatable_layers.append(l)
        if l._is_master_layer:
            locations.append(font.masters[l.associatedMasterId].axes)
            interpolatable_layers.append(l)
    glyph_level_model, _ = variation_model(font, locations)

    # Interpolate new layer width
    all_widths = [l.width for l in interpolatable_layers]
    layer.width = glyph_level_model.interpolateFromMasters(
        normalized_location, all_widths
    )

    # Interpolate layer shapes
    for ix, shape in enumerate(componentglyph.layers[0].shapes):
        all_shapes = [l.shapes[ix] for l in interpolatable_layers]
        if isinstance(shape, GSPath):
            # We are making big assumptions about compatibility here
            layer.shapes.append(
                interpolate_path(all_shapes, glyph_level_model, normalized_location)
            )
        else:
            ensure_component_has_sparse_layer(font, shape, parent_layer)
            layer.shapes.append(
                interpolate_component(
                    all_shapes, glyph_level_model, normalized_location
                )
            )
    componentglyph.layers.append(layer)


def interpolate_path(paths, model, location):
    path = GSPath()
    for master_nodes in zip(*[p.nodes for p in paths]):
        node = GSNode()
        node.type = master_nodes[0].type
        node.smooth = master_nodes[0].smooth
        xs = [n.position.x for n in master_nodes]
        ys = [n.position.y for n in master_nodes]
        node.position.x = model.interpolateFromMasters(location, xs)
        node.position.y = model.interpolateFromMasters(location, ys)
        path.nodes.append(node)
    return path


def interpolate_component(components, model, location):
    component = components[0].clone()
    if all(c.transform == component.transform for c in components):
        return component
    transforms = [c.transform for c in components]
    for element in range(6):
        values = [t[element] for t in transforms]
        component.transform[element] = model.interpolateFromMasters(location, values)
    return component
