"""Tests for the Glyphs 3 component transform fields, in particular `slant`.

See https://github.com/googlefonts/glyphsLib/issues/1047. Provenance of the
expected values, since they differ: SLANTED_COMPONENT is Georg Seifert's value
from the issue thread. SLANTED_ROTATED_COMPONENT was derived from the fixture's
fields and then read back out of Glyphs 3.4.1, which reproduces it exactly. The
decomposition expectations in TestDecomposition.test_matches_glyphs_app and the
background image matrix also come from Glyphs 3.4.1 directly.
"""

import math
import random
from unittest.mock import patch

import pytest
from fontTools.pens.recordingPen import RecordingPen

import glyphsLib
from glyphsLib import to_glyphs, to_ufos
from glyphsLib.classes import (
    GSBackgroundImage,
    GSComponent,
    GSFont,
    GSFontMaster,
    GSGlyph,
    GSLayer,
    composeGlyphs3Transform,
    decomposeGlyphs3Transform,
)
from glyphsLib.types import Point, Transform
from glyphsLib.writer import dumps

# component "B" of glyph "bitcoin": pos=(5,21) scale=(1,0.94) slant=(-0.7,0)
SLANTED_COMPONENT = (1, 0, -0.011484837902484654, 0.94, 5, 21)
# component "A" of glyph "B" in GlyphsFileFormatv3.glyphs, which also has a
# rotation and so pins the order of the skew and the rotation
SLANTED_ROTATED_COMPONENT = (
    0.8,
    0.273616114660535,
    -0.14106158456677195,
    0.7517540966287268,
    0.0,
    0.0,
)


def component_transform(layer):
    pen = RecordingPen()
    layer.draw(pen)
    (component,) = [args for operator, args in pen.value if operator == "addComponent"]
    return tuple(component[1])


def assert_close(actual, expected, tolerance=1e-12):
    assert len(actual) == len(expected)
    for got, want in zip(actual, expected):
        assert abs(got - want) <= tolerance, (tuple(actual), tuple(expected))


class TestParsing:
    def test_slant_is_applied(self, datadir):
        font = glyphsLib.GSFont(str(datadir.join("ComponentSlant.glyphs")))
        layer = font.glyphs["bitcoin"].layers[0]
        assert_close(component_transform(layer), SLANTED_COMPONENT)

    def test_slant_with_rotation_is_applied(self, datadir):
        font = glyphsLib.GSFont(str(datadir.join("GlyphsFileFormatv3.glyphs")))
        layer = font.glyphs["B"].layers["m01"]
        assert_close(component_transform(layer), SLANTED_ROTATED_COMPONENT)

    def test_fields_are_kept_verbatim(self, datadir):
        font = glyphsLib.GSFont(str(datadir.join("GlyphsFileFormatv3.glyphs")))
        component = font.glyphs["B"].layers["m01"].components[0]
        assert component.rotation == 20
        assert component.scale == (0.8, 0.8)
        assert component.slant == (10, 0)
        assert component.position == Point(0, 0)

    def test_field_order_does_not_matter(self):
        """Fields used to be applied in the order the file listed them."""
        forwards = GSComponent("A")
        forwards.rotation = 20
        forwards.scale = (0.8, 0.8)
        forwards.slant = (10, 0)

        backwards = GSComponent("A")
        backwards.slant = (10, 0)
        backwards.scale = (0.8, 0.8)
        backwards.rotation = 20

        assert_close(forwards.transform, backwards.transform)
        assert_close(forwards.transform, SLANTED_ROTATED_COMPONENT)

    def test_parser_defers_composition_until_matrix_is_read(self, datadir):
        with patch(
            "glyphsLib.classes.composeGlyphs3Transform",
            wraps=composeGlyphs3Transform,
        ) as compose:
            font = glyphsLib.GSFont(str(datadir.join("ComponentSlant.glyphs")))
            assert compose.call_count == 0

            component = font.glyphs["bitcoin"].layers[0].components[0]
            transform = component._transformMatrix()
            assert compose.call_count == 1
            assert component._transformMatrix() is transform
            assert compose.call_count == 1

        assert_close(transform, SLANTED_COMPONENT)


