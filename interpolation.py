__all__ = [
    'build_instances'
]


import os

from fontbuild.convertCurves import glyphCurvesToQuadratic
from fontbuild.outlineTTF import OutlineTTFCompiler
from mutatorMath.ufo import build
from mutatorMath.ufo.document import DesignSpaceDocumentWriter
from robofab.world import OpenFont

from torf import clear_data, set_redundant_data, build_family_name
from torf import build_style_name, build_postscript_name


def build_instances(rfonts, instances, italic=False):
    """Create MutatorMath designspace and generate instances."""

    print '>>> Writing masters'
    for font in rfonts:
        font.save(os.path.join(
            'master_ufo', font.info.postscriptFullName + '.ufo'))

    xml_path = 'tmp.designspace'
    writer = DesignSpaceDocumentWriter(xml_path)
    base_family = add_masters_to_writer(writer, rfonts)
    ofiles = add_instances_to_writer(writer, base_family, instances, italic)
    writer.save()

    print '>>> Building instances'
    build(xml_path)

    for path, custom_params in ofiles:
        rfont = OpenFont(path)
        for param in custom_params:
            if param.pop('name') == 'panose':
                rfont.info.openTypeOS2Panose = map(int, param.pop('value'))
        set_redundant_data(rfont)
        save_ttf(rfont)

    return clear_data(instances)


def add_masters_to_writer(writer, rfonts):
    """Add master RFonts to a MutatorMath document writer.

    Returns the masters' base family name, as determined by taking the
    intersection of their individual family names."""

    master_data = []
    base_family = ''

    # build list of <path, family, style, weight, width> tuples for each master
    for font in rfonts:
        family, style = font.info.familyName, font.info.styleName
        if family in base_family or not base_family:
            base_family = family
        elif base_family not in family:
            raise ValueError('Inconsistent family names for masters')
        master_data.append((
            font.path, family, style,
            font.lib['com.google.glyphs2ufo.weightValue'],
            font.lib['com.google.glyphs2ufo.widthValue']))

    # add the masters to the writer in a separate loop, when we have a good
    # candidate to copy metadata from ([base_family] Regular)
    for path, family, style, weight, width in master_data:
        writer.addSource(
            path=path,
            name='%s %s' % (family, style),
            location={'weight': weight, 'width': width},
            copyInfo=(family == base_family and style == 'Regular'))

    return base_family


def add_instances_to_writer(writer, base_family, instances, italic):
    """Add instances from Glyphs data to a MutatorMath document writer.

    Returns a list of <ufo_path, custom_font_data> pairs, corresponding to the
    instances which will be output by the document writer. The custom font data
    is Glyphs customParameters data (a list of <attr_name, value> pairs)."""

    ofiles = []
    for instance in instances:

        family_name = build_family_name(base_family, instance, 'widthClass')
        style_name = build_style_name(instance, 'weightClass', italic)
        ufo_path = os.path.join(
            'ufo', build_postscript_name(family_name, style_name) + '.ufo')
        ofiles.append((ufo_path, instance['customParameters']))

        writer.startInstance(
            name=instance.pop('name'),
            location={'weight': instance.pop('interpolationWeight'),
                      'width': instance.pop('interpolationWidth')},
            familyName=family_name,
            styleName=style_name,
            fileName=ufo_path)

        writer.writeInfo()
        writer.writeKerning()
        writer.endInstance()

    return ofiles


def save_ttf(font):
    """Save an RFont as a TTF."""

    ofile = font.info.postscriptFullName + '.ttf'
    print '>>> Compiling %s' % ofile
    for glyph in font:
        glyphCurvesToQuadratic(glyph)
    compiler = OutlineTTFCompiler(font, ofile)
    compiler.compile()
