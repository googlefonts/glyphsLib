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


import copy
import logging
import math
import os
import re
import uuid
from collections import OrderedDict
from enum import IntEnum
from io import StringIO

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
from glyphsLib.pens import LayerPointPen
from glyphsLib.types import (
    IndexPath,
    OneLineList,
    Point,
    Rect,
    Transform,
    UnicodesList,
    floatToString5,
    floatToString3,
    parse_datetime,
    parse_float_or_int,
    readIntlist,
    NegateBool,
)

from glyphsLib.util import isString, isList
from glyphsLib.writer import Writer
import glyphsLib.glyphdata as glyphdata

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
    "GSAnchor",
    "GSComponent",
    "GSSmartComponentAxis",
    "GSPath",
    "GSNode",
    "GSGuide",
    "GSAnnotation",
    "GSHint",
    "GSBackgroundImage",
    # Constants
    "__all__",
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

MOVE = "move"
LINE = "line"
CURVE = "curve"
OFFCURVE = "offcurve"
QCURVE = "qcurve"

GSMetricsKeyUndefined = None
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


class GSWritingDirection(IntEnum):
    """a default value, not used"""

    GSWritingDirectionBIDI = 1

    """Left to Right"""
    GSWritingDirectionLeftToRight = 0  # bit one and two not set

    """Right to Left"""
    GSWritingDirectionRightToLeft = 1 << 1

    """Vertical"""
    GSWritingDirectionVertical = 1 << 2

    """Line to Right"""
    GSWritingDirectionLineToRight = 1 << 3


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

# Writing direction
LTR = 0
RTL = 1
LTRTTB = 3
RTLTTB = 2


