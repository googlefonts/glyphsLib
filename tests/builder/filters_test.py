from glyphsLib.builder.filters import parse_glyphs_filter


def test_complete_parameter():
    inputstr = (
        "Transformations;LSB:+23;RSB:-22;SlantCorrection:true;"
        "OffsetX:10;OffsetY:-10;Origin:0;exclude:uni0334,uni0335 uni0336"
    )
    expected = {
        "name": "Transformations",
        "kwargs": {
            "LSB": 23,
            "RSB": -22,
            "SlantCorrection": True,
            "OffsetX": 10,
            "OffsetY": -10,
            "Origin": 0,
        },
        "exclude": ["uni0334", "uni0335", "uni0336"],
    }
    result = parse_glyphs_filter(inputstr)
    assert result == expected


def test_is_pre():
    inputstr = "Dummy"
    expected = {"name": "Dummy", "pre": True}
    result = parse_glyphs_filter(inputstr, is_pre=True)
    assert result == expected


def test_positional_parameter():
    inputstr = "Roughenizer;34;2;0;0.34"
    expected = {"name": "Roughenizer", "args": [34, 2, 0, 0.34]}
    result = parse_glyphs_filter(inputstr)
    assert result == expected


def test_single_name():
    inputstr = "AddExtremes"
    expected = {"name": "AddExtremes"}
    result = parse_glyphs_filter(inputstr)
    assert result == expected


def test_empty_string(caplog):
    inputstr = ""
    parse_glyphs_filter(inputstr)
    assert len(
        [r for r in caplog.records if "Failed to parse glyphs filter" in r.msg]
    ), "Empty string should trigger an error message"


def test_no_name(caplog):
    inputstr = ";OffsetX:2"
    parse_glyphs_filter(inputstr)
    assert len(
        [r for r in caplog.records if "Failed to parse glyphs filter" in r.msg]
    ), "Empty string with no filter name should trigger an error message"


def test_duplicate_exclude_include(caplog):
    inputstr = "thisisaname;34;-3.4;exclude:uni1111;include:uni0022;exclude:uni2222"
    expected = {"name": "thisisaname", "args": [34, -3.4], "exclude": ["uni2222"]}
    result = parse_glyphs_filter(inputstr)

    assert len(
        [r for r in caplog.records if "can only present as the last argument" in r.msg]
    ), (
        "The parse_glyphs_filter should warn user that the exclude/include "
        "should only be the last argument in the filter string."
    )
    assert result == expected


def test_empty_args_trailing_semicolon():
    inputstr = "thisisaname;3;;a:b;;;"
    expected = {"name": "thisisaname", "args": [3], "kwargs": {"a": "b"}}
    result = parse_glyphs_filter(inputstr)
    assert result == expected
