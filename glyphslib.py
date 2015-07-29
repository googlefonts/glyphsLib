#!/usr/bin/python

__all__ = [
    "load_to_rfonts", "build_instances", "load", "loads",
]

import json
import os
import sys

from fontbuild.convertCurves import glyphCurvesToQuadratic
from fontbuild.outlineTTF import OutlineTTFCompiler

from parser import Parser
from casting import cast_data, cast_noto_data
from torf import to_robofab, clear_data, set_redundant_data, build_family_name
from torf import build_postscript_name, build_style_map_style


def load(fp, dict_type=dict):
	"""Read a .glyphs file. 'fp' should be (readable) file object.
	Return the unpacked root object (which usually is a dictionary).
	"""
	return loads(fp.read(), dict_type=dict_type)


def loads(value, dict_type=dict):
	"""Read a .glyphs file from a bytes object.
	Return the unpacked root object (which usually is a dictionary).
	"""
	p = Parser(dict_type=dict_type)
	print '>>> Parsing .glyphs file'
	data = p.parse(value)
	print '>>> Casting parsed values'
	cast_data(data)
	cast_noto_data(data)
	return data


def load_to_rfonts(filename):
    """Load an unpacked .glyphs object to a RoboFab RFont."""
    data = load(open(filename, 'rb'))
    print '>>> Loading to RFonts'
    return to_robofab(data, include_instances=True)
    #return to_robofab(data, debug=True)


def save_ufo(font):
    """Save an RFont as a UFO."""
    ofile = os.path.join('master_ufo', font.info.postscriptFullName + '.ufo')
    print '>>> Compiling %s' % ofile
    font.save(ofile)


def save_ttf(font):
    """Save an RFont as a TTF."""
    ofile = font.info.postscriptFullName + '.ttf'
    print '>>> Compiling %s' % ofile
    for glyph in font:
        glyphCurvesToQuadratic(glyph)
    compiler = OutlineTTFCompiler(font, ofile)
    compiler.compile()


def build_instances(rfonts, instances):
    """Create MutatorMath designspace and generate instances."""

    from mutatorMath.ufo import build
    from mutatorMath.ufo.document import DesignSpaceDocumentWriter
    from robofab.world import OpenFont

    xml_path = 'tmp.designspace'
    writer = DesignSpaceDocumentWriter(xml_path)
    family_name = ''

    for font in rfonts:
        save_ufo(font)
        cur_family_name = font.info.familyName
        if cur_family_name in family_name or not family_name:
            family_name = cur_family_name
        elif family_name not in cur_family_name:
            raise ValueError('Inconsistent family names for masters')
        writer.addSource(
            path=font.path,
            name='%s %s' % (font.info.familyName, font.info.styleName),
            location={'weight': font.lib['com.google.glyphs2ufo.weightValue'],
                      'width': font.lib['com.google.glyphs2ufo.widthValue']})

    ofiles = []
    for instance in instances:
        cur_family_name = build_family_name(family_name, instance, 'widthClass')
        style_name = instance.pop('weightClass', 'Regular')
        ps_name = build_postscript_name(cur_family_name, style_name)
        cur_path = os.path.join('ufo', ps_name + '.ufo')
        ofiles.append((cur_path, instance['customParameters']))
        writer.startInstance(
            name=instance.pop('name'),
            location={'weight': instance.pop('interpolationWeight'),
                      'width': instance.pop('interpolationWidth')},
            familyName=cur_family_name,
            styleName=style_name,
            fileName=cur_path)
        writer.writeInfo()
        writer.writeKerning()
        writer.endInstance()

    writer.save()
    print '>>> Building instances'
    build(xml_path)

    for ofile, custom_params in ofiles:
        rfont = OpenFont(ofile)
        for param in custom_params:
            if param.pop('name') == 'panose':
                rfont.info.openTypeOS2Panose = map(int, param.pop('value'))
        set_redundant_data(rfont)
        save_ttf(rfont)

    return clear_data(instances)


def main(argv):
    #print json.dumps(load(open(sys.argv[1], 'rb')), indent=2, sort_keys=True)
    rfonts, instances = load_to_rfonts(sys.argv[1])
    data = build_instances(rfonts, instances)
    print 'unloaded:', json.dumps(data, indent=2)


if __name__ == '__main__':
    main(sys.argv)
