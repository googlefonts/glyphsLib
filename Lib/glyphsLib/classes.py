# Copyright 2016 Georg Seifert. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
import logging
import math
import os
import re
import uuid
from collections import OrderedDict
from enum import IntEnum
from io import StringIO
from typing import Dict, List, Optional, Tuple, Union, Any, Iterator, cast, overload

# renamed to avoid shadowing glyphsLib.types.Transform imported further below
from fontTools.misc.transform import Identity, Transform as Affine
from fontTools.pens.basePen import AbstractPen
from fontTools.pens.pointPen import (
    AbstractPointPen,
    PointToSegmentPen,
    SegmentToPointPen,
)

from fontTools.ufoLib import filenames
from glyphsLib.parser import load, Parser
from glyphsLib.types import (
    IndexPath,
    OneLineList,
    Point,
    Rect,
    Size,
    Transform,
    UnicodesList,
    floatToString5,
    floatToString3,
    parse_datetime,
    parse_float_or_int,
    readIntList,
    NegateBool,
)

from glyphsLib.util import isString, isList
from glyphsLib.writer import Writer
import glyphsLib.glyphdata as glyphdata
from glyphsLib.glyphdata import GSGlyphInfo, GSWritingDirection, GSCase, GSLTR

logger = logging.getLogger(__name__)

__all__ = [
    "Glyphs",
    "GSFont",
    "GSFontMaster",
    "GSAlignmentZone",
    "GSInstance",
    "GSCustomParameter",
    "GSClass",
    "GSFeaturePrefix",
    "GSFeature",
    "GSGlyph",
    "GSLayer",
    "GSBackgroundLayer",
    "GSAnchor",
    "GSComponent",
    "GSSmartComponentAxis",
    "GSPath",
    "GSNode",
    "GSGuide",
    "GSAnnotation",
    "GSHint",
    "GSBackgroundImage",
    "GSAxis",
    # Constants
    "MOVE",
    "LINE",
    "CURVE",
    "QCURVE",
    "OFFCURVE",
    "GSMOVE",
    "GSLINE",
    "GSCURVE",
    "GSOFFCURVE",
    "GSSHARP",
    "GSSMOOTH",
    "PS_TOP_GHOST",
    "PS_BOTTOM_GHOST",
    "PS_STEM",
    "PS_FLEX",
    "TTSTEM",
    "TTSHIFT",
    "TTSNAP",
    "TTINTERPOLATE",
    "TTDIAGONAL",
    "TTDELTA",
    "TAG",
    "CORNER",
    "CAP",
    "BRUSH",
    "SEGMENT",
    "TTDONTROUND",
    "TTROUND",
    "TTROUNDUP",
    "TTROUNDDOWN",
    # "TRIPLE",
    "TEXT",
    "ARROW",
    "CIRCLE",
    "PLUS",
    "MINUS",
    "LTR",
    "RTL",
    "LTRTTB",
    "RTLTTB",
    "GSTopLeft",
    "GSTopCenter",
    "GSTopRight",
    "GSCenterLeft",
    "GSCenterCenter",
    "GSCenterRight",
    "GSBottomLeft",
    "GSBottomCenter",
    "GSBottomRight",
    "WEIGHT_CODES",
    "WIDTH_CODES",
    "LAYER_ATTRIBUTE_COORDINATES",
]

# CONSTANTS
GSMOVE_ = 17
GSLINE_ = 1
GSCURVE_ = 35
GSOFFCURVE_ = 65
GSSHARP = 0
GSSMOOTH = 100

GSMOVE = "move"
GSLINE = "line"
GSCURVE = "curve"
GSQCURVE = "qcurve"
GSOFFCURVE = "offcurve"

MOVE = GSMOVE
LINE = GSLINE
CURVE = GSCURVE
OFFCURVE = GSOFFCURVE
QCURVE = GSQCURVE

GSMetricsKeyUndefined = "undefined"
GSMetricsKeyAscender = "ascender"
GSMetricsKeyCapHeight = "cap height"
GSMetricsKeySlantHeight = "slant height"  # defaults to half xHeight
GSMetricsKeyxHeight = "x-height"
GSMetricsKeyMidHeight = "midHeight"
GSMetricsKeyTopHeight = "topHeight"  # old key
# global top boundary, can be xHeight, CapHeight, ShoulderHeight...
GSMetricsKeyBodyHeight = "bodyHeight"
GSMetricsKeyDescender = "descender"
GSMetricsKeyBaseline = "baseline"
GSMetricsKeyItalicAngle = "italic angle"

PROPERTIES_WHITELIST = [
    # This is stored in the official descriptor attributes.
    "familyNames",
    "designers",
    "designerURL",
    "manufacturers",
    "manufacturerURL",
    "copyrights",
    "versionString",
    "vendorID",
    "uniqueID",
    "licenses",
    "licenseURL",
    "trademarks",
    "descriptions",
    "sampleTexts",
    "postscriptFullNames",
    "postscriptFullName",
    # This is stored in the official descriptor attributes.
    # "postscriptFontName",
    "compatibleFullNames",
    "styleNames",
    "styleMapFamilyNames",
    "styleMapStyleNames",
    "preferredFamilyNames",
    "preferredSubfamilyNames",
    "variableStyleNames",
    "WWSFamilyName",
    "WWSSubfamilyName",
    "variationsPostScriptNamePrefix",
]


# Instance types; normal instance or variable font setting pseudo-instance
class InstanceType(IntEnum):
    SINGLE = 0
    VARIABLE = 1


# Font types; default or variable
class FontType(IntEnum):
    DEFAULT = 0
    VARIABLE = 1


""" # Glyphs used those int values, but we can use the str values from the file as is for now
TAG = -2
TOPGHOST = -1
STEM = 0
BOTTOMGHOST = 1
TTANCHOR = 2
TTSTEM = 3
TTALIGN = 4
TTINTERPOLATE = 5
TTDIAGONAL = 6
TTDELTA = 7
CORNER = 16
CAP = 17
"""

PS_TOP_GHOST = "TopGhost"
PS_BOTTOM_GHOST = "BottomGhost"
PS_STEM = "Stem"
PS_FLEX = "Flex"
TTSTEM = "TTStem"
TTSHIFT = "TTShift"  # TTAlign in G2
TTSNAP = "TTSnap"  # "TTAnchor" in G2
TTINTERPOLATE = "TTInterpolate"
TTDIAGONAL = "TTDiagonal"
TTDELTA = "TTDelta"
TAG = "Tag"
CORNER = "Corner"
CAP = "Cap"
BRUSH = "Brush"
SEGMENT = "Segment"

TTDONTROUND = 4
TTROUND = 0
TTROUNDUP = 1
TTROUNDDOWN = 2
# TRIPLE = 128

# Annotations:
TEXT = 1
ARROW = 2
CIRCLE = 3
PLUS = 4
MINUS = 5

# Directions:
LTR = 0  # Left To Right (e.g. Latin)
RTL = 1  # Right To Left (e.g. Arabic, Hebrew)
LTRTTB = 3  # Left To Right, Top To Bottom
RTLTTB = 2  # Right To Left, Top To Bottom

LAYER_ATTRIBUTE_AXIS_RULES = "axisRules"
LAYER_ATTRIBUTE_COORDINATES = "coordinates"
LAYER_ATTRIBUTE_COLOR_PALETTE = "colorPalette"
LAYER_ATTRIBUTE_SBIX_SIZE = "sbixSize"
LAYER_ATTRIBUTE_COLOR = "color"
LAYER_ATTRIBUTE_SVG = "svg"

GSTopLeft = 6
GSTopCenter = 7
GSTopRight = 8
GSCenterLeft = 3
GSCenterCenter = 4
GSCenterRight = 5
GSBottomLeft = 0
GSBottomCenter = 1
GSBottomRight = 2

WEIGHT_CODES: Dict[Optional[str], int] = {
    "Thin": 100,
    "UltraLight": 200,
    "ExtraLight": 200,
    "Light": 300,
    None: 400,  # default value normally omitted in source
    "Normal": 400,
    "Regular": 400,
    "Medium": 500,
    "DemiBold": 600,
    "SemiBold": 600,
    "Bold": 700,
    "UltraBold": 800,
    "ExtraBold": 800,
    "Black": 900,
    "Heavy": 900,
}

WEIGHT_CODES_REVERSE: Dict[int, Optional[str]] = {v: k for k, v in WEIGHT_CODES.items()}

WIDTH_CODES: Dict[Optional[str], int] = {
    "Ultra Condensed": 1,
    "Extra Condensed": 2,
    "Condensed": 3,
    "SemiCondensed": 4,
    None: 5,  # default value normally omitted in source
    "Medium (normal)": 5,
    "Semi Expanded": 6,
    "Expanded": 7,
    "Extra Expanded": 8,
    "Ultra Expanded": 9,
}

WIDTH_CODES_REVERSE: Dict[int, Optional[str]] = {v: k for k, v in WIDTH_CODES.items()}

DefaultAxisValuesV2 = [100, 100, 0, 0, 0, 0]


def instance_type(value: str) -> InstanceType:
    # Convert the instance type from the plist ("variable") into the integer constant
    return getattr(InstanceType, value.upper())


def font_type(value: str) -> FontType:
    # Convert the instance type from the plist ("variable") into the integer constant
    return getattr(FontType, value.upper())


class OnlyInGlyphsAppError(NotImplementedError):
    def __init__(self):
        NotImplementedError.__init__(
            self,
            "This property/method is only available in the real UI-based "
            "version of Glyphs.app.",
        )


def transformStructToScaleAndRotation(transform: Tuple[float, float, float, float, float, float]) -> Tuple[float, float, float]:
    Det: float = transform[0] * transform[3] - transform[1] * transform[2]
    _sX: float = math.sqrt(math.pow(transform[0], 2) + math.pow(transform[1], 2))
    _sY: float = math.sqrt(math.pow(transform[2], 2) + math.pow(transform[3], 2))
    if Det < 0:
        _sY = -_sY
    _R: float = math.atan2(transform[1] * _sY, transform[0] * _sX) * 180 / math.pi

    if Det < 0 and (math.fabs(_R) > 135 or _R < -90):
        _sX = -_sX
        _sY = -_sY
        if _R < 0:
            _R += 180
        else:
            _R -= 180

    quadrant: int = 0
    if _R < -90:
        quadrant = 180
        _R += quadrant
    if _R > 90:
        quadrant = -180
        _R += quadrant
    _R = _R * _sX / _sY
    _R -= quadrant
    if _R < -179:
        _R += 360

    return _sX, _sY, _R


class GSApplication:
    __slots__ = "font", "fonts"

    def __init__(self):
        self.font = None
        self.fonts = []

    def open(self, path):
        newFont = GSFont(path)
        self.fonts.append(newFont)
        self.font = newFont
        return newFont

    def __repr__(self):
        return "<glyphsLib>"


Glyphs = GSApplication()


class GSBase:
    """Represent the base class for all GS classes.

    Attributes:
        _defaultsForName (dict): Used to determine which values to serialize and which
            to imply by their absence.
    """

    _defaultsForName: Dict[str, Any] = {}

    def __repr__(self) -> str:
        content = ""
        if hasattr(self, "_dict"):
            content = str(self._dict)
        return f"<{self.__class__.__name__} {hex(id(self))}> {content}"

    # Note:
    # The dictionary API exposed by GS* classes is "private" in the sense that:
    #  * it should only be used by the parser, so it should only
    #    work for key names that are found in the files
    #  * and only for filling data in the objects, which is why it only
    #    implements `__setitem__`
    #
    # Users of the library should only rely on the object-oriented API that is
    # documented at https://docu.glyphsapp.com/
    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    @classmethod
    def _add_parsers(cls, specification: List[Dict[str, Any]]) -> None:
        for field in specification:
            keyname = field["plist_name"]
            dict_parser_name = f"_parse_{keyname}_dict"
            target = field.get("object_name", keyname)
            classname = field.get("type")
            transformer = field.get("converter")

            def _generic_parser(
                self: GSBase,
                parser: Parser,
                value: Any,
                keyname: str = keyname,
                target: str = target,
                classname: Optional[str] = classname,
                transformer: Optional[Any] = transformer,
            ) -> None:
                if transformer:
                    if isinstance(value, list) and transformer not in [IndexPath, Point, Rect]:
                        self[target] = [transformer(v) for v in value]
                    else:
                        self[target] = transformer(value)
                else:
                    obj = parser._parse(value, classname)
                    self[target] = obj

            setattr(cls, dict_parser_name, _generic_parser)


class Proxy:
    __slots__ = ("_owner",)

    def __init__(self, owner: Any) -> None:
        self._owner = owner

    def __repr__(self) -> str:
        """Return class name, id(), and list-lookalike representation of objects."""
        strings = [str(item) for item in self]
        content = ", ".join(strings)
        return f"<{self.__class__.__name__} {hex(id(self))}> ({content})"

    def __str__(self) -> str:
        """Return list-lookalike representation of objects."""
        strings = [str(item) for item in self]
        return f"({', '.join(strings)})"

    def __len__(self) -> int:
        values = self.values()
        if values is not None:
            return len(values)
        return 0

    def get(self, key: Any, default: Optional[Any] = None) -> Any:
        if isinstance(key, int) and key >= self.__len__():
            return default
        result = self[key]
        return result if result else default

    def pop(self, i: int) -> Any:
        if isinstance(i, int):
            node = self[i]
            del self[i]
            return node
        raise KeyError

    def __iter__(self):
        values = self.values()
        if values is not None:
            yield from values

    def index(self, value: Any) -> int:
        return self.values().index(value)

    def __copy__(self) -> List[Any]:
        return list(self)

    def __deepcopy__(self, memo: Dict[int, Any]) -> List[Any]:
        return [x.copy() for x in self.values()]

    def setter(self, values: Any) -> None:
        method = self.setterMethod()
        if isinstance(values, list):
            method(values)
        elif isList(values) or isinstance(values, type(self)):
            method(list(values))
        elif values is None:
            method([])
        else:
            raise TypeError

    def __getitem__(self, item: Any) -> Any:
        raise NotImplementedError("Should be implemented in a subclass")

    def __setitem__(self, key: Any, value: Any) -> None:
        raise NotImplementedError("Should be implemented in a subclass")

    def __delitem__(self, item: Any) -> None:
        raise NotImplementedError("Should be implemented in a subclass")

    def values(self) -> List[Any]:
        raise NotImplementedError("Should be implemented in a subclass")

    def setdefault(self, key: Any, default: Any):
        value = self[key]
        if value is None:
            value = default
            self[key] = default
        return value

    def setterMethod(self) -> Any:
        raise NotImplementedError("Should be implemented in a subclass")


class ListDictionaryProxy(Proxy):
    def __init__(self, owner: Any, name: str, klass: Any) -> None:
        super().__init__(owner)
        self._name: str = name
        self._class: Any = klass
        self._items: List[Any] = getattr(owner, name, [])

    def get(self, name: str, default: Optional[Any] = None) -> Optional[Any]:
        item = self._get_by_name(name)
        return item.value if item else default

    def append(self, item: Any) -> None:
        item.parent = self._owner
        self._items.append(item)

    def extend(self, items: List[Any]) -> None:
        for item in items:
            item.parent = self._owner
        self._items.extend(items)

    def remove(self, item: Any) -> None:
        if isinstance(item, str):
            item = self.__getitem__(item)
        self._items.remove(item)

    def insert(self, index: int, item: Any) -> None:
        item.parent = self._owner
        self._items.insert(index, item)

    def values(self) -> List[Any]:
        return self._items

    def setterMethod(self) -> Any:
        return self.__setter__

    def __getitem__(self, key: Union[int, str]) -> Optional[Any]:
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        if isinstance(key, int):
            return self._items[key]
        else:
            item = self._get_by_name(key)
            if item is not None:
                return item.value
        return None

    def __setitem__(self, key: Union[int, str], value: Any) -> None:
        if isinstance(key, int):
            item = self._items[key]
        else:
            item = self._get_by_name(key)

        if item is not None:
            item.value = value
        else:
            item = self._class(key, value)
            item.parent = self._owner
            self._items.append(item)

    def __delitem__(self, key: Union[int, str]) -> None:
        if isinstance(key, int):
            del self._items[key]
        elif isinstance(key, str):
            for item in list(self._items):
                if item.name == key:
                    self._items.remove(item)
        else:
            raise KeyError(key)

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, str):
            return self.__getitem__(item) is not None
        return item in self._items

    def __iter__(self):
        for index in range(len(self._items)):
            yield self._items[index]

    def __len__(self) -> int:
        return len(self._items)

    def __setter__(self, items: List[Any]) -> None:
        for item in items:
            item.parent = self._owner
        self._items = items
        setattr(self._owner, self._name, items)

    def _get_by_name(self, name: str) -> Optional[Any]:
        for item in self._items:
            if item.name == name:
                return item
        return None


class LayersIterator:
    __slots__ = ("_layers",)

    def __init__(self, owner: GSGlyph) -> None:
        if owner.parent:
            self._layers: Iterator[GSLayer] = self.orderedLayers(owner)
        else:
            self._layers = iter(owner._layers.values())

    def __iter__(self) -> LayersIterator:
        return self

    def next(self) -> GSLayer:
        return self.__next__()

    def __next__(self) -> GSLayer:
        return next(self._layers)

    @staticmethod
    def orderedLayers(glyph: GSGlyph) -> Iterator[GSLayer]:
        font = glyph.parent
        assert font is not None
        glyphLayerIds = {
            l.associatedMasterId
            for l in glyph._layers.values()
            if l.associatedMasterId == l.layerId
        }
        masterIds = {m.id for m in font.masters}
        intersectedLayerIds = glyphLayerIds & masterIds
        orderedLayers = [
            glyph._layers[m.id] for m in font.masters if m.id in intersectedLayerIds
        ]
        orderedLayers.extend(
            glyph._layers[l.layerId]
            for l in glyph._layers.values()
            if l.layerId not in intersectedLayerIds
        )
        return iter(orderedLayers)


class FontFontMasterProxy(Proxy):
    """The list of masters. You can access it with the index or the master ID.
    Usage:
        Font.masters[index]
        Font.masters[id]
        for master in Font.masters:
            ...
    """

    def __getitem__(self, key: Union[int, str]) -> Optional[GSFontMaster]:
        if isinstance(key, str):
            # UUIDs are case-sensitive in Glyphs.app.
            return next((master for master in self.values() if master.id == key), None)
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            return self.values()[key]
        raise KeyError(key)

    def __setitem__(self, key: Union[int, str], fontMaster: GSFontMaster) -> None:
        fontMaster.font = self._owner
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            oldFontMaster = self.__getitem__(key)
            if oldFontMaster:
                fontMaster.id = oldFontMaster.id
                self._owner._masters[key] = fontMaster
        elif isinstance(key, str):
            oldFontMaster = self.__getitem__(key)
            if oldFontMaster:
                fontMaster.id = oldFontMaster.id
                idx = self._owner._masters.index(oldFontMaster)
            self._owner._masters[idx] = fontMaster
        else:
            raise KeyError

    def __delitem__(self, key: Union[int, str]) -> None:
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            self.remove(self._owner._masters[key])
        else:
            oldFontMaster = self.__getitem__(key)
            if oldFontMaster:
                self.remove(oldFontMaster)

    def values(self) -> List[GSFontMaster]:
        return self._owner._masters

    def append(self, fontMaster: GSFontMaster) -> None:
        fontMaster.font = self._owner
        # If the master to be appended has no ID yet or it's a duplicate,
        # make up a new one.
        if not fontMaster.id or self[fontMaster.id]:
            fontMaster.id = str(uuid.uuid4()).upper()
        self._owner._masters.append(fontMaster)

        # Cycle through all glyphs and append layer
        for glyph in self._owner.glyphs:
            if not glyph.layers[fontMaster.id]:
                newLayer = GSLayer()
                glyph._setupLayer(newLayer, fontMaster.id)
                glyph.layers.append(newLayer)

    def remove(self, fontMaster: GSFontMaster) -> None:
        # First remove all layers in all glyphs that reference this master
        for glyph in self._owner.glyphs:
            for layer in list(glyph.layers):
                if layer.associatedMasterId == fontMaster.id or layer.layerId == fontMaster.id:
                    glyph.layers.remove(layer)
        self._owner._masters.remove(fontMaster)

    def insert(self, index: int, fontMaster: GSFontMaster) -> None:
        fontMaster.font = self._owner
        self._owner._masters.insert(index, fontMaster)

    def extend(self, fontMasters: List[GSFontMaster]) -> None:
        for fontMaster in fontMasters:
            fontMaster.font = self._owner
            self.append(fontMaster)

    def setter(self, values: Union[List[GSFontMaster], Proxy]) -> None:
        if isinstance(values, Proxy):
            values = list(values)
        self._owner._masters = values
        for m in values:
            m.font = self._owner


class FontInstanceProxy(Proxy):
    """The list of instances. You can access it with the index.
    Usage:
        Font.instances[index]
        for instance in Font.instances:
            ...
    """

    def __getitem__(self, key: Union[int, slice]) -> GSInstance:
        if isinstance(key, slice):
            return self._owner._instances.__getitem__(key)
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            return self._owner._instances[key]
        raise KeyError(key)

    def __setitem__(self, key: int, instance: GSInstance) -> None:
        instance.font = self._owner
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            self._owner._instances[key] = instance
        else:
            raise KeyError(key)

    def __delitem__(self, key: int) -> None:
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            return self.remove(self._owner._instances[key])
        else:
            raise KeyError(key)

    def values(self) -> List[GSInstance]:
        return self._owner._instances

    def append(self, instance: GSInstance) -> None:
        instance.font = self._owner
        # If the master to be appended has no ID yet or it's a duplicate,
        # make up a new one.
        self._owner._instances.append(instance)

    def remove(self, instance: GSInstance) -> None:
        if instance.font == self._owner:
            instance._font = None
        self._owner._instances.remove(instance)

    def insert(self, index: int, instance: GSInstance) -> None:
        instance.font = self._owner
        self._owner._instances.insert(index, instance)

    def extend(self, instances: List[GSInstance]) -> None:
        for instance in instances:
            instance.font = self._owner
        self._owner._instances.extend(instances)

    def setter(self, values: Union[List[GSInstance], Proxy]) -> None:
        if isinstance(values, Proxy):
            values = list(values)
        self._owner._instances = values
        for instance in values:
            instance.font = self._owner


class FontGlyphsProxy(Proxy):
    """The list of glyphs. You can access it with the index or the glyph name.
    Usage:
        Font.glyphs[index]
        Font.glyphs[name]
        for glyph in Font.glyphs:
        ...
    """

    @overload
    def __getitem__(self, key: int) -> Optional[GSGlyph]: ...  # noqa: E704
    @overload
    def __getitem__(self, key: str) -> Optional[GSGlyph]: ...  # noqa: E704
    @overload
    def __getitem__(self, key: slice) -> List[Optional[GSGlyph]]: ...  # noqa: E704
    def __getitem__(self, key: Union[int, str, slice]) -> Union[Optional[GSGlyph], List[Optional[GSGlyph]]]:  # noqa: E704 E301
        if isinstance(key, slice):
            return self._owner._glyphs.__getitem__(key)
        if isinstance(key, int):
            return self._owner._glyphs[key]
        if isinstance(key, str):
            return self._get_glyph_by_string(key)
        return None

    def __setitem__(self, key: int, glyph: GSGlyph) -> None:
        if isinstance(key, int):
            self._owner._setupGlyph(glyph)
            self._owner._glyphs[key] = glyph
        else:
            raise KeyError(key)  # TODO: add other access methods

    def __delitem__(self, key: Union[int, str]) -> None:
        if isinstance(key, int):
            del self._owner._glyphs[key]
        elif isinstance(key, str):
            glyph = self._get_glyph_by_string(key)
            if not glyph:
                raise KeyError(f"No glyph '{key}' in the font")
            self._owner._glyphs.remove(glyph)
        else:
            raise KeyError(key)

    def __contains__(self, item: Union[str, GSGlyph]) -> bool:
        if isinstance(item, str):
            return self._get_glyph_by_string(item) is not None
        return item in self._owner._glyphs

    def _get_glyph_by_string(self, key: str) -> Optional[GSGlyph]:
        # FIXME: (jany) looks inefficient
        if not isinstance(key, str):
            return None
            # by glyph name
        for glyph in self._owner._glyphs:
            if glyph.name == key:
                return glyph
        # by string representation as u'ä'
        if len(key) == 1:
            for glyph in self._owner._glyphs:
                if glyph.unicode == f"{ord(key):04X}":
                    return glyph
        # by unicode
        else:
            for glyph in self._owner._glyphs:
                if glyph.unicode == key.upper():
                    return glyph
        return None

    def values(self) -> List[GSGlyph]:
        return self._owner._glyphs

    def items(self) -> List[Tuple[str, GSGlyph]]:
        return [(glyph.name, glyph) for glyph in self._owner._glyphs]

    def append(self, glyph: GSGlyph) -> None:
        self._owner._setupGlyph(glyph)
        self._owner._glyphs.append(glyph)

    def extend(self, objects: List[GSGlyph]) -> None:
        for glyph in objects:
            self._owner._setupGlyph(glyph)
        self._owner._glyphs.extend(list(objects))

    def __len__(self) -> int:
        return len(self._owner._glyphs)

    def setter(self, values: Union[List[GSGlyph], Proxy]) -> None:
        if isinstance(values, Proxy):
            values = list(values)
        self._owner._glyphs = values
        for g in self._owner._glyphs:
            g.parent = self._owner
            for layer in g.layers.values():
                if not hasattr(layer, "associatedMasterId") or not layer.associatedMasterId:
                    g._setupLayer(layer, layer.layerId)


class FontClassesProxy(Proxy):
    VALUES_ATTR = "_classes"

    def __getitem__(self, key: Union[int, str, slice]) -> Optional[Union[GSClass, List[GSClass]]]:
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        if isinstance(key, str):
            for index, klass in enumerate(self.values()):
                if klass.name == key:
                    return self.values()[index]
        raise KeyError

    def __setitem__(self, key: Union[int, str], value: GSClass) -> None:
        if isinstance(key, int):
            self.values()[key] = value
            value._parent = self._owner
        elif isinstance(key, str):
            for index, klass in enumerate(self.values()):
                if klass.name == key:
                    self.values()[index] = value
                    value._parent = self._owner
        else:
            raise KeyError

    def __delitem__(self, key: Union[int, str]) -> None:
        if isinstance(key, int):
            del self.values()[key]
        elif isinstance(key, str):
            for index, klass in enumerate(self.values()):
                if klass.name == key:
                    del self.values()[index]

    def __contains__(self, item: Union[str, GSClass]) -> bool:
        if isinstance(item, str):
            for klass in self.values():
                if klass.name == item:
                    return True
            return False
        return item in self.values()

    def append(self, item: GSClass) -> None:
        self.values().append(item)
        item._parent = self._owner

    def insert(self, key: int, item: GSClass) -> None:
        self.values().insert(key, item)
        item._parent = self._owner

    def extend(self, items: List[GSClass]) -> None:
        self.values().extend(items)
        for value in items:
            value._parent = self._owner

    def remove(self, item: GSClass) -> None:
        self.values().remove(item)

    def values(self) -> List[GSClass]:
        return getattr(self._owner, self.VALUES_ATTR)

    def setter(self, values: Union[List[GSClass], Proxy]) -> None:
        if isinstance(values, Proxy):
            values = list(values)
        setattr(self._owner, self.VALUES_ATTR, values)
        for value in values:
            value._parent = self._owner


