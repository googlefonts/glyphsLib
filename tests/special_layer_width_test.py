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

from glyphsLib import load_to_ufos, GSFont, to_designspace


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


def test_intermediate_layer_width_with_metrics_source_on_parent():
    """This checks that "intermediate layers", a.k.a. "brace layers", do not
    incorrectly inherit an irrelevant width from their parent layer.

    Scenario in the test file:

    - Glyph /a
        - Regular (400, 0): advance width = 100
            - Intermediate layer {500, 0}: advance width = 200
        - Bold (700, 0): advance width = 300
        - Regular ROUND (400, 1); advance width = 100
            * This master layer has a "metricsSource" pointing to Regular (400, 0)
              to ensure the widths are consistent.
            - Intermediate layer {500, 1}: advance width = 200
                * This intermediate layer is under consideration for the test.
        - Bold ROUND (700, 1): advance width = 300

    Previously, the advance width of the intermediate layer `{500, 1}` would be
    forcibly taken from the `metricsSource` of the master layer `Regular ROUND
    (400, 1)` to which the intermediate layer `{500, 1}` was attached, and so it
    would get 100 instead of 200.

    With this patch, the advance width of the layer `{500, 1}` will not be
    changed, because the the layer `{500, 1}` does not define itself a
    `metricsSource`.

    See https://github.com/googlefonts/glyphsLib/pull/985
    """
    test_path = os.path.join(
        os.path.dirname(__file__), "data", "IntermediateLayerWidth.glyphs"
    )
    font = GSFont(test_path)
    doc = to_designspace(font)
    for intermediate_round in doc.sources:
        if intermediate_round.getFullDesignLocation(doc) == {"Weight": 500, "ROUND": 1}:
            break
    else:
        raise AssertionError("Can't find intermediate layer in the desigspace")
    assert (
        intermediate_round.font.layers[intermediate_round.layerName]["a"].width == 200
    )
