import pytest

from glyphsLib.builder import to_ufos
from glyphsLib.builder.names import build_stylemap_names

from ..classes_test import generate_minimal_font


def test_regular():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Regular",
        is_bold=False,
        is_italic=False,
        linked_style=None,
    )
    assert map_family == "NotoSans"
    assert map_style == "regular"


def test_regular_isBold():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Regular",
        is_bold=True,
        is_italic=False,
        linked_style=None,
    )
    assert map_family == "NotoSans Regular"
    assert map_style == "bold"


def test_regular_isItalic():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Regular",
        is_bold=False,
        is_italic=True,
        linked_style=None,
    )
    assert map_family == "NotoSans Regular"
    assert map_style == "italic"


def test_non_regular():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="ExtraBold",
        is_bold=False,
        is_italic=False,
        linked_style=None,
    )
    assert map_family == "NotoSans ExtraBold"
    assert map_style == "regular"


def test_bold_no_style_link():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Bold",
        is_bold=False,  # not style-linked, despite the name
        is_italic=False,
        linked_style=None,
    )
    assert map_family == "NotoSans Bold"
    assert map_style == "regular"


def test_italic_no_style_link():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Italic",
        is_bold=False,
        is_italic=False,  # not style-linked, despite the name
        linked_style=None,
    )
    assert map_family == "NotoSans Italic"
    assert map_style == "regular"


def test_bold_italic_no_style_link():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Bold Italic",
        is_bold=False,  # not style-linked, despite the name
        is_italic=False,  # not style-linked, despite the name
        linked_style=None,
    )
    assert map_family == "NotoSans Bold Italic"
    assert map_style == "regular"


def test_bold():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Bold",
        is_bold=True,
        is_italic=False,
        linked_style=None,
    )
    assert map_family == "NotoSans"
    assert map_style == "bold"


def test_italic():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Italic",
        is_bold=False,
        is_italic=True,
        linked_style=None,
    )
    assert map_family == "NotoSans"
    assert map_style == "italic"


def test_bold_italic():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Bold Italic",
        is_bold=True,
        is_italic=True,
        linked_style=None,
    )
    assert map_family == "NotoSans"
    assert map_style == "bold italic"


def test_incomplete_bold_italic():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Bold",  # will be stripped...
        is_bold=True,
        is_italic=True,
        linked_style=None,
    )
    assert map_family == "NotoSans"
    assert map_style == "bold italic"

    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Italic",  # will be stripped...
        is_bold=True,
        is_italic=True,
        linked_style=None,
    )
    assert map_family == "NotoSans"
    assert map_style == "bold italic"


def test_italicbold_isBoldItalic():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Italic Bold",  # reversed
        is_bold=True,
        is_italic=True,
        linked_style=None,
    )
    assert map_family == "NotoSans"
    assert map_style == "bold italic"


def test_linked_style_regular():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Condensed",
        is_bold=False,
        is_italic=False,
        linked_style="Cd",
    )
    assert map_family == "NotoSans Cd"
    assert map_style == "regular"


def test_linked_style_bold():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Condensed Bold",
        is_bold=True,
        is_italic=False,
        linked_style="Cd",
    )
    assert map_family == "NotoSans Cd"
    assert map_style == "bold"


def test_linked_style_italic():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Condensed Italic",
        is_bold=False,
        is_italic=True,
        linked_style="Cd",
    )
    assert map_family == "NotoSans Cd"
    assert map_style == "italic"


def test_linked_style_bold_italic():
    map_family, map_style = build_stylemap_names(
        family_name="NotoSans",
        style_name="Condensed Bold Italic",
        is_bold=True,
        is_italic=True,
        linked_style="Cd",
    )
    assert map_family == "NotoSans Cd"
    assert map_style == "bold italic"


@pytest.mark.parametrize(
    "master_name, expected_family, expected_style",
    [
        ("Regular", "MyFont", "regular"),
        ("Bold", "MyFont", "bold"),
        ("Thin", "MyFont Thin", "regular"),
        ("Italic", "MyFont", "italic"),
        ("Bold Italic", "MyFont", "bold italic"),
        ("Thin Italic", "MyFont Thin", "italic"),
        ("Oblique", "MyFont", "italic"),
        ("Bold Oblique", "MyFont", "bold italic"),
    ],
)
def test_master_stylemap_names_without_italic_angle(
    master_name, expected_family, expected_style
):
    font = generate_minimal_font()
    font.masters[0].name = master_name
    assert not font.masters[0].italicAngle

    (ufo,) = to_ufos(font)

    assert ufo.info.styleName == master_name
    assert ufo.info.styleMapFamilyName == expected_family
    assert ufo.info.styleMapStyleName == expected_style
