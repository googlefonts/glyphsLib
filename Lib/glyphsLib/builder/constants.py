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
import re


PUBLIC_PREFIX = "public."
GLYPH_ORDER_KEY = PUBLIC_PREFIX + "glyphOrder"
OBJECT_LIBS_KEY = PUBLIC_PREFIX + "objectLibs"

POSTSCRIPT_NAMES_KEY = PUBLIC_PREFIX + "postscriptNames"

GLYPHS_PREFIX = "com.schriftgestaltung."
GLYPHLIB_PREFIX = GLYPHS_PREFIX + "Glyphs."
ROBOFONT_PREFIX = "com.typemytype.robofont."
UFO2F_PREFIX = "com.github.googlei18n.ufo2ft."
UFO2FT_FILTERS_KEY = UFO2F_PREFIX + "filters"
UFO2FT_USE_PROD_NAMES_KEY = UFO2F_PREFIX + "useProductionNames"
UFO2FT_FEATURE_WRITERS_KEY = UFO2F_PREFIX + "featureWriters"
UFO2FT_COLOR_PALETTES_KEY = UFO2F_PREFIX + "colorPalettes"
UFO2FT_COLOR_LAYER_MAPPING_KEY = UFO2F_PREFIX + "colorLayerMapping"
UFO2FT_COLOR_LAYERS_KEY = UFO2F_PREFIX + "colorLayers"

ANNOTATIONS_LIB_KEY = GLYPHS_PREFIX + "annotations"
COMPONENT_INFO_KEY = GLYPHLIB_PREFIX + "ComponentInfo"
UFO_FILENAME_CUSTOM_PARAM = "UFO Filename"

BACKGROUND_IMAGE_PREFIX = GLYPHS_PREFIX + "backgroundImage."
CROP_KEY = BACKGROUND_IMAGE_PREFIX + "crop"
LOCKED_KEY = BACKGROUND_IMAGE_PREFIX + "locked"
ALPHA_KEY = BACKGROUND_IMAGE_PREFIX + "alpha"

BRACKET_GLYPH_TEMPLATE = "{glyph_name}.BRACKET.{description}"
BRACKET_GLYPH_RE = re.compile(r"(?P<glyph_name>.+)\.BRACKET.(?P<box>.*)$")
BRACKET_GLYPH_SUFFIX_RE = re.compile(r".*(\.BRACKET\..*)$")

# legacy. Should use GLYPHS_PREFIX.fontMaster.customParameters > list of parameters
MASTER_CUSTOM_PARAM_PREFIX = GLYPHS_PREFIX + "customParameter.GSFontMaster."
# legacy. Should use GLYPHS_PREFIX.font.customParameters > list of parameters
FONT_CUSTOM_PARAM_PREFIX = GLYPHS_PREFIX + "customParameter.GSFont."

ANONYMOUS_FEATURE_PREFIX_NAME = "<anonymous>"
ORIGINAL_FEATURE_CODE_KEY = GLYPHLIB_PREFIX + "originalFeatureCode"
ORIGINAL_CATEGORY_KEY = GLYPHLIB_PREFIX + "originalOpenTypeCategory"

INSERT_FEATURE_MARKER_RE = r"\s*# Automatic Code.*"
INSERT_FEATURE_MARKER_COMMENT = "# Automatic Code\n"

APP_VERSION_LIB_KEY = GLYPHS_PREFIX + "appVersion"
FORMATVERSION_LIB_KEY = GLYPHS_PREFIX + "formatVersion"
KEYBOARD_INCREMENT_KEY = GLYPHS_PREFIX + "keyboardIncrement"
KEYBOARD_INCREMENT_BIG_KEY = GLYPHS_PREFIX + "keyboardIncrementBig"
KEYBOARD_INCREMENT_HUGE_KEY = GLYPHS_PREFIX + "keyboardIncrementHuge"
GRID_SIZE_KEY = GLYPHS_PREFIX + "gridSize"
GRID_SUBDIVISION_KEY = GLYPHS_PREFIX + "gridSubDivision"
MASTER_ORDER_LIB_KEY = GLYPHS_PREFIX + "fontMasterOrder"

SCRIPT_LIB_KEY = GLYPHLIB_PREFIX + "script"
ORIGINAL_WIDTH_KEY = GLYPHLIB_PREFIX + "originalWidth"
BACKGROUND_WIDTH_KEY = GLYPHLIB_PREFIX + "backgroundWidth"

