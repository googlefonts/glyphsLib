from robofab.world import RFont


def to_robofab(data):
    """Take .glyphs file data and load it into RFonts.
 
    Takes in data as a dictionary structured according to
    https://github.com/schriftgestalt/GlyphsSDK/blob/master/GlyphsFileFormat.md
    and returns a list of RFonts, one per master.
    """

    copyright = data['copyright']
    date_created = data['date'].strftime('%Y/%m/%d %H:%M:%S')
    designer = data['designer']
    designer_url = data['designerURL']
    family_name = data['familyName']
    manufacturer = data['manufacturer']
    manufacturer_url = data['manufacturerURL']
    units_per_em = data['unitsPerEm']
    version_major = data['versionMajor']
    version_minor = data['versionMinor']

    feature_prefixes = [f['code'] for f in data['featurePrefixes']]
    classes = [(c['name'], c['code']) for c in data['classes']]
    features = [(f['name'], f['code']) for f in data['features']]

    #TODO(jamesgk) maybe create one font at a time to reduce memory usage
    rfonts = {}
    for master in data['fontMaster']:
        rfont = RFont()

        rfont.info.copyright = copyright
        rfont.info.openTypeNameDesigner = designer
        rfont.info.openTypeNameDesignerURL = designer_url
        rfont.info.familyName = family_name
        rfont.info.openTypeNameManufacturer = manufacturer
        rfont.info.openTypeNameManufacturerURL = manufacturer_url
        rfont.info.openTypeHeadCreated = date_created
        rfont.info.unitsPerEm = units_per_em
        rfont.into.versionMajor = version_major
        rfont.info.versionMinor = version_minor

        rfont.info.ascender = master['ascender']
        rfont.info.capHeight = master['capHeight']
        rfont.info.descender = master['descender']
        rfont.info.postscriptStemSnapH = master['horizontalStems']
        rfont.info.postscriptStemSnapV = master['verticalStems']
        rfont.info.xHeight = master['xHeight']

        rfonts[master['id']] = rfont

    for glyph in data['glyphs']:
        glyph_name = glyph['glyphname']
        glyph_unicode = glyph.get('unicode')

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

            glyph = rfont.newGlyph(glyph_name)
            if glyph_unicode:
                glyph.unicode = glyph_unicode
            to_glyph(glyph, layer)

    for master_id, kerning in data['kerning'].items():
        rfont = rfonts[master_id]
        for left, pairs in kerning.items():
            for right, kerning_val in pairs.items():
                rfont.kerning[left, right] = kerning_val

    result = []
    for rfont in rfonts.values():
        write_features(rfont, feature_prefixes, classes, features)
        rfont.info.postscriptFullName = (
            '%s-%s' % (rfont.info.familyName.replace(' ', ''),
                       rfont.info.styleName.replace(' ', '')))
        result.append(rfont)
    return result


def to_glyph(glyph, layer):
    """Add .glyphs paths, components, and anchors as applicable to an RGlyph."""

    pen = glyph.getPointPen()
    draw_paths(pen, layer.get('paths', []))
    draw_components(pen, layer.get('components', []))
    add_anchors(glyph, layer.get('anchors', []))
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


def add_anchors(glyph, anchors):
    """Add .glyphs anchors to an RGlyph."""

    for anchor in anchors:
        glyph.appendAnchor(anchor['name'], anchor['position'])


def write_features(font, feature_prefixes, classes, features):
    """Write an RFont's OpenType feature file."""

    text = ''
    for feature_prefix in feature_prefixes:
        text += feature_prefix + '\n'
    text += '\n'
    for class_info in classes:
        text += '@%s = [%s];\n' % class_info
    text += '\n'
    for name, code in features:
        text += '%s {\n%s\n} %s;\n\n' % (name, code, name)
    font.features.text = text