class FontFeaturesProxy(FontClassesProxy):
    VALUES_ATTR = "_features"


class FontFeaturePrefixesProxy(FontClassesProxy):
    VALUES_ATTR = "_featurePrefixes"


class GlyphLayerProxy(Proxy):
    def __getitem__(self, key: Union[int, str, slice]) -> Optional[Union[GSLayer, List[GSLayer]]]:
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            if self._owner.parent:
                return list(self)[key]
            return list(self.values())[key]
        elif isinstance(key, str):
            return self._owner._layers.get(key, None)

    def __setitem__(self, key: Union[int, str], layer: GSLayer) -> None:
        if isinstance(key, int) and self._owner.parent:
            if key < 0:
                key = self.__len__() + key
            old_layer = self._owner._layers.values()[key]
            layer.layerId = old_layer.layerId
            layer.associatedMasterId = old_layer.associatedMasterId
            self._owner._setupLayer(layer, old_layer.layerId)
            self._owner._layers[key] = layer
        elif isinstance(key, str) and self._owner.parent:
            self._owner._setupLayer(layer, key)
            self._owner._layers[key] = layer
        else:
            raise KeyError

    def __delitem__(self, key: Union[int, str]) -> None:
        if isinstance(key, int) and self._owner.parent:
            layer: GSLayer = self.values()[key]
            key = layer.layerId
        del self._owner._layers[key]

    def __iter__(self) -> Iterator[GSLayer]:
        return LayersIterator(self._owner)

    def __len__(self) -> int:
        return len(self.values())

    def keys(self) -> List[str]:
        return self._owner._layers.keys()

    def values(self) -> List[GSLayer]:
        return list(self._owner._layers.values())

    def append(self, layer: GSLayer) -> None:
        assert layer is not None
        if not layer.associatedMasterId and self._owner.parent:
            layer.associatedMasterId = self._owner.parent.masters[0].id
        if not layer.layerId:
            layer.layerId = str(uuid.uuid4()).upper()
        self._owner._setupLayer(layer, layer.layerId)
        self._owner._layers[layer.layerId] = layer

    def extend(self, layers: List[GSLayer]) -> None:
        for layer in layers:
            self.append(layer)

    def remove(self, layer: GSLayer) -> None:
        self._owner.removeLayerForKey(layer.layerId)

    def insert(self, index: int, layer: GSLayer) -> None:
        self.append(layer)

    def setter(self, values: Union[List[GSLayer], Dict[str, GSLayer]]) -> None:
        new_layers: OrderedDict[str, GSLayer] = OrderedDict()
        if isinstance(values, (list, tuple, type(self))):
            for layer in values:
                new_layers[layer.layerId] = layer
        elif isinstance(values, dict):
            new_layers.update(values)
        else:
            raise TypeError
        for key, layer in new_layers.items():
            self._owner._setupLayer(layer, key)
        self._owner._layers = new_layers

    def plistArray(self) -> List[GSLayer]:
        return list(self._owner._layers.values())


class LayerAnchorsProxy(Proxy):
    def __getitem__(self, key: Union[int, str, slice]) -> Optional[Union[GSAnchor, List[GSAnchor]]]:
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        elif isinstance(key, str):
            for i, a in enumerate(self._owner._anchors):
                if a.name == key:
                    return self._owner._anchors[i]
            return None
        else:
            raise KeyError

    def __setitem__(self, key: str, anchor: GSAnchor) -> None:
        if isinstance(key, str):
            anchor.name = key
            for i, a in enumerate(self._owner._anchors):
                if a.name == key:
                    self._owner._anchors[i] = anchor
                    return
            anchor._parent = self._owner
            self._owner._anchors.append(anchor)
        else:
            raise TypeError

    def __delitem__(self, key: Union[int, str]) -> None:
        if isinstance(key, int):
            del self._owner._anchors[key]
        elif isinstance(key, str):
            for i, a in enumerate(self._owner._anchors):
                if a.name == key:
                    self._owner._anchors[i]._parent = None
                    del self._owner._anchors[i]
                    return

    def values(self) -> List[GSAnchor]:
        return self._owner._anchors

    def append(self, anchor: GSAnchor) -> None:
        for i, a in enumerate(self._owner._anchors):
            if a.name == anchor.name:
                anchor._parent = self._owner
                self._owner._anchors[i] = anchor
                return
        if anchor.name:
            self._owner._anchors.append(anchor)
        else:
            raise ValueError("Anchor must have name")

    def extend(self, anchors: List[GSAnchor]) -> None:
        for anchor in anchors:
            anchor._parent = self._owner
        self._owner._anchors.extend(anchors)

    def remove(self, anchor: Union[str, GSAnchor]) -> None:
        if isinstance(anchor, str):
            for a in self._owner._anchors:
                if a.name == anchor:
                    anchor = a
        self._owner._anchors.remove(anchor)

    def insert(self, index: int, anchor: GSAnchor) -> None:
        anchor._parent = self._owner
        self._owner._anchors.insert(index, anchor)

    def __len__(self) -> int:
        return len(self._owner._anchors)

    def setter(self, anchors: Union[List[GSAnchor], Proxy]) -> None:
        if isinstance(anchors, Proxy):
            anchors = list(anchors)
        self._owner._anchors = anchors
        for anchor in anchors:
            anchor._parent = self._owner


class IndexedObjectsProxy(Proxy):
    _objects_name: str

    def __getitem__(self, key: Union[int, slice]) -> Any:
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        raise KeyError

    def __setitem__(self, key: int, value: Any) -> None:
        if isinstance(key, int):
            self.values()[key] = value
            value._parent = self._owner
        else:
            raise KeyError

    def __delitem__(self, key: int) -> None:
        if isinstance(key, int):
            del self.values()[key]
        else:
            raise KeyError

    def values(self) -> List[Any]:
        return getattr(self._owner, self._objects_name)

    def append(self, value: Any) -> None:
        self.values().append(value)
        value._parent = self._owner

    def extend(self, values: List[Any]) -> None:
        self.values().extend(values)
        for value in values:
            value._parent = self._owner

    def remove(self, value: Any) -> None:
        self.values().remove(value)

    def insert(self, index: int, value: Any) -> None:
        self.values().insert(index, value)
        value._parent = self._owner

    def __len__(self) -> int:
        return len(self.values())

    def setter(self, values: List[Any]) -> None:
        setattr(self._owner, self._objects_name, list(values))
        for value in self.values():
            value._parent = self._owner


class InternalAxesProxy(Proxy):
    def __getitem__(self, key: Union[int, str, slice]) -> Optional[Union[int, float, List[float]]]:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return None
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            if key < len(self._owner.font.axes):
                axis = self._owner.font.axes[key]
                return self._owner._internalAxesValues.get(axis.axisId)
            return None
        elif isinstance(key, str):
            return self._owner._internalAxesValues.get(key)
        raise TypeError(
            "list indices must be integers, strings or slices, not %s" % type(key).__name__
        )

    def __setitem__(self, key: Union[int, str], value: Union[int, float]) -> None:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return
        if isinstance(key, int) and self._owner.font:
            key = self._owner.font.axes[key].axisId
        self._owner._internalAxesValues[key] = value

    def values(self) -> List[Union[int, float]]:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return []
        if self._owner.font is None:
            return []
        return [self._owner._internalAxesValues.get(axis.axisId, 0) for axis in self._owner.font.axes]

    def __len__(self) -> int:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return 0
        if self._owner.font is None:
            return 0
        return len(self._owner.font.axes)

    def _setterMethod(self, values: List[Union[int, float]]) -> None:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return
        if self._owner.font is None:
            return
        for idx, axis in enumerate(self._owner.font.axes):
            self._owner._internalAxesValues[axis.axisId] = values[idx]

    def setterMethod(self) -> Any:
        return self._setterMethod


class ExternalAxesProxy(Proxy):
    def __getitem__(self, key: Union[int, str, slice]) -> Optional[Union[int, float, List[float]]]:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return None
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            if key < len(self._owner.font.axes):
                axis = self._owner.font.axes[key]
                return self._owner._externalAxesValues.get(axis.axisId)
            return None
        elif isinstance(key, str):
            return self._owner._externalAxesValues.get(key)
        raise TypeError(
            "list indices must be integers, strings or slices, not %s" % type(key).__name__
        )

    def __setitem__(self, key: Union[int, str], value: Union[int, float]) -> None:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return
        if isinstance(key, int):
            key = self._owner.font.axes[key].axisId
        self._owner._externalAxesValues[key] = value

    def values(self) -> List[Union[int, float]]:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return []
        if self._owner.font is None:
            return []
        return [self._owner._externalAxesValues.get(axis.axisId, 0) for axis in self._owner.font.axes]

    def __len__(self) -> int:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return 0
        if self._owner.font is None:
            return 0
        return self._owner.font.countOfAxes()

    def _setterMethod(self, values: List[Union[int, float]]) -> None:
        if isinstance(self._owner, GSInstance) and self._owner.type == InstanceType.VARIABLE:
            return
        if self._owner.font is None:
            return
        for idx, axis in enumerate(self._owner.font.axes):
            self._owner._externalAxesValues[axis.axisId] = values[idx]


def axisLocationToAxesValue(master_or_instances: GSFontMaster | GSInstance) -> None:
    axisLocations = master_or_instances.customParameters.get("Axis Location")
    if axisLocations is None:
        return
    if not master_or_instances.font:
        return
    for axis in master_or_instances.font.axes:
        locationDict = None
        for currLocation in axisLocations:
            if currLocation["Axis"] == axis.name:
                locationDict = currLocation
                break
        if locationDict is None:
            continue
        location = locationDict.get("Location")
        if location is not None:
            master_or_instances.externalAxesValues[axis.axisId] = location


def axisValueToAxisLocation(master_or_instance: GSFontMaster | GSInstance) -> None:
    if master_or_instance._externalAxesValues and master_or_instance.font:
        locations = [
            {"Axis": axis.name, "Location": master_or_instance.externalAxesValues.get(axis.axisId)}
            for axis in master_or_instance.font.axes
            if master_or_instance.externalAxesValues.get(axis.axisId) is not None
        ]
        if locations:
            master_or_instance.customParameters["Axis Location"] = locations


class MasterStemsProxy(Proxy):
    def __getitem__(self, key: str | int | slice) -> Union[int, float, List[float]]:
        if isinstance(key, slice):
            return [cast(float, self.__getitem__(i)) for i in range(*key.indices(self.__len__()))]
        stem = self._owner.font.stemForKey(key)
        if stem is None:
            raise KeyError(f"No stem for {key}")
        return self._owner._stems[stem.id]

    def __setitem__(self, key: str | int, value: Union[int, float]) -> None:
        stem = self._owner.font.stemForKey(key)
        if stem is None:
            name = key if isinstance(key, str) else f"stem{key}"
            stem = GSMetric()
            stem.name = name
            stem.horizontal = True
            self._owner.font.stems.append(stem)
        self._owner._stems[stem.id] = value

    def values(self) -> List[Optional[Union[int, float]]]:
        return [self._owner._stems.get(stem.id, None) for stem in self._owner.font.stems]

    def __len__(self) -> int:
        if self._owner.font is None:
            return 0
        return len(self._owner.font.stems)

    def _setterMethod(self, values: List[Union[int, float]]) -> None:
        if self._owner.font is None:
            return
        if self.__len__() != len(values):
            raise ValueError("Count of values doesn’t match stems")
        for idx, stem in enumerate(self._owner.font.stems):
            self._owner.stems[stem.id] = values[idx]

    def setterMethod(self) -> Any:
        return self._setterMethod


class MasterNumbersProxy(Proxy):
    def __getitem__(self, key: str | int | slice) -> Union[int, float, List[float]]:
        if isinstance(key, slice):
            return [cast(float, self.__getitem__(i)) for i in range(*key.indices(self.__len__()))]
        number = self._owner.font.numberForKey(key)
        if number is None:
            raise KeyError(f"No number for {key}")
        return self._owner._numbers[number.id]

    def __setitem__(self, key: str | int, value: Union[int, float]) -> None:
        if self._owner.font:
            number = self._owner.font.numberForKey(key)
            if number is None:
                name = key if isinstance(key, str) else f"number{key}"
                number = GSMetric()
                number.name = name
                number.horizontal = True
                self._owner.font.numbers.append(number)
            numberId = number.id
        elif isinstance(key, str):
            numberId = key
        else:
            raise KeyError
        self._owner._numbers[numberId] = value

    def values(self) -> List[Optional[Union[int, float]]]:
        return [self._owner._numbers.get(number.id, None) for number in self._owner.font.numbers]

    def __len__(self) -> int:
        if self._owner.font is None:
            return 0
        return len(self._owner.font.numbers)

    def _setterMethod(self, values: List[Union[int, float]]) -> None:
        if self._owner.font is None:
            return
        if self.__len__() != len(values):
            raise ValueError("Count of values doesn’t match numbers")
        for idx, number in enumerate(self._owner.font.numbers):
            self._owner.numbers[number.id] = values[idx]

    def setterMethod(self) -> Any:
        return self._setterMethod


class LayerShapesProxy(IndexedObjectsProxy):
    _objects_name: str = "_shapes"
    _filter: Optional[Any] = None

    def __init__(self, owner: GSLayer) -> None:
        super().__init__(owner)

    def append(self, value: GSShape) -> None:
        self._owner._shapes.append(value)
        value.parent = self._owner

    def extend(self, values: List[GSShape]) -> None:
        self._owner._shapes.extend(values)
        for value in values:
            value.parent = self._owner

    def remove(self, value: GSShape) -> None:
        self._owner._shapes.remove(value)

    def insert(self, index: int, value: GSShape) -> None:
        self._owner._shapes.insert(index, value)
        value.parent = self._owner

    def __setitem__(self, key: int, value: GSShape) -> None:
        if isinstance(key, int):
            index = self._owner._shapes.index(self.values()[key])
            self._owner._shapes[index] = value
            value.parent = self._owner
        else:
            raise KeyError

    def __delitem__(self, key: int) -> None:
        if isinstance(key, int):
            index = self._owner._shapes.index(self.values()[key])
            del self._owner._shapes[index]
        else:
            raise KeyError

    def setter(self, values: List[GSShape]) -> None:
        if self._filter:
            new_values: List = list(
                filter(lambda s: not isinstance(s, self._filter), self._owner._shapes)  # type: ignore # TODO: (gs) Check
            )
        else:
            new_values = []
        new_values.extend(list(values))
        self._owner._shapes = new_values
        for value in new_values:
            value.parent = self._owner

    def values(self) -> List[GSShape]:
        if self._filter:
            return list(
                filter(lambda s: isinstance(s, self._filter), self._owner._shapes)  # type: ignore # TODO: (gs) Check
            )
        else:
            return self._owner._shapes[:]


class LayerHintsProxy(IndexedObjectsProxy):
    _objects_name: str = "_hints"

    def __init__(self, owner: GSLayer) -> None:
        super().__init__(owner)


class LayerAnnotationProxy(IndexedObjectsProxy):
    _objects_name: str = "_annotations"

    def __init__(self, owner: GSLayer) -> None:
        super().__init__(owner)


class LayerGuideLinesProxy(IndexedObjectsProxy):
    _objects_name: str = "_guides"

    def __init__(self, owner: GSLayer) -> None:
        super().__init__(owner)


class PathNodesProxy(IndexedObjectsProxy):
    _objects_name: str = "_nodes"

    def __init__(self, owner: GSPath) -> None:
        super().__init__(owner)


class CustomParametersProxy(ListDictionaryProxy):
    def __init__(self, owner: Union[GSFont, GSFontMaster, GSInstance]) -> None:
        super().__init__(owner, "_customParameters", GSCustomParameter)
        self._update_lookup()

    def __getitem__(self, key: Union[int, str, slice]) -> Any:
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            return self.values()[key]
        elif isinstance(key, str):
            return self._lookup.get(key)
        raise TypeError(f"key must be integer or string, not {type(key).__name__}")

    def __setitem__(self, key: Union[int, str], value: Any) -> None:
        super().__setitem__(key, value)
        self._update_lookup()

    def setter(self, params: List[GSCustomParameter]) -> None:
        super().setter(params)
        self._update_lookup()

    def __iter__(self) -> Iterator[GSCustomParameter]:
        yield from super().__iter__()

    def keys(self) -> List[str]:
        return [parameter.name for parameter in self]

    def _get_by_name(self, name: str) -> Optional[GSCustomParameter]:
        if name == "Name Table Entry":
            return None
        return super()._get_by_name(name)

    def is_font(self) -> bool:
        """Returns whether we are looking at a top-level GSFont object as
        opposed to a master or instance.
        This is a stupid hack to make the globally registered parameter handler work
        """
        return isinstance(self._owner, GSFont)

    def _update_lookup(self) -> None:
        self._lookup: Dict[str, Any] = {}
        for param in self:
            params = self._lookup.get(param.name, None)
            if params is None:
                self._lookup[param.name] = param.value  # the first wins


class PropertiesProxy(ListDictionaryProxy):
    def __init__(self, owner: Any) -> None:
        assert owner
        super().__init__(owner, "_properties", GSFontInfoValue)

    def __getitem__(self, key: Union[int, str, slice]) -> Any:
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            return self.values()[key]
        elif isinstance(key, str):
            return self.getProperty(key, language="dflt") or self.getProperty(key, language="ENG")
        raise TypeError(f"key must be integer or string, not {type(key).__name__}")

    def __setitem__(self, key: str, value: Any) -> None:  # type: ignore
        infoValue = self[key]
        if infoValue is None or not isinstance(infoValue, GSFontInfoValue):
            infoValue = GSFontInfoValue(key)
            infoValue.parent = self._owner
            self._owner._properties.append(infoValue)
        if key.endswith("s"):
            if isinstance(value, dict):
                infoValue.values = value
            else:
                infoValue.defaultValue = value
        else:
            infoValue.value = value

    def getProperty(self, key: str, language: str = "dflt") -> Any:
        for infoValue in self:
            if infoValue.name != key:
                continue
            if key.endswith("s"):
                return infoValue.localizedValue(language)
            else:
                return infoValue.value

    def setProperty(self, key: str, value: Any, language: str = "dflt") -> None:
        for infoValue in self:
            if infoValue.name != key:
                continue
            infoValue.parent = self._owner
            infoValue.setLocalizedValue(value, language)
            return
        infoValue = GSFontInfoValue(key)
        if key.endswith("s"):
            infoValue.setLocalizedValue(value, language)
        else:
            infoValue.value = value
        infoValue.parent = self._owner
        self._owner._properties.append(infoValue)


class UserDataProxy(Proxy):
    def __getitem__(self, key: str) -> Optional[Any]:
        if self._owner._userData is None:
            return None
        # This is not the normal `dict` behaviour, because this does not raise
        # `KeyError` and instead just returns `None`. It matches Glyphs.app.
        return self._owner._userData.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if self._owner._userData is not None:
            self._owner._userData[key] = value
        else:
            self._owner._userData = {key: value}

    def __delitem__(self, key: str) -> None:
        if self._owner._userData is not None and key in self._owner._userData:
            del self._owner._userData[key]

    def __contains__(self, item: str) -> bool:
        if self._owner._userData is None:
            return False
        return item in self._owner._userData

    def __iter__(self) -> Iterator[Any]:
        if self._owner._userData is None:
            return
        # This is not the normal `dict` behaviour, because this yields values
        # instead of keys. It matches Glyphs.app though. Urg.
        yield from self._owner._userData.values()

    def __repr__(self) -> str:
        strings = []
        if self._owner._userData is not None:
            for key, item in self._owner._userData.items():
                strings.append(f"{key}:{item}")
        return f"({', '.join(strings)})"

    def values(self) -> List[Any]:
        if self._owner._userData is None:
            return []
        return self._owner._userData.values()

    def keys(self) -> List[str]:
        if self._owner._userData is None:
            return []
        return self._owner._userData.keys()

    def items(self) -> List[Tuple[str, Any]]:
        if self._owner._userData is None:
            return []
        return self._owner._userData.items()

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if self._owner._userData is None:
            return None
        return self._owner._userData.get(key, default)

    def setter(self, values: Dict[str, Any]) -> None:
        self._owner._userData = values

    def __copy__(self) -> Optional[Dict[str, Any]]:  # type: ignore
        return copy.copy(self._owner._userData)  # type: ignore

    def __deepcopy__(self, memo: Dict[int, Any]) -> Optional[Dict[str, Any]]:  # type: ignore
        return copy.deepcopy(self._owner._userData)  # type: ignore


class GSAxis(GSBase):
    __slots__ = ("name", "axisTag", "axisId", "hidden")

    def _serialize_to_plist(self, writer: Writer) -> None:
        writer.writeObjectKeyValue(self, "hidden", "if_true")
        writer.writeObjectKeyValue(self, "name", True)
        writer.writeKeyValue("tag", self.axisTag)

    def __init__(self, name: str = "", tag: str = "", hidden: bool = False) -> None:
        self.name: str = name
        self.axisTag: str = tag
        self.axisId: str = "%X" % id(self)
        self.hidden: bool = hidden

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {hex(id(self))}> {self.name}: {self.axisTag}"

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}: {self.axisTag}>"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GSAxis) and self.name == other.name and self.axisTag == other.axisTag

    _shortAxisTagMapping: Dict[str, str] = {
        "ital": "it",
        "opsz": "oz",
        "slnt": "sl",
        "wdth": "wd",
        "wght": "wg",
    }

    @property
    def shortAxisTag(self) -> str:
        return self._shortAxisTagMapping.get(self.axisTag, self.axisTag)


GSAxis._add_parsers(
    [
        {"plist_name": "tag", "object_name": "axisTag"},
        {"plist_name": "hidden", "converter": bool},
    ]
)


class GSCustomParameter(GSBase):
    def _serialize_to_plist(self, writer: Writer) -> None:
        if writer.formatVersion >= 3 and not self.active:
            writer.writeKeyValue("disabled", True)
        writer.writeKeyValue("name", self.name)
        if self.name == "Color Palettes":
            if writer.formatVersion >= 3:
                writer.allowTuple = True
                writer.writeKeyValue("value", self.value)
                writer.allowTuple = False
            else:
                palettes: List[List[str]] = []
                for palette in self.value:
                    colorStrings: List[str] = []
                    for color in palette:
                        colorStrings.append(",".join(str(v) for v in color))
                    palettes.append(colorStrings)
                writer.writeKeyValue("value", palettes)
        elif self.name in self._CUSTOM_COLOR_PARAMS:
            writer.writeKey("value")
            writer.writeValue(self.value, forKey="color")
            writer.file.write(";\n")
        else:
            writer.writeKeyValue("value", self.value)

    _CUSTOM_INT_PARAMS = frozenset(
        (
            "ascender",
            "blueShift",
            "capHeight",
            "descender",
            "hheaAscender",
            "hheaDescender",
            "hheaLineGap",
            "subscriptXSize",
            "subscriptYSize",
            "subscriptXOffset",
            "subscriptYOffset",
            "superscriptXSize",
            "superscriptYSize",
            "superscriptXOffset",
            "superscriptYOffset",
            "macintoshFONDFamilyID",
            "openTypeHeadLowestRecPPEM",
            "openTypeHheaAscender",
            "openTypeHheaCaretOffset",
            "openTypeHheaCaretSlopeRise",
            "openTypeHheaCaretSlopeRun",
            "openTypeHheaDescender",
            "openTypeHheaLineGap",
            "openTypeOS2StrikeoutPosition",
            "openTypeOS2StrikeoutSize",
            "openTypeOS2SubscriptXOffset",
            "openTypeOS2SubscriptXSize",
            "openTypeOS2SubscriptYOffset",
            "openTypeOS2SubscriptYSize",
            "openTypeOS2SuperscriptXOffset",
            "openTypeOS2SuperscriptXSize",
            "openTypeOS2SuperscriptYOffset",
            "openTypeOS2SuperscriptYSize",
            "openTypeOS2TypoAscender",
            "openTypeOS2TypoDescender",
            "openTypeOS2TypoLineGap",
            "openTypeOS2WeightClass",
            "openTypeOS2WidthClass",
            "openTypeOS2WinAscent",
            "openTypeOS2WinDescent",
            "openTypeVheaCaretOffset",
            "openTypeVheaCaretSlopeRise",
            "openTypeVheaCaretSlopeRun",
            "openTypeVheaVertTypoAscender",
            "openTypeVheaVertTypoDescender",
            "openTypeVheaVertTypoLineGap",
            "postscriptBlueFuzz",
            "postscriptBlueShift",
            "postscriptDefaultWidthX",
            "postscriptUnderlinePosition",
            "postscriptUnderlineThickness",
            "postscriptUniqueID",
            "postscriptWindowsCharacterSet",
            "shoulderHeight",
            "smallCapHeight",
            "typoAscender",
            "typoDescender",
            "typoLineGap",
            "underlinePosition",
            "underlineThickness",
            "strikeoutSize",
            "strikeoutPosition",
            "unitsPerEm",
            "vheaVertAscender",
            "vheaVertDescender",
            "vheaVertLineGap",
            "weightClass",
            "widthClass",
            "winAscent",
            "winDescent",
            "year",
            "Grid Spacing",
        )
    )

    _CUSTOM_FLOAT_PARAMS = frozenset(("postscriptSlantAngle", "postscriptBlueScale"))

    _CUSTOM_BOOL_PARAMS = frozenset(
        (
            "isFixedPitch",
            "postscriptForceBold",
            "postscriptIsFixedPitch",
            "Don\u2019t use Production Names",
            "DisableAllAutomaticBehaviour",
            "Use Typo Metrics",
            "Has WWS Names",
            "Use Extension Kerning",
            "Disable Subroutines",
            "Don't use Production Names",
            "Disable Last Change",
        )
    )

    _CUSTOM_INTLIST_PARAMS = frozenset(
        (
            "fsType",
            "openTypeOS2FamilyClass",
            "openTypeOS2Panose",
            "openTypeOS2Type",
            "openTypeOS2UnicodeRanges",
            "panose",
            "unicodeRanges",
            "openTypeHeadFlags",
            # "Color Palettes",
        )
    )

    _CUSTOM_COLOR_PARAMS = frozenset(
        (
            "Master Color",
            "Master Color Dark",
            "Master Stroke Color",
            "Master Stroke Color Dark",
            "Master Background Color",
            "Master Background Color Dark",
            "Instance Color",
            "Instance Color Dark",
        )
    )

    _CUSTOM_DICT_PARAMS = frozenset("GASP Table")

    def __init__(self, name: str = "New Value", value: Any = "New Parameter", active: bool = True) -> None:
        self.name: str = name
        self._value: Any = value
        self.active: bool = active

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {hex(id(self))}> {self.name}: {self._value}"

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}: {self._value}>"

    def plistValue(self, formatVersion: int = 2) -> str:
        string = StringIO()
        writer = Writer(string, formatVersion=formatVersion)
        self._serialize_to_plist(writer)
        return "{\n" + string.getvalue() + "}"

    def post_read(self, formatVersion: int) -> None:  # GSCustomParameter
        if self.name == "Color Palettes" and formatVersion < 3:
            palettes: List[List[List[int]]] = []
            for palette in self.value:
                colors: List[List[int]] = []
                for color in palette:
                    colors.append([int(v) for v in color.split(',')])
                palettes.append(colors)
            self.value = palettes

    def getValue(self) -> Any:
        return self._value

    def setValue(self, value: Any) -> None:
        """Cast some known data in custom parameters."""
        if self.name in self._CUSTOM_INT_PARAMS:
            value = int(value)
        elif self.name in self._CUSTOM_FLOAT_PARAMS:
            value = float(value)
        elif self.name in self._CUSTOM_BOOL_PARAMS:
            value = bool(value)
        elif self.name in self._CUSTOM_INTLIST_PARAMS:
            value = readIntList(value)
        elif self.name in self._CUSTOM_DICT_PARAMS:
            parser = Parser()
            value = parser.parse(value)
        elif self.name == "note":
            value = str(value)
        elif self.name == "Axis Mappings":
            newValue: Dict[str, Dict[float, float]] = {}
            for axisTag, mapping in value.items():
                # make sure the mapping keys are all numbers, not str
                newMapping: Dict[float, float] = {}
                for input, output in mapping.items():
                    if not isinstance(input, (int, float)):
                        input = float(input)
                    if not isinstance(output, (int, float)):
                        output = float(output)
                    newMapping[input] = output
                newValue[axisTag] = newMapping
            value = newValue
        self._value = value

    value = property(getValue, setValue)


