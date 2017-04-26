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

from fontTools.misc.py23 import round, unicode

import logging
import re

from glyphsLib.anchors import propagate_font_anchors
from glyphsLib.util import clear_data, cast_to_number_or_bool
import glyphsLib.glyphdata

__all__ = [
    'to_ufos', 'set_redundant_data', 'set_custom_params',
    'GLYPHS_PREFIX'
]

logger = logging.getLogger(__name__)


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

WEIGHT_CODES = {
    'Thin': 250,
    'Light': 300,
    'SemiLight': 350,
    'DemiLight': 350,
    '': 400,
    'Regular': 400,
    'Medium': 500,
    'DemiBold': 600,
    'SemiBold': 600,
    'Bold': 700,
    'ExtraBold': 800,
    'Extra Bold': 800,
    'Black': 900}

WIDTH_CODES = {
    'Extra Condensed': 2,
    'Cd': 3,
    'Cond': 3,
    'Condensed': 3,
    'Narrow': 4,
    'SemiCondensed': 4,
    '': 5}


def to_ufos(data, include_instances=False, family_name=None, debug=False):
    """Take .glyphs file data and load it into UFOs.

    Takes in data as a dictionary structured according to
    https://github.com/schriftgestalt/GlyphsSDK/blob/master/GlyphsFileFormat.md
    and returns a list of UFOs, one per master.

    If debug is True, returns unused input data instead of the resulting UFOs.
    """

    # check that source was generated with at least stable version 2.3
    # https://github.com/googlei18n/glyphsLib/pull/65#issuecomment-237158140
    if data.pop('.appVersion', 0) < 895:
        logger.warn('This Glyphs source was generated with an outdated version '
                    'of Glyphs. The resulting UFOs may be incorrect.')

    source_family_name = data.pop('familyName')
    if family_name is None:
        family_name = source_family_name

    feature_prefixes, classes, features = [], [], []
    for f in data.get('featurePrefixes', []):
        feature_prefixes.append((f.pop('name'), f.pop('code'),
                                 f.pop('automatic', None)))
    for c in data.get('classes', []):
        classes.append((c.pop('name'), c.pop('code'), c.pop('automatic', None)))
    for f in data.get('features', []):
        features.append((f.pop('name'), f.pop('code'), f.pop('automatic', None),
                         f.pop('disabled', None), f.pop('notes', None)))
    kerning_groups = {}

    # stores background data from "associated layers"
    supplementary_bg_data = []

    #TODO(jamesgk) maybe create one font at a time to reduce memory usage
    ufos, master_id_order = generate_base_fonts(data, family_name)

    # get the 'glyphOrder' custom parameter as stored in the lib.plist.
    # We assume it's the same for all ufos.
    first_ufo = ufos[master_id_order[0]]
    glyphOrder_key = PUBLIC_PREFIX + 'glyphOrder'
    if glyphOrder_key in first_ufo.lib:
        glyph_order = first_ufo.lib[glyphOrder_key]
    else:
        glyph_order = []
    sorted_glyphset = set(glyph_order)

    for glyph in data['glyphs']:
        add_glyph_to_groups(kerning_groups, glyph)

        glyph_name = glyph.pop('glyphname')
        if glyph_name not in sorted_glyphset:
            # glyphs not listed in the 'glyphOrder' custom parameter but still
            # in the font are appended after the listed glyphs, in the order
            # in which they appear in the source file
            glyph_order.append(glyph_name)

        # pop glyph metadata only once, i.e. not when looping through layers
        metadata_keys = ['unicode', 'color', 'export', 'lastChange',
                         'leftMetricsKey', 'note', 'production',
                         'rightMetricsKey', 'widthMetricsKey',
                         'category', 'subCategory']
        glyph_data = {k: glyph.pop(k) for k in metadata_keys if k in glyph}

        for layer in glyph['layers']:
            layer_id = layer.pop('layerId')
            layer_name = layer.pop('name', None)

            assoc_id = layer.pop('associatedMasterId', None)
            if assoc_id is not None:
                if layer_name is not None:
                    supplementary_bg_data.append(
                        (assoc_id, glyph_name, layer_name, layer))
                continue

            ufo = ufos[layer_id]
            glyph = ufo.newGlyph(glyph_name)
            load_glyph(glyph, layer, glyph_data)

    for layer_id, glyph_name, bg_name, bg_data in supplementary_bg_data:
        glyph = ufos[layer_id][glyph_name]
        set_robofont_glyph_background(glyph, bg_name, bg_data)

    for ufo in ufos.values():
        ufo.lib[glyphOrder_key] = glyph_order
        propagate_font_anchors(ufo)
        add_features_to_ufo(ufo, feature_prefixes, classes, features)
        add_groups_to_ufo(ufo, kerning_groups)

    for master_id, kerning in data.pop('kerning', {}).items():
        load_kerning(ufos[master_id], kerning)

    result = [ufos[master_id] for master_id in master_id_order]
    instances = {'defaultFamilyName': source_family_name,
                 'data': data.pop('instances', [])}
    for key in ("Variation Font Origin",):
        value = data.get(key)
        if value:
            instances[key] = value
    if debug:
        return clear_data(data)
    elif include_instances:
        return result, instances
    return result


