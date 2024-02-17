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


import os
from collections import OrderedDict

import pytest

from fontTools.designspaceLib import DesignSpaceDocument
from glyphsLib import classes
from glyphsLib.types import BinaryData
from glyphsLib.builder.constants import (
    GLYPHLIB_PREFIX,
    FONT_CUSTOM_PARAM_PREFIX,
    UFO2FT_FEATURE_WRITERS_KEY,
    DEFAULT_FEATURE_WRITERS,
    GLYPHS_MATH_CONSTANTS_KEY,
    GLYPHS_MATH_EXTENDED_SHAPE_KEY,
    GLYPHS_MATH_VARIANTS_KEY,
)
from glyphsLib import to_glyphs, to_ufos, to_designspace


# GOAL: Test the translations between the various UFO lib and Glyphs userData.
# See the associated UML diagram: `lib_and_user_data.png`


def test_designspace_lib_equivalent_to_font_user_data(tmpdir):
    designspace = DesignSpaceDocument()
    designspace.lib["designspaceLibKey1"] = "designspaceLibValue1"

    # Save to disk and reload the designspace to test the write/read of lib
    path = os.path.join(str(tmpdir), "test.designspace")
    designspace.write(path)
    designspace = DesignSpaceDocument()
    designspace.read(path)

    font = to_glyphs(designspace)

    assert font.userData["designspaceLibKey1"] == "designspaceLibValue1"

    designspace = to_designspace(font)

    assert designspace.lib["designspaceLibKey1"] == "designspaceLibValue1"


def test_custom_featureWriters_in_designpace_lib(tmpdir, ufo_module):
    """Test that we can roundtrip custom user-defined ufo2ft featureWriters
    settings that are stored in the designspace lib or GSFont.userData.
    """
    font = classes.GSFont()
    font.masters.append(classes.GSFontMaster())
    kern = classes.GSFeature(name="kern", code="pos a b 100;")
    font.features.append(kern)
    customFeatureWriters = list(DEFAULT_FEATURE_WRITERS) + [
        {"class": "MyCustomWriter", "module": "myCustomWriter"}
    ]
    font.userData[UFO2FT_FEATURE_WRITERS_KEY] = customFeatureWriters

    designspace = to_designspace(font, ufo_module=ufo_module)
    path = str(tmpdir / "test.designspace")
    designspace.write(path)
    for source in designspace.sources:
        source.font.save(str(tmpdir / source.filename))

    designspace2 = DesignSpaceDocument.fromfile(path)

    assert UFO2FT_FEATURE_WRITERS_KEY in designspace2.lib
    assert designspace2.lib[UFO2FT_FEATURE_WRITERS_KEY] == customFeatureWriters

    font2 = to_glyphs(designspace2, ufo_module=ufo_module)

    assert len(font2.userData) == 1
    assert font2.userData[UFO2FT_FEATURE_WRITERS_KEY] == customFeatureWriters


def test_font_user_data_to_ufo_lib():
    # This happens only when not building a designspace
    # Since there is no designspace.lib to store the font userData,
    # the latter is duplicated in each output ufo
    font = classes.GSFont()
    font.masters.append(classes.GSFontMaster())
    font.masters.append(classes.GSFontMaster())
    font.userData["fontUserDataKey"] = "fontUserDataValue"

    ufo1, ufo2 = to_ufos(font)

    assert ufo1.lib[GLYPHLIB_PREFIX + "fontUserData"] == {
        "fontUserDataKey": "fontUserDataValue"
    }
    assert ufo2.lib[GLYPHLIB_PREFIX + "fontUserData"] == {
        "fontUserDataKey": "fontUserDataValue"
    }

    font = to_glyphs([ufo1, ufo2])

    assert font.userData["fontUserDataKey"] == "fontUserDataValue"


