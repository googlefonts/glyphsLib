__all__ = [
    'to_robofab'
]


from robofab.world import RFont


def to_robofab(data):
    """Take .glyphs file data and load it into RFonts.

    Takes in data as a dictionary structured according to
    https://github.com/schriftgestalt/GlyphsSDK/blob/master/GlyphsFileFormat.md
    and returns a list of RFonts, one per master.
    """

    feature_prefixes = [f['code'] for f in data['featurePrefixes']]
    classes = [(c['name'], c['code']) for c in data['classes']]
    features = [(f['name'], f['code']) for f in data['features']]
    kerning_groups = {}

    #TODO(jamesgk) maybe create one font at a time to reduce memory usage
    rfonts = generate_base_fonts(data)

    for glyph in data['glyphs']:
        add_glyph_to_groups(kerning_groups, glyph)

        for layer in glyph['layers']:
            try:
                rfont = rfonts[layer['layerId']]
            except KeyError:
                print 'Odd data, layer with id', layer['layerId']
                continue

            style_name = layer['name']
            if rfont.info.styleName:
                assert rfont.info.styleName == style_name, ('Inconsistent '
                    'layer id/name pairs between glyphs')
            else:
                rfont.info.styleName = style_name

            rglyph = rfont.newGlyph(glyph['glyphname'])
            rglyph.unicode = glyph.get('unicode')
            load_glyph(rglyph, layer)

    for master_id, kerning in data['kerning'].items():
        load_kerning(rfonts[master_id].kerning, kerning)

    result = []
    for rfont in rfonts.values():
        add_features_to_rfont(rfont, feature_prefixes, classes, features)
        add_groups_to_rfont(rfont, kerning_groups)

        style_code = 0
        style_map = ['regular', 'bold', 'italic', 'bold italic']
        style_name = rfont.info.styleName.lower()
        if 'bold' in style_name or 'black' in style_name:
            style_code += 1
        if 'italic' in style_name:
            style_code += 2
        rfont.info.styleMapStyleName = style_map[style_code]

        rfont.info.postscriptFullName = (
            '%s-%s' % (rfont.info.familyName.replace(' ', ''),
                       rfont.info.styleName.replace(' ', '')))
        rfont.info.openTypeNameUniqueID += rfont.info.styleName
        rfont.info.openTypeNamePreferredSubfamilyName = rfont.info.styleName
        result.append(rfont)
    return result


def generate_base_fonts(data):
    """Generate a list of RFonts with metadata loaded from .glyphs data."""

    copyright = data['copyright']
    date_created = data['date'].strftime('%Y/%m/%d %H:%M:%S')
    designer = data['designer']
    designer_url = data['designerURL']
    family_name = data['familyName']
    manufacturer = data['manufacturer']
    manufacturer_url = data['manufacturerURL']
    unique_id = '%s - %s ' % (manufacturer, family_name)
    units_per_em = data['unitsPerEm']
    version_major = data['versionMajor']
    version_minor = data['versionMinor']
    version_string = 'Version %s.%s' % (version_major, version_minor)

    custom_params = dict(
        (p['name'], p['value']) for p in data['customParameters'])
    trademark = custom_params.get('trademark')
    license = custom_params.get('openTypeNameLicense')
    license_url = custom_params.get('openTypeNameLicenseURL')

    rfonts = {}
    for master in data['fontMaster']:
        rfont = RFont()

        rfont.info.copyright = copyright
        rfont.info.openTypeNameDesigner = designer
        rfont.info.openTypeNameDesignerURL = designer_url
        rfont.info.openTypeNameUniqueID = unique_id
        rfont.info.familyName = rfont.info.styleMapFamilyName = family_name
        rfont.info.openTypeNameManufacturer = manufacturer
        rfont.info.openTypeNameManufacturerURL = manufacturer_url
        rfont.info.openTypeHeadCreated = date_created
        rfont.info.unitsPerEm = units_per_em
        rfont.info.versionMajor = version_major
        rfont.info.versionMinor = version_minor
        rfont.info.openTypeNameVersion = version_string

        rfont.info.trademark = trademark
        rfont.info.openTypeNameLicense = license
        rfont.info.openTypeNameLicenseURL = license_url

        rfont.info.openTypeNamePreferredFamilyName = family_name

        rfont.info.ascender = master['ascender']
        rfont.info.capHeight = master['capHeight']
        rfont.info.descender = master['descender']
        rfont.info.postscriptStemSnapH = master['horizontalStems']
        rfont.info.postscriptStemSnapV = master['verticalStems']
        rfont.info.xHeight = master['xHeight']

        rfonts[master['id']] = rfont

    return rfonts


def load_kerning(rkerning, glyphs_kerning):
    """Add .glyphs kerning to an RKerning object."""

    for left, pairs in glyphs_kerning.items():
        for right, kerning_val in pairs.items():
            rkerning[left, right] = kerning_val


def load_glyph(glyph, layer):
    """Add .glyphs paths, components, and anchors as applicable to an RGlyph."""

    pen = glyph.getPointPen()
    draw_paths(pen, layer.get('paths', []))
    draw_components(pen, layer.get('components', []))
    add_anchors_to_glyph(glyph, layer.get('anchors', []))
    glyph.width = layer['width']


def draw_paths(pen, paths):
    """Draw .glyphs paths onto a pen."""

    for path in paths:
        pen.beginPath()
        if not 'closed' in path:
            x, y, node_type, smooth = path['nodes'][0]
            assert node_type == 'LINE', 'Open path starts with off-curve points'
            pen.addPoint((x, y), 'move')
            path['nodes'] = path['nodes'][1:]
        for x, y, node_type, smooth in path['nodes']:
            node_type = node_type.lower()
            if node_type not in ['line', 'curve']:
                node_type = None
            pen.addPoint((x, y), node_type, smooth)
        pen.endPath()


def draw_components(pen, components):
    """Draw .glyphs components onto a pen, adding them to the parent RGlyph."""

    for component in components:
        pen.addComponent(component['name'],
                         component.get('transform', (1, 0, 0, 1, 0, 0)))


def add_anchors_to_glyph(glyph, anchors):
    """Add .glyphs anchors to an RGlyph."""

    for anchor in anchors:
        glyph.appendAnchor(anchor['name'], anchor['position'])


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
        group = '@MMK_%s_%s' % (side, glyph_data[group_key])
        kerning_groups[group] = kerning_groups.get(group, []) + [glyph_name]


def add_groups_to_rfont(rfont, kerning_groups):
    """Add kerning groups to an RFont."""

    for name, glyphs in kerning_groups.items():
        rfont.groups[name] = glyphs


def add_features_to_rfont(rfont, feature_prefixes, classes, features):
    """Write an RFont's OpenType feature file."""

    text = ''
    for feature_prefix in feature_prefixes:
        text += feature_prefix + '\n'
    text += '\n'
    for class_info in classes:
        text += '@%s = [%s];\n' % class_info
    text += '\n'
    for name, code in features:
        # empty features cause makeotf to fail, but empty instructions are fine
        # so insert an empty instruction into any empty feature definitions
        if not code.strip():
            code = ';'
        text += 'feature %s {\n%s\n} %s;\n\n' % (name, code, name)
    rfont.features.text = text
