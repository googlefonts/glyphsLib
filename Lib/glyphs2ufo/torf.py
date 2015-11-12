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


__all__ = [
    'to_robofab', 'clear_data', 'set_redundant_data', 'build_family_name',
    'build_style_name', 'build_postscript_name'
]


import re
from robofab.world import RFont


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


def to_robofab(data, italic=False, include_instances=False, debug=False):
    """Take .glyphs file data and load it into RFonts.

    Takes in data as a dictionary structured according to
    https://github.com/schriftgestalt/GlyphsSDK/blob/master/GlyphsFileFormat.md
    and returns a list of RFonts, one per master.

    If debug is True, returns unused input data instead of the resulting RFonts.
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
    rfonts, master_id_order = generate_base_fonts(data, italic)

    for glyph in data['glyphs']:
        add_glyph_to_groups(kerning_groups, glyph)

        glyph_name = glyph.pop('glyphname')
        if not re.match('^[\w\d._]{1,31}$', glyph_name):
            warn('Illegal glyph name "%s". If this is used in the font\'s '
                 'feature syntax, it could cause errors.' % glyph_name)

        # pop glyph metadata only once, i.e. not when looping through layers
        metadata_keys = ['unicode', 'color', 'lastChange', 'leftMetricsKey',
                         'note', 'rightMetricsKey', 'widthMetricsKey']
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

            rfont = rfonts[layer_id]

            # ensure consistency between layer ids / names
            font_style = rfont_style_to_layer_style(rfont)
            if font_style != layer_name:
                warn('Inconsistent layer id/name pair: glyph "%s" layer "%s"' %
                     (glyph_name, layer_name))
                continue

            rglyph = rfont.newGlyph(glyph_name)
            load_glyph(rglyph, layer, glyph_data)

    for layer_id, glyph_name, bg_name, bg_data in supplementary_bg_data:
        rglyph = rfonts[layer_id][glyph_name]
        set_robofont_glyph_background(rglyph, bg_name, bg_data)

    for rfont in rfonts.itervalues():
        add_features_to_rfont(rfont, feature_prefixes, classes, features)
        add_groups_to_rfont(rfont, kerning_groups)

        # try to create a glyph order which includes all of the glyphs
        glyph_order = rfont.lib[GLYPHS_PREFIX + 'glyphOrder']
        actual_order = glyph_order + sorted(
            set(rfont.keys()) - set(glyph_order))
        rfont.lib[PUBLIC_PREFIX + 'glyphOrder'] = actual_order

    for master_id, kerning in data.pop('kerning', {}).iteritems():
        load_kerning(rfonts[master_id], kerning)

    result = [rfonts[master_id] for master_id in master_id_order]
    instances = data.pop('instances', [])
    if debug:
        return clear_data(data)
    elif include_instances:
        return result, instances
    return result


def clear_data(data):
    """Clear empty list or dict attributes in data.

    This is used to determine what input data provided to to_robofab was not
    loaded into an RFont."""

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
    """Generate a list of RFonts with metadata loaded from .glyphs data."""

    date_created = to_rf_time(data.pop('date'))
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

    rfonts = {}
    master_id_order = []
    for master in data['fontMaster']:
        rfont = RFont()

        rfont.info.familyName = build_family_name(family_name, master, 'width')
        rfont.info.styleName = build_style_name(master, 'weight', italic)

        rfont.info.openTypeHeadCreated = date_created
        rfont.info.unitsPerEm = units_per_em
        rfont.info.versionMajor = version_major
        rfont.info.versionMinor = version_minor

        if copyright:
            rfont.info.copyright = copyright
        if designer:
            rfont.info.openTypeNameDesigner = designer
        if designer_url:
            rfont.info.openTypeNameDesignerURL = designer_url
        if manufacturer:
            rfont.info.openTypeNameManufacturer = manufacturer
        if manufacturer_url:
            rfont.info.openTypeNameManufacturerURL = manufacturer_url

        rfont.info.ascender = master.pop('ascender')
        rfont.info.capHeight = master.pop('capHeight')
        rfont.info.descender = master.pop('descender')
        rfont.info.xHeight = master.pop('xHeight')
        horizontal_stems = master.pop('horizontalStems', None)
        vertical_stems = master.pop('verticalStems', None)

        if horizontal_stems:
            rfont.info.postscriptStemSnapH = horizontal_stems
        if vertical_stems:
            rfont.info.postscriptStemSnapV = vertical_stems

        set_redundant_data(rfont)
        set_blue_values(rfont, master.pop('alignmentZones', []))
        set_family_user_data(rfont, user_data)
        set_master_user_data(rfont, master.pop('userData', {}))
        set_robofont_guidelines(rfont, master, is_global=True)

        # handle random optional stuff
        misc = ['weightValue', 'widthValue']
        for name, value in custom_params + parse_custom_params(master, misc):

            # deal with any Glyphs naming quirks here
            if name == 'disablesNiceNames':
                name = 'useNiceNames'
                value = int(not value)

            opentype_attr_prefix_pairs = (
                ('hhea', 'Hhea'), ('description', 'NameDescription'),
                ('typo', 'OS2Typo'), ('win', 'OS2Win'),
                ('vendorID', 'OS2VendorID'), ('fsType', 'OS2Type'))
            for glyphs_prefix, ufo_prefix in opentype_attr_prefix_pairs:
                name = re.sub(
                    '^' + glyphs_prefix, 'openType' + ufo_prefix, name)

            # enforce that winAscent/Descent are positive, according to UFO spec
            if name.startswith('openTypeOS2Win') and value < 0:
                value = -value

            # most OpenType table entries go in the info object
            # the misc attributes double as deprecated info attributes!
            # they are Glyphs-related, not OpenType-related, and don't go here
            if hasattr(rfont.info, name) and name not in misc:
                setattr(rfont.info, name, value)

            # everything else gets dumped in the lib
            else:
                rfont.lib[GLYPHS_PREFIX + name] = value

        master_id = master.pop('id')
        rfont.lib[GLYPHS_PREFIX + 'fontMasterID'] = master_id
        master_id_order.append(master_id)
        rfonts[master_id] = rfont

    return rfonts, master_id_order


def set_redundant_data(rfont):
    """Set redundant metadata in an RFont, e.g. data based on other data."""

    family_name, style_name = rfont.info.familyName, rfont.info.styleName
    weight = style_name.replace('Italic', '').strip()
    width = family_name.split()[-1]

    rfont.info.openTypeOS2WeightClass = get_weight_code(weight)
    rfont.info.openTypeOS2WidthClass = get_width_code(width)
    if weight and weight != 'Regular':
        rfont.lib[GLYPHS_PREFIX + 'weight'] = weight
    if 'Condensed' in width:
        rfont.lib[GLYPHS_PREFIX + 'width'] = width

    ps_name = build_postscript_name(family_name, style_name)
    rfont.info.postscriptFontName = ps_name
    rfont.info.postscriptFullName = ps_name

    version_str = '%s.%s' % (rfont.info.versionMajor, rfont.info.versionMinor)
    rfont.info.openTypeNameVersion = 'Version ' + version_str
    rfont.info.openTypeNameUniqueID = '%s;%s' % (version_str, ps_name)

    if style_name.lower() in ['regular', 'bold', 'italic', 'bold italic']:
        rfont.info.styleMapStyleName = style_name.lower()
        rfont.info.styleMapFamilyName = family_name
    else:
        rfont.info.styleMapStyleName = 'regular'
        rfont.info.styleMapFamilyName = '%s %s' % (family_name, weight)
    rfont.info.openTypeNamePreferredFamilyName = family_name
    rfont.info.openTypeNamePreferredSubfamilyName = style_name


def set_blue_values(rfont, alignment_zones):
    """Set postscript blue values from Glyphs alignment zones."""

    blue_values = []
    other_blues = []

    for base, offset in sorted(alignment_zones):
        pair = [base, base + offset]
        val_list = blue_values if base >= 0 else other_blues
        val_list.extend(sorted(pair))

    rfont.info.postscriptBlueValues = blue_values
    rfont.info.postscriptOtherBlues = other_blues


def set_robofont_guidelines(rf_obj, glyphs_data, is_global=False):
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
    rf_obj.lib[ROBOFONT_PREFIX + 'guides'] = new_guidelines


def set_robofont_glyph_background(rglyph, key, background):
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

    new_background['width'] = background.pop('width', rglyph.width)
    new_background['name'] = rglyph.name
    new_background['unicodes'] = []

    libkey = ROBOFONT_PREFIX + 'layerData'
    try:
        rglyph.lib[libkey][key] = new_background
    except KeyError:
        rglyph.lib[libkey] = {key: new_background}


def set_family_user_data(rfont, user_data):
    """Set family-wide user data as Glyphs does."""

    for key, val in user_data.iteritems():
        rfont.lib[key] = val


def set_master_user_data(rfont, user_data):
    """Set master-specific user data as Glyphs does."""

    if not user_data:
        return
    for attr in ['GSOffsetHorizontal', 'GSOffsetVertical']:
        if attr in user_data:
            user_data[attr] = int(user_data[attr])
    rfont.lib[GLYPHS_PREFIX + 'fontMaster.userData'] = user_data


def build_family_name(base_family, data, width_key):
    """Build family name from base name and width string in data."""
    return ('%s %s' % (base_family, data.pop(width_key, ''))).strip()


def build_style_name(data, weight_key, italic):
    """Build style name from weight string in data and whether it's italic."""

    style_name = data.pop(weight_key, 'Regular')
    if italic:
        if style_name == 'Regular':
            style_name = 'Italic'
        else:
            style_name += ' Italic'
    return style_name