def generate_base_fonts(data, family_name):
    """Generate a list of UFOs with metadata loaded from .glyphs data."""
    from defcon import Font

    # "date" can be missing; Glyphs.app removes it on saving if it's empty:
    # https://github.com/googlei18n/glyphsLib/issues/134
    date_created = data.pop('date', None)
    if date_created is not None:
        date_created = to_ufo_time(date_created)
    units_per_em = data.pop('unitsPerEm')
    version_major = data.pop('versionMajor')
    version_minor = data.pop('versionMinor')
    user_data = data.pop('userData', {})
    copyright = data.pop('copyright', None)
    designer = data.pop('designer', None)
    designer_url = data.pop('designerURL', None)
    manufacturer = data.pop('manufacturer', None)
    manufacturer_url = data.pop('manufacturerURL', None)

    misc = ['DisplayStrings', 'disablesAutomaticAlignment', 'disablesNiceNames']
    custom_params = parse_custom_params(data, misc)

    ufos = {}
    master_id_order = []
    for master in data['fontMaster']:
        ufo = Font()

        if date_created is not None:
            ufo.info.openTypeHeadCreated = date_created
        ufo.info.unitsPerEm = units_per_em
        ufo.info.versionMajor = version_major
        ufo.info.versionMinor = version_minor

        if copyright:
            ufo.info.copyright = copyright
        if designer:
            ufo.info.openTypeNameDesigner = designer
        if designer_url:
            ufo.info.openTypeNameDesignerURL = designer_url
        if manufacturer:
            ufo.info.openTypeNameManufacturer = manufacturer
        if manufacturer_url:
            ufo.info.openTypeNameManufacturerURL = manufacturer_url

        ufo.info.ascender = master.pop('ascender')
        ufo.info.capHeight = master.pop('capHeight')
        ufo.info.descender = master.pop('descender')
        ufo.info.xHeight = master.pop('xHeight')

        horizontal_stems = master.pop('horizontalStems', None)
        vertical_stems = master.pop('verticalStems', None)
        italic_angle = -master.pop('italicAngle', 0)
        if horizontal_stems:
            ufo.info.postscriptStemSnapH = horizontal_stems
        if vertical_stems:
            ufo.info.postscriptStemSnapV = vertical_stems
        if italic_angle:
            ufo.info.italicAngle = italic_angle

        ufo.info.familyName = family_name
        ufo.info.styleName = build_style_name(
            master, 'width', 'weight', 'custom', italic_angle != 0)

        set_redundant_data(ufo)
        set_blue_values(ufo, master.pop('alignmentZones', []))
        set_family_user_data(ufo, user_data)
        set_master_user_data(ufo, master.pop('userData', {}))
        set_robofont_guidelines(ufo, master, is_global=True)

        set_custom_params(ufo, parsed=custom_params)
        # the misc attributes double as deprecated info attributes!
        # they are Glyphs-related, not OpenType-related, and don't go in info
        misc = ('customValue', 'weightValue', 'widthValue')
        set_custom_params(ufo, data=master, misc_keys=misc, non_info=misc)

        set_default_params(ufo)

        master_id = master.pop('id')
        ufo.lib[GLYPHS_PREFIX + 'fontMasterID'] = master_id
        master_id_order.append(master_id)
        ufos[master_id] = ufo

    return ufos, master_id_order


