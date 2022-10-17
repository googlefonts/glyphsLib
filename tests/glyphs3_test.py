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


def test_glyphs3_alignment_zones(datadir):
    font = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphs")))
    master = font.masters[0]

    assert master.alignmentZones != []

    # As per classes_tests::GSAlignmentZoneFromFileTest
    for i, zone in enumerate([(800, 10), (700, 10), (470, 10), (0, -10), (-200, -10)]):
        pos, size = zone
        assert master.alignmentZones[i].position == pos
        assert master.alignmentZones[i].size == size


def test_glyphs3_stems(datadir):
    font = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphs")))
    master = font.masters[0]

    assert master.verticalStems == [17, 19]
    assert master.horizontalStems == [16, 16, 18]