class TestWriting:
    @pytest.mark.parametrize(
        "source, block",
        [
            (
                "ComponentSlant.glyphs",
                "{\npos = (5,21);\nref = B;\nscale = (1,0.94);\nslant = (-0.7,0);\n}",
            ),
            (
                "GlyphsFileFormatv3.glyphs",
                "{\nangle = 20;\nlocked = 1;\nref = A;\nscale = (0.8,0.8);\n"
                "slant = (10,0);\n}",
            ),
        ],
    )
    def test_component_block_survives_round_trip(self, datadir, source, block):
        """The fields come back verbatim, no decompose-recompose drift."""
        path = str(datadir.join(source))
        with open(path, encoding="utf-8") as file:
            assert block in file.read()
        assert block in dumps(glyphsLib.GSFont(path))

    @pytest.mark.parametrize("slant", [(10, 0), (10, 8), (0, 8), (-0.7, 0)])
    def test_slant_is_written(self, slant):
        component = GSComponent("A")
        component.slant = slant
        font = _font_with_component(component)

        assert f"slant = ({_number(slant[0])},{_number(slant[1])});" in dumps(font)

    def test_default_slant_is_omitted(self):
        component = GSComponent("A")
        component.slant = (0, 0)
        assert "slant" not in dumps(_font_with_component(component))

    def test_format_2_writes_the_composed_matrix(self):
        """Format 2 has no slant field, so the shear goes into the matrix."""
        component = GSComponent("A")
        component.slant = (10, 0)
        font = _font_with_component(component, format_version=2)

        assert 'transform = "{1, 0, 0.17633, 1, 0, 0}"' in dumps(font)

    def test_format_2_composes_every_field_together(self):
        """All four fields set, then written to the format with no fields."""
        component = GSComponent("A")
        component.position = Point(45, -12)
        component.scale = (0.8, 0.8)
        component.rotation = 20
        component.slant = (10, 0)
        font = _font_with_component(component, format_version=2)

        assert 'transform = "{0.8, 0.27362, -0.14106, 0.75175, 45, -12}"' in dumps(font)
        # and the same matrix a format 3 writer would keep in fields
        assert_close(component.transform[:4], SLANTED_ROTATED_COMPONENT[:4])

    def test_format_2_round_trips_a_field_built_component(self):
        """Format 2 out, format 2 back in: same matrix, now matrix-born."""
        component = GSComponent("A")
        component.scale = (0.8, 0.8)
        component.rotation = 20
        component.slant = (10, 8)
        expected = tuple(component.transform)

        font = _font_with_component(component, format_version=2)
        reloaded = glyphsLib.loads(dumps(font))
        back = reloaded.glyphs["B"].layers[0].components[0]

        # five decimals is what the format 2 matrix is written with
        assert_close(back.transform, expected, 1e-5)
        assert back._transform is not None


