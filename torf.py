__all__ = [
    'to_robofab'
]


from robofab.world import RFont


LIB_PREFIX = 'com.google.glyphs2ufo.'


def to_robofab(data, debug=False):
    """Take .glyphs file data and load it into RFonts.

    Takes in data as a dictionary structured according to
    https://github.com/schriftgestalt/GlyphsSDK/blob/master/GlyphsFileFormat.md
    and returns a list of RFonts, one per master.

    If debug is True, returns unused input data instead of the resulting RFonts.
    """

    feature_prefixes, classes, features = [], [], []
    for f in data['featurePrefixes']:
        feature_prefixes.append((f.pop('name'), f.pop('code')))
    for c in data['classes']:
        classes.append((c.pop('name'), c.pop('code'), c.pop('automatic', None)))
    for f in data['features']:
        features.append((f.pop('name'), f.pop('code'), f.pop('automatic', None),
                         f.pop('disabled', None), f.pop('notes', None)))
    kerning_groups = {}

    #TODO(jamesgk) maybe create one font at a time to reduce memory usage
    rfonts, master_id_order = generate_base_fonts(data)

    for glyph in data['glyphs']:
        add_glyph_to_groups(kerning_groups, glyph)

        # pop glyph metadata only once, i.e. not when looping through layers
        metadata_keys = ['glyphname', 'unicode', 'lastChange',
                         'leftMetricsKey', 'rightMetricsKey', 'widthMetricsKey']
        glyph_data = dict((key, glyph.pop(key, None)) for key in metadata_keys)

        for layer in glyph['layers']:
            # whichever attribute we use for layer_id, make sure they are both
            # popped from the layer data
            layer_id = layer.pop('layerId')
            layer_id = layer.pop('associatedMasterId', layer_id)
            rfont = rfonts[layer_id]

            # ensure consistency between layer ids / names
            style_name = layer.pop('name')
            if rfont.info.styleName != style_name:
                print (
                    'Inconsistent layer id/name pair: glyph "%s" layer "%s"'
                    % (glyph_data['glyphname'], style_name))
                continue

            rglyph = rfont.newGlyph(glyph_data['glyphname'])
            load_glyph(rglyph, layer, glyph_data)

    for master_id, kerning in data.pop('kerning').items():
        load_kerning(rfonts[master_id].kerning, kerning)

    result = []
    for master_id in master_id_order:
        rfont = rfonts[master_id]
        add_features_to_rfont(rfont, feature_prefixes, classes, features)
        add_groups_to_rfont(rfont, kerning_groups)
        result.append(rfont)

    if debug:
        return clear_data(data)
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


def generate_base_fonts(data):
    """Generate a list of RFonts with metadata loaded from .glyphs data."""

    copyright = data.pop('copyright')
    date_created = to_rf_time(data.pop('date'))
    designer = data.pop('designer')
    designer_url = data.pop('designerURL')
    family_name = data.pop('familyName')
    manufacturer = data.pop('manufacturer')
    manufacturer_url = data.pop('manufacturerURL')
    unique_id = '%s - %s ' % (manufacturer, family_name)
    units_per_em = data.pop('unitsPerEm')
    version_major = data.pop('versionMajor')
    version_minor = data.pop('versionMinor')
    version_string = 'Version %s.%s' % (version_major, version_minor)

    misc = ['disablesAutomaticAlignment', 'disablesNiceNames']
    custom_params = parse_custom_params(data, misc)

    rfonts = {}
    master_id_order = []
    for master in data['fontMaster']:
        rfont = RFont()

        weight = master.pop('weight', '')
        width = master.pop('width', '')
        style_name = ('%s %s' % (weight, width)).strip() or 'Regular'
        rfont.info.styleName = style_name

        rfont.info.copyright = copyright
        rfont.info.openTypeNameDesigner = designer
        rfont.info.openTypeNameDesignerURL = designer_url
        rfont.info.openTypeNameUniqueID = unique_id + style_name
        rfont.info.familyName = rfont.info.styleMapFamilyName = family_name
        rfont.info.openTypeNamePreferredFamilyName = family_name
        rfont.info.openTypeNamePreferredSubfamilyName = style_name
        rfont.info.openTypeNameManufacturer = manufacturer
        rfont.info.openTypeNameManufacturerURL = manufacturer_url
        rfont.info.openTypeHeadCreated = date_created
        rfont.info.unitsPerEm = units_per_em
        rfont.info.versionMajor = version_major
        rfont.info.versionMinor = version_minor
        rfont.info.openTypeNameVersion = version_string

        rfont.info.ascender = master.pop('ascender')
        rfont.info.capHeight = master.pop('capHeight')
        rfont.info.descender = master.pop('descender')
        rfont.info.postscriptStemSnapH = master.pop('horizontalStems')
        rfont.info.postscriptStemSnapV = master.pop('verticalStems')
        rfont.info.xHeight = master.pop('xHeight')

        rfont.info.postscriptFontName = rfont.info.postscriptFullName = (
            '%s-%s' % (family_name.replace(' ', ''),
                       style_name.replace(' ', '')))

        style_code = 0
        style_map = ['regular', 'bold', 'italic', 'bold italic']
        style_name_lower = style_name.lower()
        if 'bold' in style_name_lower or 'black' in style_name_lower:
            style_code += 1
        if 'italic' in style_name_lower:
            style_code += 2
        rfont.info.styleMapStyleName = style_map[style_code]

        misc = ['alignmentZones', 'guideLines', 'weightValue', 'widthValue']
        for name, value in custom_params + parse_custom_params(master, misc):
            if hasattr(rfont.info, name):
                setattr(rfont.info, name, value)
            elif name == 'glyphOrder':
                rfont.lib['public.glyphOrder'] = value
            else:
                rfont.lib[LIB_PREFIX + name] = value

        master_id = master.pop('id')
        master_id_order.append(master_id)
        rfonts[master_id] = rfont

    return rfonts, master_id_order


