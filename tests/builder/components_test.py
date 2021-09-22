import pytest
from fontTools.pens.basePen import MissingComponentError

import glyphsLib
from glyphsLib import to_designspace
from glyphsLib.classes import GSComponent


def test_background_component_decompose(datadir):
    font = glyphsLib.GSFont(str(datadir.join("Recursion.glyphs")))
    ds = to_designspace(font, minimal=False)

    for source in ds.sources:
        for layer in source.font.layers:
            for glyph in layer:
                if layer.name == "Apr 27 20, 17:59" and glyph.name == "B":
                    continue
                assert not glyph.components

    ufo_rg = ds.sources[0].font
    assert ufo_rg.layers["public.background"]["A"].contours == ufo_rg["B"].contours
    assert (
        ufo_rg.layers["Apr 27 20, 17:57.background"]["A"].contours
        == ufo_rg["B"].contours
    )
    assert ufo_rg.layers["public.background"]["B"].contours == ufo_rg["A"].contours
    assert len(ufo_rg.layers["Apr 27 20, 17:59.background"]["B"].contours) == 2

    assert ufo_rg.layers["Apr 27 20, 17:59"]["B"].components

    ufo_bd = ds.sources[1].font
    assert ufo_bd.layers["public.background"]["A"].contours == ufo_bd["B"].contours
    assert (
        ufo_bd.layers["Apr 27 20, 17:57.background"]["A"].contours
        == ufo_bd["B"].contours
    )
    assert ufo_bd.layers["public.background"]["B"].contours == ufo_bd["A"].contours
    assert (
        ufo_bd.layers["Apr 27 20, 17:59.background"]["B"].contours
        == ufo_bd["A"].contours
    )


def test_background_component_decompose_missing(datadir):
    font = glyphsLib.GSFont(str(datadir.join("Recursion.glyphs")))

    layer = font.glyphs["B"].layers["DB4D7D04-C02D-48DE-811E-03AA03052DD2"].background
    layer.components.append(GSComponent("xxx"))

    with pytest.raises(MissingComponentError):
        to_designspace(font, minimal=False)
