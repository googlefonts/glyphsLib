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

import sys
from setuptools import setup, find_packages


needs_pytest = {"pytest", "test"}.intersection(sys.argv)
pytest_runner = ["pytest_runner"] if needs_pytest else []
needs_wheel = {"bdist_wheel"}.intersection(sys.argv)
wheel = ["wheel"] if needs_wheel else []

with open("README.rst", "r") as f:
    long_description = f.read()

test_requires = ["pytest>=2.8", "ufoNormalizer>=0.3.2"]
if sys.version_info < (3, 3):
    test_requires.append("mock>=2.0.0")

setup(
    name="glyphsLib",
    use_scm_version={"write_to": "Lib/glyphsLib/_version.py"},
    author="James Godfrey-Kittle",
    author_email="jamesgk@google.com",
    description="A bridge from Glyphs source files (.glyphs) to UFOs",
    long_description=long_description,
    url="https://github.com/googlei18n/glyphsLib",
    license="Apache Software License 2.0",
    package_dir={"": "Lib"},
    packages=find_packages("Lib"),
    package_data={"glyphsLib": ["data/*.xml", "data/GlyphData_LICENSE"]},
    entry_points={
        "console_scripts": [
            "ufo2glyphs = glyphsLib.cli:_ufo2glyphs_entry_point",
            "glyphs2ufo = glyphsLib.cli:_glyphs2ufo_entry_point",
        ]
    },
    setup_requires=pytest_runner + wheel + ["setuptools_scm"],
    tests_require=test_requires,
    install_requires=["fonttools>=3.24.0", "defcon>=0.3.0"],
    extras_require={"ufo_normalization": ["ufonormalizer"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Multimedia :: Graphics :: Editors :: Vector-Based",
    ],
)
