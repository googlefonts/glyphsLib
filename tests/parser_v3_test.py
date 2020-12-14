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

gsglyph_plist_v2 = """{
glyphname = A;
lastChange = "2020-10-28 19:17:01 +0000";
layers = (
{
guideLines = (
{
angle = 12.9339;
locked = 1;
position = "{348, 402}";
showMeasurement = 1;
}
);
hints = (
{
horizontal = 1;
origin = "{0, 0}";
target = "{0, 3}";
type = Stem;
}
);
layerId = m01;
rightMetricsKey = "=20";
paths = (
{
closed = 1;
nodes = (
"10 66 LINE",
"439 66 LINE",
"439 608 LINE",
"10 608 LINE {name = \\"Hallo\\011Welt\\";\\ntest = \\"Hallo\\012Welt\\";}"
);
}
);
width = 459;
},
{
associatedMasterId = m01;
layerId = "B53B276E-7ED6-4F56-94FF-4162BC3B585A";
name = Color;
width = 600;
}
);
leftKerningGroup = A;
leftMetricsKey = "=10";
rightKerningGroup = A;
topKerningGroup = A;
bottomKerningGroup = A;
unicode = "0041,0061";
}"""

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

def test_parse_gsglyph_space_v3():
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

def test_parse_gsglyph_a_v2():
    p = Parser(current_type=GSGlyph, formatVersion=2)
    g = p.parse(gsglyph_plist_v2)
    print(g.layers[0].paths[0].nodes)
    assert(False)