def test_DisplayStrings_ufo_lib():
    font = classes.GSFont()
    font.masters.append(classes.GSFontMaster())
    font.masters.append(classes.GSFontMaster())
    font.DisplayStrings = ""

    ufo1, ufo2 = to_ufos(font)
    assert FONT_CUSTOM_PARAM_PREFIX + "DisplayStrings" not in ufo1.lib
    assert FONT_CUSTOM_PARAM_PREFIX + "DisplayStrings" not in ufo2.lib

    font = to_glyphs([ufo1, ufo2])
    assert font.DisplayStrings == ""

    # ---
    font.DisplayStrings = "a"

    ufo1, ufo2 = to_ufos(font)
    assert ufo1.lib[FONT_CUSTOM_PARAM_PREFIX + "DisplayStrings"] == "a"
    assert ufo2.lib[FONT_CUSTOM_PARAM_PREFIX + "DisplayStrings"] == "a"

    font = to_glyphs([ufo1, ufo2])
    assert font.DisplayStrings == "a"


def test_ufo_lib_equivalent_to_font_master_user_data(ufo_module):
    ufo1 = ufo_module.Font()
    ufo1.lib["ufoLibKey1"] = "ufoLibValue1"
    ufo2 = ufo_module.Font()
    ufo2.lib["ufoLibKey2"] = "ufoLibValue2"

    font = to_glyphs([ufo1, ufo2])

    assert font.masters[0].userData["ufoLibKey1"] == "ufoLibValue1"
    assert font.masters[1].userData["ufoLibKey2"] == "ufoLibValue2"

    ufo1, ufo2 = to_ufos(font)

    assert ufo1.lib["ufoLibKey1"] == "ufoLibValue1"
    assert ufo2.lib["ufoLibKey2"] == "ufoLibValue2"
    assert "ufoLibKey2" not in ufo1.lib
    assert "ufoLibKey1" not in ufo2.lib


def test_ufo_data_into_font_master_user_data(tmpdir, ufo_module):
    filename = "org.customTool/ufoData.bin"
    data = b"\x00\x01\xFF"
    ufo = ufo_module.Font()
    ufo.data[filename] = data

    font = to_glyphs([ufo])
    # Round-trip to disk for this one because I'm not sure there are other
    # tests that read-write binary data
    path = os.path.join(str(tmpdir), "font.glyphs")
    font.save(path)
    font = classes.GSFont(path)

    # The path in the glyphs file should be os-agnostic (forward slashes)
    assert font.masters[0].userData[GLYPHLIB_PREFIX + "ufoData"] == {
        "org.customTool/ufoData.bin": BinaryData(data)
    }

    (ufo,) = to_ufos(font)

    assert ufo.data[filename] == data


def test_layer_lib_into_master_user_data(ufo_module):
    ufo1 = ufo_module.Font()
    ufo1.layers["public.default"].lib["layerLibKey1"] = "ufo1 layerLibValue1"
    layer = ufo1.newLayer("sketches")
    layer.lib["layerLibKey2"] = "ufo1 layerLibValue2"
    # layers won't roundtrip if they contain no glyph, except for the default
    layer.newGlyph("bob")
    ufo2 = ufo_module.Font()
    ufo2.layers["public.default"].lib["layerLibKey1"] = "ufo2 layerLibValue1"
    layer = ufo2.newLayer("sketches")
    layer.lib["layerLibKey2"] = "ufo2 layerLibValue2"
    layer.newGlyph("bob")

    font = to_glyphs([ufo1, ufo2])

    default_layer_key = GLYPHLIB_PREFIX + "layerLib.public.default"
    sketches_layer_key = GLYPHLIB_PREFIX + "layerLib.sketches"
    assert default_layer_key not in font.userData
    assert sketches_layer_key not in font.userData
    assert font.masters[0].userData[default_layer_key] == {
        "layerLibKey1": "ufo1 layerLibValue1"
    }
    assert font.masters[0].userData[sketches_layer_key] == {
        "layerLibKey2": "ufo1 layerLibValue2"
    }
    assert font.masters[1].userData[default_layer_key] == {
        "layerLibKey1": "ufo2 layerLibValue1"
    }
    assert font.masters[1].userData[sketches_layer_key] == {
        "layerLibKey2": "ufo2 layerLibValue2"
    }

    (ufo1, ufo2) = to_ufos(font, minimal=False)

    assert ufo1.layers["public.default"].lib["layerLibKey1"] == "ufo1 layerLibValue1"
    assert "layerLibKey1" not in ufo1.layers["sketches"].lib
    assert ufo1.layers["sketches"].lib["layerLibKey2"] == "ufo1 layerLibValue2"
    assert "layerLibKey2" not in ufo1.layers["public.default"].lib
    assert ufo2.layers["public.default"].lib["layerLibKey1"] == "ufo2 layerLibValue1"
    assert "layerLibKey1" not in ufo2.layers["sketches"].lib
    assert ufo2.layers["sketches"].lib["layerLibKey2"] == "ufo2 layerLibValue2"
    assert "layerLibKey2" not in ufo2.layers["public.default"].lib


