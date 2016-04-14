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


from __future__ import print_function, division, absolute_import

import os
import re
import shutil
import sys

from defcon import Font

__all__ = [
    'to_ufos', 'clear_data', 'set_redundant_data', 'set_custom_params',
    'build_style_name', 'build_ufo_path', 'write_ufo', 'GLYPHS_PREFIX'
]


PUBLIC_PREFIX = 'public.'
GLYPHS_PREFIX = 'com.schriftgestaltung.'
ROBOFONT_PREFIX = 'com.typemytype.robofont.'

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
    'Black': 900}

WIDTH_CODES = {
    'Extra Condensed': 2,
    'Cond': 3,
    'Condensed': 3,
    'Narrow': 4,
    'SemiCondensed': 4,
    '': 5}


def to_ufos(data, italic=False, include_instances=False, debug=False):
    """Take .glyphs file data and load it into UFOs.

    Takes in data as a dictionary structured according to
    https://github.com/schriftgestalt/GlyphsSDK/blob/master/GlyphsFileFormat.md
    and returns a list of UFOs, one per master.

    If debug is True, returns unused input data instead of the resulting UFOs.
    """

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
    ufos, master_id_order = generate_base_fonts(data, italic)

    glyph_order = []

    for glyph in data['glyphs']:
        add_glyph_to_groups(kerning_groups, glyph)

        glyph_name = glyph.pop('glyphname')
        glyph_order.append(glyph_name)
        if not re.match(r'^([A-Za-z_][\w.]*|\.notdef)$', glyph_name):
            warn('Illegal glyph name "%s". If this is used in the font\'s '
                 'feature syntax, it could cause errors.' % glyph_name)

        # pop glyph metadata only once, i.e. not when looping through layers
        metadata_keys = ['unicode', 'color', 'export', 'lastChange',
                         'leftMetricsKey', 'note', 'rightMetricsKey',
                         'widthMetricsKey']
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
        add_features_to_ufo(ufo, feature_prefixes, classes, features)
        add_groups_to_ufo(ufo, kerning_groups)

        ufo.lib[PUBLIC_PREFIX + 'glyphOrder'] = glyph_order

    for master_id, kerning in data.pop('kerning', {}).items():
        load_kerning(ufos[master_id], kerning)

    result = [ufos[master_id] for master_id in master_id_order]
    instances = data.pop('instances', [])
    if debug:
        return clear_data(data)
    elif include_instances:
        return result, instances
    return result


def clear_data(data):
    """Clear empty list or dict attributes in data.

    This is used to determine what input data provided to to_ufos was not
    loaded into an UFO."""

    data_type = type(data)
    if data_type is dict:
        for key, val in data.items():
            if not clear_data(val):
                del data[key]
        return data
    elif data_type is list:
        i = 0
        while i < len(data):
            val = data[i]
            if not clear_data(val):
                del data[i]
            else:
                i += 1
        return data
    return True


def generate_base_fonts(data, italic):
    """Generate a list of UFOs with metadata loaded from .glyphs data."""

    date_created = to_ufo_time(data.pop('date'))
    family_name = data.pop('familyName')
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

        ufo.info.familyName = family_name
        ufo.info.styleName = build_style_name(master, ('width', 'weight'), italic)

        ufo.info.openTypeHeadCreated = date_created
        ufo.info.unitsPerEm = units_per_em
        ufo.info.versionMajor = version_major
        ufo.info.versionMinor = version_minor

        if copyright:
            ufo.info.copyright = unicode(copyright.decode("utf-8"))
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

        if horizontal_stems:
            ufo.info.postscriptStemSnapH = horizontal_stems
        if vertical_stems:
            ufo.info.postscriptStemSnapV = vertical_stems

        set_redundant_data(ufo)
        set_blue_values(ufo, master.pop('alignmentZones', []))
        set_family_user_data(ufo, user_data)
        set_master_user_data(ufo, master.pop('userData', {}))
        set_robofont_guidelines(ufo, master, is_global=True)

        set_custom_params(ufo, parsed=custom_params)
        # the misc attributes double as deprecated info attributes!
        # they are Glyphs-related, not OpenType-related, and don't go in info
        misc = ['weightValue', 'widthValue']
        set_custom_params(ufo, data=master, misc_keys=misc, non_info=misc)

        master_id = master.pop('id')
        ufo.lib[GLYPHS_PREFIX + 'fontMasterID'] = master_id
        master_id_order.append(master_id)
        ufos[master_id] = ufo

    return ufos, master_id_order


