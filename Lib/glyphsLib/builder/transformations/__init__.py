from types import MappingProxyType
from typing import NamedTuple

from .align_alternate_layers import align_alternate_layers
from .propagate_anchors import propagate_all_anchors

TRANSFORMATIONS = [
    align_alternate_layers,
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
