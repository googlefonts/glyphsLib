#
# Copyright 2016 Google Inc. All Rights Reserved.
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


import os

from glyphsLib import load_to_ufos


def glyphs_file_path():
    return os.path.join(os.path.dirname(__file__), "data", "SpecialLayerWidth.glyphs")


def getLayer(font, layerName):
    for layer in font.layers:
        if layerName in layer.name:
            return layer


def test_intermediate_layer_width():
    ufos = load_to_ufos(glyphs_file_path())
    assert ufos[0]["A"].width == 500
    assert getLayer(ufos[0], "{50}")["A"].width == 560  # not interpolated half-way
    assert ufos[1]["A"].width == 600


def test_substitution_layer_width():
    masters, instances = load_to_ufos(glyphs_file_path(), include_instances=True)
    assert masters[0]["B"].width == 500
    assert masters[1]["B"].width == 600
    assert masters[0]["B.BRACKET.varAlt01"].width == 510
    assert masters[1]["B.BRACKET.varAlt01"].width == 610
