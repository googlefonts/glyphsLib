import copy
from dataclasses import dataclass
from enum import IntEnum
import logging
import math

from ufo2ft.filters import BaseFilter

from glyphsLib.builder.constants import HINTS_LIB_KEY
from glyphsLib.affine import Affine


logger = logging.getLogger(__name__)


class Alignment(IntEnum):
    LEFT = 0
    MIDDLE = 1
    RIGHT = 2
    UNUSED = 3
    UNALIGNED = 4


# Using a class here is mild overkill but it allows us to store
# the information about the component in a slightly more readable
# manner.
@dataclass
class CornerComponent:
    alignment: Alignment
    corner_path: object
    target_node_ix: int
    origin: (int, int) = (0, 0)
    left_x: int = 0
    right_x: int = 0

    def insert_into_path(self, path):
        self.align_my_path_to_main_path(path)
        raise NotImplementedError

    def align_my_path_to_main_path(self, path):
        target_node = path[self.target_node_ix]
        target_node_next = path[(self.target_node_ix + 1) % len(path)]
        if self.alignment == Alignment.LEFT:
            stroke_angle = math.atan2(
                target_node_next.y - target_node.y, target_node_next.x - target_node.x
            )
            rot = Affine.rotation(math.degrees(stroke_angle), self.origin)
            # Rotate the whole path around the origin
            for pt in self.corner_path:
                pt.x, pt.y = rot * (pt.x, pt.y)

        elif self.alignment == Alignment.MIDDLE:
            raise NotImplementedError
        elif self.alignment == Alignment.RIGHT:
            raise NotImplementedError
        elif self.alignment == Alignment.UNUSED:
            raise NotImplementedError
        elif self.alignment == Alignment.UNALIGNED:
            pass  # right?

        # Now position our path onto the point?
        for pt in self.corner_path:
            pt.x, pt.y = pt.x + target_node.x, pt.y + target_node.y

        raise NotImplementedError


class CornerComponentsFilter(BaseFilter):
    def filter(self, glyph):
        if not len(glyph):
            return False

        if not HINTS_LIB_KEY in glyph.lib:
            return False

        corner_components = [
            hint
            for hint in glyph.lib[HINTS_LIB_KEY]
            if hint.get("type").upper() == "CORNER"
        ]

        if not corner_components:
            return False

        for glyphs_cc in corner_components:
            path_idx, node_idx = glyphs_cc["origin"]
            layer = self.context.glyphSet[glyphs_cc["name"]]
            if len(layer) > 1:
                logger.warn(
                    "Corner components of more than one path (%s in %s) not supported",
                    glyphs_cc["name"],
                    glyph.name,
                )
                continue

            cc = CornerComponent(
                alignment=Alignment(glyphs_cc.get("options", 0)),
                corner_path=copy.deepcopy(layer[0]),
                target_node_ix=(node_idx + 1) % len(glyph[path_idx]),
            )
            cc.insert_into_path(glyph[path_idx])

        return True
