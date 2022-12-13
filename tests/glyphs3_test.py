import glyphsLib
from glyphsLib.classes import GSFont, GSFontMaster
from glyphsLib import to_designspace, to_glyphs


def test_metrics():
    font = GSFont()
    master = GSFontMaster()
    font.masters.append(master)
    master.ascender = 400
    assert master.ascender == 400
    assert master.metrics[0].position == 400


def test_glyphs3_italic_angle(datadir):
    with open(str(datadir.join("Italic-G3.glyphs")), encoding="utf-8") as f:
        font = glyphsLib.load(f)
    assert font.masters[0].italicAngle == 11


def test_glyphspackage_load(datadir):
    font1 = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphs")))
    font1.DisplayStrings = ""  # glyphspackages, rather sensibly, don't store user state
    font2 = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphspackage")))
    assert glyphsLib.dumps(font1) == glyphsLib.dumps(font2)


def test_glyphs2_rtl_kerning(datadir, ufo_module):
    file = "RTL_kerning_v2.glyphs"
    with open(str(datadir.join(file)), encoding="utf-8") as f:
        font = glyphsLib.load(f)

    designspace = to_designspace(font, ufo_module=ufo_module)
    ufos = [source.font for source in designspace.sources]
    print(file, ufos[0].groups)
    assert ufos[0].groups["public.kern1.reh-ar"] == ["reh-ar"]
    assert ufos[0].groups["public.kern2.hah-ar.init.swsh"] == ["hah-ar.init.swsh"]
    assert (
        ufos[0].kerning[("public.kern1.reh-ar", "public.kern2.hah-ar.init.swsh")] == -50
    )

    assert ufos[0].kerning[("he-hb", "he-hb")] == -21


def test_glyphs3_rtl_kerning(datadir, ufo_module):
    file = "RTL_kerning_v3.glyphs"
    with open(str(datadir.join(file)), encoding="utf-8") as f:
        original_glyphs_font = glyphsLib.load(f)

    # First conversion to UFO
    designspace = to_designspace(original_glyphs_font, ufo_module=ufo_module)
    first_derivative_ufos = [source.font for source in designspace.sources]

    assert first_derivative_ufos[0].groups["public.kern1.reh-ar"] == ["reh-ar"]
    assert first_derivative_ufos[0].groups["public.kern2.hah-ar.init.swsh"] == [
        "hah-ar.init.swsh"
    ]
    assert (
        first_derivative_ufos[0].kerning[
            ("public.kern1.reh-ar", "public.kern2.hah-ar.init.swsh")
        ]
        == -50
    )
    assert first_derivative_ufos[0].kerning[("he-hb", "he-hb")] == -21

    # Round-tripping back to Glyphs
    round_tripped_glyphs_font = to_glyphs(first_derivative_ufos)

    # Second conversion back to UFO
    designspace = to_designspace(round_tripped_glyphs_font, ufo_module=ufo_module)
    second_derivative_ufos = [source.font for source in designspace.sources]

    # Comparing kerning between first and second derivative UFOs:
    # Round-tripped RTL kernining ends up as LTR kerning, but at least it's lossless
    # and produces correct results.
    assert first_derivative_ufos[0].groups == second_derivative_ufos[0].groups
    assert first_derivative_ufos[0].kerning == second_derivative_ufos[0].kerning
    assert first_derivative_ufos[1].groups == second_derivative_ufos[1].groups
    assert first_derivative_ufos[1].kerning == second_derivative_ufos[1].kerning
