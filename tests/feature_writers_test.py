from textwrap import dedent
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
        # note there are two mark2base lookups because ufo2ft v3 generates one lookup
        # per mark class (previously 'top' and 'bottom' would go into one lookup)
        assert str(feature) == dedent(
            """\
            feature mark {
                lookup mark2base;
                lookup mark2base_1;
                lookup ContextualMarkDispatch_0;
                lookup ContextualMarkDispatch_1;
                lookup ContextualMarkDispatch_2;
            } mark;
            """
        )

        lookup = feature.statements[-3].lookup
        assert str(lookup) == (
            "lookup ContextualMarkDispatch_0 {\n"
            "    lookupflag UseMarrkFilteringSet [twodotshorizontalbelow];\n"
            "    # reh-ar * behDotess-ar.medi &\n"
            "    pos reh-ar [behDotless-ar.init] behDotess-ar.medi"
            " @MC_bottom' lookup ContextualMark_0;\n"
            "} ContextualMarkDispatch_0;\n"
        )

        lookup = feature.statements[-2].lookup
        assert str(lookup) == (
            "lookup ContextualMarkDispatch_1 {\n"
            "    lookupflag UseMarrkFilteringSet [twodotsverticalbelow];\n"
            "    # reh-ar *\n"
            "    pos reh-ar [behDotless-ar.init behDotless-ar.init.alt]"
            " @MC_bottom' lookup ContextualMark_1;\n"
            "} ContextualMarkDispatch_1;\n"
        )

        lookup = feature.statements[-1].lookup
        assert str(lookup) == (
            "lookup ContextualMarkDispatch_2 {\n"
            "    # reh-ar *\n"
            "    pos reh-ar [behDotless-ar.init] @MC_bottom' lookup ContextualMark_2;\n"
            "} ContextualMarkDispatch_2;\n"
        )


def test_ignorable_anchors(datadir):
    ufos = load_to_ufos(datadir.join("IgnorableAnchors.glyphs"))

    for ufo in ufos:
        writer = ContextualMarkFeatureWriter()
        feaFile = ast.FeatureFile()
        assert str(feaFile) == ""
        assert writer.write(ufo, feaFile)

        assert len(feaFile.markClasses) == 1
        assert "MC_top" in feaFile.markClasses

        feature = feaFile.statements[-2]
        assert feature.name == "mark"
        assert len(feature.statements) == 1

        lookup = feature.statements[0]
        assert len(lookup.statements) == 4
        for statement in lookup.statements:
            assert isinstance(statement, ast.MarkBasePosStatement)
            assert len(statement.marks) == 1
            assert statement.marks[0][1].name == "MC_top"
