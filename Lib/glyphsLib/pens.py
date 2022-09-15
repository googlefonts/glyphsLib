from typing import Any, Dict, Tuple, Union, Optional

from fontTools.pens.pointPen import AbstractPointPen

from glyphsLib.types import Transform, Point

Number = Union[int, float]


class LayerPointPen(AbstractPointPen):
    """A point pen to draw onto GSLayer object.

    See :mod:`fontTools.pens.basePen` and :mod:`fontTools.pens.pointPen` for an
    introduction to pens.
    """

    def __init__(self, layer: "GSLayer") -> None:  # noqa: F821
        self._layer: "GSLayer" = layer  # noqa: F821
        self._path: Optional["GSPath"] = None  # noqa: F821

    def beginPath(self, **kwargs: Any) -> None:
        from glyphsLib.classes import GSPath

        if self._path is not None:
            raise ValueError("Call endPath first.")

        self._path = GSPath()
        self._path.closed = True  # Until proven otherwise.

    def endPath(self) -> None:
        if self._path is None:
            raise ValueError("Call beginPath first.")

        if self._path.closed:
            self._path.nodes.append(self._path.nodes.pop(0))
        self._layer.paths.append(self._path)
        self._path = None

    def addPoint(
        self,
        pt: Tuple[Number, Number],
        segmentType: Optional[str] = None,
        smooth: bool = False,
        name: Optional[str] = None,
        userData: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        from glyphsLib.classes import GSNode

        if self._path is None:
            raise ValueError("Call beginPath first.")

        if segmentType == "move":
            if self._path.nodes:
                raise ValueError("For an open contour, 'move' must come first.")
            self._path.closed = False

        node = GSNode(
            Point(*pt),
            nodetype=_to_glyphs_node_type(segmentType),
            smooth=smooth,
            name=name,
        )
        if userData:
            node.userData = userData
        self._path.nodes.append(node)

    def addComponent(
        self,
        baseGlyph: str,
        transformation: Union[
            Transform, Tuple[float, float, float, float, float, float]
        ],
        **kwargs: Any,
    ) -> None:
        from glyphsLib.classes import GSComponent

        if not isinstance(transformation, Transform):
            transformation = Transform(*transformation)
        component = GSComponent(baseGlyph, transform=transformation)
        self._layer.components.append(component)


def _to_glyphs_node_type(node_type):
    if node_type is None:
        return "offcurve"
    if node_type == "move":
        return "line"
    return node_type


def _to_ufo_node_type(node_type):
    if node_type not in ["line", "curve", "qcurve"]:
        return None
    return node_type
