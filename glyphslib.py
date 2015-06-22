#!/usr/bin/python

__all__ = [
    "load_to_rfonts", "load", "loads",
]

import json
import sys

from parser import Parser
from casting import cast_data
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
	return cast_data(p.parse(value))


def load_to_rfonts(filename):
    return to_robofab(load(open(filename, 'rb')))


def main(argv):
    rfonts = load_to_rfonts(sys.argv[1])


if __name__ == '__main__':
    main(sys.argv)