def test_layer_lib_in_font_user_data(ufo_module):
    font = classes.GSFont()
    font.masters.append(classes.GSFontMaster())
    font.masters.append(classes.GSFontMaster())
    glyph = classes.GSGlyph(name="a")
    font.glyphs.append(glyph)
    layer = classes.GSLayer()
    layer.layerId = font.masters[0].id
    layer.width = 0
    glyph.layers.append(layer)
    layer = classes.GSLayer()
    layer.layerId = font.masters[1].id
    layer.width = 0
    glyph.layers.append(layer)

    font.userData[GLYPHLIB_PREFIX + "layerLib.public.default"] = {
        "layerLibKey": "layerLibValue"
    }

    ufo1, ufo2 = to_ufos(font)
    assert "layerLibKey" in ufo1.layers["public.default"].lib
    assert ufo1.layers["public.default"].lib["layerLibKey"] == "layerLibValue"
    assert "layerLibKey" in ufo2.layers["public.default"].lib
    assert ufo2.layers["public.default"].lib["layerLibKey"] == "layerLibValue"


def test_glyph_user_data_into_ufo_lib():
    font = classes.GSFont()
    font.masters.append(classes.GSFontMaster())
    glyph = classes.GSGlyph("a")
    glyph.userData["glyphUserDataKey"] = "glyphUserDataValue"
    font.glyphs.append(glyph)
    layer = classes.GSLayer()
    layer.layerId = font.masters[0].id
    glyph.layers.append(layer)

    (ufo,) = to_ufos(font)

    assert ufo.lib[GLYPHLIB_PREFIX + "glyphUserData.a"] == {
        "glyphUserDataKey": "glyphUserDataValue"
    }

    font = to_glyphs([ufo])

    assert font.glyphs["a"].userData["glyphUserDataKey"] == "glyphUserDataValue"


