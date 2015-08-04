#!/usr/bin/python

__all__ = [
    "load_to_rfonts", "build_instances", "load", "loads",
]

import json
import sys

from fontbuild.convertCurves import glyphCurvesToQuadratic
from fontbuild.outlineTTF import OutlineTTFCompiler

from parser import Parser
from casting import cast_data, cast_noto_data
from interpolation import build_instances
from torf import to_robofab


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


def load_to_rfonts(filename, italic):
    """Load an unpacked .glyphs object to a RoboFab RFont."""
    data = load(open(filename, 'rb'))
    print '>>> Loading to RFonts'
    return to_robofab(data, italic=italic, include_instances=True)
    #return to_robofab(data, debug=True)


def save_ufo(font):
    """Save an RFont as a UFO."""

    if font.path:
        print '>>> Compiling %s' % font.path
        font.save()
    else:
        ofile = font.info.postscriptFullName + '.ufo'
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


def main(argv):
    #print json.dumps(load(open(sys.argv[1], 'rb')), indent=2, sort_keys=True)
    filename = sys.argv[1]
    italic = 'Italic' in filename
    masters, instance_data = load_to_rfonts(filename, italic)
    instances = build_instances(masters, instance_data, italic)
    for f in instances:
        save_ufo(f)
        save_ttf(f)


if __name__ == '__main__':
    main(sys.argv)