WEIGHT_CODES = {
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

WEIGHT_CODES_REVERSE = {v: k for k, v in WEIGHT_CODES.items()}

WIDTH_CODES = {
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

WIDTH_CODES_REVERSE = {v: k for k, v in WIDTH_CODES.items()}

DefaultAxisValuesV2 = [100, 100, 0, 0, 0, 0]


def instance_type(value):
    # Convert the instance type from the plist ("variable") into the integer constant
    return getattr(InstanceType, value.upper())


def font_type(value):
    # Convert the instance type from the plist ("variable") into the integer constant
    return getattr(FontType, value.upper())


class OnlyInGlyphsAppError(NotImplementedError):
    def __init__(self):
        NotImplementedError.__init__(
            self,
            "This property/method is only available in the real UI-based "
            "version of Glyphs.app.",
        )


def transformStructToScaleAndRotation(transform):
    Det = transform[0] * transform[3] - transform[1] * transform[2]
    _sX = math.sqrt(math.pow(transform[0], 2) + math.pow(transform[1], 2))
    _sY = math.sqrt(math.pow(transform[2], 2) + math.pow(transform[3], 2))
    if Det < 0:
        _sY = -_sY
    _R = math.atan2(transform[1] * _sY, transform[0] * _sX) * 180 / math.pi

    if Det < 0 and (math.fabs(_R) > 135 or _R < -90):
        _sX = -_sX
        _sY = -_sY
        if _R < 0:
            _R += 180
        else:
            _R -= 180

    quadrant = 0
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

    _defaultsForName = {}

    def __repr__(self):
        content = ""
        if hasattr(self, "_dict"):
            content = str(self._dict)
        return f"<{self.__class__.__name__} {content}>"

    # Note:
    # The dictionary API exposed by GS* classes is "private" in the sense that:
    #  * it should only be used by the parser, so it should only
    #    work for key names that are found in the files
    #  * and only for filling data in the objects, which is why it only
    #    implements `__setitem__`
    #
    # Users of the library should only rely on the object-oriented API that is
    # documented at https://docu.glyphsapp.com/
    def __setitem__(self, key, value):
        setattr(self, key, value)

    @classmethod
    def _add_parsers(cls, specification):
        for field in specification:
            keyname = field["plist_name"]
            dict_parser_name = "_parse_%s_dict" % keyname
            target = field.get("object_name", keyname)
            classname = field.get("type")
            transformer = field.get("converter")

            def _generic_parser(
                self,
                parser,
                value,
                keyname=keyname,
                target=target,
                classname=classname,
                transformer=transformer,
            ):
                if transformer:
                    if isinstance(value, list) and transformer not in [
                        IndexPath,
                        Point,
                        Rect,
                    ]:
                        self[target] = [transformer(v) for v in value]
                    else:
                        self[target] = transformer(value)
                else:
                    obj = parser._parse(value, classname)
                    self[target] = obj

            setattr(cls, dict_parser_name, _generic_parser)


class Proxy:
    __slots__ = "_owner"

    def __init__(self, owner):
        self._owner = owner

    def __repr__(self):
        """Return list-lookalike of representation string of objects"""
        strings = []
        for currItem in self:
            strings.append("%s" % currItem)
        return "(%s)" % (", ".join(strings))

    def __len__(self):
        values = self.values()
        if values is not None:
            return len(values)
        return 0

    def get(self, key, default=None):
        if isinstance(key, int) and key >= self.__len__():
            return default
        result = self[key]
        if not result:
            result = default
        return result

    def pop(self, i):
        if isinstance(i, int):
            node = self[i]
            del self[i]
            return node
        else:
            raise KeyError

    def __iter__(self):
        values = self.values()
        if values is not None:
            yield from values

    def index(self, value):
        return self.values().index(value)

    def __copy__(self):
        return list(self)

    def __deepcopy__(self, memo):
        return [x.copy() for x in self.values()]

    def setter(self, values):
        method = self.setterMethod()
        if isinstance(values, list):
            method(values)
        elif isList(values) or isinstance(values, type(self)):
            method(list(values))
        elif values is None:
            method(list())
        else:
            raise TypeError


class ListDictionaryProxy(Proxy):
    def __init__(self, owner, name, klass):
        super().__init__(owner)
        self._name = name
        self._class = klass
        self._items = getattr(owner, name, [])

    def get(self, name, default=None):
        item = self._get_by_name(name)
        return item.value if item else default

    def append(self, item):
        item.parent = self._owner
        self._items.append(item)

    def extend(self, items):
        for item in items:
            item.parent = self._owner
        self._items.extend(items)

    def remove(self, item):
        if isinstance(item, str):
            item = self.__getitem__(item)
        self._items.remove(item)

    def insert(self, index, item):
        item.parent = self._owner
        self._items.insert(index, item)

    def values(self):
        return self._items

    def setterMethod(self):
        return self.__setter__

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        if isinstance(key, int):
            return self._items[key]
        else:
            item = self._get_by_name(key)
            if item is not None:
                return item.value
        return None

    def __setitem__(self, name, value):
        item = self._get_by_name(name)
        if item is not None:
            item.value = value
        else:
            item = self._class(name, value)
            item.parent = self._owner
            self._items.append(item)

    def __delitem__(self, key):
        if isinstance(key, int):
            del self._items[key]
        elif isinstance(key, str):
            for item in self._items:
                if item.name == key:
                    self._items.remove(item)
        else:
            raise KeyError(key)

    def __contains__(self, item):
        if isinstance(item, str):
            return self.__getitem__(item) is not None
        return item in self._items

    def __iter__(self):
        for index in range(len(self._items)):
            yield self._items[index]

    def __len__(self):
        return len(self._items)

    def __setter__(self, items):
        for item in items:
            item.parent = self._owner
        self._items = items
        setattr(self._owner, self._name, items)

    def _get_by_name(self, name):
        for item in self._items:
            if item.name == name:
                return item


class LayersIterator:
    __slots__ = "curInd", "_owner", "_orderedLayers"

    def __init__(self, owner):
        self.curInd = 0
        self._owner = owner
        self._orderedLayers = None

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if self._owner.parent:
            if self.curInd >= len(self._owner.layers):
                raise StopIteration
            item = self.orderedLayers[self.curInd]
        else:
            if self.curInd >= len(self._owner._layers):
                raise StopIteration
            item = self._owner._layers[self.curInd]
        self.curInd += 1
        return item

    @property
    def orderedLayers(self):
        if not self._orderedLayers:
            glyphLayerIds = [
                l.associatedMasterId
                for l in self._owner._layers.values()
                if l.associatedMasterId == l.layerId
            ]
            masterIds = [m.id for m in self._owner.parent.masters]
            intersectedLayerIds = set(glyphLayerIds) & set(masterIds)
            orderedLayers = [
                self._owner._layers[m.id]
                for m in self._owner.parent.masters
                if m.id in intersectedLayerIds
            ]
            orderedLayers += [
                self._owner._layers[l.layerId]
                for l in self._owner._layers.values()
                if l.layerId not in intersectedLayerIds
            ]
            self._orderedLayers = orderedLayers
        return self._orderedLayers


class FontFontMasterProxy(Proxy):
    """The list of masters. You can access it with the index or the master ID.
    Usage:
        Font.masters[index]
        Font.masters[id]
        for master in Font.masters:
            ...
    """

    def __getitem__(self, Key):
        if isinstance(Key, str):
            # UUIDs are case-sensitive in Glyphs.app.
            return next((master for master in self.values() if master.id == Key), None)
        if isinstance(Key, slice):
            return self.values().__getitem__(Key)
        if isinstance(Key, int):
            if Key < 0:
                Key = self.__len__() + Key
            return self.values()[Key]
        raise KeyError(Key)

    def __setitem__(self, Key, FontMaster):
        FontMaster.font = self._owner
        if isinstance(Key, int):
            OldFontMaster = self.__getitem__(Key)
            if Key < 0:
                Key = self.__len__() + Key
            FontMaster.id = OldFontMaster.id
            self._owner._masters[Key] = FontMaster
        elif isinstance(Key, str):
            OldFontMaster = self.__getitem__(Key)
            FontMaster.id = OldFontMaster.id
            Index = self._owner._masters.index(OldFontMaster)
            self._owner._masters[Index] = FontMaster
        else:
            raise KeyError

    def __delitem__(self, Key):
        if isinstance(Key, int):
            if Key < 0:
                Key = self.__len__() + Key
            return self.remove(self._owner._masters[Key])
        else:
            OldFontMaster = self.__getitem__(Key)
            return self.remove(OldFontMaster)

    def values(self):
        return self._owner._masters

    def append(self, FontMaster):
        FontMaster.font = self._owner
        # If the master to be appended has no ID yet or it's a duplicate,
        # make up a new one.
        if not FontMaster.id or self[FontMaster.id]:
            FontMaster.id = str(uuid.uuid4()).upper()
        self._owner._masters.append(FontMaster)

        # Cycle through all glyphs and append layer
        for glyph in self._owner.glyphs:
            if not glyph.layers[FontMaster.id]:
                newLayer = GSLayer()
                glyph._setupLayer(newLayer, FontMaster.id)
                glyph.layers.append(newLayer)

    def remove(self, FontMaster):
        # First remove all layers in all glyphs that reference this master
        for glyph in self._owner.glyphs:
            for layer in glyph.layers:
                if (
                    layer.associatedMasterId == FontMaster.id
                    or layer.layerId == FontMaster.id
                ):
                    glyph.layers.remove(layer)

        self._owner._masters.remove(FontMaster)

    def insert(self, Index, FontMaster):
        FontMaster.font = self._owner
        self._owner._masters.insert(Index, FontMaster)

    def extend(self, FontMasters):
        for FontMaster in FontMasters:
            FontMaster.font = self._owner
            self.append(FontMaster)

    def setter(self, values):
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

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            return self.values()[key]
        raise KeyError(key)

    def __setitem__(self, key, instance):
        instance.font = self._owner
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            self._owner._instances[key] = instance
        else:
            raise KeyError(key)

    def __delitem__(self, key):
        if isinstance(key, int):
            if key < 0:
                key = self.__len__() + key
            return self.remove(self._owner._instances[key])
        else:
            raise KeyError(key)

    def values(self):
        return self._owner._instances

    def append(self, instance):
        instance.font = self._owner
        # If the master to be appended has no ID yet or it's a duplicate,
        # make up a new one.
        self._owner._instances.append(instance)

    def remove(self, instance):
        if instance.font == self._owner:
            instance.font = None
        self._owner._instances.remove(instance)

    def insert(self, Index, instance):
        instance.font = self._owner
        self._owner._instances.insert(Index, instance)

    def extend(self, instances):
        for instance in instances:
            instance.font = self._owner
        self._owner._instances.extend(instances)

    def setter(self, values):
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

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values().__getitem__(key)

        # by index
        if isinstance(key, int):
            return self._owner._glyphs[key]

        if isinstance(key, str):
            return self._get_glyph_by_string(key)

        return None

    def __setitem__(self, key, glyph):
        if isinstance(key, int):
            self._owner._setupGlyph(glyph)
            self._owner._glyphs[key] = glyph
        else:
            raise KeyError(key)  # TODO: add other access methods

    def __delitem__(self, key):
        if isinstance(key, int):
            del self._owner._glyphs[key]
        elif isinstance(key, str):
            glyph = self._get_glyph_by_string(key)
            if not glyph:
                raise KeyError("No glyph '%s' in the font" % key)
            self._owner._glyphs.remove(glyph)
        else:
            raise KeyError(key)

    def __contains__(self, item):
        if isinstance(item, str):
            return self._get_glyph_by_string(item) is not None
        return item in self._owner._glyphs

    def _get_glyph_by_string(self, key):
        # FIXME: (jany) looks inefficient
        if isinstance(key, str):
            # by glyph name
            for glyph in self._owner._glyphs:
                if glyph.name == key:
                    return glyph
            # by string representation as u'ä'
            if len(key) == 1:
                for glyph in self._owner._glyphs:
                    if glyph.unicode == "%04X" % (ord(key)):
                        return glyph
            # by unicode
            else:
                for glyph in self._owner._glyphs:
                    if glyph.unicode == key.upper():
                        return glyph
        return None

    def values(self):
        return self._owner._glyphs

    def items(self):
        items = []
        for value in self._owner._glyphs:
            key = value.name
            items.append((key, value))
        return items

    def append(self, glyph):
        self._owner._setupGlyph(glyph)
        self._owner._glyphs.append(glyph)

    def extend(self, objects):
        for glyph in objects:
            self._owner._setupGlyph(glyph)
        self._owner._glyphs.extend(list(objects))

    def __len__(self):
        return len(self._owner._glyphs)

    def setter(self, values):
        if isinstance(values, Proxy):
            values = list(values)
        self._owner._glyphs = values
        for g in self._owner._glyphs:
            g.parent = self._owner
            for layer in g.layers.values():
                if (
                    not hasattr(layer, "associatedMasterId")
                    or layer.associatedMasterId is None
                    or len(layer.associatedMasterId) == 0
                ):
                    g._setupLayer(layer, layer.layerId)


class FontClassesProxy(Proxy):
    VALUES_ATTR = "_classes"

    def __getitem__(self, key):
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        if isinstance(key, str):
            for index, klass in enumerate(self.values()):
                if klass.name == key:
                    return self.values()[index]
        raise KeyError

    def __setitem__(self, key, value):
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

    def __delitem__(self, key):
        if isinstance(key, int):
            del self.values()[key]
        elif isinstance(key, str):
            for index, klass in enumerate(self.values()):
                if klass.name == key:
                    del self.values()[index]

    def __contains__(self, item):
        if isinstance(item, str):
            for klass in self.values():
                if klass.name == item:
                    return True
            return False
        return item in self.values()

    def append(self, item):
        self.values().append(item)
        item._parent = self._owner

    def insert(self, key, item):
        self.values().insert(key, item)
        item._parent = self._owner

    def extend(self, items):
        self.values().extend(items)
        for value in items:
            value._parent = self._owner

    def remove(self, item):
        self.values().remove(item)

    def values(self):
        return getattr(self._owner, self.VALUES_ATTR)

    def setter(self, values):
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
    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            if self._owner.parent:
                return list(self)[key]
            return list(self.values())[key]
        elif isinstance(key, str):
            if key in self._owner._layers:
                return self._owner._layers[key]

    def __setitem__(self, key, layer):
        if isinstance(key, int) and self._owner.parent:
            OldLayer = self._owner._layers.values()[key]
            if key < 0:
                key = self.__len__() + key
            layer.layerId = OldLayer.layerId
            layer.associatedMasterId = OldLayer.associatedMasterId
            self._owner._setupLayer(layer, OldLayer.layerId)
            self._owner._layers[key] = layer
        elif isinstance(key, str) and self._owner.parent:
            # FIXME: (jany) more work to do?
            layer.parent = self._owner
            self._owner._layers[key] = layer
        else:
            raise KeyError

    def __delitem__(self, key):
        if isinstance(key, int) and self._owner.parent:
            if key < 0:
                key = self.__len__() + key
            Layer = self.__getitem__(key)
            key = Layer.layerId
        del self._owner._layers[key]

    def __iter__(self):
        return LayersIterator(self._owner)

    def __len__(self):
        return len(self.values())

    def keys(self):
        return self._owner._layers.keys()

    def values(self):
        return self._owner._layers.values()

    def append(self, layer):
        assert layer is not None
        if not layer.associatedMasterId:
            if self._owner.parent:
                layer.associatedMasterId = self._owner.parent.masters[0].id
        if not layer.layerId:
            layer.layerId = str(uuid.uuid4()).upper()
        self._owner._setupLayer(layer, layer.layerId)
        self._owner._layers[layer.layerId] = layer

    def extend(self, layers):
        for layer in layers:
            self.append(layer)

    def remove(self, layer):
        return self._owner.removeLayerForKey_(layer.layerId)

    def insert(self, index, layer):
        self.append(layer)

    def setter(self, values):
        newLayers = OrderedDict()
        if isinstance(values, (list, tuple, type(self))):
            for layer in values:
                newLayers[layer.layerId] = layer
        elif isinstance(values, dict):  # or isinstance(values, NSDictionary)
            for layer in values.values():
                newLayers[layer.layerId] = layer
        else:
            raise TypeError
        for key, layer in newLayers.items():
            self._owner._setupLayer(layer, key)
        self._owner._layers = newLayers

    def plistArray(self):
        return list(self._owner._layers.values())


class LayerAnchorsProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        elif isinstance(key, str):
            for i, a in enumerate(self._owner._anchors):
                if a.name == key:
                    return self._owner._anchors[i]
        else:
            raise KeyError

    def __setitem__(self, key, anchor):
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

    def __delitem__(self, key):
        if isinstance(key, int):
            del self._owner._anchors[key]
        elif isinstance(key, str):
            for i, a in enumerate(self._owner._anchors):
                if a.name == key:
                    self._owner._anchors[i]._parent = None
                    del self._owner._anchors[i]
                    return

    def values(self):
        return self._owner._anchors

    def append(self, anchor):
        for i, a in enumerate(self._owner._anchors):
            if a.name == anchor.name:
                anchor._parent = self._owner
                self._owner._anchors[i] = anchor
                return
        if anchor.name:
            self._owner._anchors.append(anchor)
        else:
            raise ValueError("Anchor must have name")

    def extend(self, anchors):
        for anchor in anchors:
            anchor._parent = self._owner
        self._owner._anchors.extend(anchors)

    def remove(self, anchor):
        if isinstance(anchor, str):
            anchor = self.values()[anchor]
        return self._owner._anchors.remove(anchor)

    def insert(self, index, anchor):
        anchor._parent = self._owner
        self._owner._anchors.insert(index, anchor)

    def __len__(self):
        return len(self._owner._anchors)

    def setter(self, anchors):
        if isinstance(anchors, Proxy):
            anchors = list(anchors)
        self._owner._anchors = anchors
        for anchor in anchors:
            anchor._parent = self._owner


class IndexedObjectsProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        else:
            raise KeyError

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.values()[key] = value
            value._parent = self._owner
        else:
            raise KeyError

    def __delitem__(self, key):
        if isinstance(key, int):
            del self.values()[key]
        else:
            raise KeyError

    def values(self):
        return getattr(self._owner, self._objects_name)

    def append(self, value):
        self.values().append(value)
        value._parent = self._owner

    def extend(self, values):
        self.values().extend(values)
        for value in values:
            value._parent = self._owner

    def remove(self, value):
        self.values().remove(value)

    def insert(self, index, value):
        self.values().insert(index, value)
        value._parent = self._owner

    def __len__(self):
        return len(self.values())

    def setter(self, values):
        setattr(self._owner, self._objects_name, list(values))
        for value in self.values():
            value._parent = self._owner


class InternalAxesProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            if key < len(self._owner.font.axes):
                axis = self._owner.font.axes[key]
            else:
                return None
            return self._owner._internalAxesValues.get(axis.axisId)
        elif isinstance(key, str):
            return self._owner._internalAxesValues.get(key)
        raise TypeError(
            "list indices must be integers, strings or slices, not %s"
            % type(key).__name__
        )

    def __setitem__(self, key, value):
        if isinstance(key, int) and self._owner.font:
            key = self._owner.font.axes[key].axisId
        self._owner._internalAxesValues[key] = value

    def values(self):
        if self._owner.font is None:
            return []
        values = []
        for axis in self._owner.font.axes:
            values.append(self._owner._internalAxesValues.get(axis.axisId, 0))
        return values

    def __len__(self):
        if self._owner.font is None:
            return 0
        return len(self._owner.font.axes)

    def _setterMethod(self, values):
        if self._owner.font is None:
            return
        idx = 0
        for axis in self._owner.font.axes:
            value = values[idx]
            self._owner._internalAxesValues[axis.axisId] = value
            idx += 1

    def setterMethod(self):
        return self._setterMethod


class ExternalAxesProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            if key < len(self._owner.font.axes):
                axis = self._owner.font.axes[key]
            else:
                return None
            return self._owner._externalAxesValues.get(axis.axisId)
        elif isinstance(key, str):
            return self._owner._externalAxesValues.get(key)
        raise TypeError(
            "list indices must be integers, strings or slices, not %s"
            % type(key).__name__
        )

    def __setitem__(self, key, value):
        if isinstance(key, int):
            key = self._owner.font.axes[key].axisId
        self._owner._externalAxesValues[key] = value

    def values(self):
        if self._owner.font is None:
            return []
        values = []
        for axis in self._owner.font.axes:
            values.append(self._owner._externalAxesValues.get(axis.axisId, 0))
        return values

    def __len__(self):
        if self._owner.font is None:
            return 0
        return self._owner.font.countOfAxes()

    def setterMethod(self, values):
        if self._owner.font is None:
            return
        idx = 0
        for axis in self._owner.font.axes:
            value = values[idx]
            self._owner._externalAxesValues[axis.axisId] = value
            idx += 1


def axisLocationToAxesValue(master_or_instances):
    axisLocations = master_or_instances.customParameters["Axis Location"]
    if axisLocations is None:
        return
    for axis in master_or_instances.font.axes:
        locationDict = None
        for currLocartion in axisLocations:
            if currLocartion["Axis"] == axis.name:
                locationDict = currLocartion
                break
        if locationDict is None:
            continue
        location = locationDict.get("Location", None)
        if location:
            master_or_instances.externalAxesValues[axis.axisId] = location


class MasterStemsProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, slice):
            return [self.__getitem__(i) for i in range(*key.indices(self.__len__()))]
        stem = self._owner.font.stemForKey(key)
        if stem is None:
            raise KeyError("No stem for %s" % key)
        return self._owner._stems[stem.id]

    def __setitem__(self, key, value):
        stem = self._owner.font._stemForKey(key)
        if stem is None:
            if isString(key):
                name = key
            else:
                name = "stem%s" % key
            stem = GSMetric.new()
            stem.setName_(name)
            stem.setHorizontal_(True)
            self._owner.font.addStem_(stem)
        self._owner._stems[stem.id] = value

    def values(self):
        values = []
        for stem in self._owner.font.stems:
            values.append(self._owner._stems.get(stem.id, None))
        return values

    def __len__(self):
        if self._owner.font is None:
            return 0
        return len(self._owner.font.stems)

    def _setterMethod(self, values):
        if self._owner.font is None:
            return
        if self.__len__() != len(values):
            raise ValueError("Count of values doesn’t match stems")
        idx = 0
        for stem in self._owner.font.stems:
            self._owner.stems[stem.id] = values[idx]
            idx += 1

    def setterMethod(self):
        return self._setterMethod


class LayerShapesProxy(IndexedObjectsProxy):
    _objects_name = "_shapes"
    _filter = None

    def __init__(self, owner):
        super().__init__(owner)

    def append(self, value):
        self._owner._shapes.append(value)
        value.parent = self._owner

    def extend(self, values):
        self._owner._shapes.extend(values)
        for value in values:
            value.parent = self._owner

    def remove(self, value):
        self._owner._shapes.remove(value)

    def insert(self, index, value):
        self._owner._shapes.insert(index, value)
        value.parent = self._owner

    def __setitem__(self, key, value):
        if isinstance(key, int):
            index = self._owner._shapes.index(self.values()[key])
            self._owner._shapes[index] = value
            value.parent = self._owner
        else:
            raise KeyError

    def __delitem__(self, key):
        if isinstance(key, int):
            index = self._owner._shapes.index(self.values()[key])
            del self._owner._shapes[index]
        else:
            raise KeyError

    def setter(self, values):
        if self._filter:
            newvalues = list(
                filter(lambda s: not isinstance(s, self._filter), self._owner._shapes)
            )
        else:
            newvalues = []
        newvalues.extend(list(values))
        self._owner._shapes = newvalues
        for value in newvalues:
            value.parent = self._owner

    def values(self):
        if self._filter:
            return list(
                filter(lambda s: isinstance(s, self._filter), self._owner._shapes)
            )
        else:
            return self._owner._shapes[:]


class LayerHintsProxy(IndexedObjectsProxy):
    _objects_name = "_hints"

    def __init__(self, owner):
        super().__init__(owner)


class LayerAnnotationProxy(IndexedObjectsProxy):
    _objects_name = "_annotations"

    def __init__(self, owner):
        super().__init__(owner)


class LayerGuideLinesProxy(IndexedObjectsProxy):
    _objects_name = "_guides"

    def __init__(self, owner):
        super().__init__(owner)


class PathNodesProxy(IndexedObjectsProxy):
    _objects_name = "_nodes"

    def __init__(self, owner):
        super().__init__(owner)


class CustomParametersProxy(ListDictionaryProxy):
    def __init__(self, owner):
        super().__init__(owner, "_customParameters", GSCustomParameter)
        self._update_lookup()

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            return self.values()[key]
        elif isinstance(key, str):
            return self._lookup.get(key)
        raise TypeError("key must be integer or string, not %s" % type(key).__name__)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._update_lookup()

    def setter(self, params):
        super().setter(params)
        self._update_lookup()

    def __iter__(self):
        for item in super().__iter__():
            yield item

    def keys(self):
        keys = [parameter.name for parameter in self]
        return keys

    def _get_by_name(self, name):
        if name == "Name Table Entry":
            return None
        return super()._get_by_name(name)

    def is_font(self):
        """Returns whether we are looking at a top-level GSFont object as
        opposed to a master or instance.
        This is a stupid hack to make the globally registered parameter handler work
        """
        return isinstance(self._owner, GSFont)

    def _update_lookup(self):
        self._lookup = {}
        for param in self:
            params = self._lookup.get(param.name, None)
            if params is None:
                self._lookup[param.name] = param.value  # the first wins

    def __CustomParametersProxy_get_custom_values__(self, key):
        parameters = []
        for parameter in self:
            if not parameter.active:
                continue
            if parameter.name == key:
                parameters.append(parameter)
        return parameters

    def get_custom_value(self, key):
        for parameter in self:
            if not parameter.active:
                continue
            if parameter.name == key:
                return parameter.value
        return None

    def get_custom_values(self, key):
        parameters = []
        for parameter in self:
            if not parameter.active:
                continue
            if parameter.name == key:
                parameters.append(parameter.value)
        return parameters


class PropertiesProxy(ListDictionaryProxy):
    def __init__(self, owner):
        assert owner
        super().__init__(owner, "_properties", GSFontInfoValue)

    def __setitem__(self, key, value):
        infoValue = self[key]
        if infoValue is None or not isinstance(infoValue, GSFontInfoValue):
            infoValue = GSFontInfoValue(key)
            infoValue.parent = self._owner
            self._owner.properties.append(infoValue)
        if key.endswith("s"):
            infoValue.setLocalizedValue(value, "dflt")
        else:
            infoValue.value = value

    def getProperty(self, key, language="dflt"):
        for infoValue in self:
            if infoValue.name != key:
                continue
            return infoValue.localizedValue(language)

    def setProperty(self, key, value, language="dflt"):
        for infoValue in self:
            if infoValue.name != key:
                continue
            infoValue.parent = self._owner
            infoValue.setLocalizedValue(value, language)
            return
        infoValue = GSFontInfoValue(key)
        infoValue.setLocalizedValue(value, language)
        infoValue.parent = self._owner
        self._owner.properties.append(infoValue)


class UserDataProxy(Proxy):
    def __getitem__(self, key):
        if self._owner._userData is None:
            return None
        # This is not the normal `dict` behaviour, because this does not raise
        # `KeyError` and instead just returns `None`. It matches Glyphs.app.
        return self._owner._userData.get(key)

    def __setitem__(self, key, value):
        if self._owner._userData is not None:
            self._owner._userData[key] = value
        else:
            self._owner._userData = {key: value}

    def __delitem__(self, key):
        if self._owner._userData is not None and key in self._owner._userData:
            del self._owner._userData[key]

    def __contains__(self, item):
        if self._owner._userData is None:
            return False
        return item in self._owner._userData

    def __iter__(self):
        if self._owner._userData is None:
            return
        # This is not the normal `dict` behaviour, because this yields values
        # instead of keys. It matches Glyphs.app though. Urg.
        yield from self._owner._userData.values()

    def __repr__(self):
        strings = []
        for key, item in self._owner._userData.items():
            strings.append("%s:%s" % (key, item))
        return "(%s)" % (", ".join(strings))

    def values(self):
        if self._owner._userData is None:
            return []
        return self._owner._userData.values()

    def keys(self):
        if self._owner._userData is None:
            return []
        return self._owner._userData.keys()

    def items(self):
        if self._owner._userData is None:
            return []
        return self._owner._userData.items()

    def get(self, key):
        if self._owner._userData is None:
            return None
        return self._owner._userData.get(key)

    def setter(self, values):
        self._owner._userData = values

    def __copy__(self):
        return copy.copy(self._owner._userData)

    def __deepcopy__(self, memo):
        return copy.deepcopy(self._owner._userData)


class GSAxis(GSBase):
    def _serialize_to_plist(self, writer):
        writer.writeObjectKeyValue(self, "hidden", "if_true")
        writer.writeObjectKeyValue(self, "name", True)
        writer.writeKeyValue("tag", self.axisTag)

    def __init__(self, name="", tag="", hidden=False):
        self.name = name
        self.axisTag = tag
        self.axisId = "%X" % id(self)
        self.hidden = hidden

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}: {self.axisTag}>"

    def __eq__(self, other):
        return self.name == other.name and self.axisTag == other.axisTag

    @property
    def shortAxisTag(self):
        shortAxisTagMapping = {
            "ital": "it",
            "opsz": "oz",
            "slnt": "sl",
            "wdth": "wd",
            "wght": "wg",
        }
        return shortAxisTagMapping.get(self.axisTag, self.axisTag)


