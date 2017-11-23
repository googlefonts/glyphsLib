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

import re

from glyphsLib.util import bin_to_int_list
from .filters import parse_glyphs_filter
from .constants import (GLYPHS_PREFIX, PUBLIC_PREFIX, CODEPAGE_RANGES,
                        UFO2FT_FILTERS_KEY)
from .features import replace_feature


def to_ufo_custom_params(self, ufo, master):
    misc = ['DisplayStrings', 'disablesAutomaticAlignment', 'disablesNiceNames']
    custom_params = parse_custom_params(self.font, misc)
    set_custom_params(ufo, parsed=custom_params)
    # the misc attributes double as deprecated info attributes!
    # they are Glyphs-related, not OpenType-related, and don't go in info
    misc = ('customValue', 'weightValue', 'widthValue')
    set_custom_params(ufo, data=master, misc_keys=misc, non_info=misc)

    set_default_params(ufo)


def set_custom_params(ufo, parsed=None, data=None, misc_keys=(), non_info=()):
    """Set Glyphs custom parameters in UFO info or lib, where appropriate.

    Custom parameter data can be pre-parsed out of Glyphs data and provided via
    the `parsed` argument, otherwise `data` should be provided and will be
    parsed. The `parsed` option is provided so that custom params can be popped
    from Glyphs data once and used several times; in general this is used for
    debugging purposes (to detect unused Glyphs data).

    The `non_info` argument can be used to specify potential UFO info attributes
    which should not be put in UFO info.
    """

    if parsed is None:
        parsed = parse_custom_params(data or {}, misc_keys)
    else:
        assert data is None, "Shouldn't provide parsed data and data to parse."

    fsSelection_flags = {'Use Typo Metrics', 'Has WWS Names'}
    for name, value in parsed:
        name = normalize_custom_param_name(name)

        if name in fsSelection_flags:
            if value:
                if ufo.info.openTypeOS2Selection is None:
                    ufo.info.openTypeOS2Selection = []
                if name == 'Use Typo Metrics':
                    ufo.info.openTypeOS2Selection.append(7)
                elif name == 'Has WWS Names':
                    ufo.info.openTypeOS2Selection.append(8)
            continue

        # deal with any Glyphs naming quirks here
        if name == 'disablesNiceNames':
            name = 'useNiceNames'
            value = not value

        if name == 'Disable Last Change':
            name = 'disablesLastChange'

        # convert code page numbers to OS/2 ulCodePageRange bits
        if name == 'codePageRanges':
            value = [CODEPAGE_RANGES[v] for v in value]

        # convert Glyphs' GASP Table to UFO openTypeGaspRangeRecords
        if name == 'GASP Table':
            name = 'openTypeGaspRangeRecords'
            # XXX maybe the parser should cast the gasp values to int?
            value = {int(k): int(v) for k, v in value.items()}
            gasp_records = []
            # gasp range records must be sorted in ascending rangeMaxPPEM
            for max_ppem, gasp_behavior in sorted(value.items()):
                gasp_records.append({
                    'rangeMaxPPEM': max_ppem,
                    'rangeGaspBehavior': bin_to_int_list(gasp_behavior)})
            value = gasp_records

        opentype_attr_prefix_pairs = (
            ('hhea', 'Hhea'), ('description', 'NameDescription'),
            ('license', 'NameLicense'),
            ('licenseURL', 'NameLicenseURL'),
            ('preferredFamilyName', 'NamePreferredFamilyName'),
            ('preferredSubfamilyName', 'NamePreferredSubfamilyName'),
            ('compatibleFullName', 'NameCompatibleFullName'),
            ('sampleText', 'NameSampleText'),
            ('WWSFamilyName', 'NameWWSFamilyName'),
            ('WWSSubfamilyName', 'NameWWSSubfamilyName'),
            ('panose', 'OS2Panose'),
            ('typo', 'OS2Typo'), ('unicodeRanges', 'OS2UnicodeRanges'),
            ('codePageRanges', 'OS2CodePageRanges'),
            ('weightClass', 'OS2WeightClass'),
            ('widthClass', 'OS2WidthClass'),
            ('win', 'OS2Win'), ('vendorID', 'OS2VendorID'),
            ('versionString', 'NameVersion'), ('fsType', 'OS2Type'))
        for glyphs_prefix, ufo_prefix in opentype_attr_prefix_pairs:
            name = re.sub(
                '^' + glyphs_prefix, 'openType' + ufo_prefix, name)

        postscript_attrs = ('underlinePosition', 'underlineThickness')
        if name in postscript_attrs:
            name = 'postscript' + name[0].upper() + name[1:]

        # enforce that winAscent/Descent are positive, according to UFO spec
        if name.startswith('openTypeOS2Win') and value < 0:
            value = -value

        # The value of these could be a float or str, and UFO expects an int.
        if name in ('openTypeOS2WeightClass', 'openTypeOS2WidthClass',
                    'xHeight'):
            value = int(value)

        if name == 'glyphOrder':
            # store the public.glyphOrder in lib.plist
            ufo.lib[PUBLIC_PREFIX + name] = value
        elif name in ('PreFilter', 'Filter'):
            filter_struct = parse_glyphs_filter(
                value, is_pre=name.startswith('Pre'))
            if not filter_struct:
                continue
            if UFO2FT_FILTERS_KEY not in ufo.lib.keys():
                ufo.lib[UFO2FT_FILTERS_KEY] = []
            ufo.lib[UFO2FT_FILTERS_KEY].append(filter_struct)
        elif name == "Replace Feature":
            tag, repl = re.split("\s*;\s*", value, 1)
            ufo.features.text = replace_feature(tag, repl,
                                                ufo.features.text or "")
        elif hasattr(ufo.info, name) and name not in non_info:
            # most OpenType table entries go in the info object
            setattr(ufo.info, name, value)
        else:
            # everything else gets dumped in the lib
            ufo.lib[GLYPHS_PREFIX + name] = value


def set_default_params(ufo):
    """ Set Glyphs.app's default parameters when different from ufo2ft ones.
    """
    # ufo2ft defaults to fsType Bit 2 ("Preview & Print embedding"), while
    # Glyphs.app defaults to Bit 3 ("Editable embedding")
    if ufo.info.openTypeOS2Type is None:
        ufo.info.openTypeOS2Type = [3]

    # Reference:
    # https://glyphsapp.com/content/1-get-started/2-manuals/1-handbook-glyphs-2-0/Glyphs-Handbook-2.3.pdf#page=200
    if ufo.info.postscriptUnderlineThickness is None:
        ufo.info.postscriptUnderlineThickness = 50
    if ufo.info.postscriptUnderlinePosition is None:
        ufo.info.postscriptUnderlinePosition = -100


def normalize_custom_param_name(name):
    """Replace curved quotes with straight quotes in a custom parameter name.
    These should be the only keys with problematic (non-ascii) characters,
    since they can be user-generated.
    """

    replacements = (
        (u'\u2018', "'"), (u'\u2019', "'"), (u'\u201C', '"'), (u'\u201D', '"'))
    for orig, replacement in replacements:
        name = name.replace(orig, replacement)
    return name


def parse_custom_params(font, misc_keys):
    """Parse customParameters into a list of <name, val> pairs."""

    params = []
    for p in font.customParameters:
        params.append((p.name, p.value))
    for key in misc_keys:
        try:
            val = getattr(font, key)
        except AttributeError:
            continue
        if val is not None:
            params.append((key, val))
    return params