class TestDecomposition:
    """Only matrix-born components decompose, i.e. format 2 and UFO sources."""

    @pytest.mark.parametrize(
        "transform, expected",
        [
            ((1, 0, 0, 1, 0, 0), ((0, 0), (1, 1), 0, (0, 0))),
            ((1, 0, 0, 1, 30, -12), ((30, -12), (1, 1), 0, (0, 0))),
            ((2, 0, 0, 3, 0, 0), ((0, 0), (2, 3), 0, (0, 0))),
            # a plain flip should not come out as a 180 degree rotation
            ((-1, 0, 0, 1, 0, 0), ((0, 0), (-1, 1), 0, (0, 0))),
            ((1, 0, 0, -1, 0, 0), ((0, 0), (1, -1), 0, (0, 0))),
            # a real 180 degree rotation, however, should stay one
            ((-1, 0, 0, -1, 0, 0), ((0, 0), (1, 1), 180, (0, 0))),
            (SLANTED_COMPONENT, ((5, 21), (1, 0.94), 0, (-0.7, 0))),
            (SLANTED_ROTATED_COMPONENT, ((0, 0), (0.8, 0.8), 20, (10, 0))),
            # steeper than atan(1/2), so it has no slantY=0 solution at all
            ((1, 1, 0, 1, 0, 0), ((0, 0), (1, 1), 0, (0, 45))),
        ],
    )
    def test_known_matrices(self, transform, expected):
        position, scale, rotation, slant = decomposeGlyphs3Transform(
            Transform(*transform)
        )
        assert_close(position, expected[0], 1e-9)
        assert_close(scale, expected[1], 1e-9)
        assert abs(rotation - expected[2]) <= 1e-9
        assert_close(slant, expected[3], 1e-9)

    @pytest.mark.parametrize(
        "matrix, scale, rotation, slant",
        [
            # Read off Glyphs 3.4.1: each matrix assigned to a component's
            # transform, then its own scale/rotation/slant reported back.
            ((-1, 0, 0, 1, 0, 0), (-1, 1), 0, (0, 0)),
            ((1, 0, 0, -1, 0, 0), (1, -1), 0, (0, 0)),
            ((-1, 0, 0, -1, 0, 0), (1, 1), 180, (0, 0)),
            ((1, 0, 0.5, 1, 0, 0), (1, 1), 0, (26.565051177, 0)),
            ((1, 1, 0, 1, 0, 0), (1, 1), 0, (0, 45)),
            ((0.866025403784, 0.5, -0.5, 0.866025403784, 0, 0), (1, 1), 30, (0, 0)),
        ],
    )
    def test_matches_glyphs_app(self, matrix, scale, rotation, slant):
        _, gotScale, gotRotation, gotSlant = decomposeGlyphs3Transform(
            Transform(*matrix)
        )
        assert_close(gotScale, scale, 1e-9)
        assert abs(gotRotation - rotation) <= 1e-9
        assert_close(gotSlant, slant, 1e-9)

    @pytest.mark.parametrize(
        "matrix",
        [
            (1, 2, 2, 4, 0, 0),  # collinear columns
            (1, 0, 0, 0, 0, 0),  # collapsed to a line
            (0, 0, 0, 0, 5, 5),  # collapsed to a point
        ],
    )
    def test_singular_matrix_is_rejected(self, matrix):
        assert decomposeGlyphs3Transform(Transform(*matrix)) is None

    @pytest.mark.parametrize(
        "matrix",
        [(1, 2, 2, 4, 0, 0), (1, 0, 0, 0, 0, 0), (0, 0, 0, 0, 5, 5)],
    )
    def test_singular_matrix_still_reads_and_writes(self, matrix):
        """Degenerate shapes exist in the wild; they must not crash the writer."""
        component = GSComponent("A", transform=Transform(*matrix))

        assert component.slant == (0.0, 0.0)
        assert len(component.scale) == 2
        assert isinstance(component.rotation, float)
        assert component.position == Point(matrix[4], matrix[5])
        dumps(_font_with_component(component))

    def test_random_matrices_round_trip(self):
        rng = random.Random(1047)
        checked = 0
        while checked < 500:
            matrix = [rng.uniform(-3, 3) for _ in range(4)]
            if abs(matrix[0] * matrix[3] - matrix[1] * matrix[2]) < 1e-3:
                continue
            checked += 1
            transform = Transform(
                *matrix, rng.uniform(-500, 500), rng.uniform(-500, 500)
            )
            fields = decomposeGlyphs3Transform(transform)
            assert fields is not None, tuple(transform)
            assert_close(composeGlyphs3Transform(*fields), transform, 1e-9)


