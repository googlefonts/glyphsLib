import glyphsLib

def test_glyphs_font_without_propagated_anchors(datadir):

    font = glyphsLib.GSFont(str(datadir.join("AnchorPropagation.glyphs")))

    # These two layers are supposed to be devoid of anchors in the .glyphs source
    # with Glyphs.app expecting to propagate them automatically upon font generation
    assert len(font.glyphs['lam_alefHamzaabove-ar'].layers[0].anchors) == 0
    assert len(font.glyphs['shadda_fatha-ar'].layers[0].anchors) == 0

def test_ufo_with_propagated_anchors(datadir):

    ufo = glyphsLib.load_to_ufos(datadir.join("AnchorPropagation.glyphs"))[0]

    # In UFO, the same two glyphs (see above) are supposed to show anchors
    assert len(ufo['lam_alefHamzaabove-ar'].anchors) > 0
    assert len(ufo['shadda_fatha-ar'].anchors) > 0

    # Additionally, we’ll check the anchor positions and compare them with Glyphs.app’s 
    # own results (hard coded) from `layer.anchorsTraversingComponents()`

    # In case of `lam_alefHamzaabove-ar` it’s crucial that the `top_2` anchor moved
    # upwards following the `hamza-ar` mark as part of the ligature base glyph

    # lam_alefHamzaabove-ar
    assert 'top_2' in [x.name for x in ufo['lam_alefHamzaabove-ar'].anchors]
    for anchor in ufo['lam_alefHamzaabove-ar'].anchors:
        if anchor.name == 'top_2':
            assert anchor.x == 129
            assert anchor.y == 950

    # shadda_fatha-ar
    assert 'top' in [x.name for x in ufo['shadda_fatha-ar'].anchors]
    for anchor in ufo['shadda_fatha-ar'].anchors:
        if anchor.name == 'top':
            assert anchor.x == 160
            assert anchor.y == 971
