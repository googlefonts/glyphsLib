import copy
import os

import glyphsLib

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def test_ufo_instance_properties():
    from glyphsLib.interpolation import apply_instance_data_to_ufo

    file = glyphsLib.GSFont(os.path.join(DATA, "UFOInstancePropertiesTest.glyphs"))
    space = glyphsLib.to_designspace(file, minimal=True)

    for instance, name in zip(space.instances, ["Thin", "Regular", "Black"]):
        source = copy.deepcopy(space.sources[0])
        apply_instance_data_to_ufo(source.font, instance, space)

        actual = source.font.info.openTypeNamePreferredFamilyName
        assert actual == "Typographic Neue"

        actual = source.font.info.openTypeNamePreferredSubfamilyName
        assert actual == f"Typographic {name}"