class TestModes:
    def test_assigning_transform_switches_to_the_matrix(self):
        component = GSComponent("A")
        component.slant = (10, 0)
        component.transform = Transform(2, 0, 0, 2, 5, 5)

        assert component.slant == (0, 0)
        assert component.scale == (2, 2)
        assert component.position == Point(5, 5)

    def test_public_transform_is_a_tuple_in_both_modes(self):
        field_born = GSComponent("A")
        field_born.slant = (10, 0)
        matrix_born = GSComponent("A")
        matrix_born.transform = Transform(2, 0, 0, 3, 5, 6)

        assert type(field_born.transform) is tuple
        assert type(matrix_born.transform) is tuple
        with pytest.raises(TypeError):
            field_born.transform[0] = -1.0
        with pytest.raises(TypeError):
            matrix_born.transform[0] = -1.0

    def test_assigning_a_transform_copies_its_value(self):
        matrix = Transform(2, 0, 0, 3, 5, 6)
        component = GSComponent("A")
        component.transform = matrix

        matrix[0] = -1

        assert component.transform == (2, 0, 0, 3, 5, 6)

    def test_assigning_field_born_transform_does_not_share_storage(self):
        source = GSComponent("A")
        source.slant = (10, 0)
        original = source.transform
        target = GSComponent("B")

        target.transform = source.transform
        target.position = Point(5, 6)
        target.transform = (2, *target.transform[1:])

        assert target.transform == (2, *original[1:4], 5, 6)
        assert source.transform == original

    @pytest.mark.parametrize("method_name", ["draw", "drawPoints"])
    @pytest.mark.parametrize("matrix_born", [False, True])
    def test_drawing_does_not_expose_internal_matrix(self, method_name, matrix_born):
        component = GSComponent("A")
        if matrix_born:
            component.transform = Transform(2, 0, 0, 3, 5, 6)
        else:
            component.slant = (10, 0)
        original = component.transform
        pen = RecordingPen()

        getattr(component, method_name)(pen)

        recorded = pen.value[0][1][1]
        assert type(recorded) is tuple
        with pytest.raises(TypeError):
            recorded[0] = -1
        assert component.transform == original

    def test_assigning_a_field_decomposes_the_matrix(self):
        component = GSComponent("A", transform=Transform(1, 1, 0, 1, 0, 0))
        component.scale = (2, 2)

        # the shear was recovered, not silently dropped
        assert_close(component.slant, (0, 45), 1e-9)
        assert_close(component.transform, (2, 2, 0, 2, 0, 0), 1e-9)

    def test_position_does_not_disturb_a_matrix(self):
        """Translation is independent of the linear part, so it stays exact."""
        component = GSComponent("A", transform=Transform(0.1, 0.2, 0.3, 0.4, 0, 0))
        component.position = Point(7, 9)

        assert tuple(component.transform) == (0.1, 0.2, 0.3, 0.4, 7, 9)

    def test_field_born_position_has_value_semantics(self):
        component = GSComponent("A", offset=(5, 6))
        position = component.position
        position.x = 100

        assert component.position == Point(5, 6)

    def test_field_born_matrix_cache_tracks_field_setters(self):
        component = GSComponent("A")
        identity = component._transformMatrix()
        assert component._transformMatrix() is identity

        component.position = Point(5, 21)
        positioned = component._transformMatrix()
        assert positioned is component._transformMatrix()
        assert positioned is not identity
        assert tuple(positioned) == (1, 0, 0, 1, 5, 21)

        component.scale = (1, 0.94)
        component.slant = (-0.7, 0)
        assert_close(component._transformMatrix(), SLANTED_COMPONENT)

    def test_constructor_arguments_stay_in_field_mode(self):
        component = GSComponent("A", offset=(5, 6), scale=(2, 3))

        assert component.position == Point(5, 6)
        assert component.scale == (2, 3)
        assert component._transform is None

    def test_whole_numbers_stay_whole(self):
        """Floats here propagate all the way into UFO anchor coordinates."""
        component = GSComponent("A")
        component.position = Point(613, 0)

        assert tuple(component.transform) == (1, 0, 0, 1, 613, 0)
        assert all(isinstance(v, int) for v in component.transform)

    def test_single_slant_value_is_horizontal(self):
        component = GSComponent("A")
        component.slant = 10
        assert component.slant == (10, 0)

    def test_clone_keeps_the_fields(self):
        component = GSComponent("A")
        component.slant = (10, 8)
        component.rotation = 20
        clone = component.clone()

        assert clone.slant == (10, 8)
        assert clone.rotation == 20
        assert_close(clone.transform, component.transform)