GSAxis._add_parsers(
    [
        {"plist_name": "tag", "object_name": "axisTag"},
        {"plist_name": "hidden", "converter": bool},
    ]
)


class GSCustomParameter(GSBase):
    def _serialize_to_plist(self, writer):
        if writer.formatVersion >= 3 and not self.active:
            writer.writeKeyValue("disabled", True)
        writer.writeKeyValue("name", self.name)
        if self.name == "Color Palettes":
            writer.allowTuple = True
            writer.writeKeyValue("value", self.value)
            writer.allowTuple = False
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
            "openTypeOS2CodePageRanges",
            "openTypeOS2FamilyClass",
            "openTypeOS2Panose",
            "openTypeOS2Type",
            "openTypeOS2UnicodeRanges",
            "panose",
            "unicodeRanges",
            # "codePageRanges",
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

    def __init__(self, name="New Value", value="New Parameter"):
        self.name = name
        self.value = value
        self.active = True

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}: {self._value}>"

    def plistValue(self, formatVersion=2):
        string = StringIO()
        writer = Writer(string, formatVersion=formatVersion)
        self._serialize_to_plist(writer)
        return "{\n" + string.getvalue() + "}"

    def getValue(self):
        return self._value

    def setValue(self, value):
        """Cast some known data in custom parameters."""
        if self.name in self._CUSTOM_INT_PARAMS:
            value = int(value)
        elif self.name in self._CUSTOM_FLOAT_PARAMS:
            value = float(value)
        elif self.name in self._CUSTOM_BOOL_PARAMS:
            value = bool(value)
        elif self.name in self._CUSTOM_INTLIST_PARAMS:
            value = readIntlist(value)
        elif self.name in self._CUSTOM_DICT_PARAMS:
            parser = Parser()
            value = parser.parse(value)
        elif self.name == "note":
            value = str(value)
        elif self.name == "Axis Mappings":
            # make sure the mapping keys are all numbers, not str
            newValue = {}
            for axisTag, mapping in value.items():
                newMapping = {}
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
    def __init__(self, name=None, metricType=None):
        self.name = name
        self.metricType = metricType
        self.id = str(uuid.uuid4()).upper()
        self.filter = None
        self.horizontal = False

    def _serialize_to_plist(self, writer):
        writer.writeObjectKeyValue(self, "horizontal", "if_true")
        writer.writeObjectKeyValue(self, "filter", "if_true")
        writer.writeObjectKeyValue(self, "name", "if_true")
        if self.metricType:
            writer.writeKeyValue("type", self.metricType)

    def __repr__(self):
        string = "<{} {} ({})".format(self.__class__.__name__, self.metricType, self.id)
        if self.filter:
            string += self.filter
        string += ">"
        return string


GSMetric._add_parsers(
    [
        {"plist_name": "type", "object_name": "metricType"},
    ]
)


class GSMetricValue(GSBase):
    def __init__(self, position=0, overshoot=0):
        self.position = position
        self.overshoot = overshoot
        self.metric = None

    def _serialize_to_plist(self, writer):
        if self.overshoot:
            writer.writeKeyValue("over", self.overshoot)
        if self.position:
            writer.writeKeyValue("pos", self.position)

    def __repr__(self):
        return "<{} {}: {}/{}>".format(
            self.__class__.__name__,
            self.metric.metricType if self.metric else "-",
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
    def __init__(self, pos=0, size=20):
        self.position = pos
        self.size = size

    def read(self, src):
        if src is not None:
            p = Point(src)
            self.position = parse_float_or_int(p.value[0])
            self.size = parse_float_or_int(p.value[1])
        return self

    def __repr__(self):
        return "<{} pos:{} size:{}>".format(
            self.__class__.__name__, self.position, self.size
        )

    def __lt__(self, other):
        if not isinstance(other, GSAlignmentZone):
            return NotImplemented
        return (self.position, self.size) < (other.position, other.size)

    def __eq__(self, other):
        if not isinstance(other, GSAlignmentZone):
            return NotImplemented
        return (self.position, self.size) == (other.position, other.size)

    def plistValue(self, formatVersion=2):
        return '"{{{}, {}}}"'.format(
            floatToString5(self.position), floatToString5(self.size)
        )


class GSGuide(GSBase):
    def _serialize_to_plist(self, writer):
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

    _parent = None
    _defaultsForName = {"position": Point(0, 0), "angle": 0}

    def __init__(self):
        self.alignment = ""
        self.angle = 0
        self.filter = ""
        self.locked = False
        self.name = ""
        self.position = Point(0, 0)
        self.showMeasurement = False
        self.lockAngle = False
        self._userData = None
        self.orientation = None

    def __repr__(self):
        return "<{} x={:.1f} y={:.1f} angle={:.1f}>".format(
            self.__class__.__name__, self.position.x, self.position.y, self.angle
        )

    @property
    def parent(self):
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
MASTER_ICON_NAMES = set(
    (
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
    )
)


class GSFontMaster(GSBase):
    def _write_axis_value(self, writer, idx, defaultValue):
        axes = self.font.axes
        axesCount = len(axes)
        if axesCount > idx:
            value = self.internalAxesValues[axes[idx].axisId]
            if value is not None and abs(value - defaultValue) > 0.0001:
                writer.writeKeyValue(MASTER_AXIS_VALUE_KEYS[idx], value)

    def _default_icon_name(self):
        name_parts = self.name.split(" ")
        if len(name_parts) > 1:
            try:
                name_parts.remove("Regular")
            except ValueError:
                pass
            try:
                name_parts.remove("Italic")
            except ValueError:
                pass
        iconName = "_".join(name_parts)
        if len(iconName) == 0 or iconName not in MASTER_ICON_NAMES:
            iconName = "Regular"
        return iconName

    def _serialize_to_plist(self, writer):  # noqa: C901
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "alignmentZones", "if_true")
            writer.writeObjectKeyValue(self, "ascender")
        if writer.formatVersion >= 3 and len(self.internalAxesValues):
            writer.writeKeyValue("axesValues", self.internalAxesValues)
        customParameters = list(self.customParameters)

        if writer.formatVersion == 2:
            (weightName, widthName, customName) = self._splitName(self.name)
            writer.writeObjectKeyValue(self, "capHeight")
            if customName:
                writer.writeKeyValue("custom", customName)

            self._write_axis_value(writer, 2, 0)
            self._write_axis_value(writer, 3, 0)
            self._write_axis_value(writer, 4, 0)
            self._write_axis_value(writer, 5, 0)

            smallCapMetric = self._get_metric_position(
                GSMetricsKeyxHeight, filter="case == 3"
            )

            if smallCapMetric:
                parameter = GSCustomParameter("smallCapHeight", smallCapMetric)
                customParameters.append(parameter)

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
        ):  # TODO: Glyhs <= 3.1 had a bug that it would not compute the defaultIconName correctly for v3 files.
            writer.writeKeyValue("iconName", self.iconName)
        writer.writeObjectKeyValue(self, "id")
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "italicAngle", "if_true")
        if writer.formatVersion >= 3:
            metrics = []
            for metric in self.font.metrics:
                metricValue = self.metrics.get(metric.id)
                metrics.append(metricValue)
            writer.writeKeyValue("metricValues", metrics)

        if writer.formatVersion > 2:
            writer.writeKeyValue("name", self.name)

        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(
                self, "numbers", "if_true", keyName="numberValues"
            )
            writer.writeObjectKeyValue(self, "stems", "if_true", keyName="stemValues")
        if True:
            userData = dict(self.userData)
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

    def _parse_alignmentZones_dict(self, parser, text):
        """
        For glyphs file format 2 this parses the alignmentZone parameter directly.
        """
        _zones = parser._parse(text, str)
        self._alignmentZones = [GSAlignmentZone().read(x) for x in _zones]

    def __init__(self, name="Regular"):
        self.customParameters = []
        self.name = name
        self._userData = None
        self._horizontalStems = None
        self._verticalStems = None
        self._internalAxesValues = {}
        self._externalAxesValues = {}
        self._metrics = {}
        self.font = None
        self.guides = []
        self.iconName = ""
        self.id = str(uuid.uuid4()).upper()
        self.numbers = []
        self._stems = {}
        self.visible = False
        self.weight = None
        self.width = None
        self.customName = None
        self.readBuffer = {}  # temp storage while reading
        self._axesValues = None
        self._stems = None
        self._alignmentZones = None

    def __repr__(self):
        return '<GSFontMaster "{}" {}>'.format(
            self.name, self.internalAxesValues.values()
        )

    def _import_stem_list(self, stems, horizontal):
        if self._stems is None:
            self._stems = {}
        for idx in range(len(stems)):
            name = "%sStem%d" % ("h" if horizontal else "v", idx)
            metric = self.font.stemForName(name)
            if not metric:
                metric = GSMetric()
                metric.name = name
                metric.horizontal = horizontal
                self.font.stems.append(metric)
            self._stems[metric.id] = stems[idx]

    def post_read(self):  # GSFontMaster
        axes = self.font.axes
        if self.font.formatVersion < 3:
            axesValues = self.readBuffer.get("axesValues", {})
            axesCount = len(axes)
            for idx in range(axesCount):
                axis = axes[idx]
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

        if isinstance(self._metrics, list):
            metricValues = list(self._metrics)
            self._metrics = {}
            if metricValues:
                for fontMetric, metricValue in zip(self.font.metrics, metricValues):
                    # TODO: use better accessor
                    self._metrics[fontMetric.id] = metricValue
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

            parameter = self.customParameters["smallCapHeight"]
            if parameter:
                xHeightMetricValue = self._get_metric(GSMetricsKeyxHeight)
                filterString = "case == 3"
                self._set_metric(
                    GSMetricsKeyxHeight,
                    parameter,
                    xHeightMetricValue.overshoot,
                    filter=filterString,
                )
                del self.customParameters["smallCapHeight"]

            if self._alignmentZones:
                self._import_alignmentZones_to_metrics()

            position, overshoot = self.readBuffer.get(GSMetricsKeyItalicAngle, (0, 0))
            self._set_metric(GSMetricsKeyItalicAngle, position, overshoot)

        if self._stems:
            assert len(self.font.stems) == len(self._stems)
            stems = {}
            for idx, stem in enumerate(self.font.stems):
                stems[stem.id] = self._stems[idx]
            self._stems = stems
        else:
            if self._horizontalStems:
                self._import_stem_list(self._horizontalStems, True)
            if self._verticalStems:
                self._import_stem_list(self._verticalStems, False)
        if self.font.formatVersion < 3 and (
            self.weight or self.width or self.customName
        ):
            self.name = self._joinNames(self.weight, self.width, self.customName)
            self.weight = None
            self.width = None
            self.customName = None
        if not self.name:
            self.name = self._defaultsForName["name"]
        axisLocationToAxesValue(self)

    @property
    def metricsSource(self):
        """Returns the source master to be used for glyph and kerning metrics.

        If linked metrics parameters are being used, the master is returned here,
        otherwise None."""
        if self.customParameters["Link Metrics With First Master"]:
            return self.font.masters[0]
        source_master_id = self.customParameters["Link Metrics With Master"]

        # No custom parameters apply, go home
        if not source_master_id:
            return None

        # Try by master id
        source_master = self.font.masterForId(source_master_id)
        if source_master is not None:
            return source_master

        # Try by name
        for source_master in self.font.masters:
            if source_master.name == source_master_id:
                return source_master

        logger.warning(f"Source master for metrics not found: '{source_master_id}'")
        return self

    def _joinNames(self, width, weight, custom):
        # Remove None and empty string
        names = list(filter(None, [width, weight, custom]))
        return " ".join(names)

    def _splitName(self, value):
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

    customParameters = property(
        lambda self: CustomParametersProxy(self),
        lambda self, value: CustomParametersProxy(self).setter(value),
    )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    def _get_metric_layer(self, metricType, layer=None):
        for metric in self.font.metrics:
            if (
                metric.metricType == metricType
                and metric.filter
                and metric.filter.evaluateWithObject(layer.parent)
            ):
                metricValue = self.metric[metric.id]
                return metricValue
        return self._get_metric(metricType)

    def _get_metric(self, metricType, name=None, filter=None):
        for metric in self.font.metrics:
            if metric.metricType == metricType and metric.filter == filter:
                metricValue = self.metrics.get(metric.id)
                if not metricValue:
                    metricValue = GSMetricValue()
                    self.metrics[metric.id] = metricValue
                metricValue.metric = metric
                return metricValue
        if metricType == GSMetricsKeyBodyHeight:
            return self._get_metric(GSMetricsKeyAscender)
        return None

    def _get_metric_position(self, metricType, name=None, filter=None):
        metricValue = self._get_metric(metricType, name, filter)
        if metricValue:
            return metricValue.position
        return None

    def _set_metric(
        self, metricType, position=None, overshoot=None, name=None, filter=None
    ):
        if not self.font:
            # we read that later in postRead
            self.readBuffer[metricType] = (position, overshoot)
            return
        metrics = self.font.metrics
        metric = None
        for currMetric in metrics:
            if (
                metricType == currMetric.metricType
                and name == currMetric.name
                and filter == currMetric.filter
                and metricType != GSMetricsKeyUndefined
            ):
                metric = currMetric
                break
        if not metric:
            metric = GSMetric()
            metric.metricType = metricType
            metric.filter = filter
            self.font.metrics.append(metric)
        metricValue = self.metrics.get(metric.id)
        if not metricValue:
            metricValue = GSMetricValue(position=position, overshoot=overshoot)
            self.metrics[metric.id] = metricValue
            metricValue.metric = metric
        else:
            if position is not None:
                metricValue.position = position
            if overshoot is not None:
                metricValue.overshoot = overshoot

    def _import_alignmentZones_to_metrics(self):
        for metricValue in self.metrics.values():
            for zone in list(self._alignmentZones):
                if abs(zone.position - metricValue.position) <= 1:
                    end = zone.position + zone.size
                    metricValue.overshoot = end - metricValue.position
                    self._alignmentZones.remove(zone)
        if len(self._alignmentZones) > 0:
            zoneIdx = 1
            for zone in self._alignmentZones:
                # zoneKey = "zone %d" % zoneIdx
                self._set_metric(GSMetricsKeyUndefined, zone.position, zone.size)
                zoneIdx += 1
        self._alignmentZones = None

    @property
    def metrics(self):
        return self._metrics

    @metrics.setter
    def metrics(self, metrics):
        assert isinstance(metrics, dict)
        self._metrics = metrics

    # Legacy accessors
    @property
    def alignmentZones(self):
        if len(self.font.metrics) == 0:
            return []

        zones = []
        for fontMetric in self.font.metrics:
            # Ignore the "italic angle" "metric", it is not an alignmentZone
            if fontMetric.metricType == GSMetricsKeyItalicAngle or (
                fontMetric.filter and fontMetric.filter != "case == 3"
            ):
                continue
            metric = self.metrics.get(fontMetric.id)
            if not metric:
                continue
            # Ignore metric without overshoot, it is not an alignmentZone
            if metric.overshoot is None or metric.overshoot == 0:
                continue
            zone = GSAlignmentZone(pos=metric.position, size=metric.overshoot)
            zones.append(zone)
        zones.sort()
        zones.reverse()
        return zones

    @alignmentZones.setter
    def alignmentZones(self, entries):
        if not isinstance(entries, (tuple, list)):
            raise TypeError(
                "alignmentZones expected as list, got %s (%s)"
                % (entries, type(entries))
            )
        zones = []
        for zone in entries:
            if not isinstance(zone, (tuple, GSAlignmentZone)):
                raise TypeError(
                    "alignmentZones values expected as tuples of (pos, size) "
                    "or GSAligmentZone, got: %s (%s)" % (zone, type(zone))
                )
            if zone not in zones:
                zones.append(zone)
        self._alignmentZones = zones
        if self.font:
            self._import_alignmentZones_to_metrics()

    @property
    def blueValues(self):
        """Set postscript blue values from Glyphs alignment zones."""

        if len(self.font.metrics) == 0:
            return []

        blueValues = []
        for fontMetric in self.font.metrics:
            # Ignore the "italic angle" "metric", it is not an alignmentZone
            if fontMetric.metricType == GSMetricsKeyItalicAngle or fontMetric.filter:
                continue
            metric = self.metrics.get(fontMetric.id)
            if not metric:
                continue
            # Ignore metric without overshoot, it is not an alignmentZone
            if metric.overshoot is None or (
                metric.overshoot <= 0 and metric.position != 0
            ):
                continue
            if metric.overshoot != 0:
                blueValues.append(metric.position)
                blueValues.append(metric.position + metric.overshoot)

        blueValues.sort()
        return blueValues

    @property
    def otherBlues(self):
        """Set postscript blue values from Glyphs alignment zones."""

        if len(self.font.metrics) == 0:
            return []

        otherBlues = []
        for fontMetric in self.font.metrics:
            # Ignore the "italic angle" "metric", it is not an alignmentZone
            if fontMetric.metricType == GSMetricsKeyItalicAngle or fontMetric.filter:
                continue
            metric = self.metrics.get(fontMetric.id)
            if not metric:
                continue
            # Ignore metric without overshoot, it is not an alignmentZone
            if (
                metric.overshoot is None
                or metric.overshoot >= 0
                or metric.position == 0
            ):
                continue
            otherBlues.append(metric.position)
            otherBlues.append(metric.position + metric.overshoot)

        otherBlues.sort()
        return otherBlues

    def _set_stem(self, name, size, direction, filter=None):
        assert self.font
        stems = self.font.stems
        stem = None
        for currStem in stems:
            if (
                name == currStem.mame
                and name == currStem.name
                and filter == currStem.filter
            ):
                stem = currStem
                break
        if not stem:
            stem = GSMetric()
            stem.name = name
            stem.direction = direction
            stem.filter = filter
            self.font.stems.append(stem)
        metricValue = GSMetricValue(position=size)
        metricValue.metric = stem
        self.metrics[stem.id] = metricValue

    stems = property(
        lambda self: MasterStemsProxy(self),
        lambda self, value: MasterStemsProxy(self).setter(value),
    )

    # Legacy accessors
    @property
    def horizontalStems(self):
        horizontalStems = []
        for index, font_stem in enumerate(self.font.stems):
            if not font_stem.horizontal:
                continue
            horizontalStems.append(self.stems[index])
        return horizontalStems

    @horizontalStems.setter
    def horizontalStems(self, value):
        assert isinstance(value, list)
        if self.font:
            self._import_stem_list(value, True)
        else:
            self._horizontalStems = value

    @property
    def verticalStems(self):
        verticalStems = []
        for index, font_stem in enumerate(self.font.stems):
            if font_stem.horizontal:
                continue
            verticalStems.append(self.stems[index])
        return verticalStems

    @verticalStems.setter
    def verticalStems(self, value):
        assert isinstance(value, list)
        if self.font:
            self._import_stem_list(value, False)
        else:
            self._verticalStems = value

    @property
    def ascender(self):
        return self._get_metric_position(GSMetricsKeyAscender)

    @ascender.setter
    def ascender(self, value):
        self._set_metric(GSMetricsKeyAscender, value)

    @property
    def xHeight(self):
        return self._get_metric_position(GSMetricsKeyxHeight)

    @xHeight.setter
    def xHeight(self, value):
        self._set_metric(GSMetricsKeyxHeight, value)

    @property
    def capHeight(self):
        return self._get_metric_position(GSMetricsKeyCapHeight)

    @capHeight.setter
    def capHeight(self, value):
        self._set_metric(GSMetricsKeyCapHeight, value)

    @property
    def descender(self):
        return self._get_metric_position(GSMetricsKeyDescender)

    @descender.setter
    def descender(self, value):
        self._set_metric(GSMetricsKeyDescender, value)

    @property
    def italicAngle(self):
        value = self._get_metric_position(GSMetricsKeyItalicAngle)
        if value:
            return value
        return 0

    @italicAngle.setter
    def italicAngle(self, value):
        self._set_metric(GSMetricsKeyItalicAngle, value)

    internalAxesValues = property(
        lambda self: InternalAxesProxy(self),
        lambda self, value: InternalAxesProxy(self).setter(value),
    )

    externalAxesValues = property(
        lambda self: ExternalAxesProxy(self),
        lambda self, value: ExternalAxesProxy(self).setter(value),
    )

    @property
    def weightValue(self):
        return self.internalAxesValues[0] if len(self.font.axes) > 0 else None

    @weightValue.setter
    def weightValue(self, value):
        if self.font:
            axis = self.font.axes[0]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][0] = value

    @property
    def widthValue(self):
        return self.internalAxesValues[1] if len(self.font.axes) > 1 else None

    @widthValue.setter
    def widthValue(self, value):
        if self.font:
            axis = self.font.axes[1]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][1] = value

    @property
    def customValue(self):
        return self.internalAxesValues.get(2)

    @customValue.setter
    def customValue(self, value):
        if self.font:
            axis = self.font.axes[2]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][2] = value

    @property
    def customValue1(self):
        return self.internalAxesValues.get(3)

    @customValue1.setter
    def customValue1(self, value):
        if self.font:
            axis = self.font.axes[3]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][3] = value

    @property
    def customValue2(self):
        return self.internalAxesValues.get(4)

    @customValue2.setter
    def customValue2(self, value):
        if self.font:
            axis = self.font.axes[4]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return

        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][4] = value

    @property
    def customValue3(self):
        return self.internalAxesValues.get(5)

    @customValue3.setter
    def customValue3(self, value):
        if self.font:
            axis = self.font.axes[5]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return

        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][5] = value


