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
    return os.path.join(os.path.dirname(__file__), "data", "LinkMetrics.glyphs")


def test_link_metrics_to_master():
    ufos = load_to_ufos(glyphs_file_path())
    # M1 should be linked to M3
    M1 = ufos[1]
    M3 = ufos[3]
    assert M1.kerning == M3.kerning
    assert M1["A"].width == M3["A"].width


def test_link_metrics_to_first_master():
    ufos = load_to_ufos(glyphs_file_path())
    # M2 should be linked to M0
    M0 = ufos[0]
    M2 = ufos[2]
    assert M2.kerning == M0.kerning
    assert M2["A"].width == M0["A"].width


def test_link_metrics_to_master_missing():
    ufos = load_to_ufos(glyphs_file_path())
    # M4 should be linked to M5 which is missing, thus it has no kerning
    M4 = ufos[4]
    assert M4.kerning == {}
    assert M4["A"].width == 300