GSCustomParameter._add_parsers(
    [
        {"plist_name": "disabled", "object_name": "active", "converter": NegateBool},
    ]
)


class GSMetric(GSBase):
    def __init__(self, name: Optional[str] = None, type: Optional[str] = None) -> None:
        self.name: Optional[str] = name
        self.type: Optional[str] = type
        self.id: str = str(uuid.uuid4()).upper()
        self.filter: Optional[str] = None
        self.horizontal: bool = False

    def _serialize_to_plist(self, writer: Writer) -> None:
        writer.writeObjectKeyValue(self, "horizontal", "if_true")
        writer.writeObjectKeyValue(self, "filter", "if_true")
        writer.writeObjectKeyValue(self, "name", "if_true")
        if self.type:
            writer.writeKeyValue("type", self.type)

    def __repr__(self) -> str:
        string = f"<{self.__class__.__name__} {hex(id(self))}> {self.type}"
        if self.filter:
            string += " " + self.filter
        if self.name:
            string += " " + self.name
        return string

    def __str__(self) -> str:
        string = f"<{self.__class__.__name__} {self.type}"
        if self.filter:
            string += self.filter
        string += ">"
        return string


GSMetric._add_parsers(
    [
        {"plist_name": "type"},
    ]
)


class GSMetricValue(GSBase):
    def __init__(self, position: float = 0, overshoot: float = 0) -> None:
        self.position: float = position
        self.overshoot: float = overshoot
        self.metric: Optional[GSMetric] = None

    def _serialize_to_plist(self, writer: Writer) -> None:
        if self.overshoot:
            writer.writeKeyValue("over", self.overshoot)
        if self.position:
            writer.writeKeyValue("pos", self.position)

    def __repr__(self) -> str:
        return "<{} {}> {}: {}/{}".format(
            self.__class__.__name__,
            hex(id(self)),
            self.metric.type if self.metric else "-",
            self.position,
            self.overshoot,
        )

    def __str__(self) -> str:
        return "<{} {}: {}/{}>".format(
            self.__class__.__name__,
            self.metric.type if self.metric else "-",
            self.position,
            self.overshoot,
        )


GSMetricValue._add_parsers(
    [
        {"plist_name": "over", "object_name": "overshoot"},
        {"plist_name": "pos", "object_name": "position"},
    ]
)


class GSAlignmentZone(GSBase):
    def __init__(self, pos: float = 0, size: float = 20) -> None:
        self.position: float = pos
        self.size: float = size

    def read(self, src: Optional[Any]) -> GSAlignmentZone:
        if src is not None:
            p = Point(src)
            self.position = parse_float_or_int(p.value[0])
            self.size = parse_float_or_int(p.value[1])
        return self

    def __repr__(self) -> str:
        return "<{} {}> pos:{} size:{}".format(
            self.__class__.__name__, hex(id(self)), self.position, self.size
        )

    def __str__(self) -> str:
        return "<{} pos:{} size:{}>".format(
            self.__class__.__name__, self.position, self.size
        )

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, GSAlignmentZone):
            return NotImplemented
        return (self.position, self.size) < (other.position, other.size)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, GSAlignmentZone):
            return NotImplemented
        return (self.position, self.size) == (other.position, other.size)

    def plistValue(self, formatVersion: int = 2) -> str:
        return '"{{{}, {}}}"'.format(
            floatToString5(self.position), floatToString5(self.size)
        )


class GSGuide(GSBase):
    _parent: Optional[Union[GSLayer, GSFontMaster]] = None
    _defaultsForName: Dict[str, Any] = {"position": Point(0, 0), "angle": 0}
    __slots__ = ("alignment", "angle", "filter", "locked", "name", "position", "showMeasurement", "lockAngle", "_userData", "orientation")

    def __init__(self) -> None:
        self.alignment: str = ""
        self.angle: float = 0
        self.filter: str = ""
        self.locked: bool = False
        self.name: str = ""
        self.position: Point = Point(0, 0)
        self.showMeasurement: bool = False
        self.lockAngle: bool = False
        self._userData: Optional[Dict[str, Any]] = None
        self.orientation: Optional[str] = None

    def _serialize_to_plist(self, writer: Writer) -> None:
        for field in ["alignment", "angle", "filter"]:
            writer.writeObjectKeyValue(self, field, "if_true")
        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(self, "lockAngle", "if_true")
        writer.writeObjectKeyValue(self, "locked", "if_true")

        writer.writeObjectKeyValue(self, "name", "if_true")
        if self.orientation and self.orientation != "left":
            writer.writeKeyValue("orientation", self.orientation)
        if writer.formatVersion >= 3 and self.position != Point(0, 0):
            writer.writeKeyValue("pos", self.position)
        else:
            writer.writeObjectKeyValue(self, "position", self.position != Point(0, 0))
        writer.writeObjectKeyValue(self, "showMeasurement", "if_true")
        if writer.formatVersion >= 3 and len(self.userData) > 0:
            writer.writeKeyValue("userData", self.userData)

    def __repr__(self) -> str:
        return "<{} {}> x={:.1f} y={:.1f} angle={:.1f}".format(
            self.__class__.__name__, hex(id(self)), self.position.x, self.position.y, self.angle
        )

    def __str__(self) -> str:
        return "<{} x={:.1f} y={:.1f} angle={:.1f}>".format(
            self.__class__.__name__, self.position.x, self.position.y, self.angle
        )

    @property
    def parent(self) -> Optional[GSLayer | GSFontMaster]:
        return self._parent

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )


GSGuide._add_parsers(
    [
        {"plist_name": "position", "converter": Point},  # v2
        {"plist_name": "pos", "object_name": "position", "converter": Point},  # v3
        {"plist_name": "userData", "object_name": "_userData", "type": dict},  # v3
        {"plist_name": "orientation"},  # v3
    ]
)


MASTER_NAME_WEIGHTS = ("Light", "SemiLight", "SemiBold", "Bold")
MASTER_NAME_WIDTHS = ("Condensed", "SemiCondensed", "Extended", "SemiExtended")
MASTER_AXIS_VALUE_KEYS = (
    "weightValue",
    "widthValue",
    "customValue",
    "customValue1",
    "customValue2",
    "customValue3",
)
MASTER_ICON_NAMES = {
    "Light_Condensed",
    "Light_SemiCondensed",
    "Light",
    "Light_SemiExtended",
    "Light_Extended",
    "SemiLight_Condensed",
    "SemiLight_SemiCondensed",
    "SemiLight",
    "SemiLight_SemiExtended",
    "SemiLight_Extended",
    "Condensed",
    "SemiCondensed",
    "Regular",
    "SemiExtended",
    "Extended",
    "SemiBold_Condensed",
    "SemiBold_SemiCondensed",
    "SemiBold",
    "SemiBold_SemiExtended",
    "SemiBold_Extended",
    "Bold_Condensed",
    "Bold_SemiCondensed",
    "Bold",
    "Bold_SemiExtended",
    "Bold_Extended",
}