@pytest.mark.parametrize("minimal", [True, False])
def test_math_user_data_into_ufo_lib(datadir, minimal, caplog):
    font = classes.GSFont(str(datadir.join("Math.glyphs")))

    ufos = to_ufos(font, minimal=minimal)

    math_glyphs = ["parenleft", "parenright"]

    for ufo, master in zip(ufos, font.masters):
        assert ufo.lib[GLYPHS_MATH_EXTENDED_SHAPE_KEY] == math_glyphs
        assert (
            ufo.lib[GLYPHS_MATH_CONSTANTS_KEY]
            == master.userData[GLYPHS_MATH_CONSTANTS_KEY]
        )
        for name in math_glyphs:
            for key in {"vVariants", "hVariants"}:
                result = ufo[name].lib[GLYPHS_MATH_VARIANTS_KEY].get(key)
                expected = font.glyphs[name].userData[GLYPHS_MATH_VARIANTS_KEY].get(key)
                assert result == expected
            for key in {"vAssembly", "hAssembly"}:
                result = ufo[name].lib[GLYPHS_MATH_VARIANTS_KEY].get(key)
                expected = (
                    font.glyphs[name]
                    .layers[master.id]
                    .userData[GLYPHS_MATH_VARIANTS_KEY]
                    .get(key)
                )
                assert result == expected

    font2 = to_glyphs(ufos)
    assert "already has different 'vVariants'" not in caplog.text

    for master, ufo in zip(font2.masters, ufos):
        assert font2.userData[GLYPHS_MATH_EXTENDED_SHAPE_KEY] is None
        assert font2.userData[GLYPHS_MATH_CONSTANTS_KEY] is None
        assert (
            master.userData[GLYPHS_MATH_CONSTANTS_KEY]
            == ufo.lib[GLYPHS_MATH_CONSTANTS_KEY]
        )
        for name in math_glyphs:
            for key in {"vVariants", "hVariants"}:
                result = font2.glyphs[name].userData[GLYPHS_MATH_VARIANTS_KEY].get(key)
                expected = ufo[name].lib[GLYPHS_MATH_VARIANTS_KEY].get(key)
                assert result == expected
            for key in {"vAssembly", "hAssembly"}:
                result = (
                    font2.glyphs[name]
                    .layers[master.id]
                    .userData[GLYPHS_MATH_VARIANTS_KEY]
                    .get(key)
                )
                expected = ufo[name].lib[GLYPHS_MATH_VARIANTS_KEY].get(key)
                assert result == expected


@pytest.mark.parametrize("minimal", [True, False])
def test_math_user_data_into_ufo_lib_warn(datadir, minimal, caplog):
    import copy

    font = classes.GSFont(str(datadir.join("Math.glyphs")))

    ufos = to_ufos(font, minimal=minimal)
    ufos[0]["parenleft"] = copy.deepcopy(ufos[0]["parenleft"])
    ufos[0]["parenleft"].lib[GLYPHS_MATH_VARIANTS_KEY]["vVariants"].pop()

    assert (
        ufos[0]["parenleft"].lib[GLYPHS_MATH_VARIANTS_KEY]["vVariants"]
        != ufos[1]["parenleft"].lib[GLYPHS_MATH_VARIANTS_KEY]["vVariants"]
    )

    to_glyphs(ufos)

    assert any(record.levelname == "WARNING" for record in caplog.records)
    assert (
        "Glyph 'parenleft' already has different 'vVariants' in "
        "userData['com.nagwa.MATHPlugin.variants']. Overwriting it." in caplog.text
    )


def test_glif_lib_equivalent_to_layer_user_data(ufo_module):
    ufo = ufo_module.Font()
    # This glyph is in the `public.default` layer
    a = ufo.newGlyph("a")
    a.lib["glifLibKeyA"] = "glifLibValueA"
    customLayer = ufo.newLayer("middleground")
    # "a" is in both layers
    customLayer.newGlyph("a")
    # "b" is only in the second layer
    b = customLayer.newGlyph("b")
    b.lib["glifLibKeyB"] = "glifLibValueB"

    font = to_glyphs([ufo])

    for layer_id in font.glyphs["a"].layers.keys():
        layer = font.glyphs["a"].layers[layer_id]
        if layer.layerId == font.masters[0].id:
            default_layer = layer
        else:
            middleground = layer
    assert default_layer.userData["glifLibKeyA"] == "glifLibValueA"
    assert "glifLibKeyA" not in middleground.userData.keys()

    for layer_id in font.glyphs["b"].layers.keys():
        layer = font.glyphs["b"].layers[layer_id]
        if layer.layerId == font.masters[0].id:
            default_layer = layer
        else:
            middleground = layer
    assert "glifLibKeyB" not in default_layer.userData.keys()
    assert middleground.userData["glifLibKeyB"] == "glifLibValueB"

    (ufo,) = to_ufos(font, minimal=False)

    assert ufo["a"].lib["glifLibKeyA"] == "glifLibValueA"
    assert "glifLibKeyA" not in ufo.layers["middleground"]["a"]
    assert ufo.layers["middleground"]["b"].lib["glifLibKeyB"] == "glifLibValueB"


