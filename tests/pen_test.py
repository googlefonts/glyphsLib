import fontTools.pens.recordingPen
from fontTools.pens.pointPen import PointToSegmentPen

import glyphsLib.classes as classes
from glyphsLib.types import Transform


def test_pen_roundtrip(datadir, ufo_module):
    font = classes.GSFont(str(datadir.join("PenTest.glyphs")))
    font_temp = ufo_module.Font()
    glyph_temp = font_temp.newGlyph("test")

    for glyph in font.glyphs:
        for layer in glyph.layers:
            glyph_temp.clear()
            ufo_pen = glyph_temp.getPointPen()
            layer.drawPoints(ufo_pen)

            layer_temp = classes.GSLayer()
            glyphs_pen = layer_temp.getPointPen()
            glyph_temp.drawPoints(glyphs_pen)

            assert len(layer.paths) == len(layer_temp.paths)
            for path_orig, path_temp in zip(layer.paths, layer_temp.paths):
                assert len(path_orig.nodes) == len(path_temp.nodes)
                assert path_orig.closed == path_temp.closed
                for node_orig, node_temp in zip(path_orig.nodes, path_temp.nodes):
                    assert node_orig.position.x == node_temp.position.x
                    assert node_orig.position.y == node_temp.position.y
                    assert node_orig.smooth == node_temp.smooth
                    assert node_orig.type == node_temp.type

            assert len(layer.components) == len(layer_temp.components)
            for comp_orig, comp_temp in zip(layer.components, layer_temp.components):
                assert comp_orig.name == comp_temp.name
                assert comp_orig.transform == comp_temp.transform


def test_pen_recording_equivalent(datadir):
    font = classes.GSFont(str(datadir.join("PenTest.glyphs")))

    for glyph in font.glyphs:
        for layer in glyph.layers:
            rpen1 = fontTools.pens.recordingPen.RecordingPen()
            rpen2 = fontTools.pens.recordingPen.RecordingPen()
            layer.draw(rpen1)
            layer.drawPoints(PointToSegmentPen(rpen2))
            assert rpen1.value == rpen2.value


def test_pen_recording(datadir):
    font = classes.GSFont(str(datadir.join("PenTest.glyphs")))
    pen = fontTools.pens.recordingPen.RecordingPen()
    layer = font.glyphs["recording1"].layers[0]
    layer.draw(pen)

    assert pen.value == [
        ("moveTo", ((0, 141),)),
        ("lineTo", ((0, 0),)),
        ("lineTo", ((162, 0),)),
        ("lineTo", ((162, 141),)),
        ("closePath", ()),
        ("moveTo", ((366, 0),)),
        ("curveTo", ((413, 0), (452, 32), (452, 71))),
        ("curveTo", ((452, 109), (413, 141), (366, 141))),
        ("curveTo", ((319, 141), (280, 109), (280, 71))),
        ("curveTo", ((280, 32), (319, 0), (366, 0))),
        ("closePath", ()),
        ("moveTo", ((64, 255),)),
        ("lineTo", ((56, 419),)),
        ("lineTo", ((186, 415),)),
        ("curveTo", ((189, 387), (118, 295), (196, 331))),
        ("endPath", ()),
        ("moveTo", ((266, 285),)),
        ("lineTo", ((412, 421),)),
        ("endPath", ()),
        ("moveTo", ((462, 387),)),
        ("curveTo", ((458, 358), (514, 295), (450, 301))),
        ("endPath", ()),
        ("addComponent", ("dieresis", Transform(1, 0, 0, 1, 108, -126))),
        (
            "addComponent",
            ("adieresis", Transform(0.84572, 0.30782, -0.27362, 0.75175, 517, 308)),
        ),
    ]


def test_pointpen_recording(datadir):
    font = classes.GSFont(str(datadir.join("PenTest.glyphs")))
    pen = fontTools.pens.recordingPen.RecordingPointPen()
    layer = font.glyphs["recording1"].layers[0]
    layer.drawPoints(pen)

    assert pen.value == [
        ("beginPath", (), {}),
        ("addPoint", ((0, 141), "line", False, None), {"userData": {}}),
        ("addPoint", ((0, 0), "line", False, None), {"userData": {}}),
        ("addPoint", ((162, 0), "line", False, None), {"userData": {}}),
        ("addPoint", ((162, 141), "line", False, None), {"userData": {}}),
        ("endPath", (), {}),
        ("beginPath", (), {}),
        ("addPoint", ((366, 0), "curve", True, None), {"userData": {}}),
        ("addPoint", ((413, 0), None, False, None), {"userData": {}}),
        ("addPoint", ((452, 32), None, False, None), {"userData": {}}),
        ("addPoint", ((452, 71), "curve", True, None), {"userData": {}}),
        ("addPoint", ((452, 109), None, False, None), {"userData": {}}),
        ("addPoint", ((413, 141), None, False, None), {"userData": {}}),
        ("addPoint", ((366, 141), "curve", True, None), {"userData": {}}),
        ("addPoint", ((319, 141), None, False, None), {"userData": {}}),
        ("addPoint", ((280, 109), None, False, None), {"userData": {}}),
        ("addPoint", ((280, 71), "curve", True, None), {"userData": {}}),
        ("addPoint", ((280, 32), None, False, None), {"userData": {}}),
        ("addPoint", ((319, 0), None, False, None), {"userData": {}}),
        ("endPath", (), {}),
        ("beginPath", (), {}),
        ("addPoint", ((64, 255), "move", False, None), {}),
        ("addPoint", ((56, 419), "line", False, None), {"userData": {}}),
        ("addPoint", ((186, 415), "line", False, None), {"userData": {}}),
        ("addPoint", ((189, 387), None, False, None), {"userData": {}}),
        ("addPoint", ((118, 295), None, False, None), {"userData": {}}),
        ("addPoint", ((196, 331), "curve", False, None), {"userData": {}}),
        ("endPath", (), {}),
        ("beginPath", (), {}),
        ("addPoint", ((266, 285), "move", False, None), {}),
        ("addPoint", ((412, 421), "line", False, None), {"userData": {}}),
        ("endPath", (), {}),
        ("beginPath", (), {}),
        ("addPoint", ((462, 387), "move", False, None), {}),
        ("addPoint", ((458, 358), None, False, None), {"userData": {}}),
        ("addPoint", ((514, 295), None, False, None), {"userData": {}}),
        ("addPoint", ((450, 301), "curve", False, None), {"userData": {}}),
        ("endPath", (), {}),
        ("addComponent", ("dieresis", Transform(1, 0, 0, 1, 108, -126)), {}),
        (
            "addComponent",
            ("adieresis", Transform(0.84572, 0.30782, -0.27362, 0.75175, 517, 308)),
            {},
        ),
    ]
