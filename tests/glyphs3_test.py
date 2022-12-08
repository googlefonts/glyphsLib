import glyphsLib
from glyphsLib.classes import GSFont, GSFontMaster
from glyphsLib import to_designspace


def test_metrics():
    font = GSFont()
    master = GSFontMaster()
    font.masters.append(master)
    master.ascender = 400
    assert master.ascender == 400
    assert master.metrics[0].position == 400


def test_glyphs3_italic_angle(datadir):
    with open(str(datadir.join("Italic-G3.glyphs"))) as f:
        font = glyphsLib.load(f)
    assert font.masters[0].italicAngle == 11


def test_glyphspackage_load(datadir):
    font1 = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphs")))
    font1.DisplayStrings = ""  # glyphspackages, rather sensibly, don't store user state
    font2 = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphspackage")))
    assert glyphsLib.dumps(font1) == glyphsLib.dumps(font2)


def test_glyphs2_rtl_kerning(datadir, ufo_module):
    file = "RTL_kerning_v2.glyphs"
    with open(str(datadir.join(file))) as f:
        font = glyphsLib.load(f)

    designspace = to_designspace(font, ufo_module=ufo_module)
    ufos = [source.font for source in designspace.sources]
    print(file, ufos[0].groups)
    assert ufos[0].groups["public.kern2.hah-ar.init"] == ["hah-ar.init"]
    assert ufos[0].groups["public.kern2.hah-ar.init.swsh"] == ["hah-ar.init.swsh"]
    assert (
        ufos[0].kerning[("public.kern1.reh-ar", "public.kern2.hah-ar.init.swsh")] == -50
    )

    assert ufos[0].kerning[("he-hb", "he-hb")] == -21


def test_glyphs3_rtl_kerning(datadir, ufo_module):
    file = "RTL_kerning_v3.glyphs"
    with open(str(datadir.join(file))) as f:
        font = glyphsLib.load(f)

    designspace = to_designspace(font, ufo_module=ufo_module)
    ufos = [source.font for source in designspace.sources]
    print(file, ufos[0].groups)
    assert ufos[0].groups["public.kern1.reh-ar.RTL"] == ["reh-ar"]
    assert ufos[0].groups["public.kern2.hah-ar.init.RTL"] == ["hah-ar.init"]
    assert ufos[0].groups["public.kern2.hah-ar.init.swsh.RTL"] == ["hah-ar.init.swsh"]
    assert (
        ufos[0].kerning[
            ("public.kern1.reh-ar.RTL", "public.kern2.hah-ar.init.swsh.RTL")
        ]
        == -50
    )

    assert ufos[0].kerning[("he-hb", "he-hb")] == -21