class GSFontMaster(GSBase):
    _font: Optional[GSFont] = None

    def __init__(self, name: str = "Regular") -> None:
        self.customParameters = []
        self.name: str = name
        self._userData: Optional[dict] = None
        self._horizontalStems: Optional[List[float]] = None
        self._verticalStems: Optional[List[float]] = None
        self._internalAxesValues: Dict[str, float] = {}
        self._externalAxesValues: Dict[str, float] = {}
        self._metricValues: Dict[str, GSMetricValue] = {}
        self.guides: List[GSGuide] = []
        self.iconName: str = ""
        self.id: str = str(uuid.uuid4()).upper()
        self._numbers: Dict[str, float] = {}
        self._stems: Dict[str, float] = {}
        self.visible: bool = False
        self.weight: Optional[str] = None
        self.width: Optional[str] = None
        self.customName: Optional[str] = None
        self.readBuffer: Dict[str, Any] = {}
        self._axesValues: Optional[List[float]] = None
        self._alignmentZones: Optional[List[Any]] = None

    def _write_axis_value(self, writer: Writer, idx: int, defaultValue: float) -> None:
        axes = self.font.axes
        axesCount: int = len(axes)
        if axesCount > idx:
            value: float = self.internalAxesValues[axes[idx].axisId]
            if value is not None and abs(value - defaultValue) > 0.0001:
                writer.writeKeyValue(MASTER_AXIS_VALUE_KEYS[idx], value)

    def _default_icon_name(self) -> str:
        name_parts: List[str] = self.name.split(" ")
        if len(name_parts) > 1:
            try:
                name_parts.remove("Regular")
            except ValueError:
                pass
            try:
                name_parts.remove("Italic")
            except ValueError:
                pass
        iconName: str = "_".join(name_parts)
        if len(iconName) == 0 or iconName not in MASTER_ICON_NAMES:
            iconName = "Regular"
        return iconName

    def _serialize_to_plist(self, writer: Writer) -> None:  # noqa: C901
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "alignmentZones", "if_true")
            writer.writeObjectKeyValue(self, "ascender")
        if writer.formatVersion >= 3 and len(self.internalAxesValues):
            writer.writeKeyValue("axesValues", self.internalAxesValues)
        customParameters: List[Any] = list(self.customParameters)

        if writer.formatVersion == 2:
            weightName, widthName, customName = self._splitName(self.name)
            writer.writeObjectKeyValue(self, "capHeight")
            if customName:
                writer.writeKeyValue("custom", customName)

            for idx in range(2, 6):
                self._write_axis_value(writer, idx, 0)

            smallCapMetric = self._get_metric_position(
                GSMetricsKeyxHeight, filter="case == 3"
            )

            if smallCapMetric:
                parameter = GSCustomParameter("smallCapHeight", smallCapMetric)
                customParameters.append(parameter)

        if writer.formatVersion <= 3:
            axisValueToAxisLocation(self)

        if customParameters:
            writer.writeKeyValue("customParameters", customParameters)

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "descender")

        if self.guides:
            if writer.formatVersion >= 3:
                writer.writeKeyValue("guides", self.guides)
            else:
                writer.writeKeyValue("guideLines", self.guides)

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "horizontalStems", "if_true")

        if (
            len(self.iconName) > 0
            and (
                self.iconName != self._default_icon_name() or writer.formatVersion == 3
            )
            and self.iconName != "Regular"
        ):  # TODO: Glyphs <= 3.1 had a bug that it would not compute the defaultIconName correctly for v3 files.
            writer.writeKeyValue("iconName", self.iconName)

        writer.writeObjectKeyValue(self, "id")

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "italicAngle", "if_true")

        if writer.formatVersion >= 3:
            metricValues: List[Any] = []
            for metric in self.font.metrics:
                metricValue: GSMetricValue = self.metricValues.get(metric.id, GSMetricValue())
                metricValues.append(metricValue)
            writer.writeKeyValue("metricValues", metricValues)

        if writer.formatVersion > 2:
            writer.writeKeyValue("name", self.name)

        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(
                self, "numbers", "if_true", keyName="numberValues"
            )
            writer.writeObjectKeyValue(self, "stems", "if_true", keyName="stemValues")

        if True:
            userData: Dict[str, Any] = dict(self.userData)
            if "com.github.googlei18n.ufo2ft.filters" in userData:
                del userData["com.github.googlei18n.ufo2ft.filters"]
            if len(userData) > 0:
                writer.writeKeyValue("userData", userData)
        else:
            writer.writeObjectKeyValue(self, "userData", "if_true")

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "verticalStems", "if_true")

        writer.writeObjectKeyValue(self, "visible", "if_true")

        if writer.formatVersion == 2:
            if weightName and len(weightName) > 0 and weightName != "Regular":
                writer.writeKeyValue("weight", weightName)

            self._write_axis_value(writer, 0, 100)

            if widthName and len(widthName) > 0:
                writer.writeKeyValue("width", widthName)

            self._write_axis_value(writer, 1, 100)

            writer.writeObjectKeyValue(self, "xHeight")

    _defaultsForName = {
        # FIXME: (jany) In the latest Glyphs (1113), masters don't have a width
        # and weight anymore as attributes, even though those properties are
        # still written to the saved files.
        "name": "Regular",
        # "weight": "Regular",
        # "width": "Regular",
        "x-height": 500,
        "cap height": 700,
        "ascender": 800,
        "descender": -200,
        "italic angle": 0,
        "weightValue": 100,
        "widthValue": 100,
    }

    _axis_defaults = (100, 100)

    def _parse_alignmentZones_dict(self, parser: Parser, text: str):
        """
        For glyphs file format 2 this parses the alignmentZone parameter directly.
        """
        _zones = parser._parse(text, str)
        self._alignmentZones = [GSAlignmentZone().read(x) for x in _zones]

    def __repr__(self) -> str:
        return '<GSFontMaster {}> "{}" {}'.format(
            hex(id(self)), self.name, self.internalAxesValues.values()
        )

    def __str__(self) -> str:
        return '<GSFontMaster "{}" {}>'.format(
            self.name, self.internalAxesValues.values()
        )

    def _import_stem_list(self, stems: List[float], horizontal: bool) -> None:
        if self._stems is None:
            self._stems = {}
        font = self.font
        for idx in range(len(stems)):
            name: str = "%sStem%d" % ("h" if horizontal else "v", idx)
            metric: Optional[GSMetric] = font.stemForName(name)
            if not metric:
                metric = GSMetric()
                metric.name = name
                metric.horizontal = horizontal
                font.stems.append(metric)
            self._stems[metric.id] = stems[idx]

    # GSFontMaster
    def post_read(self) -> None:  # noqa: C901
        font = self.font
        axes: List[Any] = font.axes
        axesCount: int = len(axes)
        if font.formatVersion < 3:
            axesValues2: Dict[int, float] = self.readBuffer.get("axesValues", {})
            for idx in range(axesCount):
                axis = axes[idx]
                if axis.axisId in self._internalAxesValues:  # (gs) e.g. when loading from designspace, this is properly set already
                    continue
                value: float = axesValues2.get(idx, DefaultAxisValuesV2[idx])
                self.internalAxesValues[axis.axisId] = value
            if axes and len(self._internalAxesValues) == 0:
                axisId: str = axes[0].axisId
                self._internalAxesValues[axisId] = 100
        else:
            axesValues3: Optional[List[float]] = self._axesValues
            if axesValues3:
                for idx in range(axesCount):
                    axis = axes[idx]
                    if idx < len(axesValues3):
                        value = axesValues3[idx]
                    else:
                        # (georg) fallback for old designspace setup
                        value = 100 if idx < 2 else 0
                    self.internalAxesValues[axis.axisId] = value

        if isinstance(self._metricValues, list):
            metricValues: List[Any] = list(self._metricValues)
            self._metricValues = {}
            if metricValues:
                for fontMetric, metricValue in zip(self.font.metrics, metricValues):
                    # TODO: use better accessor
                    self._metricValues[fontMetric.id] = metricValue
                    metricValue.metric = fontMetric
        else:
            for metricKey in (
                GSMetricsKeyAscender,
                GSMetricsKeyCapHeight,
                GSMetricsKeyxHeight,
                GSMetricsKeyBaseline,
                GSMetricsKeyDescender,
            ):
                position, overshoot = self.readBuffer.get(metricKey, (0, 0))
                self._set_metric(metricKey, position, overshoot)

            parameter: Optional[Any] = self.customParameters["smallCapHeight"]
            if parameter:
                xHeightMetricValue: GSMetricValue = self._get_metric(GSMetricsKeyxHeight) or GSMetricValue()
                filterString: str = "case == 3"
                self._set_metric(
                    GSMetricsKeyxHeight,
                    parameter,
                    xHeightMetricValue.overshoot,
                    filter=filterString,
                )
                del self.customParameters["smallCapHeight"]
                metric: Optional[GSMetric] = font.metricFor(GSMetricsKeyItalicAngle)
                if metric:
                    font.metrics.remove(metric)
                    font.metrics.append(metric)

            if self._alignmentZones:
                self._import_alignmentZones_to_metrics()

            position, overshoot = self.readBuffer.get(GSMetricsKeyItalicAngle, (0, 0))
            self._set_metric(GSMetricsKeyItalicAngle, position, overshoot)

        if self._stems:
            assert len(font.stems) == len(self._stems)
            stems: Dict[str, float] = {}
            for idx, stem in enumerate(font.stems):
                stems[stem.id] = self._stems[idx]  # type: ignore
            self._stems = stems
        else:
            if self._horizontalStems:
                self._import_stem_list(self._horizontalStems, True)
            if self._verticalStems:
                self._import_stem_list(self._verticalStems, False)

        if self._numbers:
            assert len(font.numbers) == len(self._numbers)
            numbers: Dict[str, float] = {}
            for idx, number in enumerate(font.numbers):
                numbers[number.id] = self._numbers[idx]  # type: ignore
            self._numbers = numbers

        if font.formatVersion < 3 and (
            self.weight or self.width or self.customName
        ):
            self.name = self._joinNames(self.weight, self.width, self.customName)
            self.weight = None
            self.width = None
            self.customName = None
        if not self.name:
            self.name = self._defaultsForName["name"]
        axisLocationToAxesValue(self)
        for customParameter in self.customParameters:
            customParameter.post_read(font.formatVersion)

    @property
    def metricsSource(self) -> Optional["GSFontMaster"]:
        """Returns the source master to be used for glyph and kerning metrics.

        If linked metrics parameters are being used, the master is returned here,
        otherwise None."""

        font = self.font

        if self.customParameters["Link Metrics With First Master"]:
            return font.masters[0]
        source_master_id = self.customParameters["Link Metrics With Master"]

        # No custom parameters apply, go home
        if not source_master_id:
            return None

        # Try by master id
        source_master = font.masterForId(source_master_id)
        if source_master is not None:
            return source_master

        # Try by name
        for source_master in font.masters:
            if source_master.name == source_master_id:
                return source_master

        logger.warning(f"Source master for metrics not found: '{source_master_id}'")
        return self

    def _joinNames(self, width: Optional[str], weight: Optional[str], custom: Optional[str]) -> str:
        # Remove None and empty string
        names = list(filter(None, [width, weight, custom]))
        while len(names) > 1 and "Regular" in names:
            names.remove("Regular")
        return " ".join(names)

    def _splitName(self, value: Optional[str]) -> Tuple[str, str, str]:
        if value is None:
            value = ""
        weight = "Regular"
        width = ""
        custom = ""
        names = []
        previous_was_removed = False
        for name in value.split(" "):
            if name == "Regular":
                pass
            elif name in MASTER_NAME_WEIGHTS:
                if previous_was_removed:
                    # Get the double space in custom
                    names.append("")
                previous_was_removed = True
                weight = name
            elif name in MASTER_NAME_WIDTHS:
                if previous_was_removed:
                    # Get the double space in custom
                    names.append("")
                previous_was_removed = True
                width = name
            else:
                previous_was_removed = False
                names.append(name)
        custom = " ".join(names).strip()
        return weight, width, custom

    @property
    def font(self) -> GSFont:
        return cast(GSFont, self._font)

    @font.setter
    def font(self, value: Optional[GSFont]) -> None:
        self._font = value

    customParameters = property(
        lambda self: CustomParametersProxy(self),
        lambda self, value: CustomParametersProxy(self).setter(value),
    )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    def _get_metric_layer(
        self, metricType: str, layer: Optional["GSLayer"] = None
    ) -> Optional["GSMetricValue"]:
        for metric in self.font.metrics:
            if (
                metric.type == metricType
                and metric.filter
                and metric.filter.evaluateWithObject(layer.parent if layer else None)
            ):
                metricValue = self.metricValues[metric.id]
                return metricValue
        return self._get_metric(metricType)

    def _get_metric(
        self, metricType: str, filter: Optional[str] = None, name: Optional[str] = None
    ) -> Optional["GSMetricValue"]:
        metric = self.font.metricFor(metricType, name, filter)
        if metric:
            metricValue = self.metricValues.get(metric.id)
            if not metricValue:
                metricValue = GSMetricValue()
                self.metricValues[metric.id] = metricValue
            metricValue.metric = metric
            return metricValue
        if metricType == GSMetricsKeyBodyHeight:
            return self._get_metric(GSMetricsKeyAscender)
        return None

    def _get_metric_position(
        self, metricType: str, filter: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[float]:
        metricValue = self._get_metric(metricType, name, filter)
        if metricValue:
            return metricValue.position
        return None

    def _set_metric(
        self,
        metricType: str,
        position: float,
        overshoot: Optional[float] = None,
        name: Optional[str] = None,
        filter: Optional[str] = None,
    ) -> None:
        if not self.font:
            # we read that later in postRead
            self.readBuffer[metricType] = (position, overshoot)
            return
        metrics = self.font.metrics
        metric: Optional["GSMetric"] = None
        for currMetric in metrics:
            if (
                metricType == currMetric.type
                and name == currMetric.name
                and filter == currMetric.filter
                and (metricType != GSMetricsKeyUndefined or name is not None)
            ):
                metric = currMetric
                break
        if not metric:
            metric = GSMetric()
            metric.type = metricType
            metric.filter = filter
            metric.name = name
            self.font.metrics.append(metric)
        metricValue = self.metricValues.get(metric.id)
        if not metricValue:
            metricValue = GSMetricValue(position=position, overshoot=overshoot if overshoot is not None else 0)
            self.metricValues[metric.id] = metricValue
            metricValue.metric = metric
        else:
            if position is not None:
                metricValue.position = position
            if overshoot is not None:
                metricValue.overshoot = overshoot

    def _import_alignmentZones_to_metrics(self) -> None:
        if not self._alignmentZones:
            return
        for metricValue in self.metricValues.values():
            for zone in list(self._alignmentZones):
                if abs(zone.position - metricValue.position) <= 1:
                    end = zone.position + zone.size
                    metricValue.overshoot = end - metricValue.position
                    self._alignmentZones.remove(zone)
        if len(self._alignmentZones) > 0:
            zoneIdx = 1
            for zone in self._alignmentZones:
                zoneKey = "zone %d" % zoneIdx
                self._set_metric(
                    GSMetricsKeyUndefined, zone.position, zone.size, name=zoneKey
                )
                zoneIdx += 1
        self._alignmentZones = None

    @property
    def metricValues(self) -> Dict[str, "GSMetricValue"]:
        return self._metricValues

    @metricValues.setter
    def metricValues(self, metrics: Dict[str, "GSMetricValue"]) -> None:
        assert isinstance(metrics, dict)
        self._metricValues = metrics

    @property
    def alignmentZones(self) -> List["GSAlignmentZone"]:
        if not self.font or len(self.font.metrics) == 0:
            return []

        zones: List["GSAlignmentZone"] = []
        for fontMetric in self.font.metrics:
            if fontMetric.type == GSMetricsKeyItalicAngle or (
                fontMetric.filter and fontMetric.filter != "case == 3"
            ):
                continue
            metric = self.metricValues.get(fontMetric.id)
            if not metric or metric.overshoot is None or metric.overshoot == 0:
                continue
            zone = GSAlignmentZone(pos=metric.position, size=metric.overshoot)
            zones.append(zone)
        zones.sort()
        zones.reverse()
        return zones

    @alignmentZones.setter
    def alignmentZones(self, entries: Union[List[Tuple[float, float]], List["GSAlignmentZone"]]) -> None:
        if not isinstance(entries, (tuple, list)):
            raise TypeError(
                "alignmentZones expected as list, got %s (%s)"
                % (entries, type(entries))
            )
        zones: List[Union[Tuple[float, float], "GSAlignmentZone"]] = []
        for zone in entries:
            if not isinstance(zone, (tuple, GSAlignmentZone)):
                raise TypeError(
                    "alignmentZones values expected as tuples of (pos, size) "
                    "or GSAlignmentZone, got: %s (%s)" % (zone, type(zone))
                )
            if zone not in zones:
                zones.append(zone)
        self._alignmentZones = zones
        if self.font:
            self._import_alignmentZones_to_metrics()

    @property
    def blueValues(self) -> List[float]:
        """Get postscript blue values from Glyphs alignment zones."""
        font = self.font
        if len(font.metrics) == 0:
            return []

        blueValues: List[float] = []
        for fontMetric in font.metrics:
            # Ignore the "italic angle" "metric", it is not an alignmentZone
            if fontMetric.type == GSMetricsKeyItalicAngle or fontMetric.filter:
                continue
            metric = self.metricValues.get(fontMetric.id)
            # Ignore metric without overshoot, it is not an alignmentZone
            if not metric or metric.overshoot is None or (
                metric.overshoot <= 0 and metric.position != 0
            ):
                continue
            if metric.overshoot != 0:
                blueValues.append(metric.position)
                blueValues.append(metric.position + metric.overshoot)

        blueValues.sort()
        return blueValues

    @property
    def otherBlues(self) -> List[float]:
        """Get postscript blue values from Glyphs alignment zones."""
        font = self.font
        if len(font.metrics) == 0:
            return []

        otherBlues: List[float] = []
        for fontMetric in font.metrics:
            # Ignore the "italic angle" "metric", it is not an alignmentZone
            if fontMetric.type == GSMetricsKeyItalicAngle or fontMetric.filter:
                continue
            metric = self.metricValues.get(fontMetric.id)
            # Ignore metric without overshoot, it is not an alignmentZone
            if not metric or (
                metric.overshoot is None or metric.overshoot >= 0 or metric.position == 0
            ):
                continue
            otherBlues.append(metric.position)
            otherBlues.append(metric.position + metric.overshoot)

        otherBlues.sort()
        return otherBlues

    def _set_stem(
        self, name: str, size: float, horizontal: bool, filter: Optional[str] = None
    ) -> None:
        assert self.font
        stems = self.font.stems
        stem: Optional["GSMetric"] = None
        for currStem in stems:
            if (
                name == currStem.name
                and filter == currStem.filter
            ):
                stem = currStem
                break
        if not stem:
            stem = GSMetric()
            stem.name = name
            stem.horizontal = horizontal
            stem.filter = filter
            self.font.stems.append(stem)
        metricValue = GSMetricValue(position=size)
        metricValue.metric = stem
        self.metricValues[stem.id] = metricValue

    stems = property(
        lambda self: MasterStemsProxy(self),
        lambda self, value: MasterStemsProxy(self).setter(value),
    )

    # Legacy accessors
    @property
    def horizontalStems(self) -> List[GSMetricValue]:
        horizontalStems: List[GSMetricValue] = []
        for index, font_stem in enumerate(self.font.stems):
            if not font_stem.horizontal:
                continue
            horizontalStems.append(self.stems[index])
        return horizontalStems

    @horizontalStems.setter
    def horizontalStems(self, value: List[float]) -> None:
        assert isinstance(value, list)
        assert not value or isinstance(value[0], (float, int))
        if self.font:
            assert isinstance(value[0], (float, int))
            self._import_stem_list(value, True)
        else:
            self._horizontalStems = value

    @property
    def verticalStems(self) -> List[GSMetricValue]:
        verticalStems: List[GSMetricValue] = []
        for index, font_stem in enumerate(self.font.stems):
            if font_stem.horizontal:
                continue
            verticalStems.append(self.stems[index])
        return verticalStems

    @verticalStems.setter
    def verticalStems(self, value: List[float]) -> None:
        assert isinstance(value, list)
        assert not value or isinstance(value[0], (float, int))
        if self.font:
            self._import_stem_list(value, False)
        else:
            self._verticalStems = value

    numbers = property(
        lambda self: MasterNumbersProxy(self),
        lambda self, value: MasterNumbersProxy(self).setter(value),
    )

    @property
    def ascender(self) -> Optional[float]:
        return self._get_metric_position(GSMetricsKeyAscender)

    @ascender.setter
    def ascender(self, value: float) -> None:
        self._set_metric(GSMetricsKeyAscender, value)

    @property
    def xHeight(self) -> Optional[float]:
        return self._get_metric_position(GSMetricsKeyxHeight)

    @xHeight.setter
    def xHeight(self, value: float) -> None:
        self._set_metric(GSMetricsKeyxHeight, value)

    @property
    def capHeight(self) -> Optional[float]:
        return self._get_metric_position(GSMetricsKeyCapHeight)

    @capHeight.setter
    def capHeight(self, value: float) -> None:
        self._set_metric(GSMetricsKeyCapHeight, value)

    @property
    def descender(self) -> Optional[float]:
        return self._get_metric_position(GSMetricsKeyDescender)

    @descender.setter
    def descender(self, value: float) -> None:
        self._set_metric(GSMetricsKeyDescender, value)

    @property
    def italicAngle(self) -> float:
        value = self._get_metric_position(GSMetricsKeyItalicAngle)
        return value if value is not None else 0

    @italicAngle.setter
    def italicAngle(self, value: float) -> None:
        self._set_metric(GSMetricsKeyItalicAngle, value)

    internalAxesValues = property(
        lambda self: InternalAxesProxy(self),
        lambda self, value: InternalAxesProxy(self).setter(value),
    )

    externalAxesValues = property(
        lambda self: ExternalAxesProxy(self),
        lambda self, value: ExternalAxesProxy(self).setter(value),
    )

    # TODO: (gs) the following methods should be removed
    @property
    def weightValue(self) -> Optional[float]:
        return self.internalAxesValues[0] if len(self.font.axes) > 0 else None

    @weightValue.setter
    def weightValue(self, value: float) -> None:
        if self.font:
            axis = self.font.axes[0]
            if axis:
                self._internalAxesValues[axis.axisId] = value
        else:
            self.readBuffer.setdefault("axesValues", {})[0] = value

    @property
    def widthValue(self) -> Optional[float]:
        return self.internalAxesValues[1] if len(self.font.axes) > 1 else None

    @widthValue.setter
    def widthValue(self, value: float) -> None:
        if self.font:
            axis = self.font.axes[1]
            if axis:
                self._internalAxesValues[axis.axisId] = value
        else:
            self.readBuffer.setdefault("axesValues", {})[1] = value

    @property
    def customValue(self) -> Optional[float]:
        return self.internalAxesValues.get(2)

    @customValue.setter
    def customValue(self, value: float) -> None:
        if self.font:
            axis = self.font.axes[2]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[2] = value

    @property
    def customValue1(self) -> Optional[float]:
        return self.internalAxesValues.get(3)

    @customValue1.setter
    def customValue1(self, value: float) -> None:
        if self.font:
            axis = self.font.axes[3]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[3] = value

    @property
    def customValue2(self) -> Optional[float]:
        return self.internalAxesValues.get(4)

    @customValue2.setter
    def customValue2(self, value: float) -> None:
        if self.font:
            axis = self.font.axes[4]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[4] = value

    @property
    def customValue3(self) -> Optional[float]:
        return self.internalAxesValues.get(5)

    @customValue3.setter
    def customValue3(self, value: float) -> None:
        if self.font:
            axis = self.font.axes[5]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[5] = value


GSFontMaster._add_parsers(
    [
        {"plist_name": "customParameters", "type": GSCustomParameter},
        {"plist_name": "guideLines", "object_name": "guides", "type": GSGuide},  # v2
        {"plist_name": "guides", "object_name": "guides", "type": GSGuide},  # v3
        {"plist_name": "custom", "object_name": "customName"},
        {"plist_name": "axesValues", "object_name": "_axesValues"},  # v3
        {"plist_name": "numberValues", "object_name": "_numbers"},  # v3
        {"plist_name": "stemValues", "object_name": "_stems"},  # v3
        {
            "plist_name": "metricValues",
            "object_name": "_metricValues",
            "type": GSMetricValue,
        },  # v3
        # {"plist_name": "name", "object_name": "_name"},
    ]
)


class GSNode(GSBase):
    _PLIST_VALUE_RE = re.compile(
        r"([-.e\d]+) ([-.e\d]+) (LINE|CURVE|QCURVE|OFFCURVE|n/a)"
        r"(?: (SMOOTH))?(?: ({.*}))?",
        re.DOTALL,
    )

    __slots__ = ("_parent", "_userData", "_position", "smooth", "type", )

    _parent: Optional["GSPath"]

    def __init__(
        self,
        position: Point = Point(0, 0),
        type: str = LINE,
        smooth: bool = False,
        name: Optional[str] = None,
        nodetype: Optional[str] = None,
    ) -> None:
        self._position = Point(position[0], position[1])
        self._userData: Optional[Dict] = None
        self.smooth = smooth
        self.type = type
        if nodetype is not None:  # for backward compatibility
            self.type = nodetype
        # Optimization: Points can number in the 10000s, don't access the userDataProxy
        # through `name` unless needed.
        if name is not None:
            self.name = name

    def copy(self) -> "GSNode":
        """Clones the node (does not clone attributes)"""
        node = GSNode(
            position=self.position,
            type=self.type,
            smooth=self.smooth,
        )
        if self._userData:
            node._userData = copy.deepcopy(self._userData)
        return node

    def __repr__(self) -> str:
        content = self.type
        if self.smooth:
            content += " smooth"
        return "<{} {}> {:g} {:g} {}".format(
            self.__class__.__name__, hex(id(self)), self.position.x, self.position.y, content
        )

    def __str__(self) -> str:
        content = self.type
        if self.smooth:
            content += " smooth"
        return "<{} {:g} {:g} {}>".format(
            self.__class__.__name__, self.position.x, self.position.y, content
        )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def position(self) -> Point:
        return self._position

    @position.setter
    def position(self, value: Union[Tuple[float, float], Point]) -> None:
        if not isinstance(value, Point):
            value = Point(value[0], value[1])
        self._position = value

    @property
    def parent(self) -> Optional["GSPath"]:
        return self._parent

    _char_to_node_type = {
        "c": CURVE,
        "o": OFFCURVE,
        "l": LINE,
        "q": QCURVE
    }
    _node_type_to_char = {
        CURVE: "c",
        OFFCURVE: "o",
        LINE: "l",
        QCURVE: "q"
    }

    def plistValue(self, formatVersion: int = 2) -> str:
        string: Optional[StringIO] = None
        if self._userData is not None and len(self._userData) > 0:
            string = StringIO()
            writer = Writer(string, formatVersion=formatVersion)
            writer.writeDict(self._userData)

        if formatVersion == 2:
            content = self.type.upper()
            if self.smooth:
                content += " SMOOTH"
            if string:
                content += " "
                content += self._encode_dict_as_string(string.getvalue())
            return '"{} {} {}"'.format(
                floatToString5(self.position[0]),
                floatToString5(self.position[1]),
                content,
            )
        else:
            content = self._node_type_to_char.get(self.type, "x")
            if self.smooth:
                content += "s"
            if string:
                content += "," + string.getvalue()
            return "({},{},{})".format(
                floatToString5(self.position[0]),
                floatToString5(self.position[1]),
                content,
            )

    @classmethod
    def read(cls, line: str) -> "GSNode":
        """Parse a Glyphs node string into a GSNode.

        The format of a Glyphs node string (`line`) is:

            "X Y (LINE|CURVE|QCURVE|OFFCURVE)"
            "X Y (LINE|CURVE|QCURVE|OFFCURVE) SMOOTH"
            "X Y (LINE|CURVE|QCURVE|OFFCURVE) SMOOTH {dictionary}"
            "X Y (LINE|CURVE|QCURVE|OFFCURVE) {dictionary}"

        X and Y can be integers or floats, positive or negative.

        WARNING: This method is HOT. It is called for every single node and can
        account for a significant portion of the file parsing time.
        """
        match = cls._PLIST_VALUE_RE.match(line)
        if not match:
            return GSNode()
        m = match.groups()
        node = cls(
            position=(Point(parse_float_or_int(m[0]), parse_float_or_int(m[1]))),
            type=m[2].lower(),
            smooth=bool(m[3]),
        )
        if m[4] is not None and len(m[4]) > 0:
            value = cls._decode_dict_as_string(m[4])
            parser = Parser()
            node._userData = parser.parse(value)

        return node

    @classmethod
    def read_v3(cls, lst: List[Union[float, str, Dict]]) -> "GSNode":
        position = Point(lst[0], lst[1])
        string: str = cast(str, lst[2])
        smooth = string.endswith("s")
        node_type = cls._char_to_node_type.get(string[0], LINE)

        node = cls(position=position, type=node_type, smooth=smooth)
        if len(lst) > 3:
            node._userData = cast(dict, lst[3])
        return node

    @property
    def name(self) -> Optional[str]:
        return self.userData.get("name", None)

    @name.setter
    def name(self, value: Optional[str]) -> None:
        if value is None:
            # self.userData.pop("name", None)
            if "name" in self.userData:
                del self.userData["name"]
        else:
            self.userData["name"] = value

    @property
    def index(self) -> int:
        assert self.parent
        return self.parent.nodes.index(self)

    @property
    def nextNode(self) -> Optional["GSNode"]:
        assert self.parent
        index = self.index
        if index == (len(self.parent.nodes) - 1):
            return self.parent.nodes[0]
        elif index < len(self.parent.nodes):
            return self.parent.nodes[index + 1]
        return None

    @property
    def prevNode(self) -> Optional["GSNode"]:
        assert self.parent
        index = self.index
        if index == 0:
            return self.parent.nodes[-1]
        elif index < len(self.parent.nodes):
            return self.parent.nodes[index - 1]
        return None

    def makeNodeFirst(self) -> None:
        assert self.parent
        if self.type == OFFCURVE:
            raise ValueError("Off-curve points cannot become start points.")
        nodes = self.parent.nodes
        index = self.index
        newNodes = nodes[index:len(nodes)] + nodes[0:index]
        self.parent.nodes = newNodes

    def toggleConnection(self) -> None:
        self.smooth = not self.smooth

    # TODO
    @property
    def connection(self) -> None:
        raise NotImplementedError

    # TODO
    @property
    def selected(self) -> None:
        raise OnlyInGlyphsAppError

    @staticmethod
    def _encode_dict_as_string(value: str) -> str:
        """Takes the PLIST string of a dict, and returns the same string
        encoded such that it can be included in the string representation
        of a GSNode."""
        if value.startswith("{\n"):
            value = "{" + value[2:]
        if value.endswith("\n}"):
            value = value[:-2] + "}"
        return value.replace('"', '\\"').replace("\\n", "\\\\n").replace("\n", "\\n")

    _ESCAPED_CHAR_RE = re.compile(r'\\(\\*)(?:(n)|("))')

    @staticmethod
    def _unescape_char(m: re.Match) -> str:
        backslashes = m.group(1) or ""
        if m.group(2):
            return "\n" if not backslashes else backslashes + "n"
        else:
            return backslashes + '"'

    @classmethod
    def _decode_dict_as_string(cls, value: str) -> str:
        """Reverse function of _encode_string_as_dict"""
        # strip one level of backslashes preceding quotes and newlines
        return cls._ESCAPED_CHAR_RE.sub(cls._unescape_char, value)

    def _indices(self) -> Optional[IndexPath]:
        """Find the path_index and node_index that identify the given node."""
        path = self.parent
        if not path:
            return None
        layer = path.parent
        if not layer:
            return None
        for path_index, p in enumerate(layer.paths):
            if path == p:
                for node_index, n in enumerate(p.nodes):
                    if self == n:
                        return IndexPath(path_index, node_index)
        return None


class GSShape(GSBase):
    _parent: Optional[GSLayer] = None

    @property
    def parent(self) -> GSLayer:
        return cast(GSLayer, self._parent)

    @parent.setter
    def parent(self, value: Optional[GSLayer]) -> None:
        self._parent = value


class GSPath(GSShape):
    _defaultsForName: Dict[str, bool] = {"closed": True}
    __slots__ = ("closed", "_nodes", "_attributes", "_parent")

    def __init__(self) -> None:
        self.closed: bool = self._defaultsForName["closed"]
        self._nodes: List["GSNode"] = []
        self._attributes: Dict = {}

    def _serialize_to_plist(self, writer: Writer) -> None:
        if writer.formatVersion >= 3 and self.attributes:
            writer.allowTuple = True
            writer.writeObjectKeyValue(self, "attributes", keyName="attr")
            writer.allowTuple = False
        writer.writeObjectKeyValue(self, "closed")
        writer.writeObjectKeyValue(self, "nodes", "if_true")

    def _parse_nodes_dict(self, parser: Parser, d: List[Union[str, List]]) -> None:
        if parser.formatVersion >= 3:
            read_node: Any = GSNode.read_v3
        else:
            read_node = GSNode.read
        for x in d:
            node = read_node(x)
            node._parent = self
            self._nodes.append(node)

    def copy(self) -> "GSPath":
        """Clones the path (Does not clone attributes)"""
        cloned = GSPath()
        cloned.closed = self.closed
        cloned.nodes = [node.copy() for node in self.nodes]
        return cloned

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {hex(id(self))}> nodes:{len(self.nodes)}"

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} nodes:{len(self.nodes)}>"

    @property
    def parent(self) -> "GSLayer":
        return cast(GSLayer, self._parent)

    @parent.setter
    def parent(self, value: Optional["GSLayer"]) -> None:
        self._parent = value

    nodes = property(
        lambda self: PathNodesProxy(self),
        lambda self, value: PathNodesProxy(self).setter(value),
    )

    @property
    def segments(self) -> List["GSPathSegment"]:
        self._segments: List["GSPathSegment"] = []
        self._segmentLength: int = 0

        nodes = list(self.nodes)
        cycled = False
        for i, n in enumerate(nodes):
            if n.type in {CURVE, LINE}:
                nodes = nodes[i:] + nodes[:i]
                cycled = True
                break
        if not cycled:
            return []

        for nodeIndex in range(len(nodes)):
            count = 3 if nodes[nodeIndex].type == CURVE else 2 if nodes[nodeIndex].type == QCURVE else 1 if nodes[nodeIndex].type == LINE else 0
            if count == 0:
                continue
            newSegment = GSPathSegment()
            newSegment.parent = self  # type: ignore # TODO: (gs) Check
            newSegment.index = len(self._segments)  # type: ignore # TODO: (gs) Check
            for ix in range(-count, 1):
                newSegment.appendNode(nodes[(nodeIndex + ix) % len(nodes)])
            self._segments.append(newSegment)

        if not self.closed:
            self._segments.pop(0)

        self._segmentLength = len(self._segments)
        return self._segments

    @segments.setter
    def segments(self, value: List["GSPathSegment"]) -> None:
        if isinstance(value, (list, tuple)):
            self.setSegments(value)
        else:
            raise TypeError

    def setSegments(self, segments: List["GSPathSegment"]) -> None:
        self.nodes = []
        for segment in segments:
            if len(segment.nodes) in {2, 4}:
                self.nodes.extend(segment.nodes[1:])
            else:
                raise ValueError

    @property
    def bounds(self) -> Optional[Rect]:
        left, bottom, right, top = None, None, None, None
        for segment in self.segments:
            newLeft, newBottom, newRight, newTop = segment.bbox()
            left = min(left, newLeft) if left is not None else newLeft
            bottom = min(bottom, newBottom) if bottom is not None else newBottom
            right = max(right, newRight) if right is not None else newRight
            top = max(top, newTop) if top is not None else newTop
        if top is not None and bottom is not None and left is not None and right is not None:
            return Rect(Point(left, bottom), Size(right - left, top - bottom))
        return None

    @property
    def direction(self) -> int:
        direction = sum(
            (self.nodes[i + 1].position.x - self.nodes[i].position.x)
            * (self.nodes[i + 1].position.y + self.nodes[i].position.y)
            for i in range(len(self.nodes) - 1)
        )
        return -1 if direction < 0 else 1

    @property
    def attributes(self) -> Dict:
        return self._attributes

    @attributes.setter
    def attributes(self, attributes: Dict) -> None:
        self._attributes = attributes

    @property
    def selected(self) -> None:
        raise OnlyInGlyphsAppError

    @property
    def bezierPath(self) -> None:
        raise OnlyInGlyphsAppError

    def reverse(self) -> None:
        segments = list(reversed(self.segments))
        for s, segment in enumerate(segments):
            segment.nodes = list(reversed(segment.nodes))
            if s == len(segments) - 1:
                nextSegment = segments[0]
            else:
                nextSegment = segments[s + 1]
            if len(segment.nodes) == 2 and segment.nodes[-1].type == "curve":
                segment.nodes[-1].type = "line"
                nextSegment.nodes[0].type = "line"
            elif len(segment.nodes) == 4 and segment.nodes[-1].type == "line":
                segment.nodes[-1].type = "curve"
                nextSegment.nodes[0].type = "curve"
        self.setSegments(segments)

    # TODO
    def addNodesAtExtremes(self) -> None:
        raise NotImplementedError

    # TODO
    def applyTransform(self, transformationMatrix: Union[Transform, Tuple[float, float, float, float, float, float]]) -> None:
        assert len(transformationMatrix) == 6
        transform = Affine(*transformationMatrix)
        if transform == Identity:
            return
        for node in self.nodes:
            x, y = transform.transformPoint((node.position.x, node.position.y))
            node.position.x = x
            node.position.y = y

    def draw(self, pen: AbstractPen) -> None:
        """Draws contour with the given pen."""
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of contour with the given point pen."""
        nodes = list(self.nodes)

        pointPen.beginPath()

        if not nodes:
            pointPen.endPath()
            return

        if not self.closed:
            node = nodes.pop(0)
            assert node.type == LINE, "Open path starts with off-curve points"
            node_data = dict(node.userData)
            node_name = node_data.pop("name", None)
            pointPen.addPoint(
                tuple(node.position),
                segmentType="move",
                name=node_name,
                userData=node_data,
            )
        else:
            # In Glyphs.app, the starting node of a closed contour is always
            # stored at the end of the nodes list.
            nodes.insert(0, nodes.pop())

        for node in nodes:
            node_type = node.type if node.type in _UFO_NODE_TYPES else None
            node_data = dict(node.userData)
            node_name = node_data.pop("name", None)
            pointPen.addPoint(
                tuple(node.position),
                segmentType=node_type,
                smooth=node.smooth,
                name=node_name,
                userData=node_data,
            )
        pointPen.endPath()


GSPath._add_parsers(
    [{"plist_name": "attr", "object_name": "attributes", "type": dict}]
)  # V3


# 'offcurve' GSNode.type is equivalent to 'None' in UFO PointPen API
_UFO_NODE_TYPES = {LINE, CURVE, QCURVE}


# TODO: the GSPathSegments API and behaviour is quite different than in Glyphs. That should be adjusted (e.g. do no store GSNodes)
class GSPathSegment(list):
    def appendNode(self, node):
        if not hasattr(
            self, "nodes"
        ):  # instead of defining this in __init__(), because I hate super()
            self.nodes = []
        self.nodes.append(node)
        self.append(Point(node.position.x, node.position.y))

    # TODO: (gs) this is not available in Glyphs. And I do’t think it is a good idea to have this. path._segments are currently cached. That creates a potential of out of sync data
    @property
    def nextSegment(self):
        assert self.parent
        index = self.index
        if index == (len(self.parent._segments) - 1):
            return self.parent._segments[0]
        elif index < len(self.parent._segments):
            return self.parent._segments[index + 1]

    @property
    def prevSegment(self):
        assert self.parent
        index = self.index
        if index == 0:
            return self.parent._segments[-1]
        elif index < len(self.parent._segments):
            return self.parent._segments[index - 1]

    def bbox(self):
        if len(self) == 2:
            left = min(self[0].x, self[1].x)
            bottom = min(self[0].y, self[1].y)
            right = max(self[0].x, self[1].x)
            top = max(self[0].y, self[1].y)
            return left, bottom, right, top
        elif len(self) == 4:
            from fontTools.misc.bezierTools import calcCubicBounds
            left, bottom, right, top = calcCubicBounds(
                self[0],
                self[1],
                self[2],
                self[3],
            )
            return left, bottom, right, top
        else:
            raise ValueError


class GSTransformable(GSShape):
    _position: Point = Point(0, 0)
    _scale: Point = Point(1, 1)
    _rotation: float = 0
    _slant: Point = Point(0, 0)

    @property
    def position(self) -> Point:
        return self._position

    @position.setter
    def position(self, value: Union[Point, Tuple[float, float]]) -> None:
        if isinstance(value, tuple):
            value = Point(value[0], value[1])
        assert isinstance(value, Point)
        self._position = value

    @property
    def scale(self) -> Point:
        return self._scale

    @scale.setter
    def scale(self, value: Union[float, Point, Tuple[float, float]]) -> None:
        if isinstance(value, (int, float)):
            self._scale = Point(value, value)
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            self._scale = Point(value[0], value[1])
        elif isinstance(value, Point):
            self._scale = value
        else:
            raise ValueError("Scale must be a number or a tuple of two numbers")

    @property
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, value: Union[int, float]) -> None:
        if isinstance(value, (int, float)):
            self._rotation = value
        else:
            raise ValueError("Rotation must be a number")

    @property
    def slant(self) -> Point:
        return self._slant

    @slant.setter
    def slant(self, value: Union[Point, float, Tuple[float, float]]) -> None:
        if isinstance(value, Point):
            self._slant = value
        elif isinstance(value, (int, float)):
            self._slant = Point(value, 0)
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            self._slant = Point(value[0], value[1])
        else:
            raise ValueError("Slant must be a number, Point, or tuple of two numbers")

    @property
    def transform(self) -> Transform:
        affine = (
            Affine()
            .translate(self.position.x, self.position.y)
            .skew(math.radians(self._slant.x), math.radians(self._slant.y))
            .rotate(math.radians(self._rotation))
            .scale(self._scale.x, self._scale.y)
        )
        return Transform(affine.xx, affine.xy, affine.yx, affine.yy, affine.dx, affine.dy)

    @transform.setter
    def transform(self, value: Transform) -> None:
        sX, sY, R = transformStructToScaleAndRotation(value)
        self._scale = Point(sX, sY)
        self._rotation = R
        self._slant = Point(0, 0)
        self._position = Point(value[4], value[5])


class GSComponent(GSTransformable):
    def _serialize_to_plist(self, writer: Writer) -> None:
        # NOTE: The fields should come in alphabetical order.
        writer.writeObjectKeyValue(self, "alignment", "if_true")
        writer.writeObjectKeyValue(self, "anchor", "if_true")
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "rotation", keyName="angle", default=0)
        if writer.formatVersion >= 3 and self.attributes:
            writer.writeObjectKeyValue(self, "attributes", keyName="attr")
        writer.writeObjectKeyValue(self, "locked", "if_true")
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "componentName", keyName="name")
        if self.smartComponentValues:
            writer.writeKeyValue("piece", self.smartComponentValues)
        if writer.formatVersion > 2:
            if self._position and self._position != Point(0, 0):
                writer.writeKeyValue("pos", self._position)
            writer.writeObjectKeyValue(self, "componentName", keyName="ref")
            if self.scale and self.scale != Point(1, 1):
                writer.writeKeyValue("scale", self.scale)
            if self.slant and self.slant != Point(0, 0):
                writer.writeKeyValue("slant", Point(list(self.slant)))
        else:
            writer.writeObjectKeyValue(
                self, "transform", self.transform != Transform(1, 0, 0, 1, 0, 0)
            )
        if len(self.userData) > 0:
            writer.writeKeyValue("userData", self.userData)

    _defaultsForName: Dict[str, Transform] = {"transform": Transform(1, 0, 0, 1, 0, 0)}

    def __init__(
        self,
        glyph: Union[str, "GSGlyph"] = "",
        offset: Optional[Point] = None,
        scale: Optional[Point] = None,
        transform: Optional[Transform] = None,
    ) -> None:
        self.alignment: int = 0
        self.anchor: str = ""
        self.locked: bool = False

        if isinstance(glyph, str):
            self._componentName: str = glyph
        elif isinstance(glyph, GSGlyph):
            self._componentName = glyph.name

        self.smartComponentValues: Dict = {}

        if transform is not None:
            self.transform = transform
        if offset is not None:
            self.position = offset
        if scale is not None:
            self.scale = scale

        self._attributes: Dict = {}
        self._userData: Optional[Dict] = None

    def copy(self) -> "GSComponent":
        return GSComponent(self._componentName, transform=copy.deepcopy(self.transform))

    def __repr__(self) -> str:
        return '<GSComponent {}> "{}" x={:.1f} y={:.1f}'.format(
            hex(id(self)), self._componentName, self.transform[4], self.transform[5]
        )

    def __str__(self) -> str:
        return '<GSComponent "{}" x={:.1f} y={:.1f}>'.format(
            self._componentName, self.transform[4], self.transform[5]
        )

    def _parse_name_dict(self, parser: Parser, value: str) -> None:
        self._componentName = value

    @property
    def componentName(self) -> str:
        return self._componentName

    @componentName.setter
    def componentName(self, value: str) -> None:
        self._componentName = value

    @property
    def component(self) -> Optional["GSGlyph"]:
        return self.parent.parent.parent.glyphs[self._componentName]

    @property
    def attributes(self) -> Dict:
        return self._attributes

    @attributes.setter
    def attributes(self, attributes: Dict) -> None:
        self._attributes = attributes

    @property
    def componentLayer(self) -> Optional["GSLayer"]:
        # TODO: (gs) this needs to compute/interpolate for brace layers and smart components
        glyph = self.component
        if not glyph:
            return None

        return glyph.layers[self.parent.layerId]

    @property
    def bounds(self) -> Optional[Rect]:
        componentLayer = self.componentLayer
        bounds = componentLayer.bounds if componentLayer else None
        if bounds is not None:
            # TODO: (gs) This only produces correct results if flipped or rotated 180°
            return self.transform.transformRect(bounds)
        return None

    # smartComponentValues = property(
    #     lambda self: self.piece,
    #     lambda self, value: setattr(self, "piece", value))

    def draw(self, pen: AbstractPen) -> None:
        """Draws component with given pen."""
        pen.addComponent(self._componentName, self.transform)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of component with given point pen."""
        pointPen.addComponent(self._componentName, self.transform)

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )


GSComponent._add_parsers(
    [
        {"plist_name": "transform", "converter": Transform},
        {"plist_name": "piece", "object_name": "smartComponentValues", "type": dict},
        {"plist_name": "angle", "object_name": "rotation", "type": float},
        {"plist_name": "pos", "object_name": "position", "converter": Point},
        {"plist_name": "ref", "object_name": "componentName"},
        {"plist_name": "slant", "converter": Point},
        {"plist_name": "locked", "converter": bool},
        {"plist_name": "attr", "object_name": "attributes", "type": dict},  # V3
        {"plist_name": "userData", "object_name": "_userData", "type": dict},
    ]
)


