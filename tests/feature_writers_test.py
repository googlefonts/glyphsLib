from glyphsLib import load_to_ufos
from glyphsLib.featureWriters.markFeatureWriter import ContextualMarkFeatureWriter
from ufo2ft.featureWriters import ast


def test_contextual_anchors(datadir):
    ufos = load_to_ufos(datadir.join("ContextualAnchors.glyphs"))

    for ufo in ufos:
        writer = ContextualMarkFeatureWriter()
        feaFile = ast.FeatureFile()
        assert str(feaFile) == ""
        assert writer.write(ufo, feaFile)

        assert len(feaFile.markClasses) == 2
        assert "MC_bottom" in feaFile.markClasses

        feature = feaFile.statements[-1]
        assert feature.name == "mark"
        assert len(feature.statements) == 3

        lookup = feature.statements[-2].lookup
        assert str(lookup) == (
            "lookup ContextualMarkDispatch_0 {\n"
            "    lookupflag UseMarrkFilteringSet [twodotshorizontalbelow];\n"
            "    # reh-ar * behDotess-ar.medi &\n"
            "    pos reh-ar behDotless-ar.init behDotess-ar.medi"
            " [dotbelow-ar twodotshorizontalbelow-ar]'"
            " lookup ContextualMark_0; # behDotless-ar.init/*bottom.twodots\n"
            "} ContextualMarkDispatch_0;\n"
        )

        lookup = feature.statements[-1].lookup
        assert str(lookup) == (
            "lookup ContextualMarkDispatch_1 {\n"
            "    # reh-ar *\n"
            "    pos reh-ar behDotless-ar.init [dotbelow-ar twodotshorizontalbelow-ar]'"
            " lookup ContextualMark_1; # behDotless-ar.init/*bottom\n"
            "} ContextualMarkDispatch_1;\n"
        )
