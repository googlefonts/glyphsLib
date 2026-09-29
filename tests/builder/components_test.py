import logging

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


def test_background_component_decompose_missing(datadir, caplog):
    # A background is never compiled, so a component pointing at a deleted glyph
    # must not fail the conversion. https://github.com/googlefonts/glyphsLib/issues/743
    font = glyphsLib.GSFont(str(datadir.join("Recursion.glyphs")))

    layer = font.glyphs["B"].layers["DB4D7D04-C02D-48DE-811E-03AA03052DD2"].background
    layer.components.append(GSComponent("xxx"))

    with caplog.at_level(logging.WARNING, logger="glyphsLib.builder.components"):
        ds = to_designspace(font, minimal=False)

    assert "skipped 1 component(s) with no glyph in this master: xxx" in caplog.text
    # One warning per layer, not one per component.
    assert caplog.text.count("no glyph in this master") == 1

    # Only the dangling component is dropped, the resolvable one still decomposes.
    background = ds.sources[0].font.layers["Apr 27 20, 17:59.background"]["B"]
    assert not background.components
    assert len(background.contours) == 2


def test_background_component_decompose_missing_nested(datadir):
    # 'A''s background draws 'B', so 'B''s missing component is a nested one: the
    # background must still come out whole, not half drawn.
    font = glyphsLib.GSFont(str(datadir.join("Recursion.glyphs")))

    layer = font.glyphs["B"].layers["23DBA3BE-95F2-4A36-B846-28FED8CD3077"]
    layer.components.append(GSComponent("xxx"))

    ds = to_designspace(font, minimal=False)

    ufo = ds.sources[0].font
    assert ufo.layers["public.background"]["A"].contours == ufo["B"].contours


def test_missing_component_outside_a_background_is_left_alone(datadir):
    # 'space' is drawn by no background, so only the foreground path is exercised:
    # the component is written out as it stands, for the compiler to reject.
    font = glyphsLib.GSFont(str(datadir.join("Recursion.glyphs")))

    layer = font.glyphs["space"].layers["23DBA3BE-95F2-4A36-B846-28FED8CD3077"]
    layer.components.append(GSComponent("xxx"))

    ds = to_designspace(font, minimal=False)

    glyph = ds.sources[0].font["space"]
    assert [c.baseGlyph for c in glyph.components] == ["xxx"]