class GSSmartComponentAxis(GSBase):
    def _serialize_to_plist(self, writer: Writer) -> None:
        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(self, "bottomName", "if_true")
            writer.writeObjectKeyValue(self, "bottomValue")
            writer.writeObjectKeyValue(self, "name")
            writer.writeObjectKeyValue(self, "topName", "if_true")
        else:
            writer.writeObjectKeyValue(self, "name")
            writer.writeObjectKeyValue(self, "bottomName")
            writer.writeObjectKeyValue(self, "bottomValue", True)
            writer.writeObjectKeyValue(self, "topName")
        writer.writeObjectKeyValue(self, "topValue", True)

    _defaultsForName: Dict[str, float] = {"bottomValue": 0.0, "topValue": 0.0}

    def __init__(self) -> None:
        self.bottomName: str = ""
        self.bottomValue: float = self._defaultsForName["bottomValue"]
        self.name: str = ""
        self.topName: str = ""
        self.topValue: float = self._defaultsForName["topValue"]


class GSAnchor(GSBase):
    def _serialize_to_plist(self, writer: Writer) -> None:
        writer.writeObjectKeyValue(self, "name", "if_true")
        posKey = "pos" if writer.formatVersion > 2 else "position"
        default = Point(0, 0) if writer.formatVersion > 2 else None
        writer.writeObjectKeyValue(self, "position", keyName=posKey, default=default)
        if len(self.userData) > 0:
            writer.writeKeyValue("userData", self.userData)

    _parent: Optional[GSLayer] = None
    _defaultsForName: Dict[str, Point] = {"position": Point(0, 0)}

    def __init__(
        self,
        name: Optional[str] = None,
        position: Optional[Point] = None,
        userData: Optional[Dict] = None,
    ) -> None:
        self.name: str = "" if name is None else name
        self.position: Point = (
            copy.deepcopy(self._defaultsForName["position"])
            if position is None
            else Point(position[0], position[1]) if isinstance(position, tuple) else position
        )
        self._userData: Optional[Dict] = None
        if userData is not None:
            self.userData = userData

    def __repr__(self) -> str:
        return '<{} {}> "{}" x={:.1f} y={:.1f}'.format(
            self.__class__.__name__, hex(id(self)), self.name, self.position[0], self.position[1]
        )

    def __str__(self) -> str:
        return '<{} "{}" x={:.1f} y={:.1f}>'.format(
            self.__class__.__name__, self.name, self.position[0], self.position[1]
        )

    @property
    def parent(self) -> Optional[GSLayer]:
        return self._parent

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )


GSAnchor._add_parsers(
    [
        {"plist_name": "pos", "object_name": "position", "converter": Point},
        {"plist_name": "userData", "object_name": "_userData", "type": dict},
        {"plist_name": "position", "converter": Point},
    ]
)


HINT_TYPE_TO_STRING = {
    PS_TOP_GHOST: "TopGhost",
    PS_BOTTOM_GHOST: "BottomGhost",
    PS_STEM: "Stem",
    PS_FLEX: "Flex",
    TTSTEM: "TTStem",
    TTSHIFT: "TTShift",
    TTSNAP: "TTSnap",
    TTINTERPOLATE: "TTInterpolate",
    TTDIAGONAL: "TTDiagonal",
    TTDELTA: "TTDelta",
    TAG: "Tag",
    CORNER: "Corner",
    CAP: "Cap",
    BRUSH: "Brush",
    SEGMENT: "Segment",
}

HINT_TYPE_TO_STRING_V2 = {
    PS_TOP_GHOST: "TopGhost",
    PS_BOTTOM_GHOST: "BottomGhost",
    PS_STEM: "Stem",
    PS_FLEX: "Flex",
    TTSTEM: "TTStem",
    TTSHIFT: "Align",
    TTSNAP: "Anchor",
    TTINTERPOLATE: "Interpolate",
    TTDIAGONAL: "Diagonal",
    TTDELTA: "Delta",
    TAG: "Tag",
    CORNER: "Corner",
    CAP: "Cap",
    BRUSH: "Brush",
    SEGMENT: "Segment",
}


class GSHint(GSBase):

    _parent: Optional[GSLayer] = None

    def __init__(self) -> None:
        self.horizontal: bool = False
        self.name: str = ""
        self.options: int = 0
        self.origin = self._defaultsForName["origin"]
        self.other1 = self._defaultsForName["other1"]
        self.other2 = self._defaultsForName["other2"]
        self.place = self._defaultsForName["place"]
        self.scale = self._defaultsForName["scale"]
        self.settings: Dict = {}
        self.stem: int = self._defaultsForName["stem"]
        self.origin = None
        self.width = None
        self._type: Optional[str] = None
        self._target: Optional[Any] = None
        self._targetNode: Optional[Any] = None

    def _serialize_to_plist(self, writer: Writer) -> None:
        if writer.formatVersion >= 3:
            # NOTE: The fields should come in alphabetical order in Glyphs 3 and later
            for field in ["horizontal", "name", "options"]:
                writer.writeObjectKeyValue(self, field, "if_true")
            for field in ["origin", "other1", "other2", "place", "scale"]:
                writer.writeObjectKeyValue(self, field)
            writer.writeObjectKeyValue(self, "settings", "if_true")
            writer.writeObjectKeyValue(self, "stem", self.stem != -2)
            for field in ["target", "type"]:
                writer.writeObjectKeyValue(self, field, "if_true")
        else:
            # NOTE: Glyphs 2 had a special sorting
            for field in [
                "horizontal",
                "origin",
                "target",
                "place",
                "other1",
                "other2",
                "scale",
            ]:
                writer.writeObjectKeyValue(self, field, "if_true")
            hint_type = HINT_TYPE_TO_STRING_V2[self.type]
            writer.writeKeyValue("type", hint_type)
            writer.writeObjectKeyValue(self, "stem", self.stem != -2)
            writer.writeObjectKeyValue(self, "name", "if_true")
            writer.writeObjectKeyValue(self, "options", "if_true")
            writer.writeObjectKeyValue(self, "settings", "if_true")

    _defaultsForName: Dict[str, Any] = {
        "origin": None,
        "other1": None,
        "other2": None,
        "place": None,
        "scale": None,
        "stem": -2,
    }

    def _origin_pos(self) -> Optional[float]:
        if self.originNode:
            return self.originNode.position.y if self.horizontal else self.originNode.position.x
        return self.origin

    def _width_pos(self) -> Optional[float]:
        if self.targetNode:
            return self.targetNode.position.y if self.horizontal else self.targetNode.position.x
        return self.width

    def _str(self) -> str:
        direction = "horizontal" if self.horizontal else "vertical"
        if self.type in {PS_BOTTOM_GHOST, PS_TOP_GHOST}:
            return "{} origin=({})".format(self.type, self._origin_pos())
        elif self.type == PS_STEM:
            return "{} Stem origin=({}) target=({})".format(direction, self.origin, self.width)
        elif self.type in {CORNER, CAP}:
            return f"{self.type} {self.name}"
        else:
            return f"{self.type} {direction}"

    def __repr__(self) -> str:
        return f"<GSHint {hex(id(self))}> {self._str()}"

    def __str__(self) -> str:
        return f"<GSHint {self._str()}>"

    @property
    def parent(self) -> GSLayer:
        return cast(GSLayer, self._parent)

    @parent.setter
    def parent(self, value: Optional[GSLayer]) -> None:
        self._parent = value

    @property
    def originNode(self) -> Optional["GSNode"]:
        if self._originNode is not None:
            return self._originNode
        if self._origin is not None:
            return self.parent._find_node_by_indices(self._origin)
        return None

    @originNode.setter
    def originNode(self, node: Optional["GSNode"]) -> None:
        self._originNode = node
        self._origin = None

    @property
    def origin(self) -> Optional[Any]:
        if self._origin is not None:
            return self._origin
        if self._originNode is not None:
            return self._originNode._indices()
        return None

    @origin.setter
    def origin(self, origin: Optional[Any]) -> None:
        self._origin = origin
        self._originNode = None

    @property
    def targetNode(self) -> Optional["GSNode"]:
        if self._targetNode is not None:
            return self._targetNode
        if self._target is not None:
            return self.parent._find_node_by_indices(self._target)
        return None

    @targetNode.setter
    def targetNode(self, node: Optional["GSNode"]) -> None:
        self._targetNode = node
        self._target = None

    @property
    def target(self) -> Optional[Any]:
        if self._target is not None:
            return self._target
        if self._targetNode is not None:
            return self._targetNode._indices()
        return None

    @target.setter
    def target(self, target: Optional[Any]) -> None:
        self._target = target
        self._targetNode = None

    @property
    def otherNode1(self) -> Optional["GSNode"]:
        if self._otherNode1 is not None:
            return self._otherNode1
        if self._other1 is not None:
            return self.parent._find_node_by_indices(self._other1)
        return None

    @otherNode1.setter
    def otherNode1(self, node: Optional["GSNode"]) -> None:
        self._otherNode1 = node
        self._other1 = None

    @property
    def other1(self) -> Optional[Any]:
        if self._other1 is not None:
            return self._other1
        if self._otherNode1 is not None:
            return self._otherNode1._indices()
        return None

    @other1.setter
    def other1(self, other1: Optional[Any]) -> None:
        self._other1 = other1
        self._otherNode1 = None

    @property
    def otherNode2(self) -> Optional["GSNode"]:
        if self._otherNode2 is not None:
            return self._otherNode2
        if self._other2 is not None:
            return self.parent._find_node_by_indices(self._other2)
        return None

    @otherNode2.setter
    def otherNode2(self, node: Optional["GSNode"]) -> None:
        self._otherNode2 = node
        self._other2 = None

    @property
    def other2(self) -> Optional[Any]:
        if self._other2 is not None:
            return self._other2
        if self._otherNode2 is not None:
            return self._otherNode2._indices()
        return None

    @other2.setter
    def other2(self, other2: Optional[Any]) -> None:
        self._other2 = other2
        self._otherNode2 = None

    @property
    def type(self) -> str:
        return self._type or PS_STEM

    @type.setter
    def type(self, hintType: str) -> None:
        assert isinstance(hintType, type(CORNER)), "hintType %s (%s) != %s" % (
            hintType,
            type(hintType),
            type(CORNER),
        )
        self._type = hintType

    @property
    def isPathComponent(self) -> bool:
        return self._type in {CORNER, CAP, BRUSH, SEGMENT}

    @property
    def isCorner(self) -> bool:
        return self.isPathComponent


GSHint._add_parsers(
    [
        {"plist_name": "origin", "object_name": "_origin", "converter": IndexPath},
        {"plist_name": "other1", "object_name": "_other1", "converter": IndexPath},
        {"plist_name": "other2", "object_name": "_other2", "converter": IndexPath},
        {"plist_name": "target", "object_name": "_target", "converter": IndexPath},
        {"plist_name": "place", "converter": Point},
        {"plist_name": "scale", "converter": Point},
        {"plist_name": "horizontal", "converter": bool},
    ]
)

FEATURENAMES_PATTERN = re.compile(
    r"name\s+(?:(\d+)\s+(\d+)\s+(0x[0-9A-Fa-f]+)\s+)?\"([^\"]+)\"\;"
)


def extract_name_and_langId(s):
    match = FEATURENAMES_PATTERN.search(s)
    if match:
        # Extracted numbers are in separate groups and the string is in the last group
        numbers = [match.group(i) for i in range(1, 4) if match.group(i) is not None]
        name_string = match.group(4)
        return name_string, numbers
    return None, None


class GSFeature(GSBase):

    _parent: Optional["GSFont"]

    def __init__(self, name: str = "xxxx", code: str = "") -> None:
        self.active: bool = True
        self.automatic: bool = False
        self.code = code
        self.labels: List[Dict[str, str]] = []
        self.name: str = name
        self.notes: str = ""

    def _serialize_to_plist(self, writer: Writer) -> None:
        writer.writeObjectKeyValue(self, "automatic", "if_true")
        writer.writeObjectKeyValue(self, "code", True)
        if not self.active:
            writer.writeKeyValue("disabled", True)
        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(self, "labels", "if_true")
            writer.writeObjectKeyValue(self, "notes", "if_true")
            writer.writeKeyValue("tag", self.name)
        else:
            writer.writeKeyValue("name", self.name)
            notes = self.notes
            if self.labels:
                feature_names = self.featureNamesString()
                if feature_names:
                    notes = feature_names + notes if notes else feature_names
            if notes:
                writer.writeKeyValue("notes", notes)

    def post_read(self) -> None:
        if self.notes and len(self.notes) > 10:
            remaining_note = self.loadLabelsFromNote(self.notes)
            if remaining_note is not False:
                self.notes = cast(str, remaining_note)

    @property
    def code(self) -> str:
        return self._code

    @code.setter
    def code(self, code: str) -> None:
        replacements = (
            ("\\012", "\n"),
            ("\\011", "\t"),
            ("\\U2018", "'"),
            ("\\U2019", "'"),
            ("\\U201C", '"'),
            ("\\U201D", '"'),
        )
        for escaped, unescaped in replacements:
            code = code.replace(escaped, unescaped)
        self._code = code

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {hex(id(self))}> "{self.name}"'

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} "{self.name}">'

    @property
    def parent(self) -> Optional[GSFont]:
        return self._parent

    @property
    def disabled(self) -> None:
        raise Exception("Use .active")

    @disabled.setter
    def disabled(self, _val: Any) -> None:
        raise Exception("Use .active = ")

    def featureNamesString(self) -> Optional[str]:
        if not self.labels:
            return None
        feature_names = []
        from glyphsLib.builder.features import _to_name_langID
        for label in self.labels:
            langID = _to_name_langID(label["language"])
            name = label["value"]
            if not name:
                continue
            name = name.replace("\\", r"\005c").replace('"', r"\0022")
            if langID is None:
                feature_names.append(f'  name "{name}";')
            else:
                feature_names.append(f'  name 3 1 0x{langID:X} "{name}";')
        if feature_names:
            feature_names.insert(0, "featureNames {")
            feature_names.append("};")
        return "\n".join(feature_names)

    def loadLabelsFromNote(self, note: str) -> str | bool:
        remaining_note = note
        if note.startswith("Name:"):
            name = note[5:].strip()
            lineEnd = name.find("\n")
            if lineEnd > 0:
                name = name[:lineEnd]
                remaining_note = note[lineEnd:]
            else:
                remaining_note = ""
            if name:
                self.labels.append(dict(language="dflt", value=name))
                return remaining_note

        elif note.startswith("featureNames {"):
            lineEnd = note.find("};")
            if lineEnd < 0:
                return False
            remaining_note = note[lineEnd + 2 :]
            note = note[14:lineEnd].strip()
            if not note:
                return False

            lines = note.split("\n")
            seenLanguage = set()
            for line in lines:
                code = line.strip()
                if not code.startswith("name "):
                    continue

                name, langIDs = extract_name_and_langId(code)

                if len(langIDs) == 0:
                    platformID, platEncID, langID = 3, 1, 0x0409
                elif len(langIDs) == 1:
                    platformID, platEncID, langID = 3, 1, langIDs[0]
                elif len(langIDs) == 3:
                    platformID, platEncID, langID = int(langIDs[0]), int(langIDs[1]), int(langIDs[2], 16) if langIDs[2].startswith("0x") else int(langIDs[2])

                language = "dflt"
                if platformID == 3 and platEncID == 1:
                    from glyphsLib.builder.features import _to_glyphs_language
                    language = _to_glyphs_language(langID)
                elif platformID == 1 and platEncID == 0 and langID == 0:
                    language = "ENG"
                else:
                    logger.warning(
                        f"Unknown platform:{platformID}, enc:{platEncID}, lang:{langID} in featureNames. Defaulting to 'dflt'"
                    )
                if language in seenLanguage:
                    continue
                seenLanguage.add(language)
                self.labels.append(dict(language=language, value=name))
            return remaining_note
        return False


GSFeature._add_parsers(
    [
        {"plist_name": "code", "object_name": "_code"},
        {"plist_name": "disabled", "object_name": "active", "converter": NegateBool},
        {"plist_name": "tag", "object_name": "name"},
        {"plist_name": "labels", "type": dict},
    ]
)


class GSClass(GSFeature):
    def _serialize_to_plist(self, writer: Writer) -> None:
        # NOTE: The fields should come in alphabetical order.
        writer.writeObjectKeyValue(self, "automatic", "if_true")
        writer.writeObjectKeyValue(self, "code", True)
        if not self.active:
            writer.writeKeyValue("disabled", True)
        writer.writeKeyValue("name", self.name)
        writer.writeObjectKeyValue(self, "notes", "if_true")


class GSFeaturePrefix(GSClass):
    pass


class GSAnnotation(GSBase):
    def _serialize_to_plist(self, writer: Writer) -> None:
        writer.writeObjectKeyValue(self, "angle", default=0)
        posKey = "pos" if writer.formatVersion > 2 else "position"
        writer.writeObjectKeyValue(
            self, "position", keyName=posKey, default=Point(0, 0)
        )
        writer.writeObjectKeyValue(self, "text", "if_true")
        writer.writeObjectKeyValue(self, "type", "if_true")
        writer.writeObjectKeyValue(self, "width", default=100)

    _defaultsForName: Dict[str, Optional[Union[int, float, Point, str]]] = {
        "angle": 0,
        "position": Point(0, 0),
        "text": None,
        "type": 0,
        "width": 100,
    }

    _parent: Optional[GSLayer] = None

    def __init__(self) -> None:
        self.angle: int = cast(int, self._defaultsForName["angle"])
        self.position: Point = cast(Point, copy.copy(self._defaultsForName["position"]))
        self.text: Optional[str] = cast(str, self._defaultsForName["text"])
        self.type: int = cast(int, self._defaultsForName["type"])
        self.width: int = cast(int, self._defaultsForName["width"])

    @property
    def parent(self) -> GSLayer:
        return cast(GSLayer, self._parent)

    @parent.setter
    def parent(self, value: Optional[GSLayer]) -> None:
        self._parent = value


GSAnnotation._add_parsers(
    [
        {"plist_name": "pos", "object_name": "position", "converter": Point},
        {"plist_name": "position", "converter": Point},
    ]
)


LOCALIZED_PARAMETERS = (
    "localizedFamilyName",
    "localizedStyleName",
    "localizedStyleMapFamilyName",
    "localizedDesigner",
)
# SIMPLE_PARAMETERS = ("trademark")


class GSFontInfoValue(GSBase):
    """Combines localizable/nonlocalizable properties"""
    parent: Optional[GSBase]

    def __init__(self, key: str = "", value: Optional[Any] = None) -> None:
        self.key: str = key
        self._value: Optional[Any] = value
        self._localized_values: Optional[Dict[str, Any]] = None

    def _parse_values_dict(self, parser: Parser, values: List[Dict[str, str]]) -> None:
        self._localized_values = {}
        for v in values:
            if "language" not in v or "value" not in v:
                continue
            self._localized_values[v["language"]] = v["value"]

    def _serialize_to_plist(self, writer: Writer) -> None:
        writer.writeObjectKeyValue(self, "key", "if_true")
        if self._localized_values:
            writer.writeKeyValue(
                "values",
                [{"language": l, "value": v} for l, v in self._localized_values.items()],
            )
        else:
            writer.writeObjectKeyValue(self, "value")

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {hex(id(self))}> "{self.key}"'

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} "{self.key}">'

    @property
    def name(self) -> str:
        return self.key

    @name.setter
    def name(self, value: str) -> None:
        self.key = value

    @property
    def value(self) -> Optional[Any]:
        return self._value

    @value.setter
    def value(self, value: Optional[Any]) -> None:
        self._value = value

    @property
    def values(self) -> Optional[Dict[str, Any]]:
        return self._localized_values

    @values.setter
    def values(self, values: Optional[Dict[str, Any]]) -> None:
        self._localized_values = values

    @property
    def defaultValue(self) -> Optional[Any]:
        if not self._localized_values:
            return None
        for key in ["dflt", "ENG"]:
            if key in self._localized_values:
                return self._localized_values[key]
        return list(self._localized_values.values())[0]

    @defaultValue.setter
    def defaultValue(self, value: Any) -> None:
        self.setLocalizedValue(value)

    def localizedValue(self, language: str = "dflt") -> Optional[Any]:
        if not self._localized_values:
            return None
        if language in ["dflt", "ENG"] and language in self._localized_values:
            return self._localized_values[language]
        return self._localized_values.get(language, None)

    def setLocalizedValue(self, value: Any, language: str = "dflt") -> None:
        if not self._localized_values:
            self._localized_values = {}
        self._localized_values[language] = value

    @classmethod
    def propertiesFromLegacyCustomParameters(cls, obj: Union[GSFont, GSInstance]) -> None:
        if not obj.customParameters:
            return
        for parameter in list(obj.customParameters):
            name = parameter.name
            if name in PROPERTIES_WHITELIST or name + "s" in PROPERTIES_WHITELIST:
                propertyName = name + "s" if name + "s" in PROPERTIES_WHITELIST else name
                obj.properties.setProperty(propertyName, parameter.value)
                obj.customParameters.remove(parameter)
                continue
            if name not in LOCALIZED_PARAMETERS:
                continue
            string = parameter.value
            semicolonPos = string.find(";")
            if semicolonPos < 1:
                continue

            language = string[:semicolonPos]
            language = glyphdata.langName2Tag.get(language, language)
            value = string[semicolonPos + 1:]
            name = name[9].lower() + name[10:] + "s"
            obj.properties.setProperty(name, value, language)
            obj.customParameters.remove(parameter)

    @classmethod
    def legacyCustomParametersFromProperties(cls, properties: List["GSFontInfoValue"], obj: GSBase) -> List["GSCustomParameter"]:
        customParameters = []
        for infoValue in properties:
            newParameter = cls.legacyCustomParametersFromInfoValue(infoValue)
            if newParameter is not None:
                if len(newParameter) > 0:
                    customParameters.extend(newParameter)
            else:
                raise Exception(f"Problem converting infoValue {infoValue} in {obj}")
        return customParameters

    @classmethod
    def legacyCustomParametersFromInfoValue(cls, infoValue: "GSFontInfoValue") -> Optional[List["GSCustomParameter"]]:
        parameterKey = infoValue.key.rstrip("s")
        locParameterKey = "localized" + parameterKey[0].upper() + parameterKey[1:]
        defaultValue = None
        isLocalizedParameter = locParameterKey in LOCALIZED_PARAMETERS

        if not isLocalizedParameter:
            defaultValue = infoValue.value or infoValue.defaultValue

        customParameters = []

        if isLocalizedParameter and infoValue._localized_values:
            values = infoValue._localized_values
            for key in sorted(values.keys()):
                value = values[key]
                if key in ["dflt", "ENG"]:
                    defaultValue = value
                else:
                    langName = glyphdata.langTag2Name.get(key, key)
                    stringValue = f"{langName};{value}"
                    parameter = GSCustomParameter(locParameterKey, stringValue)
                    customParameters.append(parameter)

        if defaultValue:
            nativeDefaultKeys = {
                "designer",
                "designerURL",
                "manufacturer",
                "manufacturerURL",
                "copyright",
            }

            if parameterKey in nativeDefaultKeys and isinstance(infoValue.parent, GSFont):
                return customParameters

            parameter = GSCustomParameter(parameterKey, defaultValue)
            customParameters.insert(0, parameter)
        return customParameters if customParameters else None


INSTANCE_AXIS_VALUE_KEYS = (
    "interpolationWeight",
    "interpolationWidth",
    "interpolationCustom",
    "interpolationCustom1",
    "interpolationCustom2",
    "interpolationCustom3",
)


