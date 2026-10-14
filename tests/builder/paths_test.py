import pytest

from glyphsLib.pens import _drop_offcurves_before_lines
from glyphsLib.classes import GSNode


@pytest.mark.parametrize(
    "node_types,closed,expected_indices",
    [
        pytest.param("", True, [], id="empty"),
        pytest.param("line line line", True, [0, 1, 2], id="lines"),
        pytest.param("line offcurve offcurve line", False, [0, 3], id="open-line"),
        pytest.param("line offcurve line line", True, [0, 2, 3], id="interior-line"),
        pytest.param("offcurve line line", True, [1, 2], id="leading-control"),
        pytest.param("line line offcurve", True, [0, 1], id="closing-line"),
        pytest.param("offcurve line offcurve", True, [1], id="wrapping-controls"),
        pytest.param(
            "line offcurve offcurve curve", False, [0, 1, 2, 3], id="cubic-controls"
        ),
        pytest.param(
            "line offcurve offcurve qcurve",
            False,
            [0, 1, 2, 3],
            id="quadratic-controls",
        ),
        pytest.param(
            "curve line offcurve offcurve", True, [0, 1, 2, 3], id="closing-curve"
        ),
        pytest.param("line offcurve", False, [0, 1], id="open-trailing-control"),
        pytest.param("offcurve offcurve", True, [0, 1], id="all-offcurve"),
    ],
)
def test_drop_offcurves_before_lines(node_types, closed, expected_indices):
    nodes = [
        GSNode(position=(i, 0), nodetype=node_type)
        for i, node_type in enumerate(node_types.split())
    ]

    kept = _drop_offcurves_before_lines(nodes, closed)

    # Coordinates identify the original nodes and make their order explicit.
    assert [node.position.x for node in kept] == expected_indices
