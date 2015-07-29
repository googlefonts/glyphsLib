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
from torf import build_postscript_name


def build_instances(rfonts, instances):
    """Create MutatorMath designspace and generate instances."""

    for font in rfonts:
        font.save(os.path.join(
            'master_ufo', font.info.postscriptFullName + '.ufo'))

    xml_path = 'tmp.designspace'
    writer = DesignSpaceDocumentWriter(xml_path)
    base_family = add_masters_to_writer(writer, rfonts)
    ofiles = add_instances_to_writer(writer, base_family, instances)
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

    base_family = ''
    for font in rfonts:

        cur_family = font.info.familyName
        if cur_family in base_family or not base_family:
            base_family = cur_family
        elif base_family not in cur_family:
            raise ValueError('Inconsistent family names for masters')

        writer.addSource(
            path=font.path,
            name='%s %s' % (cur_family, font.info.styleName),
            location={'weight': font.lib['com.google.glyphs2ufo.weightValue'],
                      'width': font.lib['com.google.glyphs2ufo.widthValue']})

    return base_family


def add_instances_to_writer(writer, base_family, instances):
    """Add instances from Glyphs data to a MutatorMath document writer.

    Returns a list of <ufo_path, custom_font_data> pairs, corresponding to the
    instances which will be output by the document writer. The custom font data
    is Glyphs customParameters data (a list of <attr_name, value> pairs)."""

    ofiles = []
    for instance in instances:

        family_name = build_family_name(base_family, instance, 'widthClass')
        style_name = instance.pop('weightClass', 'Regular')
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
