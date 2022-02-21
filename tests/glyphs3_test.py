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


def test_glyphs3_rtl_kerning(datadir, ufo_module):
    for file in ("RTL_kerning_v2.glyphs", "RTL_kerning_v3.glyphs"):
        with open(str(datadir.join(file))) as f:
            font = glyphsLib.load(f)

        designspace = to_designspace(font, ufo_module=ufo_module)
        ufos = [source.font for source in designspace.sources]
        assert ufos[0].groups["public.kern2.hah-ar.init"] == ["hah-ar.init"]
        assert ufos[0].groups["public.kern2.hah-ar.init.swsh"] == ["hah-ar.init.swsh"]
        assert (
            ufos[0].kerning[("public.kern1.reh-ar", "public.kern2.hah-ar.init.swsh")]
            == -50
        )