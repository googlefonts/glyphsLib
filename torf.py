from robofab.world import RFont


def to_robofab(data):
    """Take .glyphs file data and load it into RFonts.
 
    Takes in data as a dictionary structured according to
    https://github.com/schriftgestalt/GlyphsSDK/blob/master/GlyphsFileFormat.md
    and returns a list of RFonts, one per master.
    """

    family_name = data['familyName']
    unitsPerEm = data['unitsPerEm']

    #TODO(jamesgk) maybe create one font at a time to reduce memory usage
    rfonts = {}
    for master in data['fontMaster']:
        rfont = RFont()
        rfont.info.familyName = family_name
        rfont.info.unitsPerEm = unitsPerEm
        rfont.info.ascender = master['ascender']
        rfont.info.capHeight = master['capHeight']
        rfont.info.descender = master['descender']
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
        '''
        closed = path.get('closed')
        if not closed:
            x, y, node_type, smooth = path['nodes'][0]
            assert node_type == 'LINE', 'Open path starts with off-curve points'
            pen.addPoint((x, y), 'move')
            path['nodes'] = path['nodes'][1:]
        '''
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