def to_rf_time(datetime_obj):
    """Format a datetime object as specified for UFOs."""
    return datetime_obj.strftime('%Y/%m/%d %H:%M:%S')


def parse_custom_params(data, misc_keys):
    """Parse customParameters and userData into a list of <name, val> pairs."""

    params = []
    for p in data.get('customParameters', []):
        params.append((p.pop('name'), p.pop('value')))
    params.extend(data.pop('userData', {}).iteritems())
    for key in misc_keys:
        try:
            val = data.pop(key)
        except KeyError:
            continue
        params.append((key, val))
    return params


def load_kerning(rkerning, kerning_data):
    """Add .glyphs kerning to an RKerning object."""

    for left, pairs in kerning_data.items():
        for right, kerning_val in pairs.items():
            rkerning[left, right] = kerning_val


def load_glyph_libdata(rglyph, layer):
    """Add to an RGlyph's lib data."""

    for key in ['annotations', 'background', 'guideLines', 'hints']:
        try:
            value = layer.pop(key)
        except KeyError:
            continue
        rglyph.lib[LIB_PREFIX + key] = value

    # data related to components stored in lists of booleans
    # each list's elements correspond to the components in order
    for key in ['disableAlignment', 'locked']:
        values = [c.pop(key, False) for c in layer.get('components', [])]
        if any(values):
            key = key[0].upper() + key[1:]
            rglyph.lib['%scomponents%s' % (LIB_PREFIX, key)] = values


def load_glyph(rglyph, layer, glyph_data):
    """Add .glyphs metadata, paths, components, and anchors to an RGlyph."""

    rglyph.unicode = glyph_data['unicode']
    rglyph.lib[LIB_PREFIX + 'lastChange'] = to_rf_time(glyph_data['lastChange'])

    for key in ['leftMetricsKey', 'rightMetricsKey', 'widthMetricsKey']:
        try:
            rglyph.lib[LIB_PREFIX + key] = layer.pop(key)
        except KeyError:
            glyph_metrics_key = glyph_data[key]
            if glyph_metrics_key:
                rglyph.lib[LIB_PREFIX + key] = glyph_metrics_key

    load_glyph_libdata(rglyph, layer)

    pen = rglyph.getPointPen()
    draw_paths(pen, layer.get('paths', []))
    draw_components(pen, layer.get('components', []))
    add_anchors_to_glyph(rglyph, layer.get('anchors', []))
    rglyph.width = layer.pop('width')


def draw_paths(pen, paths):
    """Draw .glyphs paths onto a pen."""

    for path in paths:
        pen.beginPath()
        if not path.pop('closed', False):
            x, y, node_type, smooth = path['nodes'].pop(0)
            assert node_type == 'LINE', 'Open path starts with off-curve points'
            pen.addPoint((x, y), 'move')
        for x, y, node_type, smooth in path.pop('nodes'):
            node_type = node_type.lower()
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

    prefix_str = '\n'.join('# -- name: %s\n%s' % fp for fp in feature_prefixes)

    class_defs = []
    for name, code, automatic in classes:
        if automatic:
            class_defs.append('# -- automatic --')
        class_defs.append('@%s = [%s];' % (name, code))
    class_str = '\n'.join(class_defs)

    feature_defs = []
    for name, code, automatic, disabled, notes in features:
        lines = ['feature %s {' % name]
        if notes:
            lines.append('  # -- notes: ' + notes)
        if automatic:
            lines.append('  # -- automatic --')
        if disabled:
            lines.append('  # -- disabled --')
            lines.extend('  #' + line for line in code.splitlines())
        else:
            # empty features cause makeotf to fail, but empty instructions are fine
            # so insert an empty instruction into any empty feature definitions
            if not code.strip():
                code = ';'
            lines.extend('  ' + line for line in code.splitlines())
        lines.append('} %s;' % name)
        feature_defs.append('\n'.join(lines))
    fea_str = '\n\n'.join(feature_defs)

    rfont.features.text = '\n\n'.join([
        '# -- feature prefixes --', prefix_str,
        '# -- classes --', class_str,
        '# -- feature prefixes --', fea_str])