UFO_ORIGINAL_KERNING_GROUPS_KEY = GLYPHLIB_PREFIX + "originalKerningGroups"
UFO_GROUPS_NOT_IN_FEATURE_KEY = GLYPHLIB_PREFIX + "groupsNotInFeature"
UFO_KERN_GROUP_PATTERN = re.compile("^public\\.kern([12])\\.(.*)$")

LOCKED_GUIDE_NAME_SUFFIX = " [locked]"

HINTS_LIB_KEY = GLYPHS_PREFIX + "hints"
SHAPE_ORDER_LIB_KEY = GLYPHLIB_PREFIX + "shapeOrder"

SMART_COMPONENT_AXES_LIB_KEY = GLYPHS_PREFIX + "smartComponentAxes"

EXPORT_KEY = GLYPHS_PREFIX + "export"
WIDTH_KEY = GLYPHS_PREFIX + "widthClass"
WEIGHT_KEY = GLYPHS_PREFIX + "weightClass"
FULL_FILENAME_KEY = GLYPHLIB_PREFIX + "fullFilename"
MANUAL_INTERPOLATION_KEY = GLYPHS_PREFIX + "manualInterpolation"
# Following typo kept for backwards compatibility
INSTANCE_INTERPOLATIONS_KEY = GLYPHS_PREFIX + "instanceInterpolations"

CUSTOM_PARAMETERS_BLACKLIST = [
    # These are stored in the official descriptor attributes.
    "familyNames",
    "postscriptFontName",
    "fileName",
    # These can be recovered by reading the mapping backward.
    "weightClass",
    "widthClass",
    # These are artificial.
    FULL_FILENAME_KEY,
    UFO_FILENAME_CUSTOM_PARAM,
    "uniqueID",
    "styleMapFamilyNames",
    "styleMapStyleNames",
    "Use Typo Metrics",
]

# Reference:
# https://github.com/googlefonts/glyphsLib/pull/881#issuecomment-1474226616
PROPERTIES_KEY = GLYPHS_PREFIX + "properties"

LAYER_ID_KEY = GLYPHS_PREFIX + "layerId"
LAYER_ORDER_PREFIX = GLYPHS_PREFIX + "layerOrderInGlyph."
LAYER_ORDER_TEMP_USER_DATA_KEY = "__layerOrder"

MASTER_ID_LIB_KEY = GLYPHS_PREFIX + "fontMasterID"
UFO_FILENAME_KEY = GLYPHLIB_PREFIX + "ufoFilename"
UFO_YEAR_KEY = GLYPHLIB_PREFIX + "ufoYear"
UFO_NOTE_KEY = GLYPHLIB_PREFIX + "ufoNote"

UFO_DATA_KEY = GLYPHLIB_PREFIX + "ufoData"
FONT_USER_DATA_KEY = GLYPHLIB_PREFIX + "font.userData"
LAYER_LIB_KEY = GLYPHLIB_PREFIX + "layerLib"
LAYER_NAME_KEY = GLYPHLIB_PREFIX + "layerName"
GLYPH_USER_DATA_KEY = GLYPHLIB_PREFIX + "glyphUserData"
NODE_USER_DATA_KEY = GLYPHLIB_PREFIX + "nodeUserData"


GLYPHS_COLORS = (
    "0.85,0.26,0.06,1",  # red
    "0.99,0.62,0.11,1",  # orange
    "0.65,0.48,0.2,1",  # brown
    "0.97,0.9,0,1",  # yellow
    "0.67,0.95,0.38,1",  # green
    "0.04,0.57,0.04,1",  # dark green
    "0.06,0.6,0.98,1",  # cyan
    "0,0.2,0.88,1",  # blue
    "0.5,0.09,0.79,1",  # violet
    "0.98,0.36,0.67,1",  # pink
    "0.75,0.75,0.75,1",
    "0.25,0.25,0.25,1",
)

