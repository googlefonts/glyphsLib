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

from fontTools.varLib.models import VariationModel, normalizeValue, VariationModelError
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


def variation_model(glyph, smart_layers, layer):
    master_locations = [normalized_location(l, smart_layers[0]) for l in smart_layers]
    axis_order = [ax.name for ax in glyph.smartComponentAxes]
    try:
        model = VariationModel(master_locations, axisOrder=axis_order, extrapolate=True)
    except VariationModelError as e:
        locations = "Locations were:\n"
        for smart_layer, master_location in zip(smart_layers, master_locations):
            locations += f"  {smart_layer.name} = {master_location}\n"
        raise ValueError(
            "Could not generate smart component model for %s used in %s.\n%s"
            % (glyph.name, layer, locations)
        ) from e
    return model


# Two slightly horrible functions for turning a GSLayer into a
# GlyphCoordinates object and back again.
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
    # Find the GSGlyph that is being used as a component by this GSComponent
    root = component.component

    masters = [l for l in root.layers if l.smartComponentPoleMapping]
    if layer.associatedMasterId:
        # Each master in the font can have its own set of smart component
        # "master layers", so we need to filter by those smart components
        # which are in the same font master as the current one
        masters = [
            l for l in masters if l.associatedMasterId == layer.associatedMasterId
        ]
    if not masters:
        raise ValueError(
            "Could not find any masters for the smart component %s used in %s"
            % (root.name, layer.name)
        )

    if len(masters) == 1:
        # Treat this as a dumb component.
        pen.addComponent(component.name, component.transform)
        return

    model = variation_model(root, masters, layer)

    # Determine the normalized location of the interpolant within the
    # mini-designspace, remembering that we have to work out where the
    # default value is by looking at the first "master"
    axes_tuples = {}
    for ax in root.smartComponentAxes:
        if masters[0].smartComponentPoleMapping[ax.name] == Pole.MIN:
            defaultValue = ax.bottomValue
        else:
            defaultValue = ax.topValue
        axes_tuples[ax.name] = (ax.bottomValue, defaultValue, ax.topValue)
    normalized_location = {
        name: normalizeValue(value, axes_tuples[name], extrapolate=True)
        for name, value in component.smartComponentValues.items()
    }
    coordinates = [get_coordinates(l) for l in masters]
    try:
        new_coords = model.interpolateFromMasters(normalized_location, coordinates)
    except Exception as e:
        raise ValueError(
            "Could not interpolate smart component %s used in %s" % (root.name, layer)
        ) from e

    # Decompose by creating a new layer, copying its shapes and applying
    # the new coordinates
    new_layer = GSLayer()
    new_layer._shapes = [shape.clone() for shape in masters[0]._shapes]
    set_coordinates(new_layer, new_coords)

    # Don't forget that the GSComponent might also be transformed, so
    # we need to apply that transformation to the new layer as well
    if component.transform:
        # We must reverse path direction for flipped components
        # https://github.com/googlefonts/glyphsLib/issues/882
        should_reverse = component.transform.determinant() < 0
        for p in new_layer.paths:
            p.applyTransform(component.transform)
            if should_reverse:
                p.reverse()

    # And we are done
    new_layer.drawPoints(pen)
