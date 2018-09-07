# coding=UTF-8
#
# Copyright 2016 Google Inc. All Rights Reserved.
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

from __future__ import print_function, division, absolute_import, unicode_literals


"""
Goal: have a unit test for each parameter that is mentioned in the UFO spec.
Each test will check that this parameter is round-tripped and, when relevant,
that the Glyphs storage of the value has the correct Glyphs meaning.

http://unifiedfontobject.org/versions/ufo3/fontinfo.plist/
"""

import os
import pytest
from collections import namedtuple

import defcon

from glyphsLib import to_glyphs, to_ufos, classes


def section(name, *fields):
    return pytest.param(fields, id=name)


def skip_section(name, *fields):
    return pytest.param(fields, id=name, marks=pytest.mark.skip)


Field = namedtuple("Field", "name test_value")


ufo_info_spec = [
    section(
        "Generic Identification Information",
        # familyName	string	Family name.
        Field("familyName", "Ronoto Sans"),
        # styleName	string	Style name.
        Field("styleName", "Condensed"),
        # styleMapFamilyName string Family name used for bold, italic and bold
        # italic style mapping.
        Field("styleMapFamilyName", "Ronoto Sans Condensed"),
        # styleMapStyleName string Style map style. The possible values are
        # regular, italic, bold and bold italic. These are case sensitive.
        Field("styleMapStyleName", "regular"),
        # versionMajor integer Major version.
        Field("versionMajor", 1),
        # versionMinor	non-negative integer	Minor version.
        Field("versionMinor", 12),
        # year integer The year the font was created. This attribute is
        # deprecated as of version 2. Its presence should not be relied upon by
        # authoring tools. However, it may occur in a font's info so authoring
        # tools should preserve it if present.
        Field("year", 2013),
    ),
    section(
        "Generic Legal Information",
        # copyright	string	Copyright statement.
        Field("copyright", "© Glooble"),
        # trademark	string	Trademark statement.
        Field("trademark", "Ronoto™® is a trademark of Glooble Inc. Ltd."),
    ),
    section(
        "Generic Dimension Information",
        # unitsPerEm	non-negative integer or float	Units per em.
        Field("unitsPerEm", 1234),
        # descender	integer or float	Descender value.
        Field("descender", 123.7),
        # xHeight	integer or float	x-height value.
        Field("xHeight", 456),
        # capHeight	integer or float	Cap height value.
        Field("capHeight", 789),
        # ascender	integer or float	Ascender value.
        Field("ascender", 789.1),
        # italicAngle integer or float Italic angle. This must be an angle in
        # counter-clockwise degrees from the vertical.
        Field("italicAngle", -12.5),
    ),
    section(
        "Generic Miscellaneous Information",
        # note	string	Arbitrary note about the font.
        Field("note", "Bla bla"),
    ),
    section(
        "OpenType GASP Table Fields",
        # openTypeGaspRangeRecords list A list of gasp Range Records. These
        # must be sorted in ascending order based on the rangeMaxPPEM value of
        # the record.
        #
        # The records are stored as dictionaries of the following format.
        # key	value type	description
        # rangeMaxPPEM non-negative integer The upper limit of the range, in
        # PPEM. If any records are in the list, the final record should use
        # 65535 (0xFFFF) as defined in the OpenType gasp specification.
        # Corresponds to the rangeMaxPPEM field of the GASPRANGE record in the
        # OpenType gasp table.
        # rangeGaspBehavior list A list of bit numbers indicating the flags
        # to be set. The bit numbers are defined below. Corresponds to the
        # rangeGaspBehavior field of the GASPRANGE record in the OpenType gasp
        # table.
        Field(
            "openTypeGaspRangeRecords",
            [
                {"rangeMaxPPEM": 16, "rangeGaspBehavior": [0]},
                {"rangeMaxPPEM": 65535, "rangeGaspBehavior": [0, 1]},
            ],
        ),
    ),
    section(
        "OpenType head Table Fields",
        # openTypeHeadCreated string Creation date. Expressed as a string of
        # the format “YYYY/MM/DD HH:MM:SS”. “YYYY/MM/DD” is year/month/day. The
        # month must be in the range 1-12 and the day must be in the range
        # 1-end of month. “HH:MM:SS” is hour:minute:second. The hour must be in
        # the range 0:23. The minute and second must each be in the range 0-59.
        Field("openTypeHeadCreated", "2014/02/28 19:20:48"),
        # openTypeHeadLowestRecPPEM non-negative integer Smallest readable size
        # in pixels. Corresponds to the OpenType head table lowestRecPPEM
        # field.
        Field("openTypeHeadLowestRecPPEM", 12),
        # openTypeHeadFlags list A list of bit numbers indicating the flags.
        # The bit numbers are listed in the OpenType head specification.
        # Corresponds to the OpenType head table flags field.
        Field("openTypeHeadFlags", [2, 3, 11]),
    ),
    section(
        "OpenType hhea Table Fields",
        # openTypeHheaAscender integer Ascender value. Corresponds to the
        # OpenType hhea table Ascender field.
        Field("openTypeHheaAscender", 123),
        # openTypeHheaDescender integer Descender value. Corresponds to the
        # OpenType hhea table Descender field.
        Field("openTypeHheaDescender", 456),
        # openTypeHheaLineGap integer Line gap value. Corresponds to the
        # OpenType hhea table LineGap field.
        Field("openTypeHheaLineGap", 789),
        # openTypeHheaCaretSlopeRise integer Caret slope rise value.
        # Corresponds to the OpenType hhea table caretSlopeRise field.
        Field("openTypeHheaCaretSlopeRise", 800),
        # openTypeHheaCaretSlopeRun integer Caret slope run value. Corresponds
        # to the OpenType hhea table caretSlopeRun field.
        Field("openTypeHheaCaretSlopeRun", 100),
        # openTypeHheaCaretOffset integer Caret offset value. Corresponds to
        # the OpenType hhea table caretOffset field.
        Field("openTypeHheaCaretOffset", 20),
    ),
    section(
        "OpenType name Table Fields",
        # openTypeNameDesigner	string	Designer name.
        # Corresponds to the OpenType name table name ID 9.
        Field("openTypeNameDesigner", "Bob"),
        # openTypeNameDesignerURL	string	URL for the designer.
        # Corresponds to the OpenType name table name ID 12.
        Field("openTypeNameDesignerURL", "http://bob.me/"),
        # openTypeNameManufacturer	string	Manufacturer name.
        # Corresponds to the OpenType name table name ID 8.
        Field("openTypeNameManufacturer", "Exemplary Type"),
        # openTypeNameManufacturerURL	string	Manufacturer URL.
        # Corresponds to the OpenType name table name ID 11.
        Field("openTypeNameManufacturerURL", "http://exemplary.type"),
        # openTypeNameLicense	string	License text.
        # Corresponds to the OpenType name table name ID 13.
        Field("openTypeNameLicense", "OFL 1.1"),
        # openTypeNameLicenseURL	string	URL for the license.
        # Corresponds to the OpenType name table name ID 14.
        Field("openTypeNameLicenseURL", "http://scripts.sil.org/OFL"),
        # openTypeNameVersion	string	Version string.
        # Corresponds to the OpenType name table name ID 5.
        Field("openTypeNameVersion", "Version 2.003"),
        # openTypeNameUniqueID	string	Unique ID string.
        # Corresponds to the OpenType name table name ID 3.
        Field("openTypeNameUniqueID", "2.003;Exemplary Sans Bold Large Display"),
        # openTypeNameDescription	string	Description of the font.
        # Corresponds to the OpenType name table name ID 10.
        Field("openTypeNameDescription", "Best used\nfor typesetting\nhaikus"),
        # openTypeNamePreferredFamilyName	string	Preferred family name.
        # Corresponds to the OpenType name table name ID 16.
        Field("openTypeNamePreferredFamilyName", "Exemplary Sans"),
        # openTypeNamePreferredSubfamilyName	string	Preferred subfamily name.
        # Corresponds to the OpenType name table name ID 17.
        Field("openTypeNamePreferredSubfamilyName", "Bold Large Display"),
        # openTypeNameCompatibleFullName	string	Compatible full name.
        # Corresponds to the OpenType name table name ID 18.
        Field("openTypeNameCompatibleFullName", "Exemplary Sans Bold Large Display"),
        # openTypeNameSampleText	string	Sample text.
        # Corresponds to the OpenType name table name ID 19.
        Field("openTypeNameSampleText", "Pickles are our friends"),
        # openTypeNameWWSFamilyName	string	WWS family name.
        # Corresponds to the OpenType name table name ID 21.
        Field("openTypeNameWWSFamilyName", "Exemplary Sans Display"),
        # openTypeNameWWSSubfamilyName	string	WWS Subfamily name.
        # Corresponds to the OpenType name table name ID 22.
        Field("openTypeNameWWSSubfamilyName", "Bold Large"),
        # openTypeNameRecords list A list of name records. This name record storage
        # area is intended for records that require platform, encoding and or
        # language localization.
        # The records are stored as dictionaries of the following format.
        # nameID	non-negative integer	The name ID.
        # platformID	non-negative integer	The platform ID.
        # encodingID	non-negative integer	The encoding ID.
        # languageID	non-negative integer	The language ID.
        # string	string	The string value for the record.
        Field(
            "openTypeNameRecords",
            [
                {
                    "nameID": 19,
                    "platformID": 1,
                    "encodingID": 0,
                    "languageID": 1,
                    "string": "Les cornichons sont nos amis",
                },
                {
                    "nameID": 1,
                    "platformID": 3,
                    "encodingID": 1,
                    "languageID": 0x0410,
                    "string": "Illustrativo Sans",
                },
            ],
        ),
    ),
    section(
        "OpenType OS/2 Table Fields",
        # openTypeOS2WidthClass integer Width class value. Must be in the range
        # 1-9 Corresponds to the OpenType OS/2 table usWidthClass field.
        Field("openTypeOS2WidthClass", 7),
        # openTypeOS2WeightClass integer Weight class value. Must be a
        # non-negative integer. Corresponds to the OpenType OS/2 table
        # usWeightClass field.
        Field("openTypeOS2WeightClass", 700),
        # openTypeOS2Selection list A list of bit numbers indicating the bits
        # that should be set in fsSelection. The bit numbers are listed in the
        # OpenType OS/2 specification.
        # Corresponds to the OpenType OS/2 table selection field.
        # Note: Bits 0 (italic), 5 (bold) and 6 (regular) must not be set here.
        # These bits should be taken from the generic styleMapStyle attribute.
        Field("openTypeOS2Selection", [7, 8]),
        # openTypeOS2VendorID string Four character identifier for the creator
        # of the font. Corresponds to the OpenType OS/2 table achVendID field.
        Field("openTypeOS2VendorID", "EXTY"),
        # openTypeOS2Panose list The list must contain 10 non-negative integers
        # that represent the setting for each category in the Panose
        # specification. The integers correspond with the option numbers in
        # each of the Panose categories. This corresponds to the OpenType OS/2
        # table Panose field.
        Field("openTypeOS2Panose", [2, 11, 8, 5, 3, 4, 0, 0, 0, 0]),
        # openTypeOS2FamilyClass list Two integers representing the IBM font
        # class and font subclass of the font. The first number, representing
        # the class ID, must be in the range 0-14. The second number,
        # representing the subclass, must be in the range 0-15. The numbers are
        # listed in the OpenType OS/2 specification.
        # Corresponds to the OpenType OS/2 table sFamilyClass field.
        Field("openTypeOS2FamilyClass", [8, 2]),
        # openTypeOS2UnicodeRanges list A list of bit numbers that are
        # supported Unicode ranges in the font. The bit numbers are listed in
        # the OpenType OS/2 specification. Corresponds to the OpenType OS/2
        # table ulUnicodeRange1, ulUnicodeRange2, ulUnicodeRange3 and
        # ulUnicodeRange4 fields.
        Field("openTypeOS2UnicodeRanges", [0, 1, 2, 3, 37, 79, 122]),
        # openTypeOS2CodePageRanges list A list of bit numbers that are
        # supported code page ranges in the font. The bit numbers are listed in
        # the OpenType OS/2 specification. Corresponds to the OpenType OS/2
        # table ulCodePageRange1 and ulCodePageRange2 fields.
        Field("openTypeOS2CodePageRanges", [0, 1, 29, 58]),
        # openTypeOS2TypoAscender	integer	Ascender value.
        # Corresponds to the OpenType OS/2 table sTypoAscender field.
        Field("openTypeOS2TypoAscender", 1000),
        # openTypeOS2TypoDescender	integer	Descender value.
        # Corresponds to the OpenType OS/2 table sTypoDescender field.
        Field("openTypeOS2TypoDescender", -234),
        # openTypeOS2TypoLineGap	integer	Line gap value.
        # Corresponds to the OpenType OS/2 table sTypoLineGap field.
        Field("openTypeOS2TypoLineGap", 456),
        # openTypeOS2WinAscent	non-negative integer	Ascender value.
        # Corresponds to the OpenType OS/2 table usWinAscent field.
        Field("openTypeOS2WinAscent", 1500),
        # openTypeOS2WinDescent	non-negative integer	Descender value.
        # Corresponds to the OpenType OS/2 table usWinDescent field.
        Field("openTypeOS2WinDescent", 750),
        # openTypeOS2Type list A list of bit numbers indicating the embedding
        # type. The bit numbers are listed in the OpenType OS/2 specification.
        # Corresponds to the OpenType OS/2 table fsType field.
        Field("openTypeOS2Type", [3, 8]),
        # openTypeOS2SubscriptXSize	integer	Subscript horizontal font size.
        # Corresponds to the OpenType OS/2 table ySubscriptXSize field.
        Field("openTypeOS2SubscriptXSize", 123),
        # openTypeOS2SubscriptYSize	integer	Subscript vertical font size.
        # Corresponds to the OpenType OS/2 table ySubscriptYSize field.
        Field("openTypeOS2SubscriptYSize", 246),
        # openTypeOS2SubscriptXOffset	integer	Subscript x offset.
        # Corresponds to the OpenType OS/2 table ySubscriptXOffset field.
        Field("openTypeOS2SubscriptXOffset", -6),
        # openTypeOS2SubscriptYOffset	integer	Subscript y offset.
        # Corresponds to the OpenType OS/2 table ySubscriptYOffset field.
        Field("openTypeOS2SubscriptYOffset", 100),
        # openTypeOS2SuperscriptXSize integer Superscript horizontal font size.
        # Corresponds to the OpenType OS/2 table ySuperscriptXSize field.
        Field("openTypeOS2SuperscriptXSize", 124),
        # openTypeOS2SuperscriptYSize integer Superscript vertical font size.
        # Corresponds to the OpenType OS/2 table ySuperscriptYSize field.
        Field("openTypeOS2SuperscriptYSize", 248),
        # openTypeOS2SuperscriptXOffset	integer	Superscript x offset.
        # Corresponds to the OpenType OS/2 table ySuperscriptXOffset field.
        Field("openTypeOS2SuperscriptXOffset", -8),
        # openTypeOS2SuperscriptYOffset	integer	Superscript y offset.
        # Corresponds to the OpenType OS/2 table ySuperscriptYOffset field.
        Field("openTypeOS2SuperscriptYOffset", 400),
        # openTypeOS2StrikeoutSize	integer	Strikeout size.
        # Corresponds to the OpenType OS/2 table yStrikeoutSize field.
        Field("openTypeOS2StrikeoutSize", 56),
        # openTypeOS2StrikeoutPosition	integer	Strikeout position.
        # Corresponds to the OpenType OS/2 table yStrikeoutPosition field.
        Field("openTypeOS2StrikeoutPosition", 200),
    ),
    section(
        "OpenType vhea Table Fields",
        # openTypeVheaVertTypoAscender integer Ascender value. Corresponds to
        # the OpenType vhea table vertTypoAscender field.
        Field("openTypeVheaVertTypoAscender", 123),
        # openTypeVheaVertTypoDescender integer Descender value. Corresponds to
        # the OpenType vhea table vertTypoDescender field.
        Field("openTypeVheaVertTypoDescender", 456),
        # openTypeVheaVertTypoLineGap integer Line gap value. Corresponds to
        # the OpenType vhea table vertTypoLineGap field.
        Field("openTypeVheaVertTypoLineGap", 789),
        # openTypeVheaCaretSlopeRise integer Caret slope rise value.
        # Corresponds to the OpenType vhea table caretSlopeRise field.
        Field("openTypeVheaCaretSlopeRise", 23),
        # openTypeVheaCaretSlopeRun integer Caret slope run value. Corresponds
        # to the OpenType vhea table caretSlopeRun field.
        Field("openTypeVheaCaretSlopeRun", 1024),
        # openTypeVheaCaretOffset integer Caret offset value. Corresponds to
        # the OpenType vhea table caretOffset field.
        Field("openTypeVheaCaretOffset", 50),
    ),
    section(
        "PostScript Specific Data",
        # postscriptFontName string Name to be used for the FontName field in
        # Type 1/CFF table.
        Field("postscriptFontName", "Exemplary-Sans"),
        # postscriptFullName string Name to be used for the FullName field in
        # Type 1/CFF table.
        Field("postscriptFullName", "Exemplary Sans Bold Whatever"),
        # postscriptSlantAngle integer or float Artificial slant angle. This
        # must be an angle in counter-clockwise degrees from the vertical.
        Field("postscriptSlantAngle", -15.5),
        # postscriptUniqueID integer A unique ID number as defined in the Type
        # 1/CFF specification.
        Field("postscriptUniqueID", 123456789),
        # postscriptUnderlineThickness integer or float Underline thickness
        # value. Corresponds to the Type 1/CFF/post table UnderlineThickness
        # field.
        Field("postscriptUnderlineThickness", 70),
        # postscriptUnderlinePosition integer or float Underline position
        # value. Corresponds to the Type 1/CFF/post table UnderlinePosition
        # field.
        Field("postscriptUnderlinePosition", -50),
        # postscriptIsFixedPitch boolean Indicates if the font is monospaced.
        # An authoring tool could calculate this automatically, but the
        # designer may wish to override this setting. This corresponds to the
        # Type 1/CFF isFixedPitched field
        Field("postscriptIsFixedPitch", True),
        # postscriptBlueValues list A list of up to 14 integers or floats
        # specifying the values that should be in the Type 1/CFF BlueValues
        # field. This list must contain an even number of integers following
        # the rules defined in the Type 1/CFF specification.
        Field("postscriptBlueValues", [-200, -185, -15, 0, 500, 515]),
        # postscriptOtherBlues list A list of up to 10 integers or floats
        # specifying the values that should be in the Type 1/CFF OtherBlues
        # field. This list must contain an even number of integers following
        # the rules defined in the Type 1/CFF specification.
        Field("postscriptOtherBlues", [-315, -300, 385, 400]),
        # postscriptFamilyBlues list A list of up to 14 integers or floats
        # specifying the values that should be in the Type 1/CFF FamilyBlues
        # field. This list must contain an even number of integers following
        # the rules defined in the Type 1/CFF specification.
        Field("postscriptFamilyBlues", [-210, -195, -25, 0, 510, 525]),
        # postscriptFamilyOtherBlues list A list of up to 10 integers or floats
        # specifying the values that should be in the Type 1/CFF
        # FamilyOtherBlues field. This list must contain an even number of
        # integers following the rules defined in the Type 1/CFF specification.
        Field("postscriptFamilyOtherBlues", [-335, -330, 365, 480]),
        # postscriptStemSnapH list List of horizontal stems sorted in the order
        # specified in the Type 1/CFF specification. Up to 12 integers or
        # floats are possible. This corresponds to the Type 1/CFF StemSnapH
        # field.
        Field("postscriptStemSnapH", [-10, 40, 400, 789]),
        # postscriptStemSnapV list List of vertical stems sorted in the order
        # specified in the Type 1/CFF specification. Up to 12 integers or
        # floats are possible. This corresponds to the Type 1/CFF StemSnapV
        # field.
        Field("postscriptStemSnapV", [-500, -40, 0, 390, 789]),
        # postscriptBlueFuzz integer or float BlueFuzz value. This corresponds
        # to the Type 1/CFF BlueFuzz field.
        Field("postscriptBlueFuzz", 2),
        # postscriptBlueShift integer or float BlueShift value. This
        # corresponds to the Type 1/CFF BlueShift field.
        Field("postscriptBlueShift", 10),
        # postscriptBlueScale float BlueScale value. This corresponds to the
        # Type 1/CFF BlueScale field.
        Field("postscriptBlueScale", 0.0256),
        # postscriptForceBold boolean Indicates how the Type 1/CFF ForceBold
        # field should be set.
        Field("postscriptForceBold", True),
        # postscriptDefaultWidthX integer or float Default width for glyphs.
        Field("postscriptDefaultWidthX", 250),
        # postscriptNominalWidthX integer or float Nominal width for glyphs.
        Field("postscriptNominalWidthX", 10),
        # postscriptWeightName string A string indicating the overall weight of
        # the font. This corresponds to the Type 1/CFF Weight field. It should
        # be in sync with the openTypeOS2WeightClass value.
        Field("postscriptWeightName", "Bold"),
        # postscriptDefaultCharacter string The name of the glyph that should
        # be used as the default character in PFM files.
        Field("postscriptDefaultCharacter", "a"),
        # postscriptWindowsCharacterSet integer The Windows character set. The
        # values are defined below.
        Field("postscriptWindowsCharacterSet", 4),
    ),
    section(
        "Macintosh FOND Resource Data",
        # macintoshFONDFamilyID integer Family ID number. Corresponds to the
        # ffFamID in the FOND resource.
        Field("macintoshFONDFamilyID", 12345),
        # macintoshFONDName string Font name for the FOND resource.
        Field("macintoshFONDName", "ExemplarySansBold"),
    ),
    skip_section(
        "WOFF Data",
        # woffMajorVersion	non-negative integer	Major version of the font.
        Field("woffMajorVersion", 1),
        # woffMinorVersion	non-negative integer	Minor version of the font.
        Field("woffMinorVersion", 12),
        # woffMetadataUniqueID dictionary Identification string. Corresponds to
        # the WOFF uniqueid. The dictionary must follow the WOFF Metadata
        # Unique ID Record structure.
        Field("woffMetadataUniqueID", {}),
        # woffMetadataVendor dictionary Font vendor. Corresponds to the WOFF
        # vendor element. The dictionary must follow the the WOFF Metadata
        # Vendor Record structure.
        Field("woffMetadataVendor", {}),
        # woffMetadataCredits dictionary Font credits. Corresponds to the WOFF
        # credits element. The dictionary must follow the WOFF Metadata Credits
        # Record structure.
        Field("woffMetadataCredits", {}),
        # woffMetadataDescription dictionary Font description. Corresponds to
        # the WOFF description element. The dictionary must follow the WOFF
        # Metadata Description Record structure.
        Field("woffMetadataDescription", {}),
        # woffMetadataLicense dictionary Font description. Corresponds to the
        # WOFF license element. The dictionary must follow the WOFF Metadata
        # License Record structure.
        Field("woffMetadataLicense", {}),
        # woffMetadataCopyright dictionary Font copyright. Corresponds to the
        # WOFF copyright element. The dictionary must follow the WOFF Metadata
        # Copyright Record structure.
        Field("woffMetadataCopyright", {}),
        # woffMetadataTrademark dictionary Font trademark. Corresponds to the
        # WOFF trademark element. The dictionary must follow the WOFF Metadata
        # Trademark Record structure.
        Field("woffMetadataTrademark", {}),
        # woffMetadataLicensee dictionary Font licensee. Corresponds to the
        # WOFF licensee element. The dictionary must follow the WOFF Metadata
        # Licensee Record structure.
        Field("woffMetadataLicensee", {}),
        # woffMetadataExtensions list List of metadata extension records. The
        # dictionaries must follow the WOFF Metadata Extension Record
        # structure. There must be at least one extension record in the list.
        Field("woffMetadataExtensions", {}),
    ),
]


@pytest.mark.parametrize("fields", ufo_info_spec)
def test_info(fields, tmpdir):
    ufo = defcon.Font()

    for field in fields:
        setattr(ufo.info, field.name, field.test_value)

    font = to_glyphs([ufo], minimize_ufo_diffs=True)
    filename = os.path.join(str(tmpdir), "font.glyphs")
    font.save(filename)
    font = classes.GSFont(filename)
    ufo, = to_ufos(font)

    for field in fields:
        assert getattr(ufo.info, field.name) == field.test_value
