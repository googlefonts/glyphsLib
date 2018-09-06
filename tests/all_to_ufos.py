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

import argparse
import os

import glyphsLib


def glyphs_files(directory):
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".glyphs"):
                yield os.path.join(root, filename)


def main():
    parser = argparse.ArgumentParser(
        "Translate all .glyphs files into UFO+designspace in the specified directories."
    )
    parser.add_argument(
        "-o", "--out", metavar="OUTPUT_DIR", default="ufos", help="Output directory"
    )
    parser.add_argument("directories", nargs="*")
    args = parser.parse_args()

    for directory in args.directories:
        files = glyphs_files(directory)
        for filename in files:
            try:
                # Code for glyphsLib with roundtrip
                from glyphsLib.builder import to_designspace

                font = glyphsLib.GSFont(filename)
                designspace = to_designspace(font)
                dsname = font.familyName.replace(" ", "") + ".designspace"
                designspace.write(os.path.join(args.out, dsname))
            except ImportError:
                # This is the version that works with glyphsLib 2.1.0
                glyphsLib.build_masters(
                    filename, master_dir=args.out, designspace_instance_dir=args.out
                )


if __name__ == "__main__":
    main()
