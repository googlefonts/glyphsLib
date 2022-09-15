from glyphsLib.builder.names import build_stylemap_names


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
