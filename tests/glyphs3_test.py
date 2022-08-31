import glyphsLib
from glyphsLib.classes import GSFont, GSFontMaster


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
