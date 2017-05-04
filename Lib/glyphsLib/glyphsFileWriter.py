#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Georg Seifert. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: #www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import traceback
import glyphsLib, glyphsLib.classes
# from .classes import GSBase, Proxy
from .types import floatToString, needsQuotes, feature_syntax_encode
import datetime
import collections

'''
    Usage

    writer = GlyphsWriter('Path/to/File.glyphs')
    writer.write(font)

'''


class GlyphsWriter(object):

    def __init__(self, filePath=None, fp=None):

        if fp is not None:
            self.file = fp
        elif filePath is None:
            self.file = sys.stdout
        else:
            self.file = open(filePath, "w")

    def write(self, baseObject):

        self.writeDict(baseObject)
        self.file.write("\n")
        self.file.close()

    def writeDict(self, dictValue):
        self.file.write("{\n")
        forType = None
        if hasattr(dictValue, "_keyOrder"):
            keys = dictValue._keyOrder
        elif hasattr(dictValue, "_classesForName"):
            keys = sorted(dictValue._classesForName.keys())
        else:
            keys = dictValue.keys()
            if not isinstance(dictValue, collections.OrderedDict):
                keys = sorted(keys)
        for key in keys:
            if hasattr(dictValue, "_classesForName"):
                forType = dictValue._classesForName[key]
            try:
                if isinstance(dictValue, (dict, collections.OrderedDict)):
                    value = dictValue[key]
                else:
                    getKey = key
                    if hasattr(dictValue, "_wrapperKeysTranslate"):
                        getKey = dictValue._wrapperKeysTranslate.get(key, key)
                    value = getattr(dictValue, getKey)
            except AttributeError:
                continue
            if value is None or (isinstance(value, (list, glyphsLib.classes.Proxy, str, unicode)) and len(value) == 0):
                continue
            try:
                if not dictValue.shouldWriteValueForKey(key):
                    continue
            except AttributeError:
                pass
            self.writeKey(key)
            self.writeValue(value, key, forType=forType)
            self.file.write(";\n")
        self.file.write("}")

    def writeArray(self, arrayValue):
        self.file.write("(\n")
        idx = 0
        length = len(arrayValue)
        for value in arrayValue:
            self.writeValue(value)
            if idx < length - 1:
                self.file.write(",\n")
            else:
                self.file.write("\n")
            idx += 1
        self.file.write(")")

    def writeValue(self, value, forKey=None, forType=None):
        if isinstance(value, (list, glyphsLib.classes.Proxy)):
            self.writeArray(value)
        elif hasattr(value, "plistValue"):
            value = value.plistValue()
            self.file.write(value)
        elif isinstance(value, (dict, collections.OrderedDict, glyphsLib.classes.GSBase)):
            self.writeDict(value)
        elif type(value) == float:
            self.file.write(floatToString(value, 5))
        elif type(value) == int:
            self.file.write(str(value))
        elif type(value) == bool:
            if value:
                self.file.write("1")
            else:
                self.file.write("0")
        elif type(value) == datetime.datetime:
            self.file.write("\"%s +0000\"" % str(value))
        else:
            if isinstance(value, unicode):
                value = value.encode("utf-8")
            value = feature_syntax_encode(value)
            self.file.write(value)

    def writeKey(self, key):
        if needsQuotes(key):
            self.file.write("\"%s\" = " % key)
        else:
            self.file.write("%s = " % key)