class TestUFORoundTrip:
    def test_shear_reaches_the_ufo(self, datadir, ufo_module):
        font = glyphsLib.GSFont(str(datadir.join("ComponentSlant.glyphs")))
        source_component = font.glyphs["bitcoin"].layers[0].components[0]
        internal_matrix = source_component._transformMatrix()
        (ufo,) = to_ufos(font, ufo_module=ufo_module)
        (component,) = ufo["bitcoin"].components

        assert_close(component.transformation, SLANTED_COMPONENT)
        assert component.transformation is not internal_matrix

    def test_shear_comes_back_from_the_ufo(self, datadir, ufo_module):
        font = glyphsLib.GSFont(str(datadir.join("ComponentSlant.glyphs")))
        ufos = to_ufos(font, ufo_module=ufo_module)
        component = to_glyphs(ufos).glyphs["bitcoin"].layers[0].components[0]

        assert_close(component.position, (5, 21), 1e-9)
        assert_close(component.scale, (1, 0.94), 1e-9)
        assert_close(component.slant, (-0.7, 0), 1e-9)
        assert abs(component.rotation) <= 1e-9

    @pytest.mark.parametrize(
        "transformation, expected",
        [
            # a plain flip, which Glyphs 2 sources are full of
            ((-1, 0, 0, 1, 0, 0), "scale = (-1,1);"),
            # a vertical shear too steep for a slantY=0 decomposition
            ((1, 1, 0, 1, 0, 0), "slant = (0,45);"),
        ],
    )
    def test_ufo_matrix_is_decomposed_on_write(
        self, transformation, expected, ufo_module
    ):
        ufo = ufo_module.Font()
        ufo.info.unitsPerEm = 1000
        ufo.newGlyph("A")
        ufo.newGlyph("B").getPen().addComponent("A", transformation)

        font = to_glyphs([ufo])
        font.format_version = 3
        written = dumps(font)

        assert expected in written
        component = font.glyphs["B"].layers[0].components[0]
        assert_close(component.transform, transformation, 1e-9)


