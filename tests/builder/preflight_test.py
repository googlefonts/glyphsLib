import glyphsLib
from glyphsLib.builder.transformations import resolve_intermediate_components


def test_intermediates_with_components_without_intermediates(datadir):
    font = glyphsLib.GSFont(str(datadir.join("ComponentsWithIntermediates.glyphs")))
    assert len(font.glyphs["A"].layers) != len(font.glyphs["Astroke"].layers)
    resolve_intermediate_components(font)
    assert len(font.glyphs["A"].layers) == len(font.glyphs["Astroke"].layers)