def build_postscript_name(family_name, style_name):
    """Build string to use for postscript*Name from family and style names."""

    return '%s-%s' % (family_name.replace(' ', ''),
                      style_name.replace(' ', ''))


def get_weight_code(style_name):
    """Get the appropriate OS/2 weight code for this style."""

    return {
        'Thin': 250,
        'Light': 300,
        'Medium': 500,
        'SemiBold': 600,
        'Bold': 700,
        'ExtraBold': 800,
        'Black': 900
    }.get(style_name, 400)


def get_width_code(style_name):
    """Get the appropriate OS/2 width code for this style."""

    return {
        'Condensed': 3,
        'SemiCondensed': 4
    }.get(style_name, 5)


def rfont_style_to_layer_style(rfont):
    """Convert style as stored in RFonts into Glyphs layer data.

    We store style info in RFonts as:
      familyName: "[family] [condensed]"
      styleName: "[weight] [italic]"
    where "Regular Italic" in styleName becomes simply "Italic".

    Glyphs layer styles are stored as "[weight] [condensed] [italic]", where
    "Regular Condensed" becomes "Condensed" but "Regular Italic" does not get
    shortened.
    """

    style = rfont.info.styleName.split()
    family = rfont.info.familyName.split()
    if style[0] == 'Italic':
        style.insert(0, 'Regular')
    if family[-1] == 'Condensed':
        if style[0] == 'Regular':
            style[0] = 'Condensed'
        else:
            if style[-1] == 'Italic':
                style.insert(-1, 'Condensed')
            else:
                style.append('Condensed')
    return ' '.join(style)