def set_redundant_data(ufo):
    """Set redundant metadata in a UFO, e.g. data based on other data."""

    family_name, style_name = ufo.info.familyName, ufo.info.styleName

    width, weight = parse_style_attrs(style_name)
    ufo.info.openTypeOS2WidthClass = WIDTH_CODES[width]
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
        ufo.info.styleMapFamilyName = ' '.join(s for s in (
            family_name, width, weight if weight != 'Bold' else '') if s)
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

    for name, value in parsed:

        # deal with any Glyphs naming quirks here
        if name == 'disablesNiceNames':
            name = 'useNiceNames'
            value = int(not value)

        opentype_attr_prefix_pairs = (
            ('hhea', 'Hhea'), ('description', 'NameDescription'),
            ('license', 'NameLicense'), ('panose', 'OS2Panose'),
            ('typo', 'OS2Typo'), ('win', 'OS2Win'), ('vendorID', 'OS2VendorID'),
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

        # most OpenType table entries go in the info object
        if hasattr(ufo.info, name) and name not in non_info:
            setattr(ufo.info, name, value)

        # everything else gets dumped in the lib
        else:
            ufo.lib[GLYPHS_PREFIX + name] = value


def set_blue_values(ufo, alignment_zones):
    """Set postscript blue values from Glyphs alignment zones."""

    blue_values = []
    other_blues = []

    for base, offset in sorted(alignment_zones):
        pair = [base, base + offset]
        val_list = blue_values if base >= 0 else other_blues
        val_list.extend(sorted(pair))

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


def build_style_name(data, attr_keys, italic):
    """Build style name from width and weight strings in data, and whether the
    style is italic.
    """

    italic = 'Italic' if italic else ''
    if len(attr_keys) == 2:
        # assume keys are for width and weight
        width = data.pop(attr_keys[0], '')
        weight = data.pop(attr_keys[1], 'Regular')
    else:
        # assume one key for both width and weight
        width, weight = parse_style_attrs(data.pop(attr_keys[0]))
    if (italic or width) and weight == 'Regular':
        weight = ''
    return ' '.join(s for s in (width, weight, italic) if s)


def parse_style_attrs(name):
    """Parse width and weight from a style name, and return them in a tuple."""

    m = re.search('(%s)' % '|'.join(k for k in WIDTH_CODES.keys() if k), name)
    width = m.group(0) if m else ''
    weight = name.replace(width, '').replace('Italic', '').strip()
    if weight not in WEIGHT_CODES:
        warn('Unrecognized weight "%s"' % weight)
        weight = ''
    return width, weight


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
    for left, pairs in kerning_data.items():
        match = re.match(r'@MMK_L_(.+)', left)
        if match:
            left = 'public.kern1.%s' % match.group(1)
            if left not in ufo.groups:
                warn(warning_msg % left)
                continue
        for right, kerning_val in pairs.items():
            match = re.match(r'@MMK_R_(.+)', right)
            if match:
                right = 'public.kern2.%s' % match.group(1)
                if right not in ufo.groups:
                    warn(warning_msg % right)
                    continue
            ufo.kerning[left, right] = kerning_val
    remove_conflicting_kerning(ufo)


def remove_conflicting_kerning(ufo):
    """Remove any conflicting kerning rules.

    If conflicts are detected in a class-to-glyph rule, the rule is replaced
    with glyph-to-glyph rules for each of the class's members (minus the
    offending members).
    """

    left_class_kerning = []
    right_class_kerning = []

    # collect kerning rules by type
    for pair, value in ufo.kerning.items():
        left, right = pair
        left_is_class = left.startswith('public.kern1.')
        right_is_class = right.startswith('public.kern2.')
        if left_is_class and not right_is_class:
            left_class_kerning.append(pair)
        elif right_is_class and not left_is_class:
            right_class_kerning.append(pair)

    # remove conflicts
    seen = {}
    for left, right in left_class_kerning:
        remove_rule_if_conflict(ufo, seen, left, right, is_left_class=True)
    for left, right in right_class_kerning:
        remove_rule_if_conflict(ufo, seen, right, left, is_left_class=False)


def remove_rule_if_conflict(ufo, seen, classname, glyph, is_left_class=True):
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
            warn('Duplicate kerning rules found for glyph pair "%s, %s" '
                 '(%s and %s), removing pair from latter rule' %
                 (pair + (existing_rule, rule)))
        else:
            new_glyphs.append(member)
            seen[pair] = rule

    if new_glyphs != old_glyphs:
        del ufo.kerning[original_pair]
        for member in new_glyphs:
            pair = (member, glyph) if is_left_class else(glyph, member)
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

    glyphlib_prefix = GLYPHS_PREFIX + 'Glyphs.'

    uval = glyph_data.get('unicode')
    if uval is not None:
        glyph.unicode = uval
    note = glyph_data.get('note')
    if note is not None:
        glyph.note = note
    last_change = glyph_data.get('lastChange')
    if last_change is not None:
        glyph.lib[glyphlib_prefix + 'lastChange'] = to_ufo_time(last_change)
    color_index = glyph_data.get('color')
    if color_index is not None:
        glyph.lib[glyphlib_prefix + 'ColorIndex'] = color_index
        glyph.lib[PUBLIC_PREFIX + 'markColor'] = GLYPHS_COLORS[color_index]
    export = glyph_data.get('export')
    if export is not None:
        glyph.lib[glyphlib_prefix + 'Export'] = export

    for key in ['leftMetricsKey', 'rightMetricsKey', 'widthMetricsKey']:
        glyph_metrics_key = None
        try:
            glyph_metrics_key = layer.pop(key)
        except KeyError:
            glyph_metrics_key = glyph_data.get(key)
        if glyph_metrics_key:
            glyph_metrics_key = unicode(glyph_metrics_key.decode("utf-8"))
            glyph.lib[glyphlib_prefix + key] = glyph_metrics_key

    # load width before background, which is loaded with lib data
    glyph.width = layer.pop('width')
    load_glyph_libdata(glyph, layer)

    pen = glyph.getPointPen()
    draw_paths(pen, layer.get('paths', []))
    draw_components(pen, layer.get('components', []))
    add_anchors_to_glyph(glyph, layer.get('anchors', []))


def draw_paths(pen, paths):
    """Draw .glyphs paths onto a pen."""

    for path in paths:
        pen.beginPath()
        if not path.pop('closed', False):
            x, y, node_type, smooth = path['nodes'].pop(0)
            assert node_type == 'line', 'Open path starts with off-curve points'
            pen.addPoint((x, y), 'move')
        for x, y, node_type, smooth in path.pop('nodes'):
            if node_type not in ['line', 'curve']:
                node_type = None
            pen.addPoint((x, y), node_type, smooth)
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

    # make sure feature text is a unicode string, for defcon
    full_text = u'\n\n'.join([prefix_str, class_str, fea_str])
    ufo.features.text = full_text if full_text.strip() else ''


def build_ufo_path(out_dir, family_name, style_name):
    """Build string to use as a UFO path."""

    return os.path.join(
        out_dir, '%s-%s.ufo' % (
            family_name.replace(' ', ''),
            style_name.replace(' ', '')))


def write_ufo(ufo, out_dir):
    """Write a UFO."""

    out_path = build_ufo_path(
        out_dir, ufo.info.familyName, ufo.info.styleName)

    # Defcon seems to fail trying to update UFOs
    # TODO(jamesgk) maybe look into this
    if os.path.exists(out_path):
        shutil.rmtree(out_path)

    print('>>> Writing %s' % out_path)
    if ufo.path:
        ufo.save()
    else:
        ufo.save(out_path)


def warn(message):
    print('WARNING: ' + message, file=sys.stderr)