class GSInstance(GSBase):
    def _write_axis_value(self, writer: Writer, idx: int, defaultValue: float) -> None:
        axes = self.font.axes
        axesCount = len(axes)
        if axesCount > idx:
            value = self.internalAxesValues[axes[idx].axisId]
            if value and abs(value - defaultValue) > 0.01:
                writer.writeKeyValue(INSTANCE_AXIS_VALUE_KEYS[idx], value)

    def _serialize_to_plist(self, writer: Writer) -> None:
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "exports", condition=(not self.exports))
        if (
            writer.formatVersion >= 3
            and len(self.internalAxesValues)
            and self.type != InstanceType.VARIABLE
        ):
            writer.writeKeyValue("axesValues", self.internalAxesValues)

        customParameters = list(self.customParameters)
        if writer.formatVersion < 3:
            weight_class_string = WEIGHT_CODES_REVERSE.get(self.weightClass)
            if weight_class_string is None:
                parameter = GSCustomParameter("weightClass", self.weightClass)
                customParameters.append(parameter)
            parameters = GSFontInfoValue.legacyCustomParametersFromProperties(
                self.properties, self
            )
            if parameters:
                customParameters.extend(parameters)

        if writer.formatVersion <= 3:
            axisValueToAxisLocation(self)

        if customParameters:
            writer.writeKeyValue("customParameters", customParameters)

        if writer.formatVersion == 2:
            self._write_axis_value(writer, 2, 0)
            self._write_axis_value(writer, 3, 0)
            self._write_axis_value(writer, 4, 0)
            self._write_axis_value(writer, 5, 0)
            self._write_axis_value(writer, 0, 100)
            self._write_axis_value(writer, 1, 100)

        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(self, "exports", condition=(not self.exports))

        writer.writeObjectKeyValue(self, "instanceInterpolations", "if_true")
        writer.writeObjectKeyValue(self, "isBold", "if_true")
        writer.writeObjectKeyValue(self, "isItalic", "if_true")
        writer.writeObjectKeyValue(self, "linkStyle", "if_true")
        writer.writeObjectKeyValue(self, "manualInterpolation", "if_true")
        writer.writeObjectKeyValue(self, "name")

        if writer.formatVersion > 2:
            if self.properties and len(self.properties) > 0:
                self._properties.sort(key=lambda key: key.key.lower())
                writer.writeObjectKeyValue(self, "properties")
            if self.type != InstanceType.SINGLE:
                writer.writeKeyValue("type", InstanceType.VARIABLE.name.lower())

        if self.userData:
            writer.writeKeyValue("userData", self.userData)

        if not self.visible:
            writer.writeKeyValue("visible", 0)

        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "weightClass", default=400)
            writer.writeObjectKeyValue(self, "widthClass", default=5)
        else:
            weight_class_string = WEIGHT_CODES_REVERSE.get(self.weightClass)
            if weight_class_string is not None and weight_class_string != "Regular":
                writer.writeKeyValue("weightClass", weight_class_string)
            width_class_string = WIDTH_CODES_REVERSE.get(self.widthClass)
            if width_class_string is not None and width_class_string != "Medium (normal)":
                writer.writeKeyValue("widthClass", width_class_string)

    _axis_defaults: tuple[int, int] = (100, 100)

    _defaultsForName: Dict[str, Any] = {
        "exports": True,
        "weightClass": 400,
        "widthClass": 5,
        "instanceInterpolations": {},
        "type": InstanceType.SINGLE,
    }

    def __init__(self, name: str = "Regular") -> None:
        self._font: Optional["GSFont"] = None
        self._internalAxesValues: Dict[str, float] = {}
        self._externalAxesValues: Dict[str, float] = {}
        self.customParameters = []
        self.exports: bool = True
        self.custom: Optional[str] = None
        self.instanceInterpolations: Dict = copy.deepcopy(self._defaultsForName["instanceInterpolations"])
        self.isBold: bool = False
        self.isItalic: bool = False
        self.linkStyle: str = ""
        self.manualInterpolation: bool = False
        self.name: str = name
        self._properties: List["GSFontInfoValue"] = []
        self.visible: bool = True
        self.weightClass: int = self._defaultsForName["weightClass"]
        self.widthClass: int = self._defaultsForName["widthClass"]
        self.type: InstanceType = self._defaultsForName["type"]
        self.readBuffer: Dict = {}
        self._axesValues: Optional[Dict[int, float]] = None
        self._userData: Optional[Dict[str, Any]] = None

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {hex(id(self))}> "{self.name}"'

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} "{self.name}">'

    @property
    def font(self) -> GSFont:
        return cast(GSFont, self._font)

    @font.setter
    def font(self, value: Optional[GSFont]) -> None:
        self._font = value

    customParameters = property(
        lambda self: CustomParametersProxy(self),
        lambda self, value: CustomParametersProxy(self).setter(value),
    )

    properties = property(
        lambda self: PropertiesProxy(self),
        lambda self, value: PropertiesProxy(self).setter(value),
    )

    def post_read(self) -> None:
        assert self.font
        axes = self.font.axes
        if axes and self.type != InstanceType.VARIABLE:
            if self.font.formatVersion < 3:
                axesValues = self.readBuffer.get("axesValues", {})
                axesCount = len(axes)
                for idx in range(axesCount):
                    axis = axes[idx]
                    if axis.axisId in self._internalAxesValues:  # (gs) e.g. when loading from designspace, this is properly set already
                        continue
                    value = axesValues.get(idx, DefaultAxisValuesV2[idx])
                    self.internalAxesValues[axis.axisId] = value
                if axes and len(self._internalAxesValues) == 0:
                    axisId = axes[0].axisId
                    self.internalAxesValues[axisId] = 100
            else:
                axesValues = self._axesValues
                if axesValues:
                    axesCount = len(axes)
                    for idx in range(axesCount):
                        axis = axes[idx]
                        if idx < len(axesValues):
                            value = axesValues[idx]
                        else:
                            # (georg) fallback for old designspace setup
                            value = 100 if idx < 2 else 0
                        self.internalAxesValues[axis.axisId] = value

        if self.font.formatVersion < 3:
            if isinstance(self.weightClass, str):
                weightClass = WEIGHT_CODES.get(self.weightClass)
                if weightClass:
                    self.weightClass = weightClass
            if isinstance(self.widthClass, str):
                widthClass = WIDTH_CODES.get(self.widthClass)
                if widthClass:
                    self.widthClass = widthClass

            if self.font.formatVersion < 3 and len(self._internalAxesValues) == 0:
                self.internalAxesValues[self.font.axes[0].axisId] = 100

            GSFontInfoValue.propertiesFromLegacyCustomParameters(self)

        weight_class_parameter = self.customParameters.get("weightClass")
        if weight_class_parameter:
            self.weightClass = int(weight_class_parameter)
            del self.customParameters["weightClass"]

        axisLocationToAxesValue(self)

        for customParameter in self.customParameters:
            customParameter.post_read(self.font.formatVersion)

    @property
    def exports(self) -> bool:
        """Deprecated alias for `active`, which is in the documentation."""
        return self._exports

    @exports.setter
    def exports(self, value: bool) -> None:
        self._exports = value

    @property
    def familyName(self) -> str:
        return self.properties["familyNames"] or self.font.familyName

    @familyName.setter
    def familyName(self, value: str) -> None:
        self.properties["familyNames"] = value

    @property
    def preferredFamily(self) -> str:
        return self.preferredFamilyName or self.font.familyName

    @preferredFamily.setter
    def preferredFamily(self, value: str) -> None:
        self.preferredFamilyName = value

    @property
    def preferredFamilyName(self) -> Optional[str]:
        return self.properties["preferredFamilyNames"]

    @preferredFamilyName.setter
    def preferredFamilyName(self, value: str) -> None:
        self.properties["preferredFamilyNames"] = value

    @property
    def preferredSubfamilyName(self) -> Optional[str]:
        return self.properties["preferredSubfamilyNames"]

    @preferredSubfamilyName.setter
    def preferredSubfamilyName(self, value: str) -> None:
        self.properties["preferredSubfamilyNames"] = value

    @property
    def windowsFamily(self) -> str:
        value = self.properties["styleMapFamilyNames"]
        if value:
            return value
        if self.name not in {
            "Regular",
            "Bold",
            "Italic",
            "Oblique",
            "Bold Italic",
            "Bold Oblique",
        }:
            return f"{self.familyName} {self.name}"
        return self.familyName

    @windowsFamily.setter
    def windowsFamily(self, value: str) -> None:
        self.properties["styleMapFamilyNames"] = value

    @property
    def windowsStyle(self) -> str:
        if self.name in {
            "Regular",
            "Bold",
            "Italic",
            "Oblique",
            "Bold Italic",
            "Bold Oblique",
        }:
            return self.name
        return "Regular"

    @property
    def styleMapFamilyNames(self) -> Optional[str]:
        return self.properties["styleMapFamilyNames"]

    @styleMapFamilyNames.setter
    def styleMapFamilyNames(self, values: str) -> None:
        self.properties["styleMapFamilyNames"] = values

    @property
    def styleMapStyleNames(self) -> Optional[str]:
        return self.properties["styleMapStyleNames"]

    @styleMapStyleNames.setter
    def styleMapStyleNames(self, values: str) -> None:
        self.properties["styleMapStyleNames"] = values

    @property
    def styleMapFamilyName(self) -> Optional[str]:
        return self.properties.getProperty("styleMapFamilyNames")

    @styleMapFamilyName.setter
    def styleMapFamilyName(self, value: str) -> None:
        self.properties.setProperty("styleMapFamilyNames", value)

    @property
    def styleMapStyleName(self) -> Optional[str]:
        return self.properties.getProperty("styleMapStyleNames")

    @styleMapStyleName.setter
    def styleMapStyleName(self, value: str) -> None:
        self.properties.setProperty("styleMapStyleNames", value)

    @property
    def windowsLinkedToStyle(self) -> Optional[str]:
        return self.linkStyle

    @property
    def fontName(self) -> str:
        return (
            self.properties["postscriptFontName"]
            # TODO: Strip invalid characters.
            or ("".join(self.familyName.split(" ")) + "-" + self.name)
        )

    @fontName.setter
    def fontName(self, value: str) -> None:
        self.properties["postscriptFontName"] = value

    @property
    def fullName(self) -> str:
        return self.properties["postscriptFullName"] or (
            self.familyName + " " + self.name
        )

    @fullName.setter
    def fullName(self, value: str) -> None:
        self.properties["postscriptFullName"] = value

    internalAxesValues = property(
        lambda self: InternalAxesProxy(self),
        lambda self, value: InternalAxesProxy(self).setter(value),
    )

    externalAxesValues = property(
        lambda self: ExternalAxesProxy(self),
        lambda self, value: ExternalAxesProxy(self).setter(value),
    )

    @property
    def weightValue(self) -> Optional[float]:
        return self.internalAxesValues[0] if len(self.font.axes) > 0 else None

    @weightValue.setter
    def weightValue(self, value: float) -> None:
        if self.font:
            axis = self.font.axes[0]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[0] = value

    @property
    def widthValue(self) -> Optional[float]:
        return self.internalAxesValues[1] if len(self.font.axes) > 1 else None

    @widthValue.setter
    def widthValue(self, value: float) -> None:
        if self.font:
            axis = self.font.axes[1]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[1] = value

    @property
    def customValue(self):
        return self.internalAxesValues[2] if len(self.font.axes) > 2 else None

    @customValue.setter
    def customValue(self, value):
        if self.font:
            axis = self.font.axes[2]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[2] = value

    @property
    def customValue1(self):
        return self.internalAxesValues[3] if len(self.font.axes) > 3 else None

    @customValue1.setter
    def customValue1(self, value):
        if self.font:
            axis = self.font.axes[3]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[3] = value

    @property
    def customValue2(self):
        return self.internalAxesValues[4] if len(self.font.axes) > 4 else None

    @customValue2.setter
    def customValue2(self, value):
        if self.font:
            axis = self.font.axes[4]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[4] = value

    @property
    def customValue3(self):
        return self.internalAxesValues[5] if len(self.font.axes) > 5 else None

    @customValue3.setter
    def customValue3(self, value):
        if self.font:
            axis = self.font.axes[5]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        self.readBuffer.setdefault("axesValues", {})[5] = value

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )


GSInstance._add_parsers(
    [
        {"plist_name": "customParameters", "type": GSCustomParameter},
        {"plist_name": "instanceInterpolations", "type": dict},
        {"plist_name": "interpolationCustom", "object_name": "customValue"},
        {"plist_name": "interpolationCustom1", "object_name": "customValue1"},
        {"plist_name": "interpolationCustom2", "object_name": "customValue2"},
        {"plist_name": "interpolationCustom3", "object_name": "customValue3"},
        {"plist_name": "interpolationWeight", "object_name": "weightValue"},
        {"plist_name": "interpolationWidth", "object_name": "widthValue"},
        {"plist_name": "manualInterpolation", "converter": bool},
        {"plist_name": "properties", "type": GSFontInfoValue},
        {"plist_name": "type", "converter": instance_type},
        {"plist_name": "axesValues", "object_name": "_axesValues"},  # v3
        {"plist_name": "visible", "object_name": "visible", "converter": bool},
        {"plist_name": "userData", "object_name": "_userData", "type": dict},
    ]
)


class GSBackgroundImage(GSTransformable):
    def _serialize_to_plist(self, writer: Writer) -> None:
        writer.writeObjectKeyValue(self, "_alpha", keyName="alpha", default=50)
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "rotation", keyName="angle", default=0)

        if self.crop:
            writer.writeObjectKeyValue(self, "crop")

        writer.writeObjectKeyValue(self, "imagePath")
        if self.locked:
            writer.writeKeyValue("locked", "1" if writer.formatVersion == 2 else 1)

        if writer.formatVersion > 2:
            if self.position != Point(0, 0):
                writer.writeObjectKeyValue(self, "position", keyName="pos")
            if self.scale and self.scale != Point(1.0, 1.0):
                writer.writeKeyValue("scale", self.scale)
        else:
            writer.writeObjectKeyValue(
                self, "transform", default=Transform(1, 0, 0, 1, 0, 0)
            )

    _defaultsForName: dict[str, Union[int, "Transform"]] = {
        "alpha": 50,
        "transform": Transform(1, 0, 0, 1, 0, 0),
    }

    def __init__(self, path: Optional[str] = None) -> None:
        self.alpha: int = self._defaultsForName["alpha"]
        self.crop: Optional[Any] = None
        self.imagePath: Optional[str] = path
        self.locked: bool = False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {hex(id(self))}> '{self.imagePath}'"

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} '{self.imagePath}'>"

    @property
    def path(self) -> Optional[str]:
        return self.imagePath

    @path.setter
    def path(self, value: str) -> None:
        self.imagePath = value

    @property
    def alpha(self) -> int:
        return self._alpha

    @alpha.setter
    def alpha(self, value: int) -> None:
        if not 10 <= value <= 100:
            value = 50
        self._alpha = value


GSBackgroundImage._add_parsers(
    [
        {"plist_name": "transform", "converter": Transform},
        {"plist_name": "crop", "converter": Rect},
        {"plist_name": "locked", "converter": bool},
        {"plist_name": "angle", "object_name": "rotation", "type": float},
        {"plist_name": "pos", "object_name": "position", "converter": Point},
    ]
)


class LayerPathsProxy(LayerShapesProxy):
    _filter = GSPath


class LayerComponentsProxy(LayerShapesProxy):
    _filter = GSComponent