def to_rf_time(datetime_obj):
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


def load_kerning(rfont, kerning_data):
    """Add .glyphs kerning to an RFont."""

    warning_msg = 'Non-existent glyph class %s found in kerning rules.'
    for left, pairs in kerning_data.items():
        if left.startswith('@') and left not in rfont.groups:
            warn(warning_msg % left)
            continue
        for right, kerning_val in pairs.items():
            if right.startswith('@') and right not in rfont.groups:
                warn(warning_msg % right)
                continue
            rfont.kerning[left, right] = kerning_val


def load_glyph_libdata(rglyph, layer):
    """Add to an RGlyph's lib data."""

    set_robofont_guidelines(rglyph, layer)
    set_robofont_glyph_background(rglyph, 'background', layer.get('background'))
    for key in ['annotations', 'hints']:
        try:
            value = layer.pop(key)
        except KeyError:
            continue
        rglyph.lib[GLYPHS_PREFIX + key] = value

    # data related to components stored in lists of booleans
    # each list's elements correspond to the components in order
    for key in ['disableAlignment', 'locked']:
        values = [c.pop(key, False) for c in layer.get('components', [])]
        if any(values):
            key = key[0].upper() + key[1:]
            rglyph.lib['%scomponents%s' % (GLYPHS_PREFIX, key)] = values


