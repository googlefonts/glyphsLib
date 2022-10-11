import copy

from fontTools.varLib.models import VariationModel, normalizeValue, supportScalar
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

AXIS_MIN = 1
AXIS_MAX = 2


def normalized_location(layer, base_layer):
    loc = {}
    for axis_name, current_value in layer.smartComponentPoleMapping.items():
        base_value = base_layer.smartComponentPoleMapping[axis_name]
        if current_value == base_value:
            loc[axis_name] = 0.0
        elif base_value == AXIS_MIN and current_value == AXIS_MAX:
            loc[axis_name] = 1.0
        elif base_value == AXIS_MAX and current_value == AXIS_MIN:
            loc[axis_name] = -1.0
        else:
            raise ValueError(
                f"Strange axis mapping for axis {axis_name} in smart layer {base_layer}"
            )
    return loc


def variation_model(glyph, smart_layers):
    if not glyph.smartComponentAxes:
        return None

    master_locations = [normalized_location(l, smart_layers[0]) for l in smart_layers]
    axis_order = [ax.name for ax in glyph.smartComponentAxes]
    return VariationModel(master_locations, axisOrder=axis_order)


def get_coordinates(layer):
    gc = GlyphCoordinates([])
    for path in layer.paths:
        gc.extend(
            GlyphCoordinates([(pt.position.x, pt.position.y) for pt in path.nodes])
        )
    return gc


def set_coordinates(layer, coords):
    counter = 0
    for path in layer.paths:
        for node in path.nodes:
            node.position.x, node.position.y = coords[counter]
            counter += 1


def to_ufo_smart_component(self, layer, component, pen):
    root = component.component
    masters = [l for l in root.layers if l.smartComponentPoleMapping]
    if layer.associatedMasterId:
        # Filter by those smart components which are in the same master
        masters = [
            l for l in masters if l.associatedMasterId == layer.associatedMasterId
        ]
    model = variation_model(root, masters)
    coordinates = [get_coordinates(l) for l in masters]
    delta_coordinates = [c - coordinates[0] for c in coordinates]
    axes_tuples = {}
    for ax in root.smartComponentAxes:
        if masters[0].smartComponentPoleMapping[ax.name] == AXIS_MIN:
            defaultValue = ax.bottomValue
        else:
            defaultValue = ax.topValue
        axes_tuples[ax.name] = (ax.bottomValue, defaultValue, ax.topValue)
    normalized_location = {
        name: normalizeValue(value, axes_tuples[name])
        for name, value in component.smartComponentValues.items()
    }
    interpolated_deltas = model.interpolateFromMasters(
        normalized_location, delta_coordinates
    )
    new_coords = coordinates[0] + interpolated_deltas
    new_layer = copy.deepcopy(masters[0])
    set_coordinates(new_layer, new_coords)
    new_layer.drawPoints(pen)