# https://www.microsoft.com/typography/otspec/os2.htm#cpr
CODEPAGE_RANGES = {
    "1252": 0,
    "1250": 1,
    "1251": 2,
    "1253": 3,
    "1254": 4,
    "1255": 5,
    "1256": 6,
    "1257": 7,
    "1258": 8,
    # 9-15: Reserved for Alternate ANSI
    "bit 9": 9,
    "bit 10": 10,
    "bit 11": 11,
    "bit 12": 12,
    "bit 13": 13,
    "bit 14": 14,
    "bit 15": 15,
    "874": 16,
    "932": 17,
    "936": 18,
    "949": 19,
    "950": 20,
    "1361": 21,
    # 22-28: Reserved for Alternate ANSI and OEM
    "bit 22": 22,
    "bit 23": 23,
    "bit 24": 24,
    "bit 25": 25,
    "bit 26": 26,
    "bit 27": 27,
    "bit 28": 28,
    # 29: Macintosh Character Set (US Roman)
    "bit 29": 29,
    # 30: OEM Character Set
    "bit 30": 30,
    # 31: Symbol Character Set
    "bit 31": 31,
    # 32-47: Reserved for OEM
    "bit 32": 32,
    "bit 33": 33,
    "bit 34": 34,
    "bit 35": 35,
    "bit 36": 36,
    "bit 37": 37,
    "bit 38": 38,
    "bit 39": 39,
    "bit 40": 40,
    "bit 41": 41,
    "bit 42": 42,
    "bit 43": 43,
    "bit 44": 44,
    "bit 45": 45,
    "bit 46": 46,
    "bit 47": 47,
    "869": 48,
    "866": 49,
    "865": 50,
    "864": 51,
    "863": 52,
    "862": 53,
    "861": 54,
    "860": 55,
    "857": 56,
    "855": 57,
    "852": 58,
    "775": 59,
    "737": 60,
    "708": 61,
    "850": 62,
    "437": 63,
}

REVERSE_CODEPAGE_RANGES = {value: key for key, value in CODEPAGE_RANGES.items()}

UFO2FT_META_TABLE_KEY = PUBLIC_PREFIX + "openTypeMeta"

DEFAULT_FEATURE_WRITERS = [
    {"class": "CursFeatureWriter"},
    {"class": "KernFeatureWriter"},
    {"class": "MarkFeatureWriter"},
    {"class": "GdefFeatureWriter"},
]

DEFAULT_LAYER_NAME = PUBLIC_PREFIX + "default"

# From the spec:
# https://docs.microsoft.com/en-gb/typography/opentype/spec/os2#uswidthclass
WIDTH_CLASS_TO_VALUE = {
    1: 50,  # Ultra-condensed
    2: 62.5,  # Extra-condensed
    3: 75,  # Condensed
    4: 87.5,  # Semi-condensed
    5: 100,  # Medium
    6: 112.5,  # Semi-expanded
    7: 125,  # Expanded
    8: 150,  # Extra-expanded
    9: 200,  # Ultra-expanded
}

LANGUAGE_MAPPING = {
    "dflt": None,
    "AFK": 0x0436,
    "ARA": 0x0C01,
    "ASM": 0x044D,
    "AZE": 0x042C,
    "BEL": 0x0423,
    "BEN": 0x0845,
    "BGR": 0x0402,
    "BRE": 0x047E,
    "CAT": 0x0403,
    "CSY": 0x0405,
    "DAN": 0x0406,
    "DEU": 0x0407,
    "ELL": 0x0408,
    "ENG": 0x0409,
    "ESP": 0x0C0A,
    "ETI": 0x0425,
    "EUQ": 0x042D,
    "FIN": 0x040B,
    "FLE": 0x0813,
    "FOS": 0x0438,
    "FRA": 0x040C,
    "FRI": 0x0462,
    "GRN": 0x046F,
    "GUJ": 0x0447,
    "HAU": 0x0468,
    "HIN": 0x0439,
    "HRV": 0x041A,
    "HUN": 0x040E,
    "HVE": 0x042B,
    "IRI": 0x083C,
    "ISL": 0x040F,
    "ITA": 0x0410,
    "IWR": 0x040D,
    "JPN": 0x0411,
    "KAN": 0x044B,
    "KAT": 0x0437,
    "KAZ": 0x043F,
    "KHM": 0x0453,
    "KOK": 0x0457,
    "LAO": 0x0454,
    "LSB": 0x082E,
    "LTH": 0x0427,
    "LVI": 0x0426,
    "MAR": 0x044E,
    "MKD": 0x042F,
    "MLR": 0x044C,
    "MLY": 0x043E,
    "MNG": 0x0352,
    "MTS": 0x043A,
    "NEP": 0x0461,
    "NLD": 0x0413,
    "NOB": 0x0414,
    "ORI": 0x0448,
    "PAN": 0x0446,
    "PAS": 0x0463,
    "PLK": 0x0415,
    "PTG": 0x0816,
    "PTG-BR": 0x0416,
    "RMS": 0x0417,
    "ROM": 0x0418,
    "RUS": 0x0419,
    "SAN": 0x044F,
    "SKY": 0x041B,
    "SLV": 0x0424,
    "SQI": 0x041C,
    "SRB": 0x081A,
    "SVE": 0x041D,
    "TAM": 0x0449,
    "TAT": 0x0444,
    "TEL": 0x044A,
    "THA": 0x041E,
    "TIB": 0x0451,
    "TRK": 0x041F,
    "UKR": 0x0422,
    "URD": 0x0420,
    "USB": 0x042E,
    "UYG": 0x0480,
    "UZB": 0x0443,
    "VIT": 0x042A,
    "WEL": 0x0452,
    "ZHH": 0x0C04,
    "ZHS": 0x0804,
    "ZHT": 0x0404,
}