GSFontMaster._add_parsers(
    [
        {"plist_name": "customParameters", "type": GSCustomParameter},
        {"plist_name": "guideLines", "object_name": "guides", "type": GSGuide},  # v2
        {"plist_name": "guides", "object_name": "guides", "type": GSGuide},  # v3
        {"plist_name": "custom", "object_name": "customName"},
        {"plist_name": "axesValues", "object_name": "_axesValues"},  # v3
        {"plist_name": "numberValues", "object_name": "numbers"},  # v3
        {"plist_name": "stemValues", "object_name": "_stems"},  # v3
        {
            "plist_name": "metricValues",
            "object_name": "_metrics",
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

    __slots__ = "_parent", "_userData", "_position", "smooth", "type"

    def __init__(
        self, position=(0, 0), type=LINE, smooth=False, name=None, nodetype=None
    ):
        self._position = Point(position[0], position[1])
        self._userData = None
        self.smooth = smooth
        self.type = type
        if nodetype is not None:  # for backward compatibility
            self.type = nodetype
        # Optimization: Points can number in the 10000s, don't access the userDataProxy
        # through `name` unless needed.
        if name is not None:
            self.name = name

    def copy(self):
        """Clones the node (does not clone attributes)"""
        return GSNode(
            position=(self._position.x, self._position.y),
            type=self.type,
            smooth=self.smooth,
        )

    def __repr__(self):
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
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if not isinstance(value, Point):
            value = Point(value[0], value[1])
        self._position = value

    @property
    def parent(self):
        return self._parent

    def plistValue(self, formatVersion=2):
        string = ""
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
            if self.type == CURVE:
                content = "c"
            elif self.type == QCURVE:
                content = "q"
            elif self.type == OFFCURVE:
                content = "o"
            elif self.type == LINE:
                content = "l"
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
    def read(cls, line):
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
        m = cls._PLIST_VALUE_RE.match(line).groups()
        node = cls(
            position=(parse_float_or_int(m[0]), parse_float_or_int(m[1])),
            type=m[2].lower(),
            smooth=bool(m[3]),
        )
        if m[4] is not None and len(m[4]) > 0:
            value = cls._decode_dict_as_string(m[4])
            parser = Parser()
            node._userData = parser.parse(value)

        return node

    @classmethod
    def read_v3(cls, lst):
        position = (lst[0], lst[1])
        smooth = lst[2].endswith("s")
        if lst[2][0] == "c":
            node_type = CURVE
        elif lst[2][0] == "o":
            node_type = OFFCURVE
        elif lst[2][0] == "l":
            node_type = LINE
        elif lst[2][0] == "q":
            node_type = QCURVE
        else:
            node_type = None
        node = cls(position=position, type=node_type, smooth=smooth)
        if len(lst) > 3:
            node._userData = lst[3]
        return node

    @property
    def name(self):
        if "name" in self.userData:
            return self.userData["name"]
        return None

    @name.setter
    def name(self, value):
        if value is None:
            if "name" in self.userData:
                del self.userData["name"]
        else:
            self.userData["name"] = value

    @property
    def index(self):
        assert self.parent
        return self.parent.nodes.index(self)

    @property
    def nextNode(self):
        assert self.parent
        index = self.index
        if index == (len(self.parent.nodes) - 1):
            return self.parent.nodes[0]
        elif index < len(self.parent.nodes):
            return self.parent.nodes[index + 1]

    @property
    def prevNode(self):
        assert self.parent
        index = self.index
        if index == 0:
            return self.parent.nodes[-1]
        elif index < len(self.parent.nodes):
            return self.parent.nodes[index - 1]

    def makeNodeFirst(self):
        assert self.parent
        if self.type == "offcurve":
            raise ValueError("Off-curve points cannot become start points.")
        nodes = self.parent.nodes
        index = self.index
        newNodes = nodes[index : len(nodes)] + nodes[0:index]
        self.parent.nodes = newNodes

    def toggleConnection(self):
        self.smooth = not self.smooth

    # TODO
    @property
    def connection(self):
        raise NotImplementedError

    # TODO
    @property
    def selected(self):
        raise OnlyInGlyphsAppError

    @staticmethod
    def _encode_dict_as_string(value):
        """Takes the PLIST string of a dict, and returns the same string
        encoded such that it can be included in the string representation
        of a GSNode."""
        # Strip the first and last newlines
        if value.startswith("{\n"):
            value = "{" + value[2:]
        if value.endswith("\n}"):
            value = value[:-2] + "}"
        # escape double quotes and newlines
        return value.replace('"', '\\"').replace("\\n", "\\\\n").replace("\n", "\\n")

    _ESCAPED_CHAR_RE = re.compile(r'\\(\\*)(?:(n)|("))')

    @staticmethod
    def _unescape_char(m):
        backslashes = m.group(1) or ""
        if m.group(2):
            return "\n" if not backslashes else backslashes + "n"
        else:
            return backslashes + '"'

    @classmethod
    def _decode_dict_as_string(cls, value):
        """Reverse function of _encode_string_as_dict"""
        # strip one level of backslashes preceding quotes and newlines
        return cls._ESCAPED_CHAR_RE.sub(cls._unescape_char, value)

    def _indices(self):
        """Find the path_index and node_index that identify the given node."""
        path = self.parent
        layer = path.parent
        for path_index in range(len(layer.paths)):
            if path == layer.paths[path_index]:
                for node_index in range(len(path.nodes)):
                    if self == path.nodes[node_index]:
                        return Point(path_index, node_index)
        return None


class GSPath(GSBase):
    _defaultsForName = {"closed": True}
    _parent = None

    def _serialize_to_plist(self, writer):
        if writer.formatVersion >= 3 and self.attributes:
            writer.allowTuple = True
            writer.writeObjectKeyValue(self, "attributes", keyName="attr")
            writer.allowTuple = False
        writer.writeObjectKeyValue(self, "closed")
        writer.writeObjectKeyValue(self, "nodes", "if_true")

    def _parse_nodes_dict(self, parser, d):
        if parser.formatVersion >= 3:
            read_node = GSNode.read_v3
        else:
            read_node = GSNode.read
        for x in d:
            node = read_node(x)
            node._parent = self
            self._nodes.append(node)

    def __init__(self):
        self.closed = self._defaultsForName["closed"]
        self._nodes = []
        self._attributes = {}

    def copy(self):
        """Clones the path (Does not clone attributes)"""
        cloned = GSPath()
        cloned.closed = self.closed
        cloned.nodes = [node.copy() for node in self.nodes]
        return cloned

    def __repr__(self):
        return "<%s 0x%X nodes:%d>" % (
            self.__class__.__name__,
            id(self),
            len(self.nodes),
        )

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    nodes = property(
        lambda self: PathNodesProxy(self),
        lambda self, value: PathNodesProxy(self).setter(value),
    )

    @property
    def segments(self):
        self._segments = []
        self._segmentLength = 0

        nodes = list(self.nodes)
        # Cycle node list until curve or line at start
        cycled = False
        for i, n in enumerate(nodes):
            if n.type == "curve" or n.type == "line":
                nodes = nodes[i:] + nodes[:i]
                cycled = True
                break
        if not cycled:
            return []

        for nodeIndex in range(len(nodes)):
            if nodes[nodeIndex].type == CURVE:
                count = 3
            elif nodes[nodeIndex].type == QCURVE:
                count = 2
            elif nodes[nodeIndex].type == LINE:
                count = 1
            else:
                continue
            newSegment = segment()
            newSegment.parent = self
            newSegment.index = len(self._segments)
            for ix in range(-count, 1):
                newSegment.appendNode(nodes[(nodeIndex + ix) % len(nodes)])
            self._segments.append(newSegment)

        if not self.closed:
            self._segments.pop(0)

        self._segmentLength = len(self._segments)
        return self._segments

    @segments.setter
    def segments(self, value):
        if isinstance(value, (list, tuple)):
            self.setSegments(value)
        else:
            raise TypeError

    def setSegments(self, segments):
        self.nodes = []
        for segment in segments:
            if len(segment.nodes) == 2 or len(segment.nodes) == 4:
                self.nodes.extend(segment.nodes[1:])
            else:
                raise ValueError

    @property
    def bounds(self):
        left, bottom, right, top = None, None, None, None
        for segment in self.segments:
            newLeft, newBottom, newRight, newTop = segment.bbox()
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
        return Rect(Point(left, bottom), Point(right - left, top - bottom))

    @property
    def direction(self):
        direction = 0
        for i in range(len(self.nodes)):
            thisNode = self.nodes[i]
            nextNode = thisNode.nextNode
            direction += (nextNode.position.x - thisNode.position.x) * (
                nextNode.position.y + thisNode.position.y
            )
        if direction < 0:
            return -1
        else:
            return 1

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, attributes):
        self._attributes = attributes

    @property
    def selected(self):
        raise OnlyInGlyphsAppError

    @property
    def bezierPath(self):
        raise OnlyInGlyphsAppError

    def reverse(self):
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
    def addNodesAtExtremes(self):
        raise NotImplementedError

    # TODO
    def applyTransform(self, transformationMatrix):
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
            assert node.type == "line", "Open path starts with off-curve points"
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
_UFO_NODE_TYPES = {"line", "curve", "qcurve"}


class segment(list):
    def appendNode(self, node):
        if not hasattr(
            self, "nodes"
        ):  # instead of defining this in __init__(), because I hate super()
            self.nodes = []
        self.nodes.append(node)
        self.append(Point(node.position.x, node.position.y))

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
            left, bottom, right, top = self.bezierMinMax(
                self[0].x,
                self[0].y,
                self[1].x,
                self[1].y,
                self[2].x,
                self[2].y,
                self[3].x,
                self[3].y,
            )
            return left, bottom, right, top
        else:
            raise ValueError

    def bezierMinMax(self, x0, y0, x1, y1, x2, y2, x3, y3):
        tvalues = []
        xvalues = []
        yvalues = []

        for i in range(2):
            if i == 0:
                b = 6 * x0 - 12 * x1 + 6 * x2
                a = -3 * x0 + 9 * x1 - 9 * x2 + 3 * x3
                c = 3 * x1 - 3 * x0
            else:
                b = 6 * y0 - 12 * y1 + 6 * y2
                a = -3 * y0 + 9 * y1 - 9 * y2 + 3 * y3
                c = 3 * y1 - 3 * y0

            if abs(a) < 1e-12:
                if abs(b) < 1e-12:
                    continue
                t = -c / b
                if 0 < t < 1:
                    tvalues.append(t)
                continue

            b2ac = b * b - 4 * c * a
            if b2ac < 0:
                continue
            sqrtb2ac = math.sqrt(b2ac)
            t1 = (-b + sqrtb2ac) / (2 * a)
            if 0 < t1 < 1:
                tvalues.append(t1)
            t2 = (-b - sqrtb2ac) / (2 * a)
            if 0 < t2 < 1:
                tvalues.append(t2)

        for j in range(len(tvalues) - 1, -1, -1):
            t = tvalues[j]
            mt = 1 - t
            newxValue = (
                (mt * mt * mt * x0)
                + (3 * mt * mt * t * x1)
                + (3 * mt * t * t * x2)
                + (t * t * t * x3)
            )
            if len(xvalues) > j:
                xvalues[j] = newxValue
            else:
                xvalues.append(newxValue)
            newyValue = (
                (mt * mt * mt * y0)
                + (3 * mt * mt * t * y1)
                + (3 * mt * t * t * y2)
                + (t * t * t * y3)
            )
            if len(yvalues) > j:
                yvalues[j] = newyValue
            else:
                yvalues.append(newyValue)

        xvalues.append(x0)
        xvalues.append(x3)
        yvalues.append(y0)
        yvalues.append(y3)

        return min(xvalues), min(yvalues), max(xvalues), max(yvalues)


class GSTransformable(GSBase):
    _position = Point(0, 0)
    _scale = Point(1, 1)
    _rotation = 0
    _slant = Point(0, 0)
    _parent = None

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    # .position
    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        assert isinstance(value, Point)
        self._position = value

    # .scale
    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        if isinstance(value, (int, float)):
            self._scale = Point(value, value)
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            self._scale = Point(value[0], value[1])
        else:
            raise ValueError

    # .rotation
    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, value):
        if isinstance(value, (int, float)):
            self._rotation = value
        else:
            raise ValueError

    # .slant
    @property
    def slant(self):
        return self._slant

    @slant.setter
    def slant(self, value):
        if isinstance(value, Point):
            self._slant = value
        elif isinstance(value, (int, float)):
            # when setting a single value, that most likly means a single x slant
            self._slant = Point(value, 0)
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            self._slant = Point(value[0], value[1])
        else:
            raise ValueError

    @property
    def transform(self):
        affine = (
            Affine()
            .translate(self.position.x, self.position.y)
            .rotate(math.radians(self._rotation))
            .scale(self._scale.x, self._scale.y)
            .skew(self._slant.x, self._slant.y)
        )
        return Transform(*affine)

    @transform.setter
    def transform(self, value):
        sX, sY, R = transformStructToScaleAndRotation(value)
        self._scale = Point(sX, sY)
        self._rotation = R
        self._slant = Point(0, 0)
        self._position = Point(value[4], value[5])


class GSComponent(GSTransformable):
    def _serialize_to_plist(self, writer):
        # NOTE: The fields should come in alphabetical order.
        writer.writeObjectKeyValue(self, "alignment", "if_true")
        writer.writeObjectKeyValue(self, "anchor", "if_true")
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "rotation", keyName="angle", default=0)
        if writer.formatVersion >= 3 and self.attributes:
            writer.writeObjectKeyValue(self, "attributes", keyName="attr")
        writer.writeObjectKeyValue(self, "locked", "if_true")
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "name")
        if self.smartComponentValues:
            writer.writeKeyValue("piece", self.smartComponentValues)
        if writer.formatVersion > 2:
            if self._position and self._position != Point(0, 0):
                writer.writeKeyValue("pos", self._position)
            writer.writeObjectKeyValue(self, "name", keyName="ref")
            if self.scale and self.scale != Point(1, 1):
                writer.writeKeyValue("scale", self.scale)
            if self.slant and self.slant != Point(0, 0):
                writer.writeKeyValue("slant", Point(list(self.slant)))
        else:
            writer.writeObjectKeyValue(
                self, "transform", self.transform != Transform(1, 0, 0, 1, 0, 0)
            )

    _defaultsForName = {"transform": Transform(1, 0, 0, 1, 0, 0)}

    # TODO: glyph arg is required
    def __init__(self, glyph="", offset=None, scale=None, transform=None):
        self.alignment = 0
        self.anchor = ""
        self.locked = False

        if isinstance(glyph, str):
            self.name = glyph
        elif isinstance(glyph, GSGlyph):
            self.name = glyph.name

        self.smartComponentValues = {}

        if transform is not None:
            self.transform = transform
        if offset is not None:
            self.position = offset
        if scale is not None:
            self.scale = scale

        self._attributes = {}

    def copy(self):
        return GSComponent(self.name, transform=copy.deepcopy(self.transform))

    def __repr__(self):
        return '<GSComponent "{}" x={:.1f} y={:.1f}>'.format(
            self.name, self.transform[4], self.transform[5]
        )

    @property
    def componentName(self):
        return self.name

    @componentName.setter
    def componentName(self, value):
        self.name = value

    @property
    def component(self):
        return self.parent.parent.parent.glyphs[self.name]

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, attributes):
        self._attributes = attributes

    @property
    def layer(self):
        return self.parent.parent.parent.glyphs[self.name].layers[self.parent.layerId]

    def applyTransformation(self, x, y):
        x *= self.scale[0]
        y *= self.scale[1]
        x += self.position.x
        y += self.position.y
        # TODO:
        # Integrate rotation
        return x, y

    @property
    def bounds(self):
        bounds = self.layer.bounds
        if bounds is not None:
            left, bottom, width, height = self.layer.bounds
            right = left + width
            top = bottom + height

            left, bottom = self.applyTransformation(left, bottom)
            right, top = self.applyTransformation(right, top)

            if (
                left is not None
                and bottom is not None
                and right is not None
                and top is not None
            ):
                return Rect(Point(left, bottom), Point(right - left, top - bottom))

    # smartComponentValues = property(
    #     lambda self: self.piece,
    #     lambda self, value: setattr(self, "piece", value))

    def draw(self, pen: AbstractPen) -> None:
        """Draws component with given pen."""
        pen.addComponent(self.name, self.transform)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of component with given point pen."""
        pointPen.addComponent(self.name, self.transform)


GSComponent._add_parsers(
    [
        {"plist_name": "transform", "converter": Transform},
        {"plist_name": "piece", "object_name": "smartComponentValues", "type": dict},
        {"plist_name": "angle", "object_name": "rotation", "type": float},
        {"plist_name": "pos", "object_name": "position", "converter": Point},
        {"plist_name": "ref", "object_name": "name"},
        {"plist_name": "slant", "converter": Point},
        {"plist_name": "locked", "converter": bool},
        {"plist_name": "attr", "object_name": "attributes", "type": dict},  # V3
    ]
)


class GSSmartComponentAxis(GSBase):
    def _serialize_to_plist(self, writer):
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

    _defaultsForName = {"bottomValue": 0, "topValue": 0}

    def __init__(self):
        self.bottomName = ""
        self.bottomValue = self._defaultsForName["bottomValue"]
        self.name = ""
        self.topName = ""
        self.topValue = self._defaultsForName["topValue"]


class GSAnchor(GSBase):
    def _serialize_to_plist(self, writer):
        writer.writeObjectKeyValue(self, "name", "if_true")
        posKey = "position"
        default = None
        if writer.formatVersion > 2:
            posKey = "pos"
            default = Point(0, 0)
        writer.writeObjectKeyValue(self, "position", keyName=posKey, default=default)
        if len(self.userData) > 0:
            writer.writeKeyValue("userData", self.userData)

    _parent = None
    _defaultsForName = {"position": Point(0, 0)}

    def __init__(self, name=None, position=None):
        self.name = "" if name is None else name
        self._userData = None
        if position is None:
            self.position = copy.deepcopy(self._defaultsForName["position"])
        else:
            self.position = position

    def __repr__(self):
        return '<{} "{}" x={:.1f} y={:.1f}>'.format(
            self.__class__.__name__, self.name, self.position[0], self.position[1]
        )

    @property
    def parent(self):
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
    def _serialize_to_plist(self, writer):
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

    _defaultsForName = {
        # TODO: (jany) check defaults in glyphs
        "origin": None,
        "other1": None,
        "other2": None,
        "place": None,
        "scale": None,
        "stem": -2,
    }

    def __init__(self):
        self.horizontal = False
        self.name = ""
        self.options = 0
        self.origin = self._defaultsForName["origin"]
        self.other1 = self._defaultsForName["other1"]
        self.other2 = self._defaultsForName["other2"]
        self.place = self._defaultsForName["place"]
        self.scale = self._defaultsForName["scale"]
        self.settings = {}
        self.stem = self._defaultsForName["stem"]
        self.origin = None
        self.width = None
        self._type = None
        self._target = None
        self._targetNode = None

    def _origin_pos(self):
        if self.originNode:
            if self.horizontal:
                return self.originNode.position.y
            else:
                return self.originNode.position.x
        return self.origin

    def _width_pos(self):
        if self.targetNode:
            if self.horizontal:
                return self.targetNode.position.y
            else:
                return self.targetNode.position.x
        return self.width

    def __repr__(self):
        if self.horizontal:
            direction = "horizontal"
        else:
            direction = "vertical"
        if self.type == PS_BOTTOM_GHOST or self.type == PS_TOP_GHOST:
            return "<GSHint {} origin=({})>".format(self.type, self._origin_pos())
        elif self.type == PS_STEM:
            return "<GSHint {} Stem origin=({}) target=({})>".format(
                direction, self.origin, self.width
            )
        elif self.type == CORNER or self.type == CAP:
            return f"<GSHint {self.type} {self.name}>"
        else:
            return f"<GSHint {self.type} {direction}>"

    @property
    def parent(self):
        return self._parent

    @property
    def originNode(self):
        if self._originNode is not None:
            return self._originNode
        if self._origin is not None:
            return self.parent._find_node_by_indices(self._origin)

    @originNode.setter
    def originNode(self, node):
        self._originNode = node
        self._origin = None

    @property
    def origin(self):
        if self._origin is not None:
            return self._origin
        if self._originNode is not None:
            return self._originNode._indices()

    @origin.setter
    def origin(self, origin):
        self._origin = origin
        self._originNode = None

    @property
    def targetNode(self):
        if self._targetNode is not None:
            return self._targetNode
        if self._target is not None:
            return self.parent._find_node_by_indices(self._target)

    @targetNode.setter
    def targetNode(self, node):
        self._targetNode = node
        self._target = None

    @property
    def target(self):
        if self._target is not None:
            return self._target
        if self._targetNode is not None:
            return self._targetNode._indices()

    @target.setter
    def target(self, target):
        self._target = target
        self._targetNode = None

    @property
    def otherNode1(self):
        if self._otherNode1 is not None:
            return self._otherNode1
        if self._other1 is not None:
            return self.parent._find_node_by_indices(self._other1)

    @otherNode1.setter
    def otherNode1(self, node):
        self._otherNode1 = node
        self._other1 = None

    @property
    def other1(self):
        if self._other1 is not None:
            return self._other1
        if self._otherNode1 is not None:
            return self._otherNode1._indices()

    @other1.setter
    def other1(self, other1):
        self._other1 = other1
        self._otherNode1 = None

    @property
    def otherNode2(self):
        if self._otherNode2 is not None:
            return self._otherNode2
        if self._other2 is not None:
            return self.parent._find_node_by_indices(self._other2)

    @otherNode2.setter
    def otherNode2(self, node):
        self._otherNode2 = node
        self._other2 = None

    @property
    def other2(self):
        if self._other2 is not None:
            return self._other2
        if self._otherNode2 is not None:
            return self._otherNode2._indices()

    @other2.setter
    def other2(self, other2):
        self._other2 = other2
        self._otherNode2 = None

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, hintType):
        assert isinstance(hintType, type(CORNER)), "hintType %s (%s) != %s" % (
            hintType,
            type(hintType),
            type(CORNER),
        )
        self._type = hintType

    @property
    def isPathComponent(self):
        return (
            self._type == CORNER
            or self._type == CAP
            or self._type == BRUSH
            or self._type == SEGMENT
        )

    @property
    def isCorner(self):
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
    def _serialize_to_plist(self, writer):
        # NOTE: The fields should come in alphabetical order.
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
                    if notes:
                        notes = feature_names + notes
                    else:
                        notes = feature_names
            if notes:
                writer.writeKeyValue("notes", notes)

    def post_read(self):
        if self.notes and len(self.notes) > 10:
            remaining_note = self.loadLabelsFromNote(self.notes)
            if remaining_note is not False:
                self.notes = remaining_note

    def __init__(self, name="xxxx", code=""):
        self.active = True
        self.automatic = False
        self.code = code
        self.labels = []
        self.name = name
        self.notes = ""

    def getCode(self):
        return self._code

    def setCode(self, code):
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

    code = property(getCode, setCode)

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}">'

    @property
    def parent(self):
        return self._parent

    @property
    def disabled(self):
        raise "Use .active"

    @disabled.setter
    def disabled(self, _val):
        raise "Use .active = "

    def featureNamesString(self):
        if len(self.labels) == 0:
            return None
        feature_names = []
        feature_names.append("featureNames {")
        for label in self.labels:
            from glyphsLib.builder.features import _to_name_langID

            langID = _to_name_langID(label["language"])
            name = label["value"]
            name = name.replace("\\", r"\005c").replace('"', r"\0022")
            if langID is None:
                feature_names.append(f'  name "{name}";')
            else:
                feature_names.append(f'  name 3 1 0x{langID:X} "{name}";')
        feature_names.append("};")
        return "\n".join(feature_names)

    def loadLabelsFromNote(self, note):
        remaining_note = note
        if note.startswith("Name:"):
            remaining_note = note
            name = note
            lineEnd = name.find("\n")
            if lineEnd > 0:
                name = name[:lineEnd]
                remaining_note = note[lineEnd:]
            else:
                remaining_note = ""
            name = name[5:]
            name = name.strip()
            if name:
                self.labels.append(dict(language="dflt", value=name))
                return remaining_note

        elif note.startswith("featureNames {"):
            lineEnd = note.find("};")
            if lineEnd < 0:
                return False
            remaining_note = note[lineEnd + 2 :]
            note = note[14:lineEnd]
            note = note.strip()
            if not note:
                return False
            """
            featureNames {
            name "Single Storey a"; # Windows (default)
            name 3 1 0x0407 "Einstöckiges a"; # 3=Windows, 1=Unicode, 0407=German
            name 1 "Single Storey a"; # 1=Mac
            name 1 0 2 "Einst\9fckiges a"; # 1=Mac, 0=MacRoman, 2=German
            };
            """
            lines = note.split("\n")
            seenLanguage = set()
            for line in lines:
                code = line.strip()
                if not code.startswith("name "):
                    continue

                name, langIDs = extract_name_and_langId(code)

                if len(langIDs) == 0:
                    platformID = 3
                    platEncID = 1
                    langID = 0x0409

                elif len(langIDs) == 1:
                    platformID = 3
                    platEncID = 1
                    langID = langIDs[0]
                elif len(langIDs) == 3:
                    platformID = int(langIDs[0])
                    platEncID = int(langIDs[1])
                    langID = langIDs[2]
                    if langID.startswith("0x"):
                        langID = int(langID, 16)
                    else:
                        langID = int(langID)

                language = "dflt"
                if platformID == 3 and platEncID == 1:
                    from glyphsLib.builder.features import _to_glyphs_language

                    language = _to_glyphs_language(langID)
                elif platformID == 1 and platEncID == 0 and langID == 0:
                    # mostly to make the test work, who is using apple names any more
                    language = "ENG"
                else:
                    self.logger.warning(
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
    def _serialize_to_plist(self, writer):
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
    def _serialize_to_plist(self, writer):
        writer.writeObjectKeyValue(self, "angle", default=0)
        posKey = "position"
        if writer.formatVersion > 2:
            posKey = "pos"
        writer.writeObjectKeyValue(
            self, "position", keyName=posKey, default=Point(0, 0)
        )
        writer.writeObjectKeyValue(self, "text", "if_true")
        writer.writeObjectKeyValue(self, "type", "if_true")
        writer.writeObjectKeyValue(self, "width", default=100)

    _defaultsForName = {
        "angle": 0,
        "position": Point(0, 0),
        "text": None,
        "type": 0,
        "width": 100,
    }
    _parent = None

    def __init__(self):
        self.angle = self._defaultsForName["angle"]
        self.position = copy.deepcopy(self._defaultsForName["position"])
        self.text = self._defaultsForName["text"]
        self.type = self._defaultsForName["type"]
        self.width = self._defaultsForName["width"]

    @property
    def parent(self):
        return self._parent


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


class GSFontInfoValue(GSBase):  # Combines localizable/nonlocalizable properties
    def __init__(self, key="", value=None):
        self.key = key
        self._value = value
        self._localized_values = None

    def _parse_values_dict(self, parser, values):
        self._localized_values = {}
        for v in values:
            if "language" not in v or "value" not in v:
                continue
            self._localized_values[v["language"]] = v["value"]

    def _serialize_to_plist(self, writer):
        writer.writeObjectKeyValue(self, "key", "if_true")
        if self._localized_values:
            writer.writeKeyValue(
                "values",
                [
                    {"language": l, "value": v}
                    for l, v in self._localized_values.items()
                ],
            )
        else:
            writer.writeObjectKeyValue(self, "value")

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.key)

    @property
    def name(self):
        return self.key

    @name.setter
    def name(self, value):
        self.key = value

    @property
    def value(self):
        if not self._localized_values:
            return self._value
        for key in ["dflt", "ENG"]:
            if key in self._localized_values:
                return self._localized_values[key]
        return list(self._localized_values.values())[0]

    @value.setter
    def value(self, value):
        self._value = value

    def localizedValue(self, language="dflt"):
        if not self._localized_values:
            return self._value
        if language in ["dflt", "ENG"]:
            if language in self._localized_values:
                value = self._localized_values[language]
                return value
        return self._localized_values.get(language, None)

    def setLocalizedValue(self, value, language="dflt"):
        if not self._localized_values:
            self._localized_values = {}
        self._localized_values[language] = value

    @classmethod
    def propertiesFromLegacyCustomParameters(cls, obj):
        for parameter in list(obj.customParameters):
            name = parameter.name
            if name in PROPERTIES_WHITELIST or name + "s" in PROPERTIES_WHITELIST:
                if name + "s" in PROPERTIES_WHITELIST:
                    propertyName = name + "s"
                else:
                    propertyName = name
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
            value = string[semicolonPos + 1 :]
            name = parameter.name
            name = name[9].lower() + name[10:] + "s"
            obj.properties.setProperty(name, value, language)
            obj.customParameters.remove(parameter)

    @classmethod
    def legacyCustomParametersFromProperties(cls, properties, obj):
        customParameters = []
        for infoValue in properties:
            newparameter = cls.legacyCustomParametersFromInfoValue(infoValue)
            # first check for nil as that is a error condition
            if newparameter is not None:
                if len(newparameter) > 0:  # this means we did find something
                    customParameters.extend(newparameter)
            else:
                raise "problem converting infoValue %s in %s" % (infoValue, obj)
                return None
        return customParameters

    @classmethod
    def legacyCustomParametersFromInfoValue(cls, infoValue):
        parameterKey = infoValue.key
        if parameterKey.endswith("s"):
            parameterKey = parameterKey[:-1]

        locParameterKey = "localized" + parameterKey[0].upper() + parameterKey[1:]
        defaultValue = None
        isLocalizedParameter = True
        if locParameterKey not in LOCALIZED_PARAMETERS:  # e.g. for trademark
            isLocalizedParameter = False
            defaultValue = infoValue.value
            # TODO: check if it is a valid parameter altogether
            # if (![GSGlyphsInfo customParameterTypes][parameterKey]) {
            #     return None
        customParameters = []

        if isLocalizedParameter and infoValue._localized_values:
            values = infoValue._localized_values
            for key in sorted(values.keys()):
                value = values[key]
                parameter = None
                if key in ["dflt", "ENG"]:
                    defaultValue = value
                else:
                    # langName = GSGlyphsInfo.langNameForTag(infoValue.languageTag)
                    langName = glyphdata.langTag2Name.get(key, key)
                    if not langName:
                        langName = key
                    stringValue = "%s;%s" % (langName, value)
                    parameter = GSCustomParameter(locParameterKey, stringValue)
                    customParameters.append(parameter)

        if defaultValue:
            nativeDefaultKeys = set(
                (
                    "designer",
                    "designerURL",
                    "manufacturer",
                    "manufacturerURL",
                    "copyright",
                )
            )
            if parameterKey in nativeDefaultKeys and isinstance(
                infoValue.parent, GSFont
            ):
                return customParameters

            # TODO: check if it is a valid parameter altogether
            # if ([GSGlyphsInfo customParameterTypes][parameterKey]) {
            if True:
                parameter = GSCustomParameter(parameterKey, defaultValue)
                customParameters.insert(0, parameter)
            else:
                return None
        return customParameters


INSTANCE_AXIS_VALUE_KEYS = (
    "interpolationWeight",
    "interpolationWidth",
    "interpolationCustom",
    "interpolationCustom1",
    "interpolationCustom2",
    "interpolationCustom3",
)


class GSInstance(GSBase):
    def _write_axis_value(self, writer, idx, defaultValue):
        axes = self.font.axes
        axesCount = len(axes)
        if axesCount > idx:
            value = self.internalAxesValues[axes[idx].axisId]
            if value and abs(value - defaultValue) > 0.01:
                writer.writeKeyValue(INSTANCE_AXIS_VALUE_KEYS[idx], value)

    def _serialize_to_plist(self, writer):
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
            width_class_string = WIDTH_CODES_REVERSE.get(self.weightClass)
            if (
                width_class_string is not None
                and width_class_string != "Medium (normal)"
            ):
                writer.writeKeyValue("widthClass", width_class_string)

    _axis_defaults = (100, 100)

    _defaultsForName = {
        "exports": True,
        "weightClass": 400,
        "widthClass": 5,
        "instanceInterpolations": {},
        "type": InstanceType.SINGLE,
    }

    def __init__(self, name="Regular"):
        self.font = None
        self._internalAxesValues = {}
        self._externalAxesValues = {}
        self.customParameters = []
        self.exports = True
        self.custom = None
        self.instanceInterpolations = copy.deepcopy(
            self._defaultsForName["instanceInterpolations"]
        )
        self.isBold = False
        self.isItalic = False
        self.linkStyle = ""
        self.manualInterpolation = False
        self.name = name
        self.properties = []
        self.visible = True
        self.weightClass = self._defaultsForName["weightClass"]
        self.widthClass = self._defaultsForName["widthClass"]
        self.type = self._defaultsForName["type"]
        self.readBuffer = {}
        self._axesValues = None
        self._userData = None
        self.userData

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}">'

    customParameters = property(
        lambda self: CustomParametersProxy(self),
        lambda self, value: CustomParametersProxy(self).setter(value),
    )

    properties = property(
        lambda self: PropertiesProxy(self),
        lambda self, value: PropertiesProxy(self).setter(value),
    )

    def post_read(self):  # GSInstance
        assert self.font
        axes = self.font.axes
        if axes and self.type != InstanceType.VARIABLE:
            if self.font.formatVersion < 3:
                axesValues = self.readBuffer.get("axesValues", {})
                axesCount = len(axes)
                for idx in range(axesCount):
                    axis = axes[idx]
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
            weightClass = WEIGHT_CODES.get(self.weightClass)
            if weightClass:
                self.weightClass = weightClass
            widthClass = WIDTH_CODES.get(self.widthClass)
            if widthClass:
                self.widthClass = widthClass

            if self.font.formatVersion < 3 and len(self._internalAxesValues) == 0:
                self.internalAxesValues[self.font.axes[0].axisId] = 100

            GSFontInfoValue.propertiesFromLegacyCustomParameters(self)

        weight_class_parameter = self.customParameters["weightClass"]
        if weight_class_parameter:
            self.weightClass = int(weight_class_parameter)
            del self.customParameters["weightClass"]

        axisLocationToAxesValue(self)

    @property
    def exports(self):
        """Deprecated alias for `active`, which is in the documentation."""
        return self._exports

    @exports.setter
    def exports(self, value):
        self._exports = value

    @property
    def familyName(self):
        return self.properties["familyNames"] or self.font.familyName

    @familyName.setter
    def familyName(self, value):
        self.properties["familyNames"] = value

    @property
    def preferredFamily(self):
        return self.preferredFamilyName or self.font.familyName

    @preferredFamily.setter
    def preferredFamily(self, value):
        self.preferredFamilyName = value

    @property
    def preferredFamilyName(self):
        return self.properties["preferredFamilyNames"]

    @preferredFamilyName.setter
    def preferredFamilyName(self, value):
        self.properties["preferredFamilyNames"] = value

    @property
    def preferredSubfamilyName(self):
        return self.properties["preferredSubfamilyNames"]

    @preferredSubfamilyName.setter
    def preferredSubfamilyName(self, value):
        self.properties["preferredSubfamilyNames"] = value

    @property
    def windowsFamily(self):
        value = self.properties["styleMapFamilyNames"]
        if value:
            return value
        if self.name not in ("Regular", "Bold", "Italic", "Bold Italic"):
            return self.familyName + " " + self.name
        else:
            return self.familyName

    @windowsFamily.setter
    def windowsFamily(self, value):
        self.properties["styleMapFamilyNames"] = value

    @property
    def windowsStyle(self):
        if self.name in ("Regular", "Bold", "Italic", "Bold Italic"):
            return self.name
        else:
            return "Regular"

    @property
    def styleMapFamilyNames(self):
        self.properties["styleMapFamilyNames"]

    @styleMapFamilyNames.setter
    def styleMapFamilyNames(self, values):
        self.properties["styleMapFamilyNames"] = values

    @property
    def styleMapStyleNames(self):
        self.properties["styleMapStyleNames"]

    @styleMapStyleNames.setter
    def styleMapStyleNames(self, values):
        self.properties["styleMapStyleNames"] = values

    @property
    def styleMapFamilyName(self):
        return self.properties.getProperty("styleMapFamilyNames")

    @styleMapFamilyName.setter
    def styleMapFamilyName(self, value):
        self.properties.setProperty("styleMapFamilyNames", value)

    @property
    def styleMapStyleName(self):
        return self.properties.getProperty("styleMapStyleNames")

    @styleMapStyleName.setter
    def styleMapStyleName(self, value):
        self.properties.setProperty("styleMapStyleNames", value)

    @property
    def windowsLinkedToStyle(self):
        value = self.linkStyle
        return value
        if self.name in ("Regular", "Bold", "Italic", "Bold Italic"):
            return self.name
        else:
            return "Regular"

    @property
    def fontName(self):
        return (
            self.properties["postscriptFontName"]
            # TODO: Strip invalid characters.
            or ("".join(self.familyName.split(" ")) + "-" + self.name)
        )

    @fontName.setter
    def fontName(self, value):
        self.properties["postscriptFontName"] = value

    @property
    def fullName(self):
        return self.properties["postscriptFullName"] or (
            self.familyName + " " + self.name
        )

    @fullName.setter
    def fullName(self, value):
        self.properties["postscriptFullName"] = value

    # v2 compatibility
    def _get_axis_value(self, index):
        if index < len(self.axes):
            return self.axes[index]
        if index < len(self._axis_defaults):
            return self._axis_defaults[index]
        return 0

    def _set_axis_value(self, index, value):
        if index < len(self.axes):
            self.axes[index] = value
            return
        for j in range(len(self.axes), index):
            if j < len(self._axis_defaults):
                self.axes.append(self._axis_defaults[j])
            else:
                self.axes.append(0)
        self.axes.append(value)

    internalAxesValues = property(
        lambda self: InternalAxesProxy(self),
        lambda self, value: InternalAxesProxy(self).setter(value),
    )

    externalAxesValues = property(
        lambda self: ExternalAxesProxy(self),
        lambda self, value: ExternalAxesProxy(self).setter(value),
    )

    @property
    def weightValue(self):
        return self.internalAxesValues[0] if len(self.font.axes) > 0 else None

    @weightValue.setter
    def weightValue(self, value):
        if self.font:
            axis = self.font.axes[0]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][0] = value

    @property
    def widthValue(self):
        return self.internalAxesValues[1] if len(self.font.axes) > 1 else None

    @widthValue.setter
    def widthValue(self, value):
        if self.font:
            axis = self.font.axes[1]
            if axis:
                self._internalAxesValues[axis.axisId] = value
            return
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][1] = value

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
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][2] = value

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
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][3] = value

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
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["axesValues"][4] = value

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
        if "axesValues" not in self.readBuffer:
            self.readBuffer["axesValues"] = {}
        self.readBuffer["_axesValues"][5] = value

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
    def _serialize_to_plist(self, writer):
        writer.writeObjectKeyValue(self, "_alpha", keyName="alpha", default=50)
        if writer.formatVersion > 2:
            writer.writeObjectKeyValue(self, "rotation", keyName="angle", default=0)

        if self.crop:
            writer.writeObjectKeyValue(self, "crop")

        writer.writeObjectKeyValue(self, "imagePath")
        if self.locked:
            if writer.formatVersion == 2:
                writer.writeKeyValue("locked", "1")
            else:
                writer.writeKeyValue("locked", 1)
        if writer.formatVersion > 2:
            if self.position != Point(0, 0):
                writer.writeObjectKeyValue(self, "position", keyName="pos")
            if self.scale and self.scale != Point(1.0, 1.0):
                writer.writeKeyValue("scale", self.scale)
        else:
            writer.writeObjectKeyValue(
                self, "transform", default=Transform(1, 0, 0, 1, 0, 0)
            )

    _defaultsForName = {"alpha": 50, "transform": Transform(1, 0, 0, 1, 0, 0)}

    def __init__(self, path=None):
        self.alpha = self._defaultsForName["alpha"]
        self.crop = None
        self.imagePath = path
        self.locked = False

    def __repr__(self):
        return "<GSBackgroundImage '%s'>" % self.imagePath

    # .path
    @property
    def path(self):
        return self.imagePath

    @path.setter
    def path(self, value):
        # FIXME: (jany) use posix pathnames here?
        # FIXME: (jany) the following code must have never been tested.
        #   Also it would require to keep track of the parent for background
        #   images.
        # if os.path.dirname(os.path.abspath(value)) == \
        #       os.path.dirname(os.path.abspath(self.parent.parent.parent.filepath)):
        #     self.imagePath = os.path.basename(value)
        # else:
        self.imagePath = value

    # .alpha
    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
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
    parent = None

    def _get_plist_attributes(self):
        attributes = dict(self.attributes)
        font = self.parent.parent
        if LAYER_ATTRIBUTE_AXIS_RULES in self.attributes:
            rule = attributes[LAYER_ATTRIBUTE_AXIS_RULES]
            ruleMap = []
            for axis in font.axes:
                ruleMap.append(rule.get(axis.axisId, {}))
            attributes[LAYER_ATTRIBUTE_AXIS_RULES] = ruleMap
        if LAYER_ATTRIBUTE_COORDINATES in self.attributes:
            coordinates = attributes[LAYER_ATTRIBUTE_COORDINATES]
            coordinatesMap = []
            for axis in font.axes:
                value = coordinates.get(axis.axisId)
                coordinatesMap.append(value)
            attributes[LAYER_ATTRIBUTE_COORDINATES] = coordinatesMap
        return attributes

    def _serialize_to_plist(self, writer):
        # NOTE: The fields should come in alphabetical order.
        writer.writeObjectKeyValue(self, "anchors", "if_true")
        writer.writeObjectKeyValue(self, "annotations", "if_true")

        userData = dict(self.userData)

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
        if writer.formatVersion == 2:
            writer.writeObjectKeyValue(self, "metricLeft", keyName="leftMetricsKey")
            # NOTE: The following two are an exception from the ordering rule.
            writer.writeObjectKeyValue(self, "metricRight", keyName="rightMetricsKey")
            writer.writeObjectKeyValue(self, "metricWidth", keyName="widthMetricsKey")
        else:
            writer.writeObjectKeyValue(self, "metricLeft")
            writer.writeObjectKeyValue(self, "metricRight")
            writer.writeObjectKeyValue(self, "metricWidth")
        if self._name is not None and len(self._name) > 0 and not self.isMasterLayer:
            if writer.formatVersion > 2:
                writer.writeKeyValue("name", self._name)
            else:
                writer.writeKeyValue("name", self.name)
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
            # FIXME: how to know if that zero is a realy value (this is a problem with the ufo spec)
            writer.writeObjectKeyValue(self, "vertWidth")
        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(self, "visible", "if_true")
        writer.writeObjectKeyValue(
            self, "width", not isinstance(self, GSBackgroundLayer)
        )

    BRACKET_LAYER_RE = re.compile(
        r".*(?P<first_bracket>[\[\]])\s*(?P<value>\d+)\s*\].*"
    )
    COLOR_PALETTE_LAYER_RE = re.compile(r"^Color (?P<index>\*|\d+)$")

    def layer_name_to_atributes(self):
        name = self.name
        m = re.match(self.BRACKET_LAYER_RE, name)
        font = self.parent.parent
        assert font
        if m:
            axis = font.axes[0]  # For glyphs 2
            reverse = m.group("first_bracket") == "]"
            bracket_crossover = int(m.group("value"))
            rule = {axis.axisId: {"max" if reverse else "min": bracket_crossover}}
            self.attributes[LAYER_ATTRIBUTE_AXIS_RULES] = rule
        elif "{" in name and "}" in name and ".background" not in self.name:
            coordinatesString = name[name.index("{") + 1 : name.index("}")]
            coordinatesMap = {}
            for c, axis in zip(coordinatesString.split(","), font.axes):
                coordinatesMap[axis.axisId] = float(c)
            master = None
            for axis in font.axes:
                if axis.axisId not in coordinatesMap:
                    if master is None:
                        master = font.masters[self.associatedMasterId]
                    value = master.internalAxesValues[axis.axisId]
                    coordinatesMap[axis.axisId] = value
            self.attributes[LAYER_ATTRIBUTE_COORDINATES] = coordinatesMap

    def post_read(self):  # GSLayer
        assert self.parent
        font = self.parent.parent
        if font.formatVersion == 2:
            self.layer_name_to_atributes()

            if not self.smartComponentPoleMapping and "PartSelection" in self.userData:
                self.smartComponentPoleMapping = self.userData["PartSelection"]
                del self.userData["PartSelection"]
        else:
            if LAYER_ATTRIBUTE_AXIS_RULES in self.attributes:
                rule = self.attributes[LAYER_ATTRIBUTE_AXIS_RULES]
                ruleMap = {}
                for axis, value in zip(font.axes, rule):
                    ruleMap[axis.axisId] = value
                self.attributes[LAYER_ATTRIBUTE_AXIS_RULES] = ruleMap
            if LAYER_ATTRIBUTE_COORDINATES in self.attributes:
                coordinates = self.attributes[LAYER_ATTRIBUTE_COORDINATES]
                coordinatesMap = {}
                for axis, value in zip(font.axes, coordinates):
                    coordinatesMap[axis.axisId] = value
                master = None
                for axis in font.axes:
                    if axis.axisId not in coordinatesMap:
                        if master is None:
                            master = font.masters[self.associatedMasterId]
                        value = master.internalAxesValues[axis.axisId]
                        coordinatesMap[axis.axisId] = value
                self.attributes[LAYER_ATTRIBUTE_COORDINATES] = coordinatesMap

    def _parse_shapes_dict(self, parser, shapes):
        for shape_dict in shapes:
            if "ref" in shape_dict:
                shape = parser._parse_dict(shape_dict, GSComponent)
                self.components.append(shape)
            else:
                shape = parser._parse_dict(shape_dict, GSPath)
                self.paths.append(shape)

    _defaultsForName = {
        "width": 600,
        "metricLeft": None,
        "metricRight": None,
        "metricWidth": None,
        "vertWidth": None,
        "vertOrigin": None,
    }

    def _parse_background_dict(self, parser, value):
        self._background = parser._parse(value, GSBackgroundLayer)
        self._background._foreground = self
        self._background.parent = self.parent

    def __init__(self):
        self._anchors = []
        self._annotations = []
        self._background = None
        self._foreground = None
        self._guides = []
        self._hints = []
        self._layerId = ""
        self._name = ""
        self._selection = []
        self._shapes = []
        self._userData = None
        self.attributes = {}
        self.smartComponentPoleMapping = {}
        self.associatedMasterId = ""
        self.backgroundImage = None
        self.color = None
        self.metricLeft = self._defaultsForName["metricLeft"]
        self.parent = None
        self.metricRight = self._defaultsForName["metricRight"]
        self.vertOrigin = self._defaultsForName["vertOrigin"]
        self.vertWidth = self._defaultsForName["vertWidth"]
        self.visible = False
        self.width = self._defaultsForName["width"]
        self.metricWidth = self._defaultsForName["metricWidth"]

    def __repr__(self):
        name = self.name
        try:
            # assert self.name
            name = self.name
        except AttributeError:
            name = "orphan (n)"
        try:
            assert self.parent.name
            parent = self.parent.name
        except (AttributeError, AssertionError):
            parent = "orphan"
        return f'<{self.__class__.__name__} "{name}" ({parent})>'

    def __lt__(self, other):
        if self.master and other.master and self.associatedMasterId == self.layerId:
            return (
                self.master.weightValue < other.master.weightValue
                or self.master.widthValue < other.master.widthValue
            )

    @property
    def layerId(self):
        return self._layerId

    @layerId.setter
    def layerId(self, value):
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
    def master(self):
        if self.associatedMasterId and self.parent:
            master = self.parent.parent.masterForId(self.associatedMasterId)
            return master

    @property
    def font(self):
        return self.parent.parent

    def _name_from_attributes(self):
        # For Glyphs 3's speciall layers (brace, bracket, color) we must generate the
        # name from the attributes (as it's shown in Glyphs.app UI) and discard
        # the layer's actual 'name' as found in the source file, which is usually just
        # the unique date-time when a layer was first created.
        # Using the generated name ensures that all the intermediate glyph instances
        # at a given location end up in the same UFO source layer, see:
        # https://github.com/googlefonts/glyphsLib/issues/851
        nameStrings = []

        if self.isColorPaletteLayer:
            name = f"color.{self._color_palette_index()}"
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
        if len(nameStrings):
            return " ".join(nameStrings)
        return None

    def _brace_layer_name(self):
        if not self.isBraceLayer:
            return None
        coordinates = self.attributes[LAYER_ATTRIBUTE_COORDINATES]
        return f"{{{', '.join(floatToString5(v) for v in coordinates.values())}}}"

    def _bracket_layer_name(self):
        axisRules = self.attributes[LAYER_ATTRIBUTE_AXIS_RULES]
        if not axisRules or not isinstance(axisRules, dict):
            return None

        ruleStrings = []
        for axis in self.font.axes:
            rule = axisRules.get(axis.axisId, None)
            if rule:
                minValue = rule.get("min", None)
                maxValue = rule.get("max", None)
                if minValue and maxValue:
                    ruleStrings.append(
                        "%s‹%s‹%s"
                        % (
                            floatToString3(minValue),
                            axis.shortAxisTag,
                            floatToString3(maxValue),
                        )
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

    @property
    def name(self):
        if self.isMasterLayer:
            master = self.parent.parent.masterForId(self.associatedMasterId)
            if master:
                return master.name
        name = self._name_from_attributes()
        if name:
            return name
        return self._name

    @name.setter
    def name(self, value):
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
    def bounds(self):
        left, bottom, right, top = None, None, None, None

        for item in self.paths.values() + self.components.values():
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
            return Rect(Point(left, bottom), Point(right - left, top - bottom))

    def _find_node_by_indices(self, point):
        """ "Find the GSNode that is refered to by the given indices.

        See GSNode::_indices()
        """
        path_index, node_index = point
        path = self.paths[int(path_index)]
        node = path.nodes[int(node_index)]
        return node

    @property
    def background(self):
        """Only a getter on purpose. See the tests."""
        if self._background is None:
            self._background = GSBackgroundLayer()
            self._background._foreground = self
            self._background.parent = self.parent
        return self._background

    # FIXME: (jany) how to check whether there is a background without calling
    #               ::background?
    @property
    def hasBackground(self):
        return bool(self._background)

    @property
    def foreground(self):
        """Forbidden, and also forbidden to set it."""
        raise AttributeError

    def getPen(self) -> AbstractPen:
        """Returns a pen for others to draw into self."""
        pen = SegmentToPointPen(self.getPointPen())
        return pen

    def getPointPen(self) -> AbstractPointPen:
        """Returns a point pen for others to draw points into self."""
        pointPen = LayerPointPen(self)
        return pointPen

    def draw(self, pen: AbstractPen) -> None:
        """Draws glyph with the given pen."""
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of glyph with the given point pen."""
        for path in self.paths:
            path.drawPoints(pointPen)
        for component in self.components:
            component.drawPoints(pointPen)

    @property
    def rightMetricsKey(self):
        return self.metricRight

    @property
    def leftMetricsKey(self):
        return self.metricLeft

    @property
    def widthMetricsKey(self):
        return self.metricWidth

    @rightMetricsKey.setter
    def rightMetricsKey(self, value):
        self.metricRight = value

    @leftMetricsKey.setter
    def leftMetricsKey(self, value):
        self.metricLeft = value

    @widthMetricsKey.setter
    def widthMetricsKey(self, value):
        self.metricWidth = value

    @property
    def isMasterLayer(self):
        return self.layerId == self.associatedMasterId

    @property
    def isBracketLayer(self):
        return LAYER_ATTRIBUTE_AXIS_RULES in self.attributes

    @property
    def isBraceLayer(self):
        return LAYER_ATTRIBUTE_COORDINATES in self.attributes

    @property
    def isColorPaletteLayer(self):
        return LAYER_ATTRIBUTE_COLOR_PALETTE in self.attributes

    def _color_palette_index(self):
        if not self.isColorPaletteLayer:
            return None
        # Glyphs 3
        index = self.attributes[LAYER_ATTRIBUTE_COLOR_PALETTE]
        if index == "*":
            return 0xFFFF
        return int(index)

    @property
    def hasPathComponents(self):
        return any(h.isPathComponent for h in self.hints)

    @property
    def hasCorners(self):
        return self.hasPathComponents


