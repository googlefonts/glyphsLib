#!/usr/bin/python
#
# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


__all__ = [
    "load_to_rfonts", "build_instances", "load", "loads",
]

import json
import sys

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
	cast_data(data)
	cast_noto_data(data)
	return data


def load_to_rfonts(filename, italic=False, include_instances=False,
                   debug=False):
    """Load an unpacked .glyphs object to a RoboFab RFont."""

    with open(filename, 'rb') as ifile:
        data = load(ifile)
    print '>>> Loading to RFonts'
    return to_robofab(data, italic=italic, include_instances=include_instances,
                      debug=debug)


def save_ufo(font):
    """Save an RFont as a UFO."""

    if font.path:
        print '>>> Compiling %s' % font.path
        font.save()
    else:
        ofile = font.info.postscriptFullName + '.ufo'
        print '>>> Compiling %s' % ofile
        font.save(ofile)


def save_otf(font, save_ttf=False):
    """Save an RFont as an OTF, using ufo2fdk."""

    from ufo2fdk import OTFCompiler

    ofile = font.info.postscriptFullName + '.otf'
    print '>>> Compiling ' + ofile
    compiler = OTFCompiler()
    reports = compiler.compile(font, ofile)
    print reports['makeotf']

    if 'Wrote new font file' not in reports['makeotf'] or not save_ttf:
        return

    from fontbuild.convertCurves import glyphCurvesToQuadratic
    from fontbuild.Build import saveTTF

    ttfile = ofile.replace('.otf', '.ttf')
    print '>>> Compiling ' + ttfile
    for glyph in font:
        glyphCurvesToQuadratic(glyph)
    saveTTF(font, ttfile, ofile)


def build_masters(filename, master_dir, out_dir, italic=False, debug=False):
    """Generate UFOs from the masters defined in a .glyphs file."""

    from interpolation import build_instances

    if debug:
        return load_to_rfonts(filename, italic, True, True)

    designspace_path = filename.replace('.glyphs', '.designspace')
    rfonts, instance_data = load_to_rfonts(filename, italic, True)
    new_instance_data = build_instances(rfonts, master_dir, out_dir,
                                        designspace_path, instance_data)
    return rfonts, designspace_path, new_instance_data


def main(filename, master_dir='master_ufo', out_dir='ufo', *args):
    rfonts, _, _ = build_masters(filename, master_dir, out_dir,
                                 italic=('Italic' in filename))
    for rfont in rfonts:
        save_ufo(rfont)


if __name__ == '__main__':
    main(*sys.argv[1:])
