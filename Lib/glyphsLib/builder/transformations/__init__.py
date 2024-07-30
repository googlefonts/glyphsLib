from types import MappingProxyType
from typing import NamedTuple

from .propagate_anchors import propagate_all_anchors

TRANSFORMATIONS = [
    propagate_all_anchors,
]


class _CustomParameter(NamedTuple):
    name: str
    default: bool


TRANSFORMATION_CUSTOM_PARAMS = MappingProxyType(
    {
        propagate_all_anchors: _CustomParameter("Propagate Anchors", True),
    }
)