GSLayer._add_parsers(
    [
        {
            "plist_name": "annotations",
            "object_name": "_annotations",
            "type": GSAnnotation,
        },
        {"plist_name": "backgroundImage", "type": GSBackgroundImage},
        {"plist_name": "paths", "type": GSPath},
        {"plist_name": "anchors", "type": GSAnchor},
        {"plist_name": "guideLines", "object_name": "guides", "type": GSGuide},  # V2
        {"plist_name": "guides", "type": GSGuide},  # V3
        {"plist_name": "components", "type": GSComponent},
        {"plist_name": "hints", "type": GSHint},
        {"plist_name": "userData", "object_name": "_userData", "type": dict},
        {
            "plist_name": "partSelection",
            "object_name": "smartComponentPoleMapping",
            "type": dict,
        },
        {
            "plist_name": "leftMetricsKey",
            "object_name": "metricLeft",
            "type": str,
        },  # V2
        {
            "plist_name": "rightMetricsKey",
            "object_name": "metricRight",
            "type": str,
        },  # V2
        {
            "plist_name": "widthMetricsKey",
            "object_name": "metricWidth",
            "type": str,
        },  # V2
        {"plist_name": "attr", "object_name": "attributes", "type": dict},  # V3
    ]
)


class GSBackgroundLayer(GSLayer):
    @property
    def background(self):
        return None

    @property
    def foreground(self):
        return self._foreground

    # The width property of this class behaves like this in Glyphs:
    #  - Always returns 600.0
    #  - Settable but does not remember the value (basically useless)
    # Reproduce this behaviour here so that the roundtrip does not rely on it.
    @property
    def width(self):
        return 600

    @width.setter
    def width(self, whatever):
        pass


