# Copyright 2015 Google Inc. All Rights Reserved.
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

from __future__ import (print_function, division, absolute_import,
                        unicode_literals)

PUBLIC_PREFIX = 'public.'
GLYPHS_PREFIX = 'com.schriftgestaltung.'
GLYPHLIB_PREFIX = GLYPHS_PREFIX + 'Glyphs.'
ROBOFONT_PREFIX = 'com.typemytype.robofont.'
UFO2FT_FILTERS_KEY = 'com.github.googlei18n.ufo2ft.filters'

GLYPHS_COLORS = (
    '0.85,0.26,0.06,1',
    '0.99,0.62,0.11,1',
    '0.65,0.48,0.2,1',
    '0.97,1,0,1',
    '0.67,0.95,0.38,1',
    '0.04,0.57,0.04,1',
    '0,0.67,0.91,1',
    '0.18,0.16,0.78,1',
    '0.5,0.09,0.79,1',
    '0.98,0.36,0.67,1',
    '0.75,0.75,0.75,1',
    '0.25,0.25,0.25,1')

# https://www.microsoft.com/typography/otspec/os2.htm#cpr
CODEPAGE_RANGES = {
    1252: 0,
    1250: 1,
    1251: 2,
    1253: 3,
    1254: 4,
    1255: 5,
    1256: 6,
    1257: 7,
    1258: 8,
    # 9-15: Reserved for Alternate ANSI
    874: 16,
    932: 17,
    936: 18,
    949: 19,
    950: 20,
    1361: 21,
    # 22-28: Reserved for Alternate ANSI and OEM
    # 29: Macintosh Character Set (US Roman)
    # 30: OEM Character Set
    # 31: Symbol Character Set
    # 32-47: Reserved for OEM
    869: 48,
    866: 49,
    865: 50,
    864: 51,
    863: 52,
    862: 53,
    861: 54,
    860: 55,
    857: 56,
    855: 57,
    852: 58,
    775: 59,
    737: 60,
    708: 61,
    850: 62,
    437: 63,
}
