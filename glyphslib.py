#!/usr/bin/python

__all__ = [
    "load_to_rfonts", "build_instances", "load", "loads",
]

import json
import sys

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


def load_to_rfonts(filename):
    """Load an unpacked .glyphs object to a RoboFab RFont."""
    data = load(open(filename, 'rb'))
    print '>>> Loading to RFonts'
    return to_robofab(data, include_instances=True)
    #return to_robofab(data, debug=True)


def save_ufo(font):
    """Save an RFont as a UFO."""
    ofile = font.info.postscriptFullName + '.ufo'
    print '>>> Compiling %s' % ofile
    font.save(ofile)


def main(argv):
    #print json.dumps(load(open(sys.argv[1], 'rb')), indent=2, sort_keys=True)
    rfonts, instances = load_to_rfonts(sys.argv[1])
    data = build_instances(rfonts, instances)
    print 'unloaded:', json.dumps(data, indent=2)


if __name__ == '__main__':
    main(sys.argv)
