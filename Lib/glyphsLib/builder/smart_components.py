"""Convert Glyphs smart components.

Smart components (https://glyphsapp.com/learn/smart-components) are a
feature within Glyphs whereby a component can essentially define its
own private designspace - each master of a component glyph can
define its own axes and masters. When the component is used, instead
of simply scaling or transforming the component, the designer can
*interpolate* the component by specifying the location in the private
designspace.

For example, a font might define a ``_part.serif`` glyph component with
"left width" and "right width" axes, and for each master in the font,
define layers for the ``_part.serif`` at some default left width and
right width, one with an extended left width, and one with an extended
right width, and use the "smart components settings" to assign locations
to these additional layers. (Unlike a full interpolation model, the
locations of smart component layers can only be at the axis extremes.)

We handle smart components by decomposing them and then applying a standard
OpenType interpolation model to adjust the node positions.
"""

from enum import IntEnum
# We're going to use pickle/unpickle to copy the node objects because
# it's considerably faster than copy.deepcopy
import pickle

from fontTools.varLib.models import VariationModel, normalizeValue
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

from glyphsLib.classes import GSLayer

# smartComponentPoleMapping returns 1 for bottom of axis and 2 for top.
class Pole(IntEnum):
    MIN = 1
    MAX = 2

# This normalizes the location of a "master" (additional smart component
# layer). Because these are defined to be at the "poles", this is always
# 0.0, 1.0 or -1.0. But working out which it should be is slightly tricky:
# the axes don't define their own defaults, but the location of the
# default layer of the glyph tells you whether the default value of the
# axis is at the top or the bottom.
def normalized_location(layer, base_layer):
    loc = {}
    for axis_name, current_value in layer.smartComponentPoleMapping.items():
        base_value = base_layer.smartComponentPoleMapping[axis_name]
        if current_value == base_value:
            loc[axis_name] = 0.0
        elif base_value == Pole.MIN and current_value == Pole.MAX:
            loc[axis_name] = 1.0
        elif base_value == Pole.MAX and current_value == Pole.MIN:
            loc[axis_name] = -1.0
        else:
            raise ValueError(
                f"Strange axis mapping for axis {axis_name} in smart layer {base_layer}"
            )
    return loc


def variation_model(glyph, smart_layers):
    master_locations = [normalized_location(l, smart_layers[0]) for l in smart_layers]
    axis_order = [ax.name for ax in glyph.smartComponentAxes]
    return VariationModel(master_locations, axisOrder=axis_order, extrapolate=True)


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
    axes_tuples = {}
    for ax in root.smartComponentAxes:
        if masters[0].smartComponentPoleMapping[ax.name] == Pole.MIN:
            defaultValue = ax.bottomValue
        else:
            defaultValue = ax.topValue
        axes_tuples[ax.name] = (ax.bottomValue, defaultValue, ax.topValue)
    normalized_location = {
        name: normalizeValue(value, axes_tuples[name])
        for name, value in component.smartComponentValues.items()
    }
    new_coords = model.interpolateFromMasters(
        normalized_location, coordinates
    )
    new_layer = GSLayer()
    new_layer._shapes = pickle.loads(pickle.dumps(masters[0]._shapes))
    set_coordinates(new_layer, new_coords)
    if component.transform:
        for p in new_layer.paths:
            p.applyTransform(component.transform)
    new_layer.drawPoints(pen)