class GSLayer(GSBase):
    _parent: Optional["GSGlyph"] = None

    def __init__(self) -> None:
        self._anchors: List[Any] = []
        self._annotations: List[Any] = []
        self._background: Optional[GSBackgroundLayer] = None
        self._foreground: Optional[GSLayer] = None
        self._guides: List[Any] = []
        self._hints: List[Any] = []
        self._layerId: str = ""
        self._name: str = ""
        self._selection: List[Any] = []
        self._shapes: List[GSShape] = []
        self._userData: Optional[Dict[str, Any]] = None
        self.attributes: Dict[str, Any] = {}
        self.smartComponentPoleMapping: Dict[str, Any] = {}
        self.associatedMasterId: str = ""
        self.backgroundImage: Optional[GSBackgroundImage] = None
        self.color: Optional[Any] = None
        self.visible: bool = False

        self.width: Union[float] = self._defaultsForName["width"] or 0
        self.vertOrigin: Optional[float] = None
        self.vertWidth: Optional[float] = None

        self._bottomKerningGroup: Optional[str] = None
        self._leftKerningGroup: Optional[str] = None
        self._rightKerningGroup: Optional[str] = None
        self._topKerningGroup: Optional[str] = None

        self._bottomMetricsKey: Optional[str] = None
        self._leftMetricsKey: Optional[str] = None
        self._rightMetricsKey: Optional[str] = None
        self._topMetricsKey: Optional[str] = None
        self._vertOriginMetricsKey: Optional[str] = None
        self._vertWidthMetricsKey: Optional[str] = None
        self._widthMetricsKey: Optional[str] = None

    def _get_plist_attributes(self) -> Dict[str, Any]:
        attributes = dict(self.attributes)
        font = self.font
        if LAYER_ATTRIBUTE_AXIS_RULES in self.attributes:
            rule = attributes[LAYER_ATTRIBUTE_AXIS_RULES]
            ruleMap: List[Dict[str, Any]] = []
            for axis in font.axes:
                ruleMap.append(rule.get(axis.axisId, {}))
            attributes[LAYER_ATTRIBUTE_AXIS_RULES] = ruleMap
        if LAYER_ATTRIBUTE_COORDINATES in self.attributes:
            coordinates = attributes[LAYER_ATTRIBUTE_COORDINATES]
            coordinatesMap: List[Optional[float]] = []
            for axis in font.axes:
                value = coordinates.get(axis.axisId)
                coordinatesMap.append(value)
            attributes[LAYER_ATTRIBUTE_COORDINATES] = coordinatesMap
        return attributes

    def _serialize_to_plist(self, writer: Writer) -> None:  # noqa: C901
        writer.writeObjectKeyValue(self, "anchors", "if_true")
        writer.writeObjectKeyValue(self, "annotations", "if_true")

        userData: Dict[str, Any] = dict(self.userData)

        if not self.isMasterLayer:
            writer.writeObjectKeyValue(self, "associatedMasterId")
        if writer.formatVersion > 2:
            attributes = self._get_plist_attributes()
            if attributes:
                writer.writeKeyValue("attr", attributes)

        writer.writeObjectKeyValue(
            self,
            "background",
            self._background is not None and len(self._background.shapes) > 0,
        )
        writer.writeObjectKeyValue(self, "backgroundImage")
        writer.writeObjectKeyValue(self, "color")
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "components", "if_true")
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "guides", "if_true")
        elif self.guides:
            writer.writeKeyValue("guideLines", self.guides)
        writer.writeObjectKeyValue(self, "hints", "if_true")
        writer.writeObjectKeyValue(self, "layerId", "if_true")
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "bottomMetricsKey", keyName="metricBottom")
            writer.writeObjectKeyValue(self, "leftMetricsKey", keyName="metricLeft")
            writer.writeObjectKeyValue(self, "rightMetricsKey", keyName="metricRight")
            writer.writeObjectKeyValue(self, "topMetricsKey", keyName="metricTop")
            writer.writeObjectKeyValue(self, "widthMetricsKey", keyName="metricWidth")
        else:
            writer.writeObjectKeyValue(self, "leftMetricsKey")
            # NOTE: The following two are an exception from the ordering rule.
            writer.writeObjectKeyValue(self, "rightMetricsKey")
            writer.writeObjectKeyValue(self, "widthMetricsKey")
        if writer.formatVersion > 2:
            if self._name and not self.isMasterLayer:
                writer.writeKeyValue("name", self._name)
        else:
            if ((self._name and len(self._name) > 0) or len(self.attributes) > 0) and not self.isMasterLayer:
                legacyName = self._legacyName()
                if legacyName:
                    writer.writeKeyValue("name", legacyName)
                elif self._name:
                    writer.writeKeyValue("name", self._name)
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(
                self, "smartComponentPoleMapping", "if_true", keyName="partSelection"
            )
            if self._shapes:
                writer.writeKeyValue("shapes", self._shapes)
        else:
            if self.smartComponentPoleMapping:
                userData["PartSelection"] = dict(self.smartComponentPoleMapping)
            writer.writeObjectKeyValue(self, "paths", "if_true")
        if len(userData) > 0:
            writer.writeKeyValue("userData", userData)
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "visible", "if_true")
        writer.writeObjectKeyValue(self, "vertOrigin")
        if self.vertWidth != 0:
            # FIXME: how to know if that zero is a really value (this is a problem with the ufo spec)
            writer.writeObjectKeyValue(self, "vertWidth")
        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(self, "visible", "if_true")
        writer.writeObjectKeyValue(self, "width", not isinstance(self, GSBackgroundLayer))

    BRACKET_LAYER_RE_V2 = re.compile(
        r".*(?P<first_bracket>[\[\]])\s*(?P<value>\d+)\s*\].*"
    )
    BRACKET_LAYER_RE_V3 = re.compile(
        r'\[(\s*\d+‹[a-zA-Z]+(?:‹\d+)?\s*(?:,\s*\d+‹[a-zA-Z]+(?:‹\d+)?\s*)*)\]'
    )
    COLOR_PALETTE_LAYER_RE = re.compile(r"^Color (?P<index>\*|\d+)$")

    def _parse_layer_bracket_name_v3(self, name: str, font: GSFont) -> Tuple[Optional[Dict[str, Dict[str, float]]], str]:
        """
        When importing from UFO.
        """
        def if_number(s: str) -> bool:
            try:
                float(s)
                return True
            except ValueError:
                return False

        m = re.search(self.BRACKET_LAYER_RE_V3, name)
        if m:
            bracket_rule: Dict[str, Dict[str, float]] = {}
            content: str = m.group(1)
            groups = [group.strip().split('‹') for group in content.split(',')]
            for rule in groups:
                firstNumber: Optional[float] = None
                short_axis_tag: Optional[str] = None
                secondNumber: Optional[float] = None
                if if_number(rule[0]):
                    firstNumber = float(rule[0])
                else:
                    short_axis_tag = rule[0]
                if if_number(rule[1]):
                    secondNumber = float(rule[1])
                else:
                    short_axis_tag = rule[1]
                if len(rule) > 2 and if_number(rule[2]):
                    secondNumber = float(rule[2])
                axis_id: Optional[str] = None
                for axis in font.axes:
                    if axis.shortAxisTag == short_axis_tag:
                        axis_id = axis.axisId
                        break
                ruleDict: Dict[str, float] = {}
                if firstNumber is not None:
                    ruleDict["min"] = firstNumber
                if secondNumber is not None:
                    ruleDict["max"] = secondNumber
                if axis_id:
                    bracket_rule[axis_id] = ruleDict
            name = name.replace(m.group(0), "").replace("  ", " ").strip()
            return bracket_rule, name
        return None, name

    def _parse_layer_bracket_name_v2(self, name: str, font: GSFont) -> Tuple[Optional[Dict[str, Dict[str, int]]], str]:
        m = re.match(self.BRACKET_LAYER_RE_V2, name)
        if m:
            axis = font.axes[0]  # For Glyphs 2
            reverse = m.group("first_bracket") == "]"
            bracket_crossover = int(m.group("value"))
            name = name.replace(m.group(0), "").replace("  ", " ").strip()
            bracket_rule = {axis.axisId: {"max" if reverse else "min": bracket_crossover}}
            return bracket_rule, name
        return None, name

    def layer_name_to_attributes(self) -> None:
        name: str = self.name
        font: GSFont = self.font
        assert font

        if "]" in name:
            rule: Optional[dict] = None
            if "‹" in name:
                rule, name = self._parse_layer_bracket_name_v3(name, font)
            else:
                rule, name = self._parse_layer_bracket_name_v2(name, font)
            if rule:
                self.attributes[LAYER_ATTRIBUTE_AXIS_RULES] = rule

        if "{" in name and "}" in name and ".background" not in self.name:
            coordinatesString: str = name[name.index("{") + 1 : name.index("}")]
            coordinatesMap: Dict[str, float] = {
                axis.axisId: float(c)
                for c, axis in zip(coordinatesString.split(","), font.axes)
            }
            master: Optional[GSFontMaster] = None
            for axis in font.axes:
                if axis.axisId not in coordinatesMap:
                    if master is None:
                        master = font.masters[self.associatedMasterId]
                    value = master.internalAxesValues[axis.axisId]
                    coordinatesMap[axis.axisId] = value
            self.attributes[LAYER_ATTRIBUTE_COORDINATES] = coordinatesMap

        if "Color" in name:
            m = re.match(self.COLOR_PALETTE_LAYER_RE, self.name.strip())
            if m and m.group("index"):
                palette: Union[int, str] = m.group("index")
                if palette != "*":
                    palette = int(palette)
                name = name.replace(m.group(0), "").replace("  ", " ").strip()
                self.attributes[LAYER_ATTRIBUTE_COLOR_PALETTE] = palette
            elif name.startswith("Color"):
                name = name.replace("Color", "").replace("  ", " ").strip()
                self.attributes[LAYER_ATTRIBUTE_COLOR] = True

        if self.name != name:
            self.name = name

    def post_read(self) -> None:  # GSLayer
        assert self.parent
        font: GSFont = self.font
        if font.formatVersion == 2:

            if hasattr(self, "_paths"):
                self.shapes.extend(self._paths)
                del self._paths
            if hasattr(self, "_components"):
                self.shapes.extend(self._components)
                del self._components
            self.layer_name_to_attributes()

            if not self.smartComponentPoleMapping and "PartSelection" in self.userData:
                self.smartComponentPoleMapping = self.userData["PartSelection"]
                del self.userData["PartSelection"]
        else:
            if LAYER_ATTRIBUTE_AXIS_RULES in self.attributes:
                rule = self.attributes[LAYER_ATTRIBUTE_AXIS_RULES]
                ruleMap: Dict[str, Any] = {
                    axis.axisId: value for axis, value in zip(font.axes, rule)
                }
                self.attributes[LAYER_ATTRIBUTE_AXIS_RULES] = ruleMap

            if LAYER_ATTRIBUTE_COORDINATES in self.attributes:
                coordinates = self.attributes[LAYER_ATTRIBUTE_COORDINATES]
                coordinatesMap: Dict[str, Any] = {
                    axis.axisId: value for axis, value in zip(font.axes, coordinates)
                }
                master: Optional[GSFontMaster] = None
                for axis in font.axes:
                    if axis.axisId not in coordinatesMap:
                        if master is None:
                            master = font.masters[self.associatedMasterId]
                        value = master.internalAxesValues[axis.axisId]
                        coordinatesMap[axis.axisId] = value
                self.attributes[LAYER_ATTRIBUTE_COORDINATES] = coordinatesMap

    def _parse_shapes_dict(self, parser: Parser, shapes: List[Dict[str, Any]]) -> None:
        for shape_dict in shapes:
            if "ref" in shape_dict:
                shape = parser._parse_dict(shape_dict, GSComponent)
            else:
                shape = parser._parse_dict(shape_dict, GSPath)
            self.shapes.append(shape)

    def _parse_background_dict(self, parser, value):
        self._background = parser._parse(value, GSBackgroundLayer)
        self._background._foreground = self
        self._background.parent = self.parent

    _defaultsForName: Dict[str, Optional[Union[int, float]]] = {
        "width": 600,
        "metricLeft": None,
        "metricRight": None,
        "metricWidth": None,
        "vertWidth": None,
        "vertOrigin": None,
    }

    def __copy__(self) -> "GSLayer":
        new_obj = self.__class__()
        new_obj._anchors = copy.copy(self._anchors)
        new_obj._annotations = copy.copy(self._annotations)
        new_obj._background = copy.copy(self._background)
        new_obj._foreground = None
        new_obj._guides = copy.copy(self._guides)
        new_obj._hints = copy.copy(self._hints)
        new_obj._layerId = self._layerId
        new_obj._name = copy.copy(self._name)
        new_obj._shapes = copy.copy(self._shapes)
        new_obj._userData = copy.copy(self._userData)
        new_obj.attributes = copy.copy(self.attributes)
        new_obj.smartComponentPoleMapping = copy.copy(self.smartComponentPoleMapping)
        new_obj.associatedMasterId = self.associatedMasterId
        new_obj.backgroundImage = copy.copy(self.backgroundImage)
        new_obj.color = copy.copy(self.color)
        new_obj.widthMetricsKey = self.widthMetricsKey
        new_obj.leftMetricsKey = self.leftMetricsKey
        new_obj.rightMetricsKey = self.rightMetricsKey
        new_obj.topMetricsKey = self.topMetricsKey
        new_obj.bottomMetricsKey = self.bottomMetricsKey
        new_obj.vertOrigin = self.vertOrigin
        new_obj.vertWidth = self.vertWidth
        new_obj.visible = self.visible
        new_obj.width = self.width
        return new_obj

    def _str(self) -> str:
        name: str = self.name
        try:
            name = self.name
        except AttributeError:
            name = "orphan (n)"
        try:
            assert self.parent and self.parent.name
            parent: str = self.parent.name
        except (AttributeError, AssertionError):
            parent = "orphan"
        return f'"{name}" ({parent})'

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {hex(id(self))}> {self._str()}'

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} {self._str()}>'

    def __lt__(self, other: "GSLayer") -> bool:
        if self.master and other.master and self.isMasterLayer:
            for axis in self.font.axes:
                value = self.master.internalAxesValues[axis.axisId]
                other_value = other.master.internalAxesValues[axis.axisId]
                if value != other_value:
                    return value < other_value
        return False

    @property
    def parent(self) -> GSGlyph:
        return cast(GSGlyph, self._parent)

    @parent.setter
    def parent(self, value: Optional[GSGlyph]) -> None:
        self._parent = value

    @property
    def layerId(self) -> str:
        return self._layerId

    @layerId.setter
    def layerId(self, value: str) -> None:
        self._layerId = value
        """ # FIXME: this is not the right place to do this. Maybe `_setupLayer`
        # Update the layer map in the parent glyph, if any.
        if self.parent:
            parent_layers = OrderedDict()
            updated = False
            for id, layer in self.parent._layers.items():
                if layer == self:
                    parent_layers[self._layerId] = self
                    updated = True
                else:
                    parent_layers[id] = layer
            if not updated:
                parent_layers[self._layerId] = self
            self.parent._layers = parent_layers
        """

    @property
    def master(self) -> Optional["GSFontMaster"]:
        if self.associatedMasterId and self.parent:
            return self.parent.parent.masterForId(self.associatedMasterId)
        return None

    @property
    def font(self) -> "GSFont":
        glyph = self.parent
        assert glyph and glyph.parent
        return glyph.parent

    def _name_from_attributes(self) -> Optional[str]:
        # For Glyphs 3's special layers (brace, bracket, color) we must generate the
        # name from the attributes (as it's shown in Glyphs.app UI) and discard
        # the layer's actual 'name' as found in the source file, which is usually just
        # the unique date-time when a layer was first created.
        # Using the generated name ensures that all the intermediate glyph instances
        # at a given location end up in the same UFO source layer, see:
        # https://github.com/googlefonts/glyphsLib/issues/851
        nameStrings: List[str] = []

        name: Optional[str] = self._colorNameString()
        if name:
            nameStrings.append(name)

        if self.isBracketLayer:
            name = self._bracket_layer_name()
            if name:
                nameStrings.append(name)
        if self.isBraceLayer:
            name = self._brace_layer_name()
            if name:
                nameStrings.append(name)

        if nameStrings:
            return " ".join(nameStrings)
        return None

    def layerKey(self) -> str:
        if not self.font:
            return self._name

        name: Optional[str]
        if self.isMasterLayer:
            master: Optional[GSFontMaster] = self.font.masters[self.associatedMasterId]
            name = "-"
            if master:
                name = master.name
            if self.isBracketLayer:
                rule_name: Optional[str] = self._bracket_layer_name()
                if rule_name:
                    name = f"{name} {rule_name}"
            return name

        name_strings: List[str] = []
        name = self._colorNameString()
        if name:
            """
            There can be more than one layer with the same palette index.
            So we need to add a counter suffix to distinguish them.
            """
            if self.isColorPaletteLayer:
                color_palette_layer_counter: int = 0
                color_idx: int = int(self.attributes[LAYER_ATTRIBUTE_COLOR_PALETTE])
                for layer in self.parent.layers:
                    if layer == self:
                        break
                    if layer.associatedMasterId != self.associatedMasterId:
                        continue
                    other_color_idx = layer.attributes.get(LAYER_ATTRIBUTE_COLOR_PALETTE, None)
                    if other_color_idx is not None and int(other_color_idx) == color_idx:
                        color_palette_layer_counter += 1
                if color_palette_layer_counter > 0:
                    name = f"{name}_{color_palette_layer_counter}"
            name_strings.append(name)

        if self.isBracketLayer:
            font_master: Optional[GSFontMaster] = self.font.masters[self.associatedMasterId]
            if font_master:
                name_strings.append(font_master.name)
            name = self._bracket_layer_name()
            if name:
                name_strings.append(name)

        if self.isBraceLayer:
            name = self._brace_layer_name()
            if name:
                name_strings.append(name)

        if name_strings:
            return " ".join(name_strings)
        return self._name

    def _colorNameString(self) -> Optional[str]:
        if self.isFullColorLayer:
            return "Color"

        colorPalette: Optional[int] = self.attributes.get(LAYER_ATTRIBUTE_COLOR_PALETTE, None)
        if colorPalette is not None:
            return f"Color {colorPalette}"

        sbixSize: Optional[int] = self.attributes.get(LAYER_ATTRIBUTE_SBIX_SIZE, None)
        if sbixSize is not None:
            return f"iColor {sbixSize}"

        if self.isSVGColorLayer:
            return "svg"

        return None

    def _legacyName(self) -> str:
        """
        The layer name to write it to a Glyphs 2 file.
        """
        if self.font is None:
            return self._name

        nameStrings: List[str] = []

        colorNameString: Optional[str] = self._colorNameString()
        if colorNameString:
            nameStrings.append(colorNameString)

        axisRules: Optional[Dict[str, Dict[str, Any]]] = self.attributes.get(LAYER_ATTRIBUTE_AXIS_RULES, None)
        if axisRules:
            axis = self.font.axes[0]
            rule: Optional[Dict[str, Any]] = axisRules.get(axis.axisId, None)
            if rule is None:
                raise ValueError("Glyphs 2 can only handle axis rules for the first axis")
            minValue: Optional[float] = rule.get("min", None)
            maxValue: Optional[float] = rule.get("max", None)
            if (minValue and maxValue) or len(axisRules) > 1:
                raise ValueError("Glyphs 2 can’t handle ranges in axis rules")
            if minValue:
                nameStrings.append(f"[{floatToString3(minValue)}]")
            elif maxValue:
                nameStrings.append(f"]{floatToString3(maxValue)}]")
            else:
                nameStrings.append("[]")

        if self.isBraceLayer:
            brace_layer_name: Optional[str] = self._brace_layer_name()
            if brace_layer_name:
                nameStrings.append(brace_layer_name)

        return " ".join(nameStrings)

    def _brace_layer_name(self) -> Optional[str]:
        if not self.isBraceLayer:
            return None
        coordinates: Dict[str, float] = self.attributes[LAYER_ATTRIBUTE_COORDINATES]
        return f"{{{', '.join(floatToString5(v) for v in coordinates.values())}}}"

    def _bracket_layer_name(self) -> Optional[str]:
        axisRules: Dict[str, Dict[str, Any]] = self.attributes[LAYER_ATTRIBUTE_AXIS_RULES]
        if not axisRules or not isinstance(axisRules, dict):
            return None

        ruleStrings: List[str] = []
        for axis in self.font.axes:
            rule: Optional[Dict[str, Any]] = axisRules.get(axis.axisId, None)
            if rule is None:
                continue
            minValue: Optional[float] = rule.get("min", None)
            maxValue: Optional[float] = rule.get("max", None)
            if minValue and maxValue:
                ruleStrings.append(
                    "%s‹%s‹%s" % (floatToString3(minValue), axis.shortAxisTag, floatToString3(maxValue))
                )
            elif minValue:
                ruleStrings.append(
                    "%s‹%s" % (floatToString3(minValue), axis.shortAxisTag)
                )
            elif maxValue:
                ruleStrings.append(
                    "%s‹%s" % (axis.shortAxisTag, floatToString3(maxValue))
                )

        if ruleStrings:
            return "[%s]" % ", ".join(ruleStrings)
        return "[]"

    def _COLR_layer_name(self) -> str:
        palette: int = self.attributes[LAYER_ATTRIBUTE_COLOR_PALETTE]
        return f"Color {palette}"

    def _sbix_layer_name(self) -> str:
        sbixSize: int = self.attributes[LAYER_ATTRIBUTE_SBIX_SIZE]
        return f"iColor {sbixSize}"

    def _svg_layer_name(self) -> Optional[str]:
        svg: Optional[Any] = self.attributes[LAYER_ATTRIBUTE_SVG]
        return "svg" if svg else None

    @property
    def name(self):
        if self.isMasterLayer and self.parent and self.parent.parent:
            master = self.parent.parent.masterForId(self.associatedMasterId)
            if master:
                return master.name
        name = self._name_from_attributes()
        if name:
            return name
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    anchors = property(
        lambda self: LayerAnchorsProxy(self),
        lambda self, value: LayerAnchorsProxy(self).setter(value),
    )

    hints = property(
        lambda self: LayerHintsProxy(self),
        lambda self, value: LayerHintsProxy(self).setter(value),
    )

    paths = property(
        lambda self: LayerPathsProxy(self),
        lambda self, value: LayerPathsProxy(self).setter(value),
    )

    components = property(
        lambda self: LayerComponentsProxy(self),
        lambda self, value: LayerComponentsProxy(self).setter(value),
    )

    shapes = property(
        lambda self: LayerShapesProxy(self),
        lambda self, value: LayerShapesProxy(self).setter(value),
    )

    guides = property(
        lambda self: LayerGuideLinesProxy(self),
        lambda self, value: LayerGuideLinesProxy(self).setter(value),
    )

    annotations = property(
        lambda self: LayerAnnotationProxy(self),
        lambda self, value: LayerAnnotationProxy(self).setter(value),
    )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def bounds(self) -> Optional[Rect]:
        left, bottom, right, top = None, None, None, None

        for item in self.shapes:
            newLeft, newBottom, newWidth, newHeight = item.bounds
            newRight = newLeft + newWidth
            newTop = newBottom + newHeight

            if left is None:
                left = newLeft
            else:
                left = min(left, newLeft)
            if bottom is None:
                bottom = newBottom
            else:
                bottom = min(bottom, newBottom)
            if right is None:
                right = newRight
            else:
                right = max(right, newRight)
            if top is None:
                top = newTop
            else:
                top = max(top, newTop)

        if (
            left is not None
            and bottom is not None
            and right is not None
            and top is not None
        ):
            return Rect(Point(left, bottom), Size(right - left, top - bottom))
        return None

    def _find_node_by_indices(self, point: Tuple[int, int]) -> "GSNode":
        """Find the GSNode that is referred to by the given indices.

        See GSNode::_indices()
        """
        path_index, node_index = point
        path = self.paths[int(path_index)]
        node = path.nodes[int(node_index)]
        return node

    @property
    def background(self) -> "GSBackgroundLayer":
        """Only a getter on purpose. See the tests."""
        if self._background is None:
            self._background = GSBackgroundLayer()
            self._background._foreground = self
            self._background.parent = self.parent
        return self._background

    @property
    def hasBackground(self) -> bool:
        return bool(self._background)

    @property
    def foreground(self) -> None:
        """Forbidden, and also forbidden to set it."""
        raise AttributeError

    def getPen(self) -> AbstractPen:
        """Returns a pen for others to draw into self."""
        pen = SegmentToPointPen(self.getPointPen())
        return pen

    def getPointPen(self) -> AbstractPointPen:

        from glyphsLib.pens import LayerPointPen

        """Returns a point pen for others to draw points into self."""
        pointPen = LayerPointPen(self)
        return pointPen

    def draw(self, pen: AbstractPen) -> None:
        """Draws glyph with the given pen."""
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of glyph with the given point pen."""
        for shape in self.shapes:
            shape.drawPoints(pointPen)

    @property
    def leftMetricsKey(self) -> Optional[str]:
        return self._leftMetricsKey

    @leftMetricsKey.setter
    def leftMetricsKey(self, value: Optional[str]) -> None:
        self._leftMetricsKey = value

    @property
    def rightMetricsKey(self) -> Optional[str]:
        return self._rightMetricsKey

    @rightMetricsKey.setter
    def rightMetricsKey(self, value: Optional[str]) -> None:
        self._rightMetricsKey = value

    @property
    def widthMetricsKey(self) -> Optional[str]:
        return self._widthMetricsKey

    @widthMetricsKey.setter
    def widthMetricsKey(self, value: Optional[str]) -> None:
        self._widthMetricsKey = value

    @property
    def topMetricsKey(self) -> Optional[str]:
        return self._topMetricsKey

    @topMetricsKey.setter
    def topMetricsKey(self, value: Optional[str]) -> None:
        self._topMetricsKey = value

    @property
    def bottomMetricsKey(self) -> Optional[str]:
        return self._bottomMetricsKey

    @bottomMetricsKey.setter
    def bottomMetricsKey(self, value: Optional[str]) -> None:
        self._bottomMetricsKey = value

    @property
    def vertWidthMetricsKey(self) -> Optional[str]:
        return self._vertWidthMetricsKey

    @vertWidthMetricsKey.setter
    def vertWidthMetricsKey(self, value: Optional[str]) -> None:
        self._vertWidthMetricsKey = value

    @property
    def vertOriginMetricsKey(self) -> Optional[str]:
        return self._vertOriginMetricsKey

    @vertOriginMetricsKey.setter
    def vertOriginMetricsKey(self, value: Optional[str]) -> None:
        self._vertOriginMetricsKey = value

    @property
    def isMasterLayer(self) -> bool:
        return self.layerId == self.associatedMasterId

    @property
    def isBracketLayer(self) -> bool:
        return LAYER_ATTRIBUTE_AXIS_RULES in self.attributes

    @property
    def isBraceLayer(self) -> bool:
        return LAYER_ATTRIBUTE_COORDINATES in self.attributes

    @property
    def isFullColorLayer(self) -> bool:
        return LAYER_ATTRIBUTE_COLOR in self.attributes

    @property
    def isColorPaletteLayer(self) -> bool:
        return self._color_palette_index() is not None

    @property
    def isSVGColorLayer(self) -> bool:
        return LAYER_ATTRIBUTE_SVG in self.attributes

    def _color_palette_index(self) -> Optional[int]:
        index = self.attributes.get(LAYER_ATTRIBUTE_COLOR_PALETTE, None)
        if index is None:
            return None
        if index == "*":
            return 0xFFFF
        if isinstance(index, str) and not index.isdecimal():
            return None
        return int(index)

    @property
    def isAppleColorLayer(self) -> bool:
        return LAYER_ATTRIBUTE_SBIX_SIZE in self.attributes

    @property
    def hasPathComponents(self) -> bool:
        return any(h.isPathComponent for h in self.hints)

    @property
    def hasCorners(self) -> bool:
        return self.hasPathComponents


GSLayer._add_parsers(
    [
        {
            "plist_name": "annotations",
            "object_name": "_annotations",
            "type": GSAnnotation,
        },
        {"plist_name": "backgroundImage", "type": GSBackgroundImage},
        {"plist_name": "paths", "object_name": "_paths", "type": GSPath},
        {"plist_name": "anchors", "type": GSAnchor},
        {"plist_name": "guideLines", "object_name": "guides", "type": GSGuide},  # V2
        {"plist_name": "guides", "type": GSGuide},  # V3
        {"plist_name": "components", "object_name": "_components", "type": GSComponent},
        {"plist_name": "hints", "type": GSHint},
        {"plist_name": "userData", "object_name": "_userData", "type": dict},
        {
            "plist_name": "partSelection",
            "object_name": "smartComponentPoleMapping",
            "type": dict,
        },
        {"plist_name": "leftMetricsKey", "type": str},  # V2
        {"plist_name": "rightMetricsKey", "type": str},  # V2
        {"plist_name": "widthMetricsKey", "type": str},  # V2
        {"plist_name": "topMetricsKey", "type": str},  # V2
        {"plist_name": "bottomMetricsKey", "type": str},  # V2
        {"plist_name": "vertOriginMetricsKey", "type": str},  # V2
        {"plist_name": "vertWidthMetricsKey", "type": str},  # V2
        {"plist_name": "metricLeft", "object_name": "leftMetricsKey", "type": str},  # V3
        {"plist_name": "metricRight", "object_name": "rightMetricsKey", "type": str},  # V3
        {"plist_name": "metricWidth", "object_name": "widthMetricsKey", "type": str},  # V3
        {"plist_name": "metricTop", "object_name": "topMetricsKey", "type": str},  # V3
        {"plist_name": "metricBottom", "object_name": "bottomMetricsKey", "type": str},  # V3
        {"plist_name": "metricVertOrigin", "object_name": "vertOriginMetricsKey", "type": str},  # V3
        {"plist_name": "metricVertWidth", "object_name": "vertWidthMetricsKey", "type": str},  # V3
        {"plist_name": "attr", "object_name": "attributes", "type": dict},  # V3
    ]
)


class GSBackgroundLayer(GSLayer):

    @property  # type: ignore
    def background(self) -> None:  # type: ignore
        return None

    @property
    def foreground(self) -> GSLayer:  # type: ignore
        return self._foreground  # type: ignore

    # The width property of this class behaves like this in Glyphs:
    #  - Always return the width of the foreground
    #  - Settable but does not remember the value (basically useless)
    # Reproduce this behaviour here so that the roundtrip does not rely on it.
    @property
    def width(self) -> float:
        return self._foreground.width if self._foreground else 0.0

    @width.setter
    def width(self, whatever: Optional[float]) -> None:
        pass


class GSGlyph(GSBase):

    _parent: Optional[GSFont] = None

    def __init__(self, name: Optional[str] = None) -> None:
        self._layers: OrderedDict[str, Any] = OrderedDict()
        self._unicodes: List[str] = []
        self._category: Optional[str] = None
        self._subCategory: Optional[str] = None
        self._case: GSCase = None
        self.color: Optional[Any] = None
        self.export: bool = self._defaultsForName["export"]
        self.lastChange: Optional[Any] = None
        self.name: str = name or "new glyph"  # make name not optional to simpify usage
        self.note: Optional[str] = None
        self.locked: bool = False
        self.smartComponentAxes: List[Any] = []
        self.production: str = ""
        self.script: Optional[str] = None
        self.selected: bool = False
        self.tags: List[str] = []
        self._userData: Optional[dict] = None
        self.sortName: Optional[str] = None
        self.sortNameKeep: Optional[str] = None
        self.direction: GSWritingDirection = GSLTR

        self._bottomKerningGroup: Optional[str] = None
        self._leftKerningGroup: Optional[str] = None
        self._rightKerningGroup: Optional[str] = None
        self._topKerningGroup: Optional[str] = None

        self._bottomMetricsKey: Optional[str] = None
        self._leftMetricsKey: Optional[str] = None
        self._rightMetricsKey: Optional[str] = None
        self._topMetricsKey: Optional[str] = None
        self._vertOriginMetricsKey: Optional[str] = None
        self._vertWidthMetricsKey: Optional[str] = None
        self._widthMetricsKey: Optional[str] = None

    def _serialize_to_plist(self, writer: Writer) -> None:
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "case")
            writer.writeObjectKeyValue(self, "category")
        writer.writeObjectKeyValue(self, "color")
        writer.writeObjectKeyValue(self, "direction", "if_true")
        writer.writeObjectKeyValue(self, "export", not self.export)
        writer.writeKeyValue("glyphname", self.name)
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "production", "if_true")
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(
                self, "bottomKerningGroup", "if_true", keyName="kernBottom"
            )
            writer.writeObjectKeyValue(
                self, "leftKerningGroup", "if_true", keyName="kernLeft"
            )
            writer.writeObjectKeyValue(
                self, "rightKerningGroup", "if_true", keyName="kernRight"
            )
            writer.writeObjectKeyValue(
                self, "topKerningGroup", "if_true", keyName="kernTop"
            )

        writer.writeObjectKeyValue(self, "lastChange")
        writer.writeObjectKeyValue(self, "layers", "if_true")

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "leftKerningGroup", "if_true")
            writer.writeObjectKeyValue(self, "leftMetricsKey", "if_true")
            writer.writeObjectKeyValue(self, "widthMetricsKey", "if_true")
            writer.writeObjectKeyValue(self, "vertWidthMetricsKey", "if_true")

        writer.writeObjectKeyValue(self, "locked", "if_true")

        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(self, "bottomMetricsKey", "if_true", keyName="metricBottom")
            writer.writeObjectKeyValue(self, "leftMetricsKey", "if_true", keyName="metricLeft")
            writer.writeObjectKeyValue(self, "rightMetricsKey", "if_true", keyName="metricRight")
            writer.writeObjectKeyValue(self, "topMetricsKey", "if_true", keyName="metricTop")
            writer.writeObjectKeyValue(self, "vertOriginMetricsKey", "if_true", keyName="metricVertOrigin")
            writer.writeObjectKeyValue(self, "vertWidthMetricsKey", "if_true", keyName="metricVertWidth")
            writer.writeObjectKeyValue(self, "widthMetricsKey", "if_true", keyName="metricWidth")

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "rightKerningGroup", "if_true")
            writer.writeObjectKeyValue(self, "rightMetricsKey", "if_true")
            writer.writeObjectKeyValue(self, "topKerningGroup", "if_true")
            writer.writeObjectKeyValue(self, "topMetricsKey", "if_true")
            writer.writeObjectKeyValue(self, "bottomKerningGroup", "if_true")
            writer.writeObjectKeyValue(self, "bottomMetricsKey", "if_true")

        writer.writeObjectKeyValue(self, "note", "if_true")

        if self.unicodes and writer.formatVersion == 2:
            writer.writeKeyValue("unicode", self.unicodes)
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "production", "if_true")

        writer.writeObjectKeyValue(self, "script")
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "category")

        if self.sortName:
            writer.writeKeyValue("sortName", self.sortName)
        if self.sortNameKeep:
            writer.writeKeyValue("sortNameKeep", self.sortNameKeep)

        writer.writeObjectKeyValue(self, "subCategory")
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "tags", "if_true")

        if self.unicodes and writer.formatVersion > 2:
            count_of_unicodes: int = len(self.unicodes)
            if count_of_unicodes == 1:
                writer.writeKeyValue("unicode", int(self.unicodes[0], 16))
            else:
                v: OneLineList = OneLineList([str(int(u, 16)) for u in self.unicodes])
                writer.writeKeyValue("unicode", v)

        writer.writeObjectKeyValue(self, "userData", "if_true")

        if self.smartComponentAxes:
            writer.writeKeyValue("partsSettings", self.smartComponentAxes)

    _defaultsForName: Dict[str, Any] = {
        "export": True,
    }

    def _parse_unicode_dict(self, parser: Parser, value: Union[int, List[int]]) -> None:
        parser.current_type = None

        uni: Optional[Union[str, list]] = None

        if parser.formatVersion >= 3:
            if not isinstance(value, list):
                value = [value]
            uni = ["%04X" % x for x in value]
        elif isinstance(value, int):
            # This is unfortunate. We've used the openstep_plist parser with
            # use_numbers=True, and it's seen something like "0041". It's
            # then interpreted this as a *decimal* integer. We have to make it
            # look like a hex string again
            uni = ["%04i" % value]
        else:
            uni = cast(str, value)
        self["_unicodes"] = UnicodesList(uni)

    def _parse_layers_dict(self, parser: Parser, value: Any) -> int:
        layers = parser._parse(value, GSLayer)
        for l in layers:
            self.layers.append(l)
        return 0

    def post_read(self) -> None:  # GSGlyph
        for layer in self.layers:
            layer.post_read()

    def __repr__(self) -> str:
        return f'<GSGlyph {hex(id(self))}> "{self.name}" with {len(self.layers)} layers'

    def __str__(self) -> str:
        return f'<GSGlyph "{self.name}" with {len(self.layers)} layers>'

    layers = property(
        lambda self: GlyphLayerProxy(self),
        lambda self, value: GlyphLayerProxy(self).setter(value),
    )

    def _setupLayer(self, layer: Any, key: str) -> None:
        assert isinstance(key, str)
        layer.parent = self
        if layer.hasBackground:
            layer._background.parent = self
        layer.layerId = key
        # TODO use proxy `self.parent.masters[key]`
        if self.parent and self.parent.masterForId(key):
            layer.associatedMasterId = key

    # def setLayerForKey(self, layer, key):
    #     if Layer and Key:
    #         Layer.parent = self
    #         Layer.layerId = Key
    #         if self.parent.fontMasterForId(Key):
    #             Layer.associatedMasterId = Key
    #         self._layers[key] = layer

    def removeLayerForKey(self, key: str) -> None:
        for layer in list(self._layers):
            if layer == key:
                del self._layers[key]

    @property
    def parent(self) -> GSFont:
        return cast(GSFont, self._parent)

    @parent.setter
    def parent(self, value: Optional[GSFont]) -> None:
        self._parent = value

    @property
    def string(self) -> Optional[str]:
        if self.unicode:
            return chr(int(self.unicode, 16))
        return None

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def glyphname(self) -> str:
        return self.name

    @glyphname.setter
    def glyphname(self, value: str) -> None:
        self.name = value

    @property
    def category(self) -> Optional[str]:
        return self._category

    @category.setter
    def category(self, value: Optional[str]) -> None:
        self._category = value

    @property
    def subCategory(self) -> Optional[str]:
        return self._subCategory

    @subCategory.setter
    def subCategory(self, value: Optional[str]) -> None:
        self._subCategory = value

    @property
    def smartComponentAxes(self) -> List[Any]:
        return self.partsSettings

    @smartComponentAxes.setter
    def smartComponentAxes(self, value: List[Any]) -> None:
        self.partsSettings = value

    @property
    def id(self) -> Optional[str]:
        """An unique identifier for each glyph"""
        return self.name

    @property
    def unicode(self) -> Optional[str]:
        if self._unicodes:
            return self._unicodes[0]
        return None

    @unicode.setter
    def unicode(self, unicode: Union[str, List[str]]) -> None:
        self._unicodes = UnicodesList(unicode)

    @property
    def unicodes(self) -> List[str]:
        return self._unicodes

    @unicodes.setter
    def unicodes(self, unicodes: Union[str, List[str]]) -> None:
        self._unicodes = UnicodesList(unicodes)

    @property
    def leftKerningGroup(self) -> Optional[str]:
        return self._leftKerningGroup

    @leftKerningGroup.setter
    def leftKerningGroup(self, value: Optional[str]) -> None:
        self._leftKerningGroup = value

    @property
    def rightKerningGroup(self) -> Optional[str]:
        return self._rightKerningGroup

    @rightKerningGroup.setter
    def rightKerningGroup(self, value: Optional[str]) -> None:
        self._rightKerningGroup = value

    @property
    def topKerningGroup(self) -> Optional[str]:
        return self._topKerningGroup

    @topKerningGroup.setter
    def topKerningGroup(self, value: Optional[str]) -> None:
        self._topKerningGroup = value

    @property
    def bottomKerningGroup(self) -> Optional[str]:
        return self._bottomKerningGroup

    @bottomKerningGroup.setter
    def bottomKerningGroup(self, value: Optional[str]) -> None:
        self._bottomKerningGroup = value

    @property
    def leftMetricsKey(self) -> Optional[str]:
        return self._leftMetricsKey

    @leftMetricsKey.setter
    def leftMetricsKey(self, value: Optional[str]) -> None:
        self._leftMetricsKey = value

    @property
    def rightMetricsKey(self) -> Optional[str]:
        return self._rightMetricsKey

    @rightMetricsKey.setter
    def rightMetricsKey(self, value: Optional[str]) -> None:
        self._rightMetricsKey = value

    @property
    def widthMetricsKey(self) -> Optional[str]:
        return self._widthMetricsKey

    @widthMetricsKey.setter
    def widthMetricsKey(self, value: Optional[str]) -> None:
        self._widthMetricsKey = value

    @property
    def topMetricsKey(self) -> Optional[str]:
        return self._topMetricsKey

    @topMetricsKey.setter
    def topMetricsKey(self, value: Optional[str]) -> None:
        self._topMetricsKey = value

    @property
    def bottomMetricsKey(self) -> Optional[str]:
        return self._bottomMetricsKey

    @bottomMetricsKey.setter
    def bottomMetricsKey(self, value: Optional[str]) -> None:
        self._bottomMetricsKey = value

    @property
    def vertWidthMetricsKey(self) -> Optional[str]:
        return self._vertWidthMetricsKey

    @vertWidthMetricsKey.setter
    def vertWidthMetricsKey(self, value: Optional[str]) -> None:
        self._vertWidthMetricsKey = value

    @property
    def vertOriginMetricsKey(self) -> Optional[str]:
        return self._vertOriginMetricsKey

    @vertOriginMetricsKey.setter
    def vertOriginMetricsKey(self, value: Optional[str]) -> None:
        self._vertOriginMetricsKey = value

    '''
    @property
    def note(self):
        return self._note

    @note.setter
    def note(self, value):
        self._note = value
    '''


GSGlyph._add_parsers(
    [
        {"plist_name": "glyphname", "object_name": "name"},
        {
            "plist_name": "partsSettings",
            "object_name": "partsSettings",
            "type": GSSmartComponentAxis,
        },
        {"plist_name": "export", "object_name": "export", "converter": bool},
        {
            "plist_name": "lastChange",
            "object_name": "lastChange",
            "converter": parse_datetime,
        },
        {"plist_name": "kernLeft", "object_name": "leftKerningGroup"},  # V3
        {"plist_name": "kernRight", "object_name": "rightKerningGroup"},  # V3
        {"plist_name": "kernBottom", "object_name": "bottomKerningGroup"},  # V3
        {"plist_name": "kernTop", "object_name": "topKerningGroup"},  # V3

        {"plist_name": "leftMetricsKey", "type": str},  # V2
        {"plist_name": "rightMetricsKey", "type": str},  # V2
        {"plist_name": "widthMetricsKey", "type": str},  # V2
        {"plist_name": "topMetricsKey", "type": str},  # V2
        {"plist_name": "bottomMetricsKey", "type": str},  # V2
        {"plist_name": "vertOriginMetricsKey", "type": str},  # V2
        {"plist_name": "vertWidthMetricsKey", "type": str},  # V2
        {"plist_name": "metricLeft", "object_name": "leftMetricsKey", "type": str},  # V3
        {"plist_name": "metricRight", "object_name": "rightMetricsKey", "type": str},  # V3
        {"plist_name": "metricWidth", "object_name": "widthMetricsKey", "type": str},  # V3
        {"plist_name": "metricTop", "object_name": "topMetricsKey", "type": str},  # V3
        {"plist_name": "metricBottom", "object_name": "bottomMetricsKey", "type": str},  # V3
        {"plist_name": "metricVertOrigin", "object_name": "vertOriginMetricsKey", "type": str},  # V3
        {"plist_name": "metricVertWidth", "object_name": "vertWidthMetricsKey", "type": str},  # V3

        {"plist_name": "sortName", "object_name": "sortName"},
        {"plist_name": "sortNameKeep", "object_name": "sortNameKeep"},
        {"plist_name": "direction", "object_name": "direction"},
    ]
)


class GSFont(GSBase):
    _defaultsForName: Dict[str, Any] = {
        "classes": [],
        "features": [],
        "featurePrefixes": [],
        "disablesAutomaticAlignment": False,
        "disablesNiceNames": False,
        "grid": 1,
        "gridSubDivision": 1,
        "unitsPerEm": 1000,
        "kerning": OrderedDict(),
        "keyboardIncrement": 1,
        "keyboardIncrementBig": 10,
        "keyboardIncrementHuge": 100,
    }

    def __init__(
        self, path: Optional[Union[str, bytes, os.PathLike[str], os.PathLike[bytes]]] = None
    ) -> None:
        self.displayStrings: str = ""
        self.familyName: str = "Unnamed font"
        self.fontType: FontType = FontType.DEFAULT
        self._glyphs: List[GSGlyph] = []
        self._instances: List[GSInstance] = []
        self._masters: List[GSFontMaster] = []
        self.axes: List[GSAxis] = []
        self._userData: Optional[Dict[str, Any]] = None
        self._versionMinor: int = 0
        self.formatVersion: int = 3
        self.appVersion: str = "3260"  # minimum required version
        self._classes: List[GSClass] = []
        self._features: List[GSFeature] = []
        self._featurePrefixes: List[GSFeaturePrefix] = []
        self.customParameters = []
        self.date: Optional[Any] = None
        self._disablesAutomaticAlignment: Optional[bool] = self._defaultsForName["disablesAutomaticAlignment"]
        self.disablesNiceNames: bool = self._defaultsForName["disablesNiceNames"]
        self.grid: int = self._defaultsForName["grid"]
        self.gridSubDivision: int = self._defaultsForName["gridSubDivision"]
        self.keepAlternatesTogether: bool = False
        self._kerningLTR: Dict[str, Dict[str, Dict[str, int]]] = OrderedDict()
        self._kerningRTL: Dict[str, Dict[str, Dict[str, int]]] = OrderedDict()
        self._kerningVertical: Dict[str, Dict[str, Dict[str, int]]] = OrderedDict()
        self.metrics: List[GSMetric] = copy.copy(self._defaultMetrics)
        self._numbers: List[GSMetric] = []
        self._properties: List[Any] = []
        self._stems: List[GSMetric] = []
        self.keyboardIncrement: int = self._defaultsForName["keyboardIncrement"]
        self.keyboardIncrementBig: int = self._defaultsForName["keyboardIncrementBig"]
        self.keyboardIncrementHuge: int = self._defaultsForName["keyboardIncrementHuge"]
        self.previewRemoveOverlap: bool = True
        self.upm: int = self._defaultsForName["unitsPerEm"]
        self.versionMajor: int = 1
        self._note: str = ""
        self.readBuffer: Dict[str, Any] = {}

        self.filepath: Optional[str] = None
        if path:
            path = os.fsdecode(os.fspath(path))
            self.filepath = path
            load(path, self)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {hex(id(self))}> "{self.familyName}"'

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} "{self.familyName}">'

    def _serialize_to_plist(self, writer: Writer) -> None:  # noqa: C901
        writer.writeKeyValue(".appVersion", self.appVersion)
        if writer.formatVersion > 2:
            writer.writeKeyValue(".formatVersion", writer.formatVersion)
        if self.displayStrings and writer.container == "flat":
            writer.writeKeyValue("DisplayStrings", self.displayStrings)

        customParameters: List[GSCustomParameter] = list(self.customParameters)
        if writer.formatVersion < 3:
            parameters = GSFontInfoValue.legacyCustomParametersFromProperties(
                self.properties, self
            )
            if parameters:
                customParameters.extend(parameters)
            if self.note:
                parameter = GSCustomParameter("note", self.note)
                customParameters.append(parameter)

        if self.axes:
            if writer.formatVersion >= 3:
                writer.writeObjectKeyValue(self, "axes", "if_true")
            else:
                axes: List[Dict[str, Union[str, int]]] = []
                for axis in self.axes:
                    axesDict: Dict[str, Union[str, int]] = {"Name": axis.name, "Tag": axis.axisTag}
                    if axis.hidden:
                        axesDict["Hidden"] = 1
                    axes.append(axesDict)
                if len(self.masters) > 1 or axes != [{"Name": "Weight", "Tag": "wght"}]:
                    parameter = GSCustomParameter("Axes", axes)
                    customParameters.append(parameter)

        writer.writeObjectKeyValue(self, "classes", "if_true")

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "copyright", "if_true")
        if customParameters:
            writer.writeKeyValue("customParameters", customParameters)
        writer.writeObjectKeyValue(self, "date")

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "designer", "if_true")
            writer.writeObjectKeyValue(self, "designerURL", "if_true")
            writer.writeObjectKeyValue(self, "disablesAutomaticAlignment", "if_true")
            writer.writeObjectKeyValue(self, "disablesNiceNames", "if_true")

        writer.writeObjectKeyValue(self, "familyName")
        if self.featurePrefixes:
            writer.writeObjectKeyValue(self, "featurePrefixes")
        if self.features:
            writer.writeObjectKeyValue(self, "features")
        writer.writeKeyValue("fontMaster", self.masters)

        if writer.container == "flat":
            writer.writeObjectKeyValue(self, "glyphs")

        if writer.formatVersion == 2:
            if self.grid != 1:
                writer.writeKeyValue("gridLength", self.grid)
            if self.gridSubDivision != 1:
                writer.writeKeyValue("gridSubDivision", self.gridSubDivision)

        if len(self.instances) > 0:
            writer.writeObjectKeyValue(self, "instances")

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "keepAlternatesTogether", "if_true")
            writer.writeKerning(self, self.kerningLTR, "kerning")
            if self.kerningVertical:
                writer.writeKerning(self, self.kerningVertical, "vertKerning")
        else:
            writer.writeKerning(self, self.kerningLTR, "kerningLTR")
            writer.writeKerning(self, self.kerningRTL, "kerningRTL")
            writer.writeKerning(self, self.kerningVertical, "kerningVertical")

        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(
                self, "keyboardIncrement", self.keyboardIncrement != 1
            )
            writer.writeObjectKeyValue(
                self, "keyboardIncrementBig", self.keyboardIncrementBig != 10
            )
            writer.writeObjectKeyValue(
                self, "keyboardIncrementHuge", self.keyboardIncrementHuge != 100
            )
            writer.writeObjectKeyValue(self, "manufacturer", "if_true")
            writer.writeObjectKeyValue(self, "manufacturerURL", "if_true")

        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(self, "metrics")
            writer.writeObjectKeyValue(self, "_note", "if_true", keyName="note")
            writer.writeObjectKeyValue(self, "numbers", "if_true")
            if len(self.properties) > 0:
                self._properties.sort(key=lambda key: key.key.lower())
                writer.writeObjectKeyValue(self, "properties")
            writer.writeObjectKeyValue(self, "settings", "if_true")
            writer.writeObjectKeyValue(self, "stems", "if_true")

        writer.writeKeyValue("unitsPerEm", self.upm or 1000)
        writer.writeObjectKeyValue(self, "userData", "if_true")
        writer.writeObjectKeyValue(self, "versionMajor")
        writer.writeObjectKeyValue(self, "versionMinor")

    _defaultMetrics: List[GSMetric] = [
        GSMetric(type=GSMetricsKeyAscender),
        GSMetric(type=GSMetricsKeyCapHeight),
        GSMetric(type=GSMetricsKeyxHeight),
        GSMetric(type=GSMetricsKeyBaseline),
        GSMetric(type=GSMetricsKeyDescender),
        GSMetric(type=GSMetricsKeyItalicAngle),
    ]

    def _parse_glyphs_dict(self, parser: Parser, value: Any) -> int:
        glyphs = parser._parse(value, GSGlyph)
        for l in glyphs:
            self.glyphs.append(l)
        return 0

    def _parse_settings_dict(self, parser: Parser, settings: Dict[str, Any]) -> None:
        self.disablesAutomaticAlignment = bool(
            settings.get("disablesAutomaticAlignment", False)
        )
        self.disablesNiceNames = bool(settings.get("disablesNiceNames", False))
        self.grid = settings.get("gridLength", 1)
        self.gridSubDivision = settings.get("gridSubDivision", 1)
        self.keepAlternatesTogether = bool(
            settings.get("keepAlternatesTogether", False)
        )
        self.keyboardIncrement = settings.get("keyboardIncrement", 1)
        self.keyboardIncrementBig = settings.get("keyboardIncrementBig", 10)
        self.keyboardIncrementHuge = settings.get("keyboardIncrementHuge", 100)
        self.fontType = font_type(settings.get("fontType", "default"))
        self.previewRemoveOverlap = bool(settings.get("previewRemoveOverlap", True))

    def _parse___formatVersion_dict(self, parser: Parser, val: int) -> None:
        self.formatVersion = parser.formatVersion = val

    def save(self, path: Optional[Union[str, os.PathLike[str]]] = None) -> None:
        if path is None:
            if self.filepath:
                path = self.filepath
            else:
                raise ValueError("No path provided and GSFont has no filepath")
        if not isinstance(path, str):  # sometimes we get a Path object
            path = str(path)
        if path.endswith(".glyphs"):
            self.save_flat_file(path)
        elif path.endswith(".glyphspackage"):
            self.save_package_file(path)
        else:
            raise ValueError("unknown file extension on path:", path)

    def save_flat_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fp:
            w = Writer(fp, formatVersion=self.formatVersion)
            logger.info("Writing %r to .glyphs file", self)
            w.write(self)

    def save_package_file(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        glyphs_folder = os.path.join(path, "glyphs")
        os.makedirs(glyphs_folder, exist_ok=True)
        glyph_order: List[str] = []
        for glyph in self.glyphs:
            name: str = glyph.name
            glyph_order.append(name)
            glyph_file_name = os.path.join(
                glyphs_folder, filenames.userNameToFileName(name) + ".glyph"
            )
            with open(glyph_file_name, "w", encoding="utf-8") as fp:
                w = Writer(fp, formatVersion=self.formatVersion)
                logger.info("Writing %r to .glyph file", glyph)
                w.write(glyph)
        glyph_order_file = os.path.join(path, "order.plist")
        with open(glyph_order_file, "w", encoding="utf-8") as fp:
            fp.write("(\n" + ",\n".join(glyph_order) + "\n)")
        info_file = os.path.join(path, "fontinfo.plist")
        with open(info_file, "w", encoding="utf-8") as fp:
            w = Writer(fp, formatVersion=self.formatVersion, container="package")
            w.write(self)
        if self.displayStrings:
            uistate_file = os.path.join(path, "UIState.plist")
            with open(uistate_file, "w", encoding="utf-8") as fp:
                w = Writer(fp, formatVersion=self.formatVersion)
                w.write({"displayStrings": self.displayStrings})

    def _getAxisCountFromMasters(self, masters: List[GSFontMaster]) -> int:
        axisCount: int = 6
        widthValueSet: set = set()
        customValueSet: set = set()
        customValue1Set: set = set()
        customValue2Set: set = set()
        customValue3Set: set = set()
        for master in masters:
            axesValues = self.readBuffer.get("axesValues", [])
            if len(axesValues) > 1:
                widthValueSet.add(axesValues[1])
            if len(axesValues) > 2:
                customValueSet.add(axesValues[2])
            if len(axesValues) > 3:
                customValue1Set.add(axesValues[3])
            if len(axesValues) > 4:
                customValue2Set.add(axesValues[4])
            if len(axesValues) > 5:
                customValue3Set.add(axesValues[5])
        if len(customValue3Set) <= 1:
            axisCount -= 1
            if len(customValue2Set) <= 1:
                axisCount -= 1
                if len(customValue1Set) <= 1:
                    axisCount -= 1
                    if len(customValueSet) <= 1:
                        axisCount -= 1
                        if len(widthValueSet) <= 1:
                            axisCount -= 1
        return axisCount

    def _getLegacyAxes(self) -> List[GSAxis]:
        legacyAxes: List[GSAxis] = []
        axesCount: int = self._getAxisCountFromMasters(self.masters)
        legacyAxes.append(GSAxis("Weight", "wght"))
        legacyAxes[-1].axisId = "a01"
        if axesCount > 1:
            legacyAxes.append(GSAxis("Width", "wdth"))
            legacyAxes[-1].axisId = "a02"
        if axesCount > 2:
            legacyAxes.append(GSAxis("Custom", "CUS1"))
            legacyAxes[-1].axisId = "a03"
        if axesCount > 3:
            legacyAxes.append(GSAxis("Custom2", "CUS2"))
            legacyAxes[-1].axisId = "a03"
        if axesCount > 4:
            legacyAxes.append(GSAxis("Custom3", "CUS3"))
            legacyAxes[-1].axisId = "a04"
        if axesCount > 5:
            legacyAxes.append(GSAxis("Custom4", "CUS4"))
            legacyAxes[-1].axisId = "a05"
        return legacyAxes

    def post_read(self) -> None:  # GSFont
        if self.formatVersion < 3:
            if not self.axes:
                axesParameter: Any = self.customParameters["Axes"]
                if axesParameter:
                    for axisDict in axesParameter:
                        axis: GSAxis = GSAxis()
                        axis.name = axisDict["Name"]
                        axis.axisTag = axisDict["Tag"]
                        axis.hidden = axisDict.get("Hidden", False)
                        axis.axisId = "a%02d" % (len(self.axes) + 1)
                        self.axes.append(axis)
                    del self.customParameters["Axes"]
                else:
                    self.axes = self._getLegacyAxes()
                GSFontInfoValue.propertiesFromLegacyCustomParameters(self)
        else:
            idx: int = 1
            for axis in self.axes:
                axis.axisId = "a%02d" % idx  # This is more cosmetic as the default would do
                idx += 1

        assert self.axes is not None
        for master in self.masters:
            assert master.font == self
            master.post_read()
        for instance in self.instances:
            assert instance.font == self
            instance.post_read()
        for glyph in self.glyphs:
            glyph.post_read()
        for feature in self.features:
            feature.post_read()
        for customParameter in self.customParameters:
            customParameter.post_read(self.formatVersion)

        if self.customParameters["note"]:
            self.note = self.customParameters["note"]
            del self.customParameters["note"]

    def getVersionMinor(self) -> int:
        return self._versionMinor

    def setVersionMinor(self, value: int) -> None:
        """Ensure that the minor version number is between 0 and 999."""
        assert 0 <= value <= 999
        self._versionMinor = value

    versionMinor = property(getVersionMinor, setVersionMinor)

    @property
    def formatVersion(self) -> int:
        return self._formatVersion

    @formatVersion.setter
    def formatVersion(self, value: int) -> None:
        self._formatVersion = value

    @property
    def glyphs(self) -> FontGlyphsProxy:
        return FontGlyphsProxy(self)

    @glyphs.setter
    def glyphs(self, value: Union[List[GSGlyph], FontGlyphsProxy]) -> None:
        FontGlyphsProxy(self).setter(value)

    def _setupGlyph(self, glyph: GSGlyph) -> None:
        glyph.parent = self
        for layer in glyph.layers:
            if (
                not hasattr(layer, "associatedMasterId")
                or layer.associatedMasterId is None
                or len(layer.associatedMasterId) == 0
            ):
                glyph._setupLayer(layer, layer.layerId)

    masters = property(
        lambda self: FontFontMasterProxy(self),
        lambda self, value: FontFontMasterProxy(self).setter(value),
    )

    def masterForId(self, key: str) -> Optional[GSFontMaster]:
        for master in self._masters:
            if master.id == key:
                return master
        return None

    def metricFor(
        self,
        metricType: str,
        filter: Optional[str] = None,
        name: Optional[str] = None,
        add_if_missing: bool = False,
    ) -> Optional[GSMetric]:
        for metric in self.metrics:
            if (
                metric.type == metricType
                and metric.filter == filter
                and metric.name == name
            ):
                return metric
        if add_if_missing:
            metric = GSMetric()
            metric.type = metricType
            metric.filter = filter
            metric.name = name
            self.metrics.append(metric)
            return metric
        return None

    instances = property(
        lambda self: FontInstanceProxy(self),
        lambda self, value: FontInstanceProxy(self).setter(value),
    )

    classes = property(
        lambda self: FontClassesProxy(self),
        lambda self, value: FontClassesProxy(self).setter(value),
    )

    features = property(
        lambda self: FontFeaturesProxy(self),
        lambda self, value: FontFeaturesProxy(self).setter(value),
    )

    featurePrefixes = property(
        lambda self: FontFeaturePrefixesProxy(self),
        lambda self, value: FontFeaturePrefixesProxy(self).setter(value),
    )

    customParameters = property(
        lambda self: CustomParametersProxy(self),
        lambda self, value: CustomParametersProxy(self).setter(value),
    )

    properties = property(
        lambda self: PropertiesProxy(self),
        lambda self, value: PropertiesProxy(self).setter(value),
    )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def stems(self) -> List[GSMetric]:
        return self._stems

    @stems.setter
    def stems(self, stems: List[GSMetric]) -> None:
        assert not stems or isinstance(stems[0], GSMetric)
        self._stems = stems

    def stemForKey(self, key: Union[int, str]) -> Optional[GSMetric]:
        if isinstance(key, int):
            if key < 0:
                key += len(self.stems)
            return self.stems[key]
        elif isString(key):
            return self.stemForName(key) or self.stemForId(key)
        else:
            raise TypeError(
                "list indices must be integers or strings, not %s" % type(key).__name__
            )

    def stemForName(self, key: str) -> Optional[GSMetric]:
        for stem in self._stems:
            if stem.name == key:
                return stem
        return None

    def stemForId(self, key: str) -> Optional[GSMetric]:
        for stem in self._stems:
            if stem.id == key:
                return stem
        return None

    @property
    def numbers(self) -> List[GSMetric]:
        return self._numbers

    @numbers.setter
    def numbers(self, numbers: List[GSMetric]) -> None:
        assert not numbers or isinstance(numbers[0], GSMetric)
        self._numbers = numbers

    def numberForKey(self, key: Union[int, str]) -> Optional[GSMetric]:
        if isinstance(key, int):
            if key < 0:
                key += len(self.numbers)
            return self.numbers[key]
        elif isinstance(key, str):
            return self.numberForName(key) or self.numberForId(key)
        else:
            raise TypeError(
                "list indices must be integers or strings, not %s" % type(key).__name__
            )

    def numberForName(self, key: str) -> Optional[GSMetric]:
        for number in self._numbers:
            if number.name == key:
                return number
        return None

    def numberForId(self, key: str) -> Optional[GSMetric]:
        for number in self._numbers:
            if number.id == key:
                return number
        return None

    @property
    def kerning(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        return self._kerningLTR

    @kerning.setter
    def kerning(self, kerning: Dict[str, Dict[str, Dict[str, int]]]) -> None:
        self.kerningLTR = kerning

    @property
    def kerningLTR(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        return self._kerningLTR

    @kerningLTR.setter
    def kerningLTR(self, kerning: Dict[str, Dict[str, Dict[str, int]]]) -> None:
        self._kerningLTR = kerning
        for master_map in kerning.values():
            for glyph_map in master_map.values():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = parse_float_or_int(value)

    @property
    def kerningRTL(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        return self._kerningRTL

    @kerningRTL.setter
    def kerningRTL(self, kerning: Dict[str, Dict[str, Dict[str, int]]]) -> None:
        self._kerningRTL = kerning
        for master_map in kerning.values():
            for glyph_map in master_map.values():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = parse_float_or_int(value)

    @property
    def kerningVertical(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        return self._kerningVertical

    @kerningVertical.setter
    def kerningVertical(self, kerning: Dict[str, Dict[str, Dict[str, int]]]) -> None:
        self._kerningVertical = kerning
        for master_map in kerning.values():
            for glyph_map in master_map.values():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = parse_float_or_int(value)

    @property
    def selection(self) -> None:
        OnlyInGlyphsAppError

    @property
    def note(self) -> str:
        return self._note

    @note.setter
    def note(self, value: str) -> None:
        self._note = value

    @property
    def gridLength(self) -> int:
        if self.gridSubDivision > 0:
            return self.grid // self.gridSubDivision
        else:
            return self.grid

    @property
    def disablesAutomaticAlignment(self) -> Optional[bool]:
        return self._disablesAutomaticAlignment

    @disablesAutomaticAlignment.setter
    def disablesAutomaticAlignment(self, value: bool) -> None:
        # assert value or self._disablesAutomaticAlignment is None
        self._disablesAutomaticAlignment = value

    EMPTY_KERNING_VALUE: int = (1 << 63) - 1  # As per the documentation

    def kerningForPair(
        self, fontMasterId: str, leftKey: str, rightKey: str, direction: int = LTR
    ) -> int:
        if direction == LTR:
            kerntable = self._kerningLTR
        elif direction == RTL:
            kerntable = self._kerningRTL
        else:
            kerntable = self._kerningVertical
        if not kerntable:
            return self.EMPTY_KERNING_VALUE
        try:
            return kerntable[fontMasterId][leftKey][rightKey]
        except KeyError:
            return self.EMPTY_KERNING_VALUE

    def setKerningForPair(
        self, fontMasterId: str, leftKey: str, rightKey: str, value: int, direction: int = LTR
    ) -> None:
        if direction == LTR:
            if not self._kerningLTR:
                self._kerningLTR = {}
            kerntable = self._kerningLTR
        elif direction == RTL:
            if not self._kerningRTL:
                self._kerningRTL = {}
            kerntable = self._kerningRTL
        else:
            if not self._kerningVertical:
                self._kerningVertical = {}
            kerntable = self._kerningVertical
        if fontMasterId not in kerntable:
            kerntable[fontMasterId] = {}
        if leftKey not in kerntable[fontMasterId]:
            kerntable[fontMasterId][leftKey] = {}
        kerntable[fontMasterId][leftKey][rightKey] = value

    def removeKerningForPair(
        self, fontMasterId: str, leftKey: str, rightKey: str, direction: int = LTR
    ) -> None:
        if direction == LTR:
            kerntable = self._kerningLTR
        elif direction == RTL:
            kerntable = self._kerningRTL
        else:
            kerntable = self._kerningVertical
        if not kerntable:
            return
        if fontMasterId not in kerntable:
            return
        if leftKey not in kerntable[fontMasterId]:
            return
        if rightKey not in kerntable[fontMasterId][leftKey]:
            return
        del kerntable[fontMasterId][leftKey][rightKey]
        if not kerntable[fontMasterId][leftKey]:
            del kerntable[fontMasterId][leftKey]
        if not kerntable[fontMasterId]:
            del kerntable[fontMasterId]

    @property
    def manufacturer(self) -> str:
        return self.properties["manufacturers"]

    @manufacturer.setter
    def manufacturer(self, value: str) -> None:
        self.properties.setProperty("manufacturers", value)

    @property
    def manufacturerURL(self) -> str:
        return self.properties["manufacturerURL"]

    @manufacturerURL.setter
    def manufacturerURL(self, value: str) -> None:
        self.properties["manufacturerURL"] = value

    @property
    def copyright(self) -> str:
        return self.properties["copyrights"]

    @copyright.setter
    def copyright(self, value: str) -> None:
        self.properties.setProperty("copyrights", value)

    @property
    def trademark(self) -> str:
        return self.properties["trademarks"]

    @trademark.setter
    def trademark(self, value: str) -> None:
        self.properties.setProperty("trademarks", value)

    @property
    def designer(self) -> str:
        return self.properties["designers"]

    @designer.setter
    def designer(self, value: str) -> None:
        self.properties.setProperty("designers", value)

    @property
    def designerURL(self) -> str:
        return self.properties["designerURL"]

    @designerURL.setter
    def designerURL(self, value: str) -> None:
        self.properties["designerURL"] = value

    @property
    def settings(self) -> Dict[str, Union[int, str]]:
        _settings: Dict[str, Union[int, str]] = OrderedDict()
        if self.disablesAutomaticAlignment:
            _settings["disablesAutomaticAlignment"] = 1
        if self.disablesNiceNames:
            _settings["disablesNiceNames"] = 1
        if self.fontType != FontType.DEFAULT:
            _settings["fontType"] = self.fontType.name.lower()
        if self.grid != 1:
            _settings["gridLength"] = self.grid
        if self.gridSubDivision != 1:
            _settings["gridSubDivision"] = self.gridSubDivision
        if self.keepAlternatesTogether:
            _settings["keepAlternatesTogether"] = 1
        if self.keyboardIncrement != 1:
            _settings["keyboardIncrement"] = self.keyboardIncrement
        if self.keyboardIncrementBig != 10:
            _settings["keyboardIncrementBig"] = self.keyboardIncrementBig
        if self.keyboardIncrementHuge != 100:
            _settings["keyboardIncrementHuge"] = self.keyboardIncrementHuge
        if not self.previewRemoveOverlap:
            _settings["previewRemoveOverlap"] = 0

        return _settings


GSFont._add_parsers(
    [
        {"plist_name": "customParameters", "type": GSCustomParameter},
        {"plist_name": "unitsPerEm", "object_name": "upm"},
        {"plist_name": "gridLength", "object_name": "grid"},
        {"plist_name": "DisplayStrings", "object_name": "displayStrings"},
        {"plist_name": "__appVersion", "object_name": "appVersion"},
        # {"plist_name": "__formatVersion", "object_name": "formatVersion"},
        {"plist_name": "classes", "type": GSClass},
        {"plist_name": "instances", "type": GSInstance},
        {"plist_name": "featurePrefixes", "type": GSFeaturePrefix},
        {"plist_name": "features", "type": GSFeature},
        {"plist_name": "fontMaster", "object_name": "masters", "type": GSFontMaster},
        {"plist_name": "kerning", "object_name": "_kerningLTR", "type": OrderedDict},
        {"plist_name": "vertKerning", "object_name": "kerningVertical", "type": OrderedDict},
        {"plist_name": "kerningLTR", "type": OrderedDict},
        {"plist_name": "kerningRTL", "type": OrderedDict},
        {"plist_name": "kerningVertical", "type": OrderedDict},
        {"plist_name": "date", "converter": parse_datetime},
        {"plist_name": "disablesAutomaticAlignment", "converter": bool},
        {"plist_name": "axes", "type": GSAxis},
        {"plist_name": "stems", "type": GSMetric},
        {"plist_name": "metrics", "type": GSMetric},
        {"plist_name": "numbers", "type": GSMetric},
        {"plist_name": "properties", "type": GSFontInfoValue},
        {"plist_name": "note", "object_name": "_note"},
    ]
)
