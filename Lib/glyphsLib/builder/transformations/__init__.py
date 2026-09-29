from types import MappingProxyType
from typing import NamedTuple

from .align_alternate_layers import align_alternate_layers
from .apply_origin_anchor import apply_origin_anchor
from .propagate_anchors import propagate_all_anchors
from .resolve_reverse_bracket_layers import resolve_reverse_bracket_layers

TRANSFORMATIONS = [
    apply_origin_anchor,
    resolve_reverse_bracket_layers,
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