class GSGlyph(GSBase):
    def _serialize_to_plist(self, writer):
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
            if True:  # self.direction != GSWritingDirectionRightToLeft:
                writer.writeObjectKeyValue(self, "leftKerningGroup", "if_true")
            # else:
            #    # Glyphs 3 switches the classes. Writing to G2
            #    writer.writeObjectKeyValue(self, "rightKerningGroup", "if_true", keyName="leftKerningGroup")

            writer.writeObjectKeyValue(
                self, "metricLeft", "if_true", keyName="leftMetricsKey"
            )
            writer.writeObjectKeyValue(
                self, "metricWidth", "if_true", keyName="widthMetricsKey"
            )
            writer.writeObjectKeyValue(
                self, "metricVertWidth", "if_true", keyName="vertWidthMetricsKey"
            )

        writer.writeObjectKeyValue(self, "locked", "if_true")

        if writer.formatVersion >= 3:
            writer.writeObjectKeyValue(
                self, "bottomMetricsKey", "if_true", keyName="metricBottom"
            )
            writer.writeObjectKeyValue(
                self, "leftMetricsKey", "if_true", keyName="metricLeft"
            )
            writer.writeObjectKeyValue(
                self, "rightMetricsKey", "if_true", keyName="metricRight"
            )
            writer.writeObjectKeyValue(
                self, "topMetricsKey", "if_true", keyName="metricTop"
            )
            writer.writeObjectKeyValue(
                self, "vertOriginMetricsKey", "if_true", keyName="metricVertOrigin"
            )
            writer.writeObjectKeyValue(
                self, "vertWidthMetricsKey", "if_true", keyName="metricVertWidth"
            )
            writer.writeObjectKeyValue(
                self, "widthMetricsKey", "if_true", keyName="metricWidth"
            )

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
            count_of_unicodes = len(self.unicodes)
            if count_of_unicodes == 1:
                writer.writeKeyValue("unicode", int(self.unicodes[0], 16))
            else:
                v = OneLineList([str(int(u, 16)) for u in self.unicodes])
                writer.writeKeyValue("unicode", v)
        writer.writeObjectKeyValue(self, "userData", "if_true")
        if self.smartComponentAxes:
            writer.writeKeyValue("partsSettings", self.smartComponentAxes)

    _defaultsForName = {
        "category": None,
        "color": None,
        "export": True,
        "lastChange": None,
        "leftKerningGroup": None,
        "metricLeft": None,
        "name": None,
        "note": None,
        "rightKerningGroup": None,
        "metricRight": None,
        "script": None,
        "subCategory": None,
        "userData": None,
        "metricWidth": None,
        "metricVertWidth": None,
    }

    def _parse_unicode_dict(self, parser, value):
        parser.current_type = None
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
            uni = value
        self["_unicodes"] = UnicodesList(uni)

    def _parse_layers_dict(self, parser, value):
        layers = parser._parse(value, GSLayer)
        for l in layers:
            self.layers.append(l)
        return 0

    def post_read(self):  # GSGlyph
        for layer in self.layers:
            layer.post_read()

    def __init__(self, name=None):
        self._layers = OrderedDict()
        self._unicodes = []
        self.bottomKerningGroup = ""
        self.bottomMetricsKey = ""
        self.category = self._defaultsForName["category"]
        self.case = None
        self.color = self._defaultsForName["color"]
        self.export = self._defaultsForName["export"]
        self.lastChange = self._defaultsForName["lastChange"]
        self.leftKerningGroup = self._defaultsForName["leftKerningGroup"]
        self.leftKerningKey = ""
        self.metricLeft = self._defaultsForName["metricLeft"]
        self.name = name
        self.note = self._defaultsForName["note"]
        self.locked = False
        self.parent = None
        self.partsSettings = []
        self.production = ""
        self.rightKerningGroup = self._defaultsForName["rightKerningGroup"]
        self.rightKerningKey = ""
        self.metricRight = self._defaultsForName["metricRight"]
        self.script = self._defaultsForName["script"]
        self.selected = False
        self.subCategory = self._defaultsForName["subCategory"]
        self.tags = []
        self.topKerningGroup = ""
        self.topMetricsKey = ""
        self.userData = self._defaultsForName["userData"]
        self.vertWidthMetricsKey = ""
        self.metricVertWidth = self._defaultsForName["metricVertWidth"]
        self.metricWidth = self._defaultsForName["metricWidth"]
        self.vertOriginMetricsKey = None
        self.vertWidthMetricsKey = None

        self.sortName = None
        self.sortNameKeep = None
        self.direction = None

    def __repr__(self):
        return '<GSGlyph "{}" with {} layers>'.format(self.name, len(self.layers))

    layers = property(
        lambda self: GlyphLayerProxy(self),
        lambda self, value: GlyphLayerProxy(self).setter(value),
    )

    def _setupLayer(self, layer, key):
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

    def removeLayerForKey_(self, key):
        for layer in list(self._layers):
            if layer == key:
                del self._layers[key]

    @property
    def string(self):
        if self.unicode:
            return chr(int(self.unicode, 16))

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def glyphname(self):
        return self.name

    @glyphname.setter
    def glyphname(self, value):
        self.name = value

    @property
    def smartComponentAxes(self):
        return self.partsSettings

    @smartComponentAxes.setter
    def smartComponentAxes(self, value):
        self.partsSettings = value

    @property
    def id(self):
        """An unique identifier for each glyph"""
        return self.name

    @property
    def unicode(self):
        if self._unicodes:
            return self._unicodes[0]
        return None

    @unicode.setter
    def unicode(self, unicode):
        self._unicodes = UnicodesList(unicode)

    @property
    def unicodes(self):
        return self._unicodes

    @unicodes.setter
    def unicodes(self, unicodes):
        self._unicodes = UnicodesList(unicodes)

    # V2 compatible interface
    @property
    def rightMetricsKey(self):
        return self.metricRight

    @rightMetricsKey.setter
    def rightMetricsKey(self, value):
        self.metricRight = value

    @property
    def leftMetricsKey(self):
        return self.metricLeft

    @leftMetricsKey.setter
    def leftMetricsKey(self, value):
        self.metricLeft = value

    @property
    def widthMetricsKey(self):
        return self.metricWidth

    @widthMetricsKey.setter
    def widthMetricsKey(self, value):
        self.metricWidth = value

    @property
    def vertWidthMetricsKey(self):
        return self.metricVertWidth

    @vertWidthMetricsKey.setter
    def vertWidthMetricsKey(self, value):
        self.metricVertWidth = value


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
        {"plist_name": "leftMetricsKey", "object_name": "metricLeft"},  # V2
        {"plist_name": "rightMetricsKey", "object_name": "metricRight"},  # V2
        {"plist_name": "widthMetricsKey", "object_name": "metricWidth"},  # V2
        {"plist_name": "vertWidthMetricsKey", "object_name": "metricVertWidth"},  # V2
        {"plist_name": "sortName", "object_name": "sortName"},
        {"plist_name": "sortNameKeep", "object_name": "sortNameKeep"},
        {"plist_name": "direction", "object_name": "direction"},
    ]
)


