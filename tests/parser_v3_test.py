from io import StringIO
import glyphsLib
from glyphsLib.parser import Parser
from glyphsLib.parser.v3 import plist_to_dict, dict_to_plist
from glyphsLib.classes import GSGuide, GSCustomParameter, GSGlyph
from glyphsLib.types import Point

gsguide_plist_v3 = """{
angle = 24.582;
lockAngle = 1;
pos = (192,216);
showMeasurement = 1;
}
"""
gsguide_plist_v2 = """{
angle = 24.582;
lockAngle = 1;
position = "{192, 216}";
showMeasurement = 1;
}
"""

gsguide = GSGuide()
gsguide.position = Point(192, 216)
gsguide.angle = 24.582
gsguide.lockAngle = True
gsguide.showMeasurement = True
gsguide.locked = False


def string_to_dict(s):
    return plist_to_dict(StringIO(s))


def normalize_plist(s):
    return dict_to_plist(string_to_dict(s))


def test_plist_to_dict():
    assert string_to_dict(gsguide_plist_v3) == {
        "angle": "24.582",
        "lockAngle": "1",
        "pos": ["192", "216"],
        "showMeasurement": "1",
    }


def test_plist_to_gsguide():
    gsguide_dict = string_to_dict(gsguide_plist_v3)
    g = GSGuide.from_dict(gsguide_dict, formatVersion=3)
    assert str(g) == "<GSGuide x=192.0 y=216.0 angle=24.6>"


def test_plist_to_gsguide_old_parser():
    p = Parser(current_type=GSGuide, formatVersion=3)
    g = p.parse(gsguide_plist_v3)
    assert str(g) == "<GSGuide x=192.0 y=216.0 angle=24.6>"


def test_plist_to_gsguide_v2():
    p = Parser(current_type=GSGuide, formatVersion=2)
    g = p.parse(gsguide_plist_v2)
    assert str(g) == "<GSGuide x=192.0 y=216.0 angle=24.6>"


def test_plist_to_gsguide_new_parser():
    g = GSGuide.from_dict(string_to_dict(gsguide_plist_v3), formatVersion=3)
    assert str(g) == "<GSGuide x=192.0 y=216.0 angle=24.6>"


def test_gsguide_to_dict_v3():
    assert gsguide.to_dict() == {
        "angle": 24.582,
        "pos": (192, 216),
        "showMeasurement": True,
        "lockAngle": True,
    }


def test_gsguide_to_dict_v2():
    assert gsguide.to_dict(formatVersion=2) == {
        "angle": 24.582,
        "position": "{192, 216}",
        "showMeasurement": True,
        "lockAngle": True,
    }


def test_gsguide_to_plist_v3():
    g = GSGuide.from_dict(string_to_dict(gsguide_plist_v3), formatVersion=3)
    assert (
        dict_to_plist(g.to_dict())
        == """{
angle = 24.582;
lockAngle = 1;
pos = (
192,
216
);
showMeasurement = 1;
}"""
    )


def test_gsguide_roundtrip_v2():
    p = Parser(current_type=GSGuide, formatVersion=2)
    g = p.parse(gsguide_plist_v2)
    assert dict_to_plist(g.to_dict(formatVersion=2)).strip() == gsguide_plist_v2.strip()


def test_gsguide_roundtrip_v2_old_writer():
    p = Parser(current_type=GSGuide, formatVersion=2)
    g = p.parse(gsguide_plist_v2)
    foo = StringIO()
    glyphsLib.dump(g, foo)
    assert foo.getvalue().strip() == gsguide_plist_v2.strip()


def test_gsguide_roundtrip_v3():
    g = GSGuide.from_dict(string_to_dict(gsguide_plist_v3), formatVersion=3)
    assert normalize_plist(dict_to_plist(g.to_dict())) == normalize_plist(
        gsguide_plist_v3
    )

def test_gscustomparameter_roundtrip_v2():
    gsc = """{
name = trademark;
value = "Default Trademark";
}"""
    p = Parser(current_type=GSCustomParameter, formatVersion=2)
    g = p.parse(gsc)
    foo = StringIO()
    glyphsLib.dump(g, foo)
    assert foo.getvalue().strip() == gsc.strip()

def test_gsglyph_space_roundtrip_v3():
    gsglyph = """{
glyphname = space;
layers = (
{
layerId = m01;
width = 200;
}
);
unicode = 0020;
}"""
    gsglyph_dict = string_to_dict(gsglyph)
    assert gsglyph_dict == {
        "glyphname": "space",
        "layers":  [{'layerId': 'm01', 'width': '200'}],
        "unicode": "0020"
    }
    l = GSGlyph.from_dict(gsglyph_dict, formatVersion=3)
    assert len(l.layers) == 1
    assert l.unicodes[0] == "0020"
    assert l.name == "space"