def load_glyph(rglyph, layer, glyph_data):
    """Add .glyphs metadata, paths, components, and anchors to an RGlyph."""

    glyphlib_prefix = GLYPHS_PREFIX + 'Glyphs.'

    uval = glyph_data.get('unicode')
    if uval is not None:
        rglyph.unicode = uval
    note = glyph_data.get('note')
    if note is not None:
        rglyph.note = note
    last_change = glyph_data.get('lastChange')
    if last_change is not None:
        rglyph.lib[glyphlib_prefix + 'lastChange'] = to_rf_time(last_change)
    color_index = glyph_data.get('color')
    if color_index is not None:
        rglyph.lib[glyphlib_prefix + 'ColorIndex'] = color_index
        rglyph.lib[PUBLIC_PREFIX + 'markColor'] = GLYPHS_COLORS[color_index]

    for key in ['leftMetricsKey', 'rightMetricsKey', 'widthMetricsKey']:
        try:
            rglyph.lib[glyphlib_prefix + key] = layer.pop(key)
        except KeyError:
            glyph_metrics_key = glyph_data.get(key)
            if glyph_metrics_key:
                rglyph.lib[glyphlib_prefix + key] = glyph_metrics_key

    # load width before background, which is loaded with lib data
    rglyph.width = layer.pop('width')
    load_glyph_libdata(rglyph, layer)

    pen = rglyph.getPointPen()
    draw_paths(pen, layer.get('paths', []))
    draw_components(pen, layer.get('components', []))
    add_anchors_to_glyph(rglyph, layer.get('anchors', []))


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
    """Draw .glyphs components onto a pen, adding them to the parent RGlyph."""

    for component in components:
        pen.addComponent(component.pop('name'),
                         component.pop('transform', (1, 0, 0, 1, 0, 0)))


def add_anchors_to_glyph(glyph, anchors):
    """Add .glyphs anchors to an RGlyph."""

    for anchor in anchors:
        glyph.appendAnchor(anchor.pop('name'), anchor.pop('position'))


def add_glyph_to_groups(kerning_groups, glyph_data):
    """Add a glyph to its kerning groups, creating new groups if necessary."""

    glyph_name = glyph_data['glyphname']
    group_keys = {
        'L': 'rightKerningGroup',
        'R': 'leftKerningGroup'}
    for side in 'LR':
        group_key = group_keys[side]
        if group_key not in glyph_data:
            continue
        #TODO(jamesgk) figure out if this is a general rule for group naming
        group = '@MMK_%s_%s' % (side, glyph_data.pop(group_key))
        kerning_groups[group] = kerning_groups.get(group, []) + [glyph_name]


def add_groups_to_rfont(rfont, kerning_groups):
    """Add kerning groups to an RFont."""

    for name, glyphs in kerning_groups.items():
        rfont.groups[name] = glyphs


def add_features_to_rfont(rfont, feature_prefixes, classes, features):
    """Write an RFont's OpenType feature file."""

    autostr = lambda automatic: '# automatic\n' if automatic else ''

    prefix_str = '\n\n'.join(
        '# Prefix: %s\n%s%s' % (name, autostr(automatic), code.strip())
        for name, code, automatic in feature_prefixes)

    class_str = '\n\n'.join(
        '%s@%s = [ %s ];' % (autostr(automatic), name, code)
        for name, code, automatic in classes)

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
            # empty features cause makeotf to fail, but empty instructions are fine
            # so insert an empty instruction into any empty feature definitions
            lines.append(';')
        else:
            # see previous comment
            if not code:
                code = ';'
            lines.append(code)
        lines.append('} %s;' % name)
        feature_defs.append('\n'.join(lines))
    fea_str = '\n\n'.join(feature_defs)

    full_text = '\n\n'.join([prefix_str, class_str, fea_str])
    rfont.features.text = full_text if full_text.strip() else ''


def warn(message):
    print(message)
