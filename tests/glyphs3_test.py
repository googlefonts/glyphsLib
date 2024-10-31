import glyphsLib
import pytest
from glyphsLib.classes import GSFont, GSFontMaster, GSAlignmentZone, GSPath, GSComponent


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
    expected = [
        "A",
        "Adieresis",
        "a",
        "adieresis",
        "h",
        "m",
        "n",
        "a.sc",
        "dieresis",
        "_part.shoulder",
        "_part.stem",  # Deliberately removed from glyph order file
    ]
    font1 = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphs")))
    font2 = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphspackage")))
    assert [glyph.name for glyph in font2.glyphs] == expected
    assert glyphsLib.dumps(font1) == glyphsLib.dumps(font2)

    font1 = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphs")))
    font2 = GSFont(str(datadir.join("GlyphsUnitTestSans3.glyphspackage")))
    assert [glyph.name for glyph in font2.glyphs] == expected
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


def test_glyphs2_rtl_kerning(datadir, ufo_module):
    file = "RTL_kerning_v2.glyphs"
    with open(str(datadir.join(file)), encoding="utf-8") as f:
        font = glyphsLib.load(f)

    designspace = glyphsLib.to_designspace(font, ufo_module=ufo_module)
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
    designspace = glyphsLib.to_designspace(original_glyphs_font, ufo_module=ufo_module)
    first_derivative_ufos = [source.font for source in designspace.sources]

    assert first_derivative_ufos[0].groups == {
        "public.kern1.A": ["A"],
        "public.kern2.A": ["A"],
        "public.kern1.quotesingle": ["quotesingle"],
        "public.kern2.quotesingle": ["quotesingle"],
        "public.kern1.hah-ar.init": ["hah-ar.init"],
        "public.kern2.hah-ar.init.swsh": ["hah-ar.init.swsh"],
        "public.kern2.left-one-ar": ["one-ar", "one-ar.wide"],
        "public.kern1.reh-ar": ["reh-ar"],
        "public.kern1.leftAlef": ["alef-hb"],
        "public.kern1.leftBet": ["bet-hb"],
        "public.kern2.rightBet": ["bet-hb"],
    }
    assert first_derivative_ufos[0].kerning == {
        ("public.kern1.A", "public.kern2.quotesingle"): -49,
        # the (@quotesingle, @A) pair should not be overwritten by the
        # (@quotesingle, @rightBet), both can co-exist in the combined kerning
        # https://github.com/googlefonts/glyphsLib/issues/1039
        ("public.kern1.quotesingle", "public.kern2.A"): -49,
        ("public.kern1.quotesingle", "public.kern2.rightBet"): -20,
        ("public.kern1.leftBet", "public.kern2.quotesingle"): -30,
        ("public.kern1.leftBet", "public.kern2.rightAlef"): 20,
        ("public.kern1.leftAlef", "public.kern2.rightBet"): -20,
        ("public.kern1.leftAlef", "he-hb"): 4,
        ("public.kern1.reh-ar", "public.kern2.hah-ar.init.swsh"): -50,
        ("he-hb", "public.kern2.rightAlef"): -2,
        ("he-hb", "he-hb"): -21,
    }

    # Round-tripping back to Glyphs
    round_tripped_glyphs_font = glyphsLib.to_glyphs(first_derivative_ufos)

    # Second conversion back to UFO
    designspace = glyphsLib.to_designspace(
        round_tripped_glyphs_font, ufo_module=ufo_module
    )
    second_derivative_ufos = [source.font for source in designspace.sources]

    # Comparing kerning between first and second derivative UFOs:
    # Round-tripped RTL kernining ends up as LTR kerning, but at least it's lossless
    # and produces correct results.
    assert first_derivative_ufos[0].groups == second_derivative_ufos[0].groups
    assert first_derivative_ufos[0].kerning == second_derivative_ufos[0].kerning
    assert first_derivative_ufos[1].groups == second_derivative_ufos[1].groups
    assert first_derivative_ufos[1].kerning == second_derivative_ufos[1].kerning
    # Check that groups within one font are identical after pruning
    assert first_derivative_ufos[0].groups == first_derivative_ufos[1].groups
    assert second_derivative_ufos[0].groups == second_derivative_ufos[1].groups


def test_glyphs3_shape_order(datadir, ufo_module):
    file = "ShapeOrder.glyphs"
    with open(str(datadir.join(file)), encoding="utf-8") as f:
        original_glyphs_font = glyphsLib.load(f)

    designspace = glyphsLib.to_designspace(original_glyphs_font, ufo_module=ufo_module)
    ufo = designspace.sources[0].font
    assert "com.schriftgestaltung.Glyphs.shapeOrder" in ufo["A"].lib
    assert "com.schriftgestaltung.Glyphs.shapeOrder" in ufo["B"].lib
    assert "com.schriftgestaltung.Glyphs.shapeOrder" not in ufo["_comp"].lib

    assert ufo["A"].lib["com.schriftgestaltung.Glyphs.shapeOrder"] == "PC"
    assert ufo["B"].lib["com.schriftgestaltung.Glyphs.shapeOrder"] == "CP"

    # Round trip
    round_trip = glyphsLib.to_glyphs([ufo])
    glyph_a = round_trip.glyphs["A"].layers[0]
    glyph_b = round_trip.glyphs["B"].layers[0]
    assert isinstance(glyph_a.shapes[0], GSPath)
    assert isinstance(glyph_b.shapes[0], GSComponent)
