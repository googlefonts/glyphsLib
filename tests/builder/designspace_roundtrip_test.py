#
# Copyright 2017 Google Inc. All Rights Reserved.
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


from fontTools import designspaceLib

from glyphsLib import to_glyphs, to_designspace


def test_default_master_roundtrips(ufo_module):
    """This test comes from a common scenario while using glyphsLib to go
    back and forth several times with "minimize diffs" in both directions.
    In the end we get UFOs that have information as below, and there was
    a bug that turned "Regular" into "Normal" and changed the default axis
    value.
    """
    thin = ufo_module.Font()
    thin.info.familyName = "CustomFont"
    thin.info.styleName = "Thin"
    thin.lib["com.schriftgestaltung.customParameter.GSFont.Axes"] = [
        {"Name": "Weight", "Tag": "wght"}
    ]
    regular = ufo_module.Font()
    regular.info.familyName = "CustomFont"
    regular.info.styleName = "Regular"
    regular.lib["com.schriftgestaltung.customParameter.GSFont.Axes"] = [
        {"Name": "Weight", "Tag": "wght"}
    ]

    ds = designspaceLib.DesignSpaceDocument()
    weight = ds.newAxisDescriptor()
    weight.tag = "wght"
    weight.name = "Weight"
    weight.minimum = 300
    weight.maximum = 700
    weight.default = 400
    weight.map = [(300, 58), (400, 85), (700, 145)]
    ds.addAxis(weight)

    thinSource = ds.newSourceDescriptor()
    thinSource.font = thin
    thinSource.location = {"Weight": 58}
    thinSource.familyName = "CustomFont"
    thinSource.styleName = "Thin"
    ds.addSource(thinSource)
    regularSource = ds.newSourceDescriptor()
    regularSource.font = regular
    regularSource.location = {"Weight": 85}
    regularSource.familyName = "CustomFont"
    regularSource.styleName = "Regular"
    regularSource.copyFeatures = True
    regularSource.copyGroups = True
    regularSource.copyInfo = True
    regularSource.copyLib = True
    ds.addSource(regularSource)

    font = to_glyphs(ds, minimize_ufo_diffs=True)
    doc = to_designspace(font, minimize_glyphs_diffs=True, ufo_module=ufo_module)

    reg = doc.sources[1]
    assert reg.styleName == "Regular"
    assert reg.font.info.styleName == "Regular"
    assert reg.copyFeatures is True
    assert reg.copyGroups is True
    assert reg.copyInfo is True
    assert reg.copyLib is True
