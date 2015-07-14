#!/usr/bin/python

__all__ = [
    "load_to_rfonts", "load", "loads",
]

import json
import sys

from fontbuild.convertCurves import glyphCurvesToQuadratic
from fontbuild.outlineTTF import OutlineTTFCompiler

from parser import Parser
from casting import cast_data, cast_noto_data
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
	data = cast_data(data)
	cast_noto_data(data)
	return data
	#return cast_data(data, print_dbg=True)


def load_to_rfonts(filename):
    """Load an unpacked .glyphs object to a RoboFab RFont."""
    data = load(open(filename, 'rb'))
    print '>>> Loading to RFonts'
    return to_robofab(data)


def main(argv):
    #print json.dumps(load(open(sys.argv[1], 'rb')), indent=2, sort_keys=True)
    rfonts = load_to_rfonts(sys.argv[1])
    for font in rfonts:
        ofile = font.info.postscriptFullName + '.ttf'
        print '>>> Compiling %s' % ofile
        for glyph in font:
            glyphCurvesToQuadratic(glyph)
        compiler = OutlineTTFCompiler(font, ofile)
        compiler.compile()


if __name__ == '__main__':
    main(sys.argv)