class TestBackgroundImage:
    """Background images carry the same transform fields as components."""

    def test_public_transform_is_a_tuple_in_both_modes(self):
        field_born = GSBackgroundImage("A.jpg")
        field_born.slant = (10, 0)
        matrix_born = GSBackgroundImage("A.jpg")
        matrix_born.transform = Transform(2, 0, 0, 3, 5, 6)

        assert type(field_born.transform) is tuple
        assert type(matrix_born.transform) is tuple
        with pytest.raises(TypeError):
            field_born.transform[0] = -1.0
        with pytest.raises(TypeError):
            matrix_born.transform[0] = -1.0

    def test_v3_fields_survive_round_trip(self, datadir):
        # the imagePath line in between comes back quoted, hence the two halves
        head = "backgroundImage = {\nangle = 3;\ncrop = (41.425,42.805,503.416,507.56);"
        tail = "pos = (61,90);\nscale = (0.529,0.8);\n}"
        path = str(datadir.join("GlyphsFileFormatv3.glyphs"))
        with open(path, encoding="utf-8") as file:
            source = file.read()
        assert head in source and tail in source

        written = dumps(glyphsLib.GSFont(path))
        assert head in written and tail in written

    def test_format_2_round_trips_the_composed_matrix(self):
        image = GSBackgroundImage("A.jpg")
        image.position = Point(45, -12)
        image.scale = (0.8, 0.8)
        image.rotation = 20
        image.slant = (10, 0)
        expected = image.transform
        font = _font_with_component(GSComponent("A"), format_version=2)
        font.glyphs["B"].layers[0].backgroundImage = image

        written = dumps(font)
        assert 'transform = "{0.8, 0.27362, -0.14106, 0.75175, 45, -12}"' in written
        back = glyphsLib.loads(written).glyphs["B"].layers[0].backgroundImage
        assert_close(back.transform, expected, 1e-5)
        assert back._transform is not None

    def test_slant_is_written(self):
        """Images take a slant key like components: Glyphs 3.4.1 reads, applies
        and rewrites one (probed with a background image at slant=(20,0))."""
        image = GSBackgroundImage("Checker.png")
        image.rotation = 3
        image.position = Point(100, 100)
        image.scale = (2, 2)
        image.slant = (20, 0)
        font = _font_with_component(GSComponent("A"))
        font.glyphs["B"].layers[0].backgroundImage = image

        written = dumps(font)
        assert "slant = (20,0);" in written
        # The linear part Glyphs 3.4.1 reports for exactly these fields. Its
        # translation reads back as 100.00000000000001 rather than 100 -- the
        # app runs the offset through its matrix pipeline where we pass it
        # straight through -- so that part is compared separately.
        assert_close(
            image.transform[:4],
            (
                2.0353565300177276,
                0.10467191248588766,
                0.622270938933654,
                1.9972590695091477,
            ),
            1e-16,
        )
        assert tuple(image.transform)[4:] == (100, 100)

    def test_assigning_transform_updates_the_fields(self):
        """These used to keep reporting scale=(1,1), rotation=0 forever."""
        image = GSBackgroundImage("A.jpg")
        image.transform = Transform(2, 0, 0, 3, 10, 20)

        assert image.scale == (2, 3)
        assert image.rotation == 0
        assert image.position == Point(10, 20)

    def test_format_2_matrix_reaches_format_3_fields(self, datadir):
        """The linear part of a format 2 matrix used to be lost on the way."""
        font = glyphsLib.GSFont(str(datadir.join("GlyphsUnitTestSans.glyphs")))
        image = font.glyphs["A"].layers[0].backgroundImage
        image.transform = Transform(0.5, 0, 0, 0.5, 3, 4)
        font.format_version = 3

        written = dumps(font)
        assert "scale = (0.5,0.5);" in written
        assert "pos = (3,4);" in written

    def test_composition_matches_components(self):
        image = GSBackgroundImage("A.jpg")
        image.scale = (0.8, 0.8)
        image.rotation = 20
        image.slant = (10, 0)

        assert_close(image.transform, SLANTED_ROTATED_COMPONENT)


def _number(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _font_with_component(component, format_version=3):
    font = GSFont()
    font.format_version = format_version
    font.upm = 1000
    master = GSFontMaster()
    master.id = "m01"
    font.masters.append(master)
    for name in ("A", "B"):
        glyph = GSGlyph()
        glyph.name = name
        layer = GSLayer()
        layer.layerId = master.id
        layer.associatedMasterId = master.id
        glyph.layers.append(layer)
        font.glyphs.append(glyph)
    font.glyphs["B"].layers[0].components.append(component)
    return font


def test_composition_order_matches_glyphs_app():
    """The order is translate * skew * rotate * scale, verified against the app."""
    assert_close(
        composeGlyphs3Transform((5, 21), (1, 0.94), 0, (-0.7, 0)), SLANTED_COMPONENT
    )
    assert_close(
        composeGlyphs3Transform((0, 0), (0.8, 0.8), 20, (10, 0)),
        SLANTED_ROTATED_COMPONENT,
    )
    # The first case's non-uniform scale pins the skew/scale order: applying
    # the skew before the scale would omit the 0.94 factor.
    wrong_skew_scale_order = math.tan(math.radians(-0.7))
    assert abs(SLANTED_COMPONENT[2] - wrong_skew_scale_order) > 1e-6