def set_redundant_data(ufo):
    """Set redundant metadata in a UFO, e.g. data based on other data."""

    family_name, style_name = ufo.info.familyName, ufo.info.styleName

    width, weight = parse_style_attrs(style_name)
    if ufo.info.openTypeOS2WidthClass is None:
        ufo.info.openTypeOS2WidthClass = WIDTH_CODES[width]
    if ufo.info.openTypeOS2WeightClass is None:
        ufo.info.openTypeOS2WeightClass = WEIGHT_CODES[weight]

    if weight and weight != 'Regular':
        ufo.lib[GLYPHS_PREFIX + 'weight'] = weight
    if width:
        ufo.lib[GLYPHS_PREFIX + 'width'] = width

    if style_name.lower() in ['regular', 'bold', 'italic', 'bold italic']:
        ufo.info.styleMapStyleName = style_name.lower()
        ufo.info.styleMapFamilyName = family_name
    else:
        ufo.info.styleMapStyleName = ' '.join(s for s in (
            'bold' if weight == 'Bold' else '',
            'italic' if 'Italic' in style_name else '') if s) or 'regular'
        ufo.info.styleMapFamilyName = ' '.join(
            [family_name] +
            style_name.replace('Bold', '').replace('Italic', '').split())
    ufo.info.openTypeNamePreferredFamilyName = family_name
    ufo.info.openTypeNamePreferredSubfamilyName = style_name


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
            value = int(not value)

        opentype_attr_prefix_pairs = (
            ('hhea', 'Hhea'), ('description', 'NameDescription'),
            ('license', 'NameLicense'), ('panose', 'OS2Panose'),
            ('typo', 'OS2Typo'), ('unicodeRanges', 'OS2UnicodeRanges'),
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

        # The value of these could be a float, and ufoLib/defcon expect an int.
        if name in ('openTypeOS2WeightClass', 'openTypeOS2WidthClass'):
            value = int(value)

        if name == 'glyphOrder':
            # store the public.glyphOrder in lib.plist
            ufo.lib[PUBLIC_PREFIX + name] = value
        elif name == 'Filter':
            filter_struct = parse_glyphs_filter(value)
            if not filter_struct:
                continue
            if UFO2FT_FILTERS_KEY not in ufo.lib.keys():
                ufo.lib[UFO2FT_FILTERS_KEY] = []
            ufo.lib[UFO2FT_FILTERS_KEY].append(filter_struct)
        elif hasattr(ufo.info, name) and name not in non_info:
            # most OpenType table entries go in the info object
            setattr(ufo.info, name, value)
        else:
            # everything else gets dumped in the lib
            ufo.lib[GLYPHS_PREFIX + name] = value


def parse_glyphs_filter(filter_str):
    """Parses glyphs custom filter string into a dict object that
       ufo2ft can consume.

        Reference:
            ufo2ft: https://github.com/googlei18n/ufo2ft
            Glyphs 2.3 Handbook July 2016, p184

        Args:
            filter_str - a string of glyphs app filter

        Return:
            A dictionary contains the structured filter.
            Return None if parse failed.
    """
    elements = filter_str.split(';')

    if elements[0] == '':
        logger.error('Failed to parse glyphs filter, expecting a filter name: \
             %s', filter_str)
        return None

    result = {}
    result['name'] = elements[0]
    for idx, elem in enumerate(elements[1:]):
        if not elem:
            # skip empty arguments
            continue
        if ':' in elem:
            # Key value pair
            key, value = elem.split(':', 1)
            if key.lower() in ['include', 'exclude']:
                if idx != len(elements[1:]) - 1:
                    logger.error('{} can only present as the last argument in the filter. {} is ignored.'.format(key, elem))
                    continue
                result[key.lower()] = re.split('[ ,]+', value)
            else:
                if 'kwargs' not in result:
                    result['kwargs'] = {}
                result['kwargs'][key] = cast_to_number_or_bool(value)
        else:
            if 'args' not in result:
                result['args'] = []
            result['args'].append(cast_to_number_or_bool(elem))
    return result


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
    These should be the only keys with problematic (non-ascii) characters, since
    they can be user-generated.
    """

    replacements = (
        ('\u2018', "'"), ('\u2019', "'"), ('\u201C', '"'), ('\u201D', '"'))
    for orig, replacement in replacements:
        name = name.replace(orig, replacement)
    return name


def set_blue_values(ufo, alignment_zones):
    """Set postscript blue values from Glyphs alignment zones."""

    blue_values = []
    other_blues = []

    for pos, size in sorted(alignment_zones):
        val_list = blue_values if pos == 0 or size >= 0 else other_blues
        val_list.extend(sorted((pos, pos + size)))

    ufo.info.postscriptBlueValues = blue_values
    ufo.info.postscriptOtherBlues = other_blues


def set_robofont_guidelines(ufo_obj, glyphs_data, is_global=False):
    """Set guidelines as Glyphs does."""

    guidelines = glyphs_data.get('guideLines')
    if not guidelines:
        return

    new_guidelines = []
    for guideline in guidelines:
        x, y = guideline.pop('position')
        angle = guideline.pop('angle', 0)
        new_guideline = {'x': x, 'y': y, 'angle': angle, 'isGlobal': is_global}

        locked = guideline.pop('locked', False)
        if locked:
            new_guideline['locked'] = True

        new_guidelines.append(new_guideline)
    ufo_obj.lib[ROBOFONT_PREFIX + 'guides'] = new_guidelines


def set_robofont_glyph_background(glyph, key, background):
    """Set glyph background as Glyphs does."""

    if not background:
        return

    new_background = {}
    new_background['lib'] = background.pop('lib', {})

    anchors = []
    for anchor in background.get('anchors', []):
        x, y = anchor.pop('position')
        anchors.append({'x': x, 'y': y, 'name': anchor.pop('name')})
    new_background['anchors'] = anchors

    components = []
    for component in background.get('components', []):
        new_component = {
            'baseGlyph': component.pop('name'),
            'transformation': component.pop('transform', (1, 0, 0, 1, 0, 0))}

        for meta_attr in ['disableAlignment', 'locked']:
            value = component.pop(meta_attr, False)
            if value:
                new_component[meta_attr] = True

        components.append(new_component)
    new_background['components'] = components

    contours = []
    for path in background.get('paths', []):
        points = []
        for x, y, node_type, smooth in path.pop('nodes', []):
            point = {'x': x, 'y': y, 'smooth': smooth}
            if node_type in ['line', 'curve']:
                point['segmentType'] = node_type
            points.append(point)
        contours.append({'points': points})
        path.pop('closed', None)  # not used, but remove for debug purposes
    new_background['contours'] = contours

    new_background['width'] = background.pop('width', glyph.width)
    new_background['name'] = glyph.name
    new_background['unicodes'] = []

    libkey = ROBOFONT_PREFIX + 'layerData'
    try:
        glyph.lib[libkey][key] = new_background
    except KeyError:
        glyph.lib[libkey] = {key: new_background}


def set_family_user_data(ufo, user_data):
    """Set family-wide user data as Glyphs does."""

    for key, val in user_data.items():
        ufo.lib[key] = val


def set_master_user_data(ufo, user_data):
    """Set master-specific user data as Glyphs does."""

    if user_data:
        ufo.lib[GLYPHS_PREFIX + 'fontMaster.userData'] = user_data


def build_style_name(data, width_key, weight_key, custom_key, italic):
    """Build style name from width, weight, and custom style strings in data,
    and whether the style is italic.
    """

    italic = 'Italic' if italic else ''
    width = data.pop(width_key, '')
    weight = data.pop(weight_key, 'Regular')
    custom = data.pop(custom_key, '')
    if (italic or width or custom) and weight == 'Regular':
        weight = ''
    return ' '.join(s for s in (width, weight, custom, italic) if s)


def parse_style_attrs(name):
    """Parse width and weight from a style name, and return them in a list."""

    attrs = []
    for codes in (WIDTH_CODES, WEIGHT_CODES):
        m = re.search('(%s)' % '|'.join(k for k in codes.keys() if k), name)
        attrs.append(m.group(0) if m else '')
    return attrs


def to_ufo_time(datetime_obj):
    """Format a datetime object as specified for UFOs."""
    return datetime_obj.strftime('%Y/%m/%d %H:%M:%S')


def parse_custom_params(data, misc_keys):
    """Parse customParameters into a list of <name, val> pairs."""

    params = []
    for p in data.get('customParameters', []):
        params.append((p.pop('name'), p.pop('value')))
    for key in misc_keys:
        try:
            val = data.pop(key)
        except KeyError:
            continue
        params.append((key, val))
    return params


def load_kerning(ufo, kerning_data):
    """Add .glyphs kerning to an UFO."""

    warning_msg = 'Non-existent glyph class %s found in kerning rules.'
    class_glyph_pairs = []

    for left, pairs in kerning_data.items():
        match = re.match(r'@MMK_L_(.+)', left)
        left_is_class = bool(match)
        if left_is_class:
            left = 'public.kern1.%s' % match.group(1)
            if left not in ufo.groups:
                logger.warn(warning_msg % left)
                continue
        for right, kerning_val in pairs.items():
            match = re.match(r'@MMK_R_(.+)', right)
            right_is_class = bool(match)
            if right_is_class:
                right = 'public.kern2.%s' % match.group(1)
                if right not in ufo.groups:
                    logger.warn(warning_msg % right)
                    continue
            if left_is_class != right_is_class:
                if left_is_class:
                    pair = (left, right, True)
                else:
                    pair = (right, left, False)
                class_glyph_pairs.append(pair)
            ufo.kerning[left, right] = kerning_val

    seen = {}
    for classname, glyph, is_left_class in reversed(class_glyph_pairs):
        remove_rule_if_conflict(ufo, seen, classname, glyph, is_left_class)


def remove_rule_if_conflict(ufo, seen, classname, glyph, is_left_class):
    """Check if a class-to-glyph kerning rule has a conflict with any existing
    rule in `seen`, and remove any conflicts if they exist.
    """

    original_pair = (classname, glyph) if is_left_class else (glyph, classname)
    val = ufo.kerning[original_pair]
    rule = original_pair + (val,)

    old_glyphs = ufo.groups[classname]
    new_glyphs = []
    for member in old_glyphs:
        pair = (member, glyph) if is_left_class else (glyph, member)
        existing_rule = seen.get(pair)
        if (existing_rule is not None and
            existing_rule[-1] != val and
            pair not in ufo.kerning):
            logger.warn(
                'Conflicting kerning rules found in %s master for glyph pair '
                '"%s, %s" (%s and %s), removing pair from latter rule' %
                ((ufo.info.styleName,) + pair + (existing_rule, rule)))
        else:
            new_glyphs.append(member)
            seen[pair] = rule

    if new_glyphs != old_glyphs:
        del ufo.kerning[original_pair]
        for member in new_glyphs:
            pair = (member, glyph) if is_left_class else (glyph, member)
            ufo.kerning[pair] = val


def load_glyph_libdata(glyph, layer):
    """Add to a glyph's lib data."""

    set_robofont_guidelines(glyph, layer)
    set_robofont_glyph_background(glyph, 'background', layer.get('background'))
    for key in ['annotations', 'hints']:
        try:
            value = layer.pop(key)
        except KeyError:
            continue
        glyph.lib[GLYPHS_PREFIX + key] = value

    # data related to components stored in lists of booleans
    # each list's elements correspond to the components in order
    for key in ['disableAlignment', 'locked']:
        values = [c.pop(key, False) for c in layer.get('components', [])]
        if any(values):
            key = key[0].upper() + key[1:]
            glyph.lib['%scomponents%s' % (GLYPHS_PREFIX, key)] = values


def load_glyph(glyph, layer, glyph_data):
    """Add .glyphs metadata, paths, components, and anchors to a glyph."""

    uval = glyph_data.get('unicode')
    if uval is not None:
        glyph.unicode = uval
    note = glyph_data.get('note')
    if note is not None:
        glyph.note = note
    last_change = glyph_data.get('lastChange')
    if last_change is not None:
        glyph.lib[GLYPHLIB_PREFIX + 'lastChange'] = to_ufo_time(last_change)
    color_index = glyph_data.get('color')
    if color_index is not None and color_index >= 0:
        glyph.lib[GLYPHLIB_PREFIX + 'ColorIndex'] = color_index
        glyph.lib[PUBLIC_PREFIX + 'markColor'] = GLYPHS_COLORS[color_index]
    export = glyph_data.get('export')
    if export is not None:
        glyph.lib[GLYPHLIB_PREFIX + 'Export'] = export
    glyphinfo = glyphsLib.glyphdata.get_glyph(glyph.name)
    production_name = glyph_data.get('production') or glyphinfo.production_name
    if production_name != glyph.name:
        postscriptNamesKey = PUBLIC_PREFIX + 'postscriptNames'
        if postscriptNamesKey not in glyph.font.lib:
            glyph.font.lib[postscriptNamesKey] = dict()
        glyph.font.lib[postscriptNamesKey][glyph.name] = production_name

    for key in ['leftMetricsKey', 'rightMetricsKey', 'widthMetricsKey']:
        glyph_metrics_key = None
        try:
            glyph_metrics_key = layer.pop(key)
        except KeyError:
            glyph_metrics_key = glyph_data.get(key)
        if glyph_metrics_key:
            glyph.lib[GLYPHLIB_PREFIX + key] = glyph_metrics_key

    # if glyph contains custom 'category' and 'subCategory' overrides, store
    # them in the UFO glyph's lib
    category = glyph_data.get('category')
    if category is None:
        category = glyphinfo.category
    else:
        glyph.lib[GLYPHLIB_PREFIX + 'category'] = category
    subCategory = glyph_data.get('subCategory')
    if subCategory is None:
        subCategory = glyphinfo.subCategory
    else:
        glyph.lib[GLYPHLIB_PREFIX + 'subCategory'] = subCategory

    # load width before background, which is loaded with lib data
    width = layer.pop('width')
    if category == 'Mark' and subCategory == 'Nonspacing' and width > 0:
        # zero the width of Nonspacing Marks like Glyphs.app does on export
        # TODO: check for customParameter DisableAllAutomaticBehaviour
        glyph.lib[GLYPHLIB_PREFIX + 'originalWidth'] = width
        glyph.width = 0
    else:
        glyph.width = width
    load_glyph_libdata(glyph, layer)

    pen = glyph.getPointPen()
    draw_paths(pen, layer.get('paths', []))
    draw_components(pen, layer.get('components', []))
    add_anchors_to_glyph(glyph, layer.get('anchors', []))


def draw_paths(pen, paths):
    """Draw .glyphs paths onto a pen."""

    for path in paths:
        pen.beginPath()
        nodes = path.get('nodes', [])
        if not nodes:
            pen.endPath()
            continue
        if not path.pop('closed', False):
            x, y, node_type, smooth = nodes.pop(0)
            assert node_type == 'line', 'Open path starts with off-curve points'
            pen.addPoint((x, y), segmentType='move')
        else:
            # In Glyphs.app, the starting node of a closed contour is always
            # stored at the end of the nodes list.
            nodes.insert(0, nodes.pop())
        for x, y, node_type, smooth in nodes:
            if node_type not in ['line', 'curve']:
                node_type = None
            pen.addPoint((x, y), segmentType=node_type, smooth=smooth)
        pen.endPath()


def draw_components(pen, components):
    """Draw .glyphs components onto a pen, adding them to the parent glyph."""

    for component in components:
        pen.addComponent(component.pop('name'),
                         component.pop('transform', (1, 0, 0, 1, 0, 0)))


def add_anchors_to_glyph(glyph, anchors):
    """Add .glyphs anchors to a glyph."""

    for anchor in anchors:
        x, y = anchor.pop('position')
        anchor_dict = {'name': anchor.pop('name'), 'x': x, 'y': y}
        glyph.appendAnchor(glyph.anchorClass(anchorDict=anchor_dict))


def add_glyph_to_groups(kerning_groups, glyph_data):
    """Add a glyph to its kerning groups, creating new groups if necessary."""

    glyph_name = glyph_data['glyphname']
    group_keys = {
        '1': 'rightKerningGroup',
        '2': 'leftKerningGroup'}
    for side, group_key in group_keys.items():
        if group_key not in glyph_data:
            continue
        group = 'public.kern%s.%s' % (side, glyph_data.pop(group_key))
        kerning_groups[group] = kerning_groups.get(group, []) + [glyph_name]


def add_groups_to_ufo(ufo, kerning_groups):
    """Add kerning groups to an UFO."""

    for name, glyphs in kerning_groups.items():
        ufo.groups[name] = glyphs


def build_gdef(ufo):
    """Build a table GDEF statement for ligature carets."""
    bases, ligatures, marks, carets = set(), set(), set(), {}
    category_key = GLYPHLIB_PREFIX + 'category'
    subCategory_key = GLYPHLIB_PREFIX + 'subCategory'
    for glyph in ufo:
        has_attaching_anchor = False
        for anchor in glyph.anchors:
            name = anchor.get('name')
            if name and not name.startswith('_'):
                has_attaching_anchor = True
            if name and name.startswith('caret_') and 'x' in anchor:
                carets.setdefault(glyph.name, []).append(round(anchor['x']))
        lib = glyph.lib
        glyphinfo = glyphsLib.glyphdata.get_glyph(glyph.name)
        # first check glyph.lib for category/subCategory overrides; else use
        # global values from GlyphData
        category = lib.get(category_key)
        if category is None:
            category = glyphinfo.category
        subCategory = lib.get(subCategory_key)
        if subCategory is None:
            subCategory = glyphinfo.subCategory

        # Glyphs.app assigns glyph classes like this:
        #
        # * Base: any glyph that has an attaching anchor
        #   (such as "top"; "_top" does not count) and is neither
        #   classified as Ligature nor Mark using the definitions below;
        #
        # * Ligature: if subCategory is "Ligature" and the glyph has
        #   at least one attaching anchor;
        #
        # * Mark: if category is "Mark" and subCategory is either
        #   "Nonspacing" or "Spacing Combining";
        #
        # * Compound: never assigned by Glyphs.app.
        #
        # https://github.com/googlei18n/glyphsLib/issues/85
        # https://github.com/googlei18n/glyphsLib/pull/100#issuecomment-275430289
        if subCategory == 'Ligature' and has_attaching_anchor:
            ligatures.add(glyph.name)
        elif category == 'Mark' and (subCategory == 'Nonspacing' or
                                     subCategory == 'Spacing Combining'):
            marks.add(glyph.name)
        elif has_attaching_anchor:
            bases.add(glyph.name)
    if not any((bases, ligatures, marks, carets)):
        return None
    lines = ['table GDEF {', '  # automatic']
    glyphOrder = ufo.lib[PUBLIC_PREFIX + 'glyphOrder']
    glyphIndex = lambda glyph: glyphOrder.index(glyph)
    fmt = lambda g: ('[%s]' % ' '.join(sorted(g, key=glyphIndex))) if g else ''
    lines.extend([
        '  GlyphClassDef',
        '    %s, # Base' % fmt(bases),
        '    %s, # Liga' % fmt(ligatures),
        '    %s, # Mark' % fmt(marks),
        '    ;'])
    for glyph, caretPos in sorted(carets.items()):
        lines.append('  LigatureCaretByPos %s %s;' %
                     (glyph, ' '.join(unicode(p) for p in sorted(caretPos))))
    lines.append('} GDEF;')
    return '\n'.join(lines)


def add_features_to_ufo(ufo, feature_prefixes, classes, features):
    """Write an UFO's OpenType feature file."""

    autostr = lambda automatic: '# automatic\n' if automatic else ''

    prefix_str = '\n\n'.join(
        '# Prefix: %s\n%s%s' % (name, autostr(automatic), code.strip())
        for name, code, automatic in feature_prefixes)

    class_defs = []
    for name, code, automatic in classes:
        if not name.startswith('@'):
            name = '@' + name
        class_defs.append('%s%s = [ %s ];' % (autostr(automatic), name, code))
    class_str = '\n\n'.join(class_defs)

    feature_defs = []
    for name, code, automatic, disabled, notes in features:
        code = code.strip()
        lines = ['feature %s {' % name]
        if notes:
            lines.append('# notes:')
            lines.extend('# ' + line for line in notes.splitlines())
        if automatic:
            lines.append('# automatic')
        if disabled:
            lines.append('# disabled')
            lines.extend('#' + line for line in code.splitlines())
        else:
            lines.append(code)
        lines.append('} %s;' % name)
        feature_defs.append('\n'.join(lines))
    fea_str = '\n\n'.join(feature_defs)
    gdef_str = build_gdef(ufo)

    # make sure feature text is a unicode string, for defcon
    full_text = '\n\n'.join(
        filter(None, [prefix_str, class_str, fea_str, gdef_str])) + '\n'
    ufo.features.text = full_text if full_text.strip() else ''
