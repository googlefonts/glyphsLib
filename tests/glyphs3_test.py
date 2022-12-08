import glyphsLib
import pytest
from glyphsLib.classes import GSFont, GSFontMaster, GSAlignmentZone


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
    zones = [(800, 10), (700, 10), (470, 10), (0, -10), (-200, -10)]
    for i, (pos, size) in enumerate(zones):
        assert master.alignmentZones[i].position == pos
        assert master.alignmentZones[i].size == size

    assert len(master.alignmentZones) == 5

    # alignmentZones can be set as tuples or instances
    master.alignmentZones = [GSAlignmentZone(800, 10), GSAlignmentZone(0, -10)]

    assert master.alignmentZones[-2].position == 800
    assert master.alignmentZones[-2].size == 10

    assert master.alignmentZones[-1].position == 0
    assert master.alignmentZones[-1].size == -10

    assert len(master.alignmentZones) == 2

    # Duplicates should get added only once
    master.alignmentZones = [(0, -10), (0, -10)]
    assert len(master.alignmentZones) == 1

    # Let it be emptyable
    master.alignmentZones = []
    assert len(master.alignmentZones) == 0

    # Non-list values not allowed
    with pytest.raises(TypeError):
        master.alignmentZones = (800, 10)

    with pytest.raises(TypeError):
        master.alignmentZones = 800

    with pytest.raises(TypeError):
        master.alignmentZones = "800"

    # Only tuples and GSAlignmentZone allowed inside
    with pytest.raises(TypeError):
        master.alignmentZones = [False, True]

    with pytest.raises(TypeError):
        master.alignmentZones = [[0, -10], [800, 10]]

    with pytest.raises(TypeError):
        master.alignmentZones = ["", ""]


def test_glyphs3_stems(datadir):
    font = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphs")))
    master = font.masters[0]

    assert master.verticalStems == [17, 19]
    assert master.horizontalStems == [16, 16, 18]