class GSFont(GSBase):
    _defaultsForName = {
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

    def _serialize_to_plist(self, writer):  # noqa: C901
        writer.writeKeyValue(".appVersion", self.appVersion)
        if writer.formatVersion > 2:
            writer.writeKeyValue(".formatVersion", self.formatVersion)
        if self.displayStrings and writer.container == "flat":
            writer.writeKeyValue("DisplayStrings", self.displayStrings)

        customParameters = list(self.customParameters)
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
                axes = []
                for axis in self.axes:
                    axesDict = {"Name": axis.name, "Tag": axis.axisTag}
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
            if self.kerningLTR:
                writer.writeKeyValue("kerning", self.kerningLTR)
            if self.kerningRTL:
                writer.writeKeyValue("vertKerning", self.kerningRTL)
        else:
            writer.writeObjectKeyValue(self, "kerningLTR", "if_true")
            writer.writeObjectKeyValue(self, "kerningRTL", "if_true")
            writer.writeObjectKeyValue(self, "kerningVertical", "if_true")

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

    _defaultMetrics = [
        GSMetric(metricType=GSMetricsKeyAscender),
        GSMetric(metricType=GSMetricsKeyCapHeight),
        GSMetric(metricType=GSMetricsKeyxHeight),
        GSMetric(metricType=GSMetricsKeyBaseline),
        GSMetric(metricType=GSMetricsKeyDescender),
        # GSMetric(metricType=GSMetricsKeyItalicAngle),
    ]

    def _parse_glyphs_dict(self, parser, value):
        glyphs = parser._parse(value, GSGlyph)
        for l in glyphs:
            self.glyphs.append(l)
        return 0

    def _parse_settings_dict(self, parser, settings):
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

    def _parse___formatVersion_dict(self, parser, val):
        self.formatVersion = parser.formatVersion = val

    def __init__(self, path=None):
        self.displayStrings = ""
        self.familyName = "Unnamed font"
        self.fontType = FontType.DEFAULT
        self._glyphs = []
        self._instances = []
        self._masters = []
        self.axes = []
        self._userData = None
        self._versionMinor = 0
        self.formatVersion = 3
        self.appVersion = "895"  # minimum required version
        self.classes = copy.copy(self._defaultsForName["classes"])
        self.features = copy.copy(self._defaultsForName["features"])
        self.featurePrefixes = copy.copy(self._defaultsForName["featurePrefixes"])
        self.customParameters = []
        self.date = None
        self._disablesAutomaticAlignment = self._defaultsForName[
            "disablesAutomaticAlignment"
        ]
        self.disablesNiceNames = self._defaultsForName["disablesNiceNames"]
        self._disablesAutomaticAlignment = None
        self.filepath = None
        self.grid = self._defaultsForName["grid"]
        self.gridSubDivision = self._defaultsForName["gridSubDivision"]
        self.keepAlternatesTogether = False
        self._kerningLTR = OrderedDict()
        self._kerningRTL = OrderedDict()
        self._kerningVertical = OrderedDict()
        self.metrics = copy.copy(self._defaultMetrics)
        self.numbers = []
        self._properties = []
        self._stems = []
        self.keyboardIncrement = self._defaultsForName["keyboardIncrement"]
        self.keyboardIncrementBig = self._defaultsForName["keyboardIncrementBig"]
        self.keyboardIncrementHuge = self._defaultsForName["keyboardIncrementHuge"]
        self.previewRemoveOverlap = True
        self.upm = self._defaultsForName["unitsPerEm"]
        self.versionMajor = 1
        self._note = ""
        self.readBuffer = {}

        if path:
            path = os.fsdecode(os.fspath(path))
            self.filepath = path
            load(path, self)

    def __repr__(self):
        adress = id(self)
        return f'<{self.__class__.__name__} "{self.familyName}" at 0x{adress}>'

    def save(self, path=None):
        if path is None:
            if self.filepath:
                path = self.filepath
            else:
                raise ValueError("No path provided and GSFont has no filepath")
        if path.endswith(".glyphs"):
            self.save_flat_file(path)
        elif path.endswith(".glyphspackage"):
            self.save_package_file(path)
        else:
            raise ValueError("unknown file extension on path:", path)

    def save_flat_file(self, path):
        with open(path, "w", encoding="utf-8") as fp:
            w = Writer(fp, formatVersion=self.formatVersion)
            logger.info("Writing %r to .glyphs file", self)
            w.write(self)

    def save_package_file(self, path):
        os.makedirs(path, exist_ok=True)
        glyphs_folder = os.path.join(path, "glyphs")
        os.makedirs(glyphs_folder, exist_ok=True)
        glyph_order = []
        for glyph in self.glyphs:
            name = glyph.name
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
        info_file = os.path.join(path, "fontinfo.plist")
        if self.displayStrings:
            uistate_file = os.path.join(path, "UIState.plist")
            with open(uistate_file, "w", encoding="utf-8") as fp:
                w = Writer(fp, formatVersion=self.formatVersion)
                w.write({"displayStrings": self.displayStrings})

    def _getAxisCountFromMasters(self, masters):
        axisCount = 6
        widthValueSet = set()
        customValueSet = set()
        customValue1Set = set()
        customValue2Set = set()
        customValue3Set = set()
        for master in masters:
            axesValues = self.readBuffer.get("axesValues")
            if not axesValues:
                axesValues = []
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

    def _getLegacyAxes(self):
        legacyAxes = []
        axesCount = self._getAxisCountFromMasters(self.masters)
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

    def post_read(self):  # GSFont
        if self.formatVersion < 3:
            axesParameter = self.customParameters["Axes"]
            if axesParameter:
                for axisDict in axesParameter:
                    axis = GSAxis()
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
            idx = 1
            for axis in self.axes:
                axis.axisId = (
                    "a%02d" % idx
                )  # this is more cosmetic as the default would do
                idx += 1
        assert self.axes is not None
        for master in self.masters:
            assert master.font == self
            master.font = self
            master.post_read()
        for instance in self.instances:
            assert instance.font == self
            instance.post_read()
        for glyph in self.glyphs:
            glyph.post_read()
        for feature in self.features:
            feature.post_read()
        if self.customParameters["note"]:
            self.note = self.customParameters["note"]
            del self.customParameters["note"]

    def getVersionMinor(self):
        return self._versionMinor

    def setVersionMinor(self, value):
        """Ensure that the minor version number is between 0 and 999."""
        assert 0 <= value <= 999
        self._versionMinor = value

    versionMinor = property(getVersionMinor, setVersionMinor)

    @property
    def formatVersion(self):
        raise "not implemented"

    @formatVersion.setter
    def formatVersion(self, value):
        raise "not implemented"

    @property
    def formatVersion(self):
        return self._formatVersion

    @formatVersion.setter
    def formatVersion(self, value):
        self._formatVersion = value

    glyphs = property(
        lambda self: FontGlyphsProxy(self),
        lambda self, value: FontGlyphsProxy(self).setter(value),
    )

    def _setupGlyph(self, glyph):
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

    def masterForId(self, key):
        for master in self._masters:
            if master.id == key:
                return master
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
    def stems(self):
        return self._stems

    @stems.setter
    def stems(self, stems):
        assert not stems or isinstance(stems[0], GSMetric)
        self._stems = stems

    def stemForKey(self, key):
        if isinstance(key, int):
            if key < 0:
                key += self.__len__()
            stem = self.stems[key]
        elif isString(key):
            stem = self.stemForName(key)
            if stem is None:
                stem = self.stemForId(key)
        else:
            raise TypeError(
                "list indices must be integers or strings, not %s" % type(key).__name__
            )
        return stem

    def stemForName(self, key):
        for stem in self._stems:
            if stem.name == key:
                return stem
        return None

    def stemForId(self, key):
        for stem in self._stems:
            if stem.id == key:
                return stem
        return None

    @property
    def kerning(self):
        return self._kerningLTR

    @kerning.setter
    def kerning(self, kerning):
        self.kerningLTR = kerning

    @property
    def kerningLTR(self):
        return self._kerningLTR

    @kerningLTR.setter
    def kerningLTR(self, kerning):
        self._kerningLTR = kerning
        for master_map in kerning.values():
            for glyph_map in master_map.values():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = parse_float_or_int(value)

    @property
    def kerningRTL(self):
        return self._kerningRTL

    @kerningRTL.setter
    def kerningRTL(self, kerning):
        self._kerningRTL = kerning
        for master_map in kerning.values():
            for glyph_map in master_map.values():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = parse_float_or_int(value)

    @property
    def kerningVertical(self):
        return self._kerningVertical

    @kerningVertical.setter
    def kerningVertical(self, kerning):
        self._kerningVertical = kerning
        for master_map in kerning.values():
            for glyph_map in master_map.values():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = parse_float_or_int(value)

    @property
    def selection(self):
        return (glyph for glyph in self.glyphs if glyph.selected)

    @property
    def note(self):
        return self._note

    @note.setter
    def note(self, value):
        self._note = value

    @property
    def gridLength(self):
        if self.gridSubDivision > 0:
            return self.grid / self.gridSubDivision
        else:
            return self.grid

    @property
    def disablesAutomaticAlignment(self):
        return self._disablesAutomaticAlignment

    @disablesAutomaticAlignment.setter
    def disablesAutomaticAlignment(self, value):
        assert value or self._disablesAutomaticAlignment is None
        self._disablesAutomaticAlignment = value

    EMPTY_KERNING_VALUE = (1 << 63) - 1  # As per the documentation

    def kerningForPair(self, fontMasterId, leftKey, rightKey, direction=LTR):
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

    def setKerningForPair(self, fontMasterId, leftKey, rightKey, value, direction=LTR):
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

    def removeKerningForPair(self, fontMasterId, leftKey, rightKey, direction=LTR):
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
    def manufacturer(self):
        return self.properties["manufacturers"]

    @manufacturer.setter
    def manufacturer(self, value):
        self.properties.setProperty("manufacturers", value)

    @property
    def manufacturerURL(self):
        return self.properties["manufacturerURL"]

    @manufacturerURL.setter
    def manufacturerURL(self, value):
        self.properties["manufacturerURL"] = value

    @property
    def copyright(self):
        return self.properties["copyrights"]

    @copyright.setter
    def copyright(self, value):
        self.properties.setProperty("copyrights", value)

    @property
    def trademark(self):
        return self.properties["trademarks"]

    @trademark.setter
    def trademark(self, value):
        self.properties.setProperty("trademarks", value)

    @property
    def designer(self):
        return self.properties["designers"]

    @designer.setter
    def designer(self, value):
        self.properties.setProperty("designers", value)

    @property
    def designerURL(self):
        return self.properties["designerURL"]

    @designerURL.setter
    def designerURL(self, value):
        self.properties["designerURL"] = value

    @property
    def settings(self):
        _settings = OrderedDict()
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
        {
            "plist_name": "vertKerning",
            "object_name": "_kerningRTL",
            "type": OrderedDict,
        },
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