def test_node_user_data_into_glif_lib():
    font = classes.GSFont()
    master = classes.GSFontMaster()
    master.id = "M1"
    font.masters.append(master)
    glyph = classes.GSGlyph("a")
    layer = classes.GSLayer()
    layer.layerId = "M1"
    layer.associatedMasterId = "M1"
    glyph.layers.append(layer)
    font.glyphs.append(glyph)
    path = classes.GSPath()
    layer.paths.append(path)
    node1 = classes.GSNode()
    node1.userData["nodeUserDataKey1"] = "nodeUserDataValue1"
    node1.name = "node1"
    node2 = classes.GSNode()
    node2.userData["nodeUserDataKey2"] = "nodeUserDataValue2"
    node2.name = "node2"
    path.nodes.append(classes.GSNode())
    path.nodes.append(node1)
    path.nodes.append(classes.GSNode())
    path.nodes.append(classes.GSNode())
    path.nodes.append(node2)

    (ufo,) = to_ufos(font, minimize_glyphs_diffs=True)

    assert ufo["a"].lib[GLYPHLIB_PREFIX + "nodeUserData.0.1"] == {
        "nodeUserDataKey1": "nodeUserDataValue1"
    }
    assert ufo["a"][0][2].name == "node1"
    assert ufo["a"].lib[GLYPHLIB_PREFIX + "nodeUserData.0.4"] == {
        "nodeUserDataKey2": "nodeUserDataValue2"
    }
    assert ufo["a"][0][0].name == "node2"

    font = to_glyphs([ufo])

    path = font.glyphs["a"].layers["M1"].paths[0]
    assert path.nodes[1].userData["nodeUserDataKey1"] == "nodeUserDataValue1"
    assert path.nodes[1].name == "node1"
    assert path.nodes[4].userData["nodeUserDataKey2"] == "nodeUserDataValue2"
    assert path.nodes[4].name == "node2"


def test_lib_data_types(tmpdir, ufo_module):
    # Test the roundtrip of a few basic types both at the top level and in a
    # nested object.
    data = OrderedDict(
        {
            "boolean": True,
            "smooth": False,
            "integer": 1,
            "float": 0.5,
            "array": [],
            "dict": {},
        }
    )
    ufo = ufo_module.Font()
    a = ufo.newGlyph("a")
    for key, value in data.items():
        a.lib[key] = value
        a.lib["nestedDict"] = dict(data)
        a.lib["nestedArray"] = list(data.values())
        a.lib["crazyNesting"] = [{"a": [{"b": [dict(data)]}]}]

    font = to_glyphs([ufo])

    # FIXME: This test will stop working if the font is written and read back,
    # because the file format of Glyphs does not make a difference between
    # `True` (bool) and `1` (int).
    # filename = os.path.join(str(tmpdir), 'font.glyphs')
    # font.save(filename)
    # font = classes.GSFont(filename)

    (ufo,) = to_ufos(font)

    for index, (key, value) in enumerate(data.items()):
        assert value == ufo["a"].lib[key]
        assert value == ufo["a"].lib["nestedDict"][key]
        assert value == ufo["a"].lib["nestedArray"][index]
        assert value == ufo["a"].lib["crazyNesting"][0]["a"][0]["b"][0][key]
        assert type(value) is type(ufo["a"].lib[key])  # noqa: E721
        assert type(value) is type(ufo["a"].lib["nestedDict"][key])  # noqa: E721
        assert type(value) is type(ufo["a"].lib["nestedArray"][index])  # noqa: E721
        assert type(value) is type(  # noqa: E721
            ufo["a"].lib["crazyNesting"][0]["a"][0]["b"][0][key]
        )
