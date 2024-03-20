import pytest
import os
import tempfile
import glyphsLib
from glyphsLib.classes import GSFont, GSFontMaster, GSPath, GSComponent


def test_round_tripping(datadir):
    original_file_path = str(datadir.join("GlyphsUnitTestSans3.glyphs"))
    with tempfile.TemporaryDirectory() as outputdir:
        temp_dir = str(outputdir)
        temp_file_path = os.path.join(temp_dir, "GlyphsUnitTestSans3.glyphs")
        temp_file_path = str(datadir.join("GlyphsUnitTestSans3_temp.glyphs"))
        font = glyphsLib.load(original_file_path)
        font.save(temp_file_path)
        original_file = open(original_file_path)
        original_file_content = original_file.read()
        original_file.close()

        temp_file = open(temp_file_path)
        temp_file_content = temp_file.read()
        temp_file.close()
        assert original_file_content == temp_file_content


def test_metrics():
    font = GSFont()
    master = GSFontMaster()
    font.masters.append(master)
    master.ascender = 400
    assert master.ascender == 400
    assert master.metrics[font.metrics[0].id].position == 400


def test_glyphs3_italic_angle(datadir):
    with open(str(datadir.join("Italic-G3.glyphs"))) as f:
        font = glyphsLib.load(f)
    assert font.masters[0].italicAngle == 11


def test_glyphspackage_load(datadir):
    expected = [
        "A",
        "Adieresis",
        "I",
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
    d1 = glyphsLib.dumps(font1)
    d2 = glyphsLib.dumps(font2)
    assert d1 == d2


''' #alignmentZones are read only
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
'''

''' # this is tested in test_classes
def test_glyphs3_stems(datadir):
    font = glyphsLib.load(str(datadir.join("GlyphsUnitTestSans3.glyphs")))
    master = font.masters[0]

    assert master.verticalStems == [17, 19]
    assert master.horizontalStems == [16, 16, 18]
'''


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

    print(first_derivative_ufos[0].groups)
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
