from __future__ import annotations

from pathlib import Path

import pytest

from glyphsLib import GSFont
from glyphsLib.builder.transformations.align_alternate_layers import (
    align_alternate_layers,
)


DATA = Path(__file__).parent.parent.parent / "data"


@pytest.mark.parametrize(
    "test_path",
    [
        DATA / "AlignAlternateLayers-g2.glyphs",
        DATA / "AlignAlternateLayers-g3.glyphs",
    ],
)
def test_align_alternate_layers(test_path):
    font = GSFont(test_path)
    # 'Cacute' has 3 master layers and no alternate layers
    Cacute = font.glyphs["Cacute"]
    assert len(Cacute.layers) == 3
    assert all(l._is_master_layer for l in Cacute.layers)
    assert not any(l._is_bracket_layer() for l in Cacute.layers)

    # it uses a component 'C' which in turn contains 3 additional alternate layers,
    # plus 'acutecomb.case' which has none
    C = font.glyphs["C"]
    assert len([l for l in font.glyphs["C"].layers if l._is_bracket_layer()]) == 3
    assert not any(l._is_bracket_layer() for l in font.glyphs["acutecomb.case"].layers)

    align_alternate_layers(font)

    # we expect 'Cacute' to now have 3 new alternate layers which have the same
    # axis coordinates as the ones from 'C'
    assert len(Cacute.layers) == 6
    assert len([l for l in Cacute.layers if l._is_master_layer]) == 3
    assert len([l for l in Cacute.layers if l._is_bracket_layer()]) == 3
    assert {
        tuple(l._bracket_axis_rules()) for l in C.layers if l._is_bracket_layer()
    } == {
        tuple(l._bracket_axis_rules()) for l in Cacute.layers if l._is_bracket_layer()
    }
