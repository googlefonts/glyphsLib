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


needs_pytest = {'pytest', 'test'}.intersection(sys.argv)
pytest_runner = ['pytest_runner'] if needs_pytest else []

with open('README.rst', 'r') as f:
    long_description = f.read()

setup(
    name='glyphsLib',
    version='1.2.0',
    author="James Godfrey-Kittle",
    author_email="jamesgk@google.com",
    description="A bridge from Glyphs source files (.glyphs) to UFOs",
    long_description=long_description,
    url="https://github.com/googlei18n/glyphsLib",
    license="Apache Software License 2.0",
    package_dir={"": "Lib"},
    packages=find_packages("Lib"),
    entry_points={
        "console_scripts": [
            "glyphs2ufo = glyphsLib.__main__:main"
        ],
    },
    setup_requires=pytest_runner,
    tests_require=[
        'pytest>=2.8',
    ],
    install_requires=[
        "fonttools>=3.1.2",
        "defcon>=0.2.0",
        "MutatorMath>=2.0.0",
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        "Environment :: Console",
        "Environment :: Other Environment",
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Graphics',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
        'Topic :: Multimedia :: Graphics :: Editors :: Vector-Based',
    ],
)
