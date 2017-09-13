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

from __future__ import print_function, division, absolute_import, unicode_literals

import sys
import argparse

import glyphsLib


description = """\n
Converts a Glyphs.app source file into UFO masters
or UFO instances and MutatorMath designspace.
"""


def parse_options(args):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--version", action="version",
                        version='glyphsLib %s' % (glyphsLib.__version__))
    parser.add_argument("-g", "--glyphs", metavar="GLYPHS", required=True,
                        help="Glyphs file to convert.")
    parser.add_argument("-m", "--masters", metavar="MASTERS",
                        default="master_ufo",
                        help="Ouput masters UFO to folder MASTERS. "
                             "(default: %(default)s)")
    parser.add_argument("-n", "--instances", metavar="INSTANCES", nargs="?",
                        const="instance_ufo", default=None,
                        help="Output and generate interpolated instances UFO "
                             "to folder INSTANCES. "
                             "(default: %(const)s)")
    parser.add_argument("-R", "--no-round", action="store_false",
                        help="Round geometry to integers")
    options = parser.parse_args(args)
    return options


def main(args=None):
    opt = parse_options(args)
    if opt.glyphs is not None:
        if opt.instances is None:
            glyphsLib.build_masters(opt.glyphs, opt.masters)
        else:
            glyphsLib.build_instances(opt.glyphs, opt.masters, opt.instances,
                                      round_geometry=opt.no_round)

if __name__ == '__main__':
    main(sys.argv[1:])
