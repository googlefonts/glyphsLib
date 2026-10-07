# MenuTitle: Add corner component expectations
"""Add Glyphs' own decomposition of each case in CornerComponents.glyphs.

tests/data/CornerComponents.glyphs has a glyph for each case, with one or more
corner components. This adds a <case>.expectation glyph for each case with the
corners decomposed by Glyphs, which test_corner_components in
tests/corner_components_test.py compares our output with.

To add or change a case, edit its glyph in the file, then, with Glyphs 3.5
running, either run this from a terminal (it needs pyobjc):

    python tests/tools/corner_components_expectations.py

or open the file in Glyphs and paste this into Window > Macro Panel. Either way
the expectations from an earlier run are replaced and the file is saved and
closed. If we don't yet match Glyphs on the case, add it to MISMATCHES in the
test.
"""

import os
import sys

try:
    from GlyphsApp import CORNER, Glyphs
except ImportError:
    Glyphs = None

FILE_NAME = "CornerComponents.glyphs"
SUFFIX = ".expectation"


def has_corners(layer):
    return any(h.type == CORNER for h in layer.hints)


def add_expectations(font):
    master_id = font.masters[0].id
    for name in [g.name for g in font.glyphs if g.name.endswith(SUFFIX)]:
        del font.glyphs[name]
    cases = [
        g.name
        for g in font.glyphs
        if not g.name.startswith("_") and has_corners(g.layers[master_id])
    ]
    for name in cases:
        expectation = font.glyphs[name].copy()
        expectation.name = name + SUFFIX
        expectation.note = None
        font.glyphs.append(expectation)
        layer = font.glyphs[expectation.name].layers[master_id]
        layer.decomposeCorners()
        if has_corners(layer):
            print("%s: Glyphs left a corner in place; removed it" % name)
            for i in reversed(range(len(layer.hints))):
                if layer.hints[i].type == CORNER:
                    del layer.hints[i]
    return cases


def drop_timestamps(path):
    # Glyphs stamps each new glyph with the time, which would change every
    # expectation on every run.
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(line for line in lines if not line.startswith("lastChange = "))


def run_in_glyphs(path=None):
    if path is None:
        fonts = [f for f in Glyphs.fonts if (f.filepath or "").endswith(FILE_NAME)]
        if not fonts:
            raise RuntimeError("open %s first" % FILE_NAME)
        font = fonts[0]
        path = font.filepath
    else:
        fonts = [f for f in Glyphs.fonts if f.filepath == path]
        font = fonts[0] if fonts else Glyphs.open(path, showInterface=False)
    font.disableUpdateInterface()
    try:
        cases = add_expectations(font)
    finally:
        font.enableUpdateInterface()
    font.save(path)
    font.close()
    drop_timestamps(path)
    print(
        "Glyphs %s (%s): added %d expectations to %s"
        % (Glyphs.versionString, Glyphs.buildNumber, len(cases), path)
    )


def run_from_terminal():
    # Glyphs serves its scripting interface over Distributed Objects; send it
    # this file to run.
    from Foundation import NSConnection, NSObject

    errors = []

    class Output(NSObject):
        def setWrite_(self, text):
            sys.stdout.write(text)

        def setWriteError_(self, text):
            errors.append(text)
            sys.stderr.write(text)

    connection = NSConnection.connectionWithRegisteredName_host_(
        "com.GeorgSeifert.Glyphs3", None
    )
    if connection is None:
        sys.exit("Glyphs 3 isn't running")
    connection.setRequestTimeout_(600.0)
    connection.setReplyTimeout_(600.0)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    path = os.path.join(os.path.realpath(path), FILE_NAME)
    with open(__file__, encoding="utf-8") as f:
        source = f.read()
    code = "exec(compile(%r, %r, 'exec'), {'__name__': 'glyphs', 'PATH': %r})" % (
        source,
        __file__,
        path,
    )
    connection.rootProxy().scriptingHandler().runMacroString_stdOut_(code, Output.new())
    if errors:
        sys.exit(1)


if Glyphs is None:
    run_from_terminal()
else:
    run_in_glyphs(globals().get("PATH"))