GLYPHS_PROPERTIES_2_UFO_FIELDS = {
    "compatibleFullNames": "openTypeNameCompatibleFullName",
    "copyrights": "copyright",
    "descriptions": "openTypeNameDescription",
    "designers": "openTypeNameDesigner",
    "designerURL": "openTypeNameDesignerURL",
    # "familyNames": "familyName",
    "preferredFamilyNames": "openTypeNamePreferredFamilyName",
    "preferredSubfamilyNames": "openTypeNamePreferredSubfamilyName",
    "licenses": "openTypeNameLicense",
    "licenseURL": "openTypeNameLicenseURL",
    "manufacturers": "openTypeNameManufacturer",
    "manufacturerURL": "openTypeNameManufacturerURL",
    "postscriptFontName": "postscriptFontName",
    "postscriptFullNames": "postscriptFullName",
    "sampleTexts": "openTypeNameSampleText",
    "styleMapFamilyNames": "styleMapFamilyName",
    "styleMapStyleNames": "styleMapStyleName",
    "trademarks": "trademark",
    "uniqueID": "openTypeNameUniqueID",
    # "variationsPostScriptNamePrefix": "variationsPostScriptNamePrefix", # TODO: what is the correct ufo key?
    "vendorID": "openTypeOS2VendorID",
    "versionString": "openTypeNameVersion",
    "WWSFamilyName": "openTypeNameWWSFamilyName",
    "WWSSubfamilyName": "openTypeNameWWSSubfamilyName",
}

GLYPHS_NAME_MAPPING = {
    "copyrights": 0,
    "styleMapFamilyNames": 1,
    "styleMapStyleNames": 2,
    "uniqueID": 3,
    "postscriptFullNames": 4,
    "versionString": 5,
    "postscriptFontName": 6,
    "trademarks": 7,
    "manufacturers": 8,
    "designers": 9,
    "descriptions": 10,
    "manufacturerURL": 11,
    "designerURL": 12,
    "licenses": 13,
    "licenseURL": 14,
    "preferredFamilyNames": 16,
    "preferredSubfamilyNames": 17,
    "compatibleFullNames": 18,
    "sampleTexts": 19,
    "WWSFamilyName": 21,
    "WWSSubfamilyName": 22,
}

REVERSE_GLYPHS_NAME_MAPPING = {v: k for k, v in GLYPHS_NAME_MAPPING.items()}

UFO_NAME_MAPPING = {}
for glyphs_name, name_id in GLYPHS_NAME_MAPPING.items():
    ufo_name = GLYPHS_PROPERTIES_2_UFO_FIELDS[glyphs_name]
    UFO_NAME_MAPPING[ufo_name] = name_id


REVERSE_LANGUAGE_MAPPING = {v: k for k, v in LANGUAGE_MAPPING.items()}

GLYPHS_MATH_PREFIX = "com.nagwa.MATHPlugin."
GLYPHS_MATH_CONSTANTS_KEY = GLYPHS_MATH_PREFIX + "constants"
GLYPHS_MATH_VARIANTS_KEY = GLYPHS_MATH_PREFIX + "variants"
GLYPHS_MATH_EXTENDED_SHAPE_KEY = GLYPHS_MATH_PREFIX + "extendedShape"
