import logging

from fontTools.pens.basePen import BasePen
from fontTools.misc.bezierTools import segmentSegmentIntersections, _split_segment_at_t
from ufo2ft.filters import BaseFilter

logger = logging.getLogger(__name__)


class EraseOpenCornersPen(BasePen):
    def __init__(self, outpen):
        self.segments = []
        self.is_closed = False
        self.affected = False
        self.outpen = outpen

    def _moveTo(self, p1):
        if self.segments or self.is_closed:
            raise ValueError(
                "EraseOpenCornersPen should only be used on single contours"
            )

    def _operate(self, *points):
        self.segments.append((self._getCurrentPoint(), *points))

    _qCurveTo = _curveTo = _lineTo = _qCurveToOne = _curveToOne = _operate

    def closePath(self):
        self.segments.append((self._getCurrentPoint(), self.segments[0][0]))
        self.is_closed = True
        self.endPath()

    def endPath(self):
        segs = self.segments
        if not segs:
            return

        ix = 0
        while ix < len(segs):
            next_ix = (ix + 1) % len(segs)
            intersection = [
                i
                for i in segmentSegmentIntersections(segs[ix - 1], segs[next_ix])
                if 0 <= i.t1 <= 1 and 0 <= i.t2 <= 1
            ]
            if intersection and (intersection[0].t1 > 0.5 and intersection[0].t2 < 0.5):
                (segs[ix - 1], _) = _split_segment_at_t(
                    segs[ix - 1], intersection[0].t1
                )
                (_, segs[next_ix]) = _split_segment_at_t(
                    segs[next_ix], intersection[0].t2
                )
                # Ensure the ends match up
                segs[next_ix] = (segs[ix - 1][-1],) + segs[next_ix][1:]
                segs[ix : ix + 1] = []
                self.affected = True
            ix = ix + 1

        self.outpen.moveTo(segs[0][0])

        for seg in segs:
            if len(seg) == 2:
                self.outpen.lineTo(*seg[1:])
            elif len(seg) == 3:
                self.outpen.qCurveTo(*seg[1:])
            elif len(seg) == 4:
                self.outpen.curveTo(*seg[1:])

        if self.is_closed:
            self.outpen.closePath()
        else:
            self.outpen.endPath()


class EraseOpenCornersFilter(BaseFilter):
    def filter(self, glyph):
        if not len(glyph):
            return False

        affected = False
        contours = list(glyph)
        glyph.clearContours()
        outpen = glyph.getPen()
        for contour in contours:
            p = EraseOpenCornersPen(outpen)
            contour.draw(p)
            if p.affected:
                affected = True
        return affected
