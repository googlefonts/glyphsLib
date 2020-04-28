import glyphsLib.classes as classes


def test_pen_roundtrip(datadir, ufo_module):
    font = classes.GSFont(str(datadir.join("GlyphsUnitTestSans.glyphs")))
    font_temp = ufo_module.Font()
    glyph_temp = font_temp.newGlyph("test")

    for glyph in font.glyphs:
        for layer in glyph.layers:
            glyph_temp.clear()
            ufo_pen = glyph_temp.getPen()
            layer.draw(ufo_pen)

            layer_temp = classes.GSLayer()
            glyphs_pen = layer_temp.getPen()
            glyph_temp.draw(glyphs_pen)

            assert len(layer.paths) == len(layer_temp.paths)
            for path_orig, path_temp in zip(layer.paths, layer_temp.paths):
                assert len(path_orig.nodes) == len(path_temp.nodes)
                assert path_orig.closed == path_temp.closed
                for node_orig, node_temp in zip(path_orig.nodes, path_temp.nodes):
                    assert node_orig.position.x == node_temp.position.x
                    assert node_orig.position.y == node_temp.position.y
                    assert node_orig.smooth == node_temp.smooth
                    assert node_orig.type == node_temp.type

            assert len(layer.components) == len(layer_temp.components)
            for comp_orig, comp_temp in zip(layer.components, layer_temp.components):
                assert comp_orig.name == comp_temp.name
                assert comp_orig.transform == comp_temp.transform
