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
import glyphsLib
from fontTools.designspaceLib import DesignSpaceDocument
from glyphsLib.builder.instances import apply_instance_data

import pytest
import py.path
from ..test_helpers import write_designspace_and_UFOs

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.mark.parametrize(
    "instance_names",
    [None, ["Extra Light"], ["Regular", "Bold"]],
    ids=["default", "include_1", "include_2"],
)
def test_apply_instance_data(tmpdir, instance_names, ufo_module):
    font = glyphsLib.GSFont(os.path.join(DATA, "GlyphsUnitTestSans.glyphs"))
    instance_dir = "instances"
    designspace = glyphsLib.to_designspace(font, instance_dir=instance_dir)
    path = str(tmpdir / (font.familyName + ".designspace"))
    write_designspace_and_UFOs(designspace, path)

    test_designspace = DesignSpaceDocument()
    test_designspace.read(designspace.path)
    if instance_names is None:
        # Collect all instances.
        test_instances = [instance.filename for instance in test_designspace.instances]
    else:
        # Collect only selected instances.
        test_instances = [
            instance.filename
            for instance in test_designspace.instances
            if instance.styleName in instance_names
        ]

    # Generate dummy UFOs for collected instances so we don't actually need to
    # interpolate.
    tmpdir.mkdir(instance_dir)
    for instance in test_instances:
        ufo = ufo_module.Font()
        ufo.save(str(tmpdir / instance))

    ufos = apply_instance_data(designspace.path, include_filenames=test_instances)

    for filename in test_instances:
        assert os.path.isdir(str(tmpdir / filename))
    assert len(ufos) == len(test_instances)

    for ufo in ufos:
        assert ufo.info.openTypeOS2WeightClass in {
            100,
            200,
            300,
            400,
            500,
            700,
            900,
            357,
        }
        assert ufo.info.openTypeOS2WidthClass is None  # GlyphsUnitTestSans is wght only


def test_reexport_apply_instance_data():
    # this is for compatibility with fontmake
    # https://github.com/googlefonts/fontmake/issues/451
    from glyphsLib.interpolation import apply_instance_data as reexported

    assert reexported is apply_instance_data


def test_reencode_glyphs(tmpdir):
    data_dir = py.path.local(DATA)

    designspace_path = data_dir / "TestReencode.designspace"
    designspace_path.copy(tmpdir)

    ufo_path = data_dir / "TestReencode-Regular.ufo"
    ufo_path.copy(tmpdir.ensure_dir("TestReencode-Regular.ufo"))

    instance_dir = tmpdir.ensure_dir("instance_ufo")
    ufo_path.copy(instance_dir.ensure_dir("TestReencode-Regular.ufo"))
    ufo_path.copy(instance_dir.ensure_dir("TestReencodeUI-Regular.ufo"))

    ufos = apply_instance_data(str(tmpdir / "TestReencode.designspace"))

    assert len(ufos) == 2
    assert ufos[0]["A"].unicode == 0x0041
    assert ufos[0]["A.alt"].unicode is None
    assert ufos[0]["C"].unicode == 0x0043
    # Reencode Glyphs: A.alt=0041, C=
    assert ufos[1]["A"].unicode is None
    assert ufos[1]["A.alt"].unicode == 0x0041
    assert ufos[1]["C"].unicode is None


def test_glyphs3_names():
    file = "InstanceFamilyName-G3.glyphs"
    font = glyphsLib.GSFont(os.path.join(DATA, file))

    expected_names = {
        "familyName": [
            "MyFamily",
            "MyFamily",
            "MyFamily 12pt",
            "MyFamily 12pt",
            "MyFamily 72pt",
            "MyFamily 72pt",
        ],
        "preferredFamily": [
            "MyFamily",
            "MyFamily",
            "MyFamily",
            "Typographic MyFamily 12pt",
            "MyFamily",
            "MyFamily",
        ],
        "preferredFamilyName": [
            None,
            None,
            None,
            "Typographic MyFamily 12pt",
            None,
            None,
        ],
        "preferredSubfamilyName": [
            None,
            None,
            None,
            None,
            None,
            "Typographic Black",
        ],
        "windowsFamily": [
            "MyFamily Thin",
            "MyFamily Black",
            "MyFamily 12pt Thin",
            "MyFamily 12pt Black",
            "MyFamily 72pt Thin",
            "MyFamily 72pt Black",
        ],
        "fontName": [
            "MyFamily-Thin",
            "MyFamily-Black",
            "MyFamily12pt-Thin",
            "MyFamily12pt-Black",
            "MyFamily72pt-Thin",
            "MyFamily72pt-Black",
        ],
        "fullName": [
            "MyFamily Thin",
            "MyFamily Black",
            "MyFamily 12pt Thin",
            "MyFamily 12pt Black",
            "MyFamily 72pt Thin",
            "MyFamily 72pt Black",
        ],
    }

    for name, expected in expected_names.items():
        actual = [getattr(instance, name) for instance in font.instances]
        assert expected == actual, name


def test_glyphs3_mapping():
    font = glyphsLib.GSFont(os.path.join(DATA, "Glyphs3Instances.glyphs"))
    # Instance1: designspace 200 -> userspace 400
    # Instance2: designspace 800 -> userspace 900
    # Instance2: designspace 600 -> userspace 650
    doc = glyphsLib.to_designspace(font)
    assert doc.axes[0].map == [(400, 200), (600, 650), (900, 800)]
    assert doc.instances[0].location == {"Weight": 200}
    assert doc.instances[1].location == {"Weight": 800}
    assert doc.instances[2].location == {"Weight": 650}


def test_glyphs3_instance_filtering():
    font = glyphsLib.GSFont(os.path.join(DATA, "InstanceFamilyName-G3.glyphs"))
    assert len(font.instances) == 6

    # Loaded from default font family name
    assert not font.instances[0].properties
    assert not font.instances[1].properties
    assert font.instances[0].familyName == "MyFamily"
    assert font.instances[1].familyName == "MyFamily"

    # Loaded from .properties
    assert font.instances[2].familyName == "MyFamily 12pt"
    assert font.instances[3].familyName == "MyFamily 12pt"
    assert font.instances[4].familyName == "MyFamily 72pt"
    assert font.instances[5].familyName == "MyFamily 72pt"

    doc = glyphsLib.to_designspace(font)
    assert len(doc.instances) == 6

    doc = glyphsLib.to_designspace(font, family_name="MyFamily 12pt")
    assert len(doc.instances) == 2


def test_glyphs3_instance_properties(tmpdir):
    expected_num_properties = [0, 0, 1, 2, 1, 2]

    file = "InstanceFamilyName-G3.glyphs"
    font = glyphsLib.GSFont(os.path.join(DATA, file))

    for expected, instance in zip(expected_num_properties, font.instances):
        assert expected == len(instance.properties)

    font.save(tmpdir / file)
    font = glyphsLib.GSFont(tmpdir / file)

    for expected, instance in zip(expected_num_properties, font.instances):
        assert expected == len(instance.properties)


def test_rename_glyphs(tmpdir):
    font = glyphsLib.GSFont(os.path.join(DATA, "RenameGlyphsTest.glyphs"))
    instance_dir = tmpdir.ensure_dir("instance_ufo")
    designspace = glyphsLib.to_designspace(font, instance_dir=instance_dir)
    path = str(tmpdir / (font.familyName + ".designspace"))
    write_designspace_and_UFOs(designspace, path)

    ufo_path = tmpdir / "RenameGlyphsTest-Regular.ufo"
    ufo_path.copy(instance_dir.ensure_dir("RenameGlyphsTest-Straight.ufo"))
    ufo_path.copy(instance_dir.ensure_dir("RenameGlyphsTest-Swapped.ufo"))

    ufos = apply_instance_data(designspace.path)

    assert len(ufos) == 2

    assert len(ufos[0]["a"][0]) == 4  # Square
    assert len(ufos[0]["b"][0]) == 12  # Circle
    assert ufos[0]["a"].unicode == 0x0061
    assert ufos[0]["b"].unicode == 0x0062

    assert len(ufos[1]["a"][0]) == 12  # Circle
    assert len(ufos[1]["b"][0]) == 4  # Square
    assert ufos[0]["a"].unicode == 0x0061
    assert ufos[0]["b"].unicode == 0x0062


def test_expand_instance_naming_tokens(ufo_module):
    from glyphsLib.builder.instances import expand_text_tokens
    from glyphsLib.builder.constants import PROPERTIES_KEY

    font = glyphsLib.GSFont()
    font.familyName = "Test"
    font.copyright = "Some rights"
    master = glyphsLib.GSFontMaster()
    master.id = "m01"
    font.masters.append(master)
    instance = glyphsLib.GSInstance()
    instance.name = "Bold"
    font.instances = [instance]

    assert expand_text_tokens("{{{familyName}}}-{{{name}}}", instance) == "Test-Bold"
    assert expand_text_tokens("{{{fullName}}}", instance) == "Test Bold"
    assert (
        expand_text_tokens("{{{familyName}}}-{{{unknownKey}}}", instance)
        == "Test-{{{unknownKey}}}"
    )
    assert expand_text_tokens("PlainName", instance) == "PlainName"
    assert expand_text_tokens(None, instance) is None
    # A font-only name (copyright) does not resolve against the instance, but
    # does resolve against the font.
    assert expand_text_tokens("{{{copyright}}}", instance) == "{{{copyright}}}"
    assert expand_text_tokens("{{{copyright}}}", font) == "Some rights"

    # End to end: tokens are expanded in the PostScript name, in the other
    # instance name properties, and in the font-level names.
    instance.customParameters["postscriptFontName"] = "{{{familyName}}}-{{{name}}}"
    instance.properties["preferredFamilyNames"] = "{{{familyName}}} Text"
    font.copyright = "(c) {{{familyName}}}"

    designspace = glyphsLib.to_designspace(font, ufo_module=ufo_module)
    ds_instance = designspace.instances[0]
    assert ds_instance.postScriptFontName == "Test-Bold"
    assert dict(ds_instance.lib[PROPERTIES_KEY])["preferredFamilyNames"] == "Test Text"
    assert designspace.sources[0].font.info.copyright == "(c) Test"


def _token_test_font(family_name="Test", instance_name="Bold"):
    """Minimal one-master, one-instance font with parent links set."""
    font = glyphsLib.GSFont()
    font.familyName = family_name
    master = glyphsLib.GSFontMaster()
    master.id = "m01"
    font.masters.append(master)
    instance = glyphsLib.GSInstance()
    instance.name = instance_name
    font.instances = [instance]
    return font, instance


def test_expand_font_level_name_properties(ufo_module):
    font, _instance = _token_test_font("PropOnly", "Regular")
    font.copyright = "(c) {{{familyName}}}"
    font.properties["trademarks"] = "TM {{{familyName}}}"
    font.properties["descriptions"] = "Desc {{{familyName}}}"
    font.properties["licenses"] = "Lic {{{familyName}}}"
    font.properties["sampleTexts"] = "Sample {{{familyName}}}"
    font.properties["versionString"] = "Version {{{familyName}}}"
    font.properties["manufacturers"] = "Mfg {{{familyName}}}"
    font.properties["designers"] = "Des {{{familyName}}}"

    designspace = glyphsLib.to_designspace(font, ufo_module=ufo_module)
    info = designspace.sources[0].font.info

    assert info.copyright == "(c) PropOnly"
    assert info.trademark == "TM PropOnly"
    assert info.openTypeNameDescription == "Desc PropOnly"
    assert info.openTypeNameLicense == "Lic PropOnly"
    assert info.openTypeNameSampleText == "Sample PropOnly"
    assert info.openTypeNameVersion == "Version PropOnly"
    assert info.openTypeNameManufacturer == "Mfg PropOnly"
    assert info.openTypeNameDesigner == "Des PropOnly"


def test_expand_font_and_instance_custom_parameter_names(ufo_module):
    from glyphsLib.builder.constants import CUSTOM_PARAMETERS_KEY
    from glyphsLib.builder.instances import apply_instance_data_to_ufo

    font, instance = _token_test_font("CpOnly", "Bold")
    font.copyright = "(c) {{{familyName}}}"
    font.customParameters["versionString"] = "CPVer {{{familyName}}}"
    font.customParameters["trademark"] = "CPFontTM {{{familyName}}}"
    font.customParameters["description"] = "CPDesc {{{familyName}}}"
    font.customParameters["license"] = "CPLic {{{familyName}}}"
    font.customParameters["sampleText"] = "CPSample {{{familyName}}}"

    instance.customParameters["postscriptFontName"] = "{{{familyName}}}-{{{name}}}"
    instance.customParameters["preferredFamilyName"] = "CP {{{familyName}}}"
    instance.customParameters["postscriptFullName"] = "CPFull {{{familyName}}}"
    instance.customParameters["trademark"] = "CPTM {{{familyName}}}"

    designspace = glyphsLib.to_designspace(font, ufo_module=ufo_module)
    info = designspace.sources[0].font.info
    assert info.copyright == "(c) CpOnly"
    assert info.openTypeNameVersion == "CPVer CpOnly"
    assert info.trademark == "CPFontTM CpOnly"
    assert info.openTypeNameDescription == "CPDesc CpOnly"
    assert info.openTypeNameLicense == "CPLic CpOnly"
    assert info.openTypeNameSampleText == "CPSample CpOnly"

    ds_instance = designspace.instances[0]
    assert ds_instance.postScriptFontName == "CpOnly-Bold"
    # Tokens must be expanded in Designspace custom parameters as well.
    cps = dict(ds_instance.lib.get(CUSTOM_PARAMETERS_KEY) or [])
    assert cps.get("preferredFamilyName") == "CP CpOnly"
    assert cps.get("postscriptFullName") == "CPFull CpOnly"
    assert cps.get("trademark") == "CPTM CpOnly"

    ufo = ufo_module.Font()
    apply_instance_data_to_ufo(ufo, ds_instance, designspace)
    assert ufo.info.openTypeNamePreferredFamilyName == "CP CpOnly"
    assert ufo.info.postscriptFullName == "CPFull CpOnly"
    assert ufo.info.trademark == "CPTM CpOnly"


def test_expand_variable_instance_naming_tokens(ufo_module):
    from glyphsLib.classes import InstanceType

    font = glyphsLib.GSFont()
    font.familyName = "VFBase"
    master = glyphsLib.GSFontMaster()
    master.id = "m01"
    font.masters.append(master)

    variable = glyphsLib.GSInstance()
    variable.name = "Regular"
    variable.type = InstanceType.VARIABLE
    variable.properties["postscriptFontName"] = "{{{familyName}}}VF"
    variable.properties["preferredFamilyNames"] = "{{{familyName}}} Pref"

    static = glyphsLib.GSInstance()
    static.name = "Bold"
    static.properties["postscriptFontName"] = "{{{familyName}}}-{{{name}}}"

    font.instances = [variable, static]

    designspace = glyphsLib.to_designspace(font, ufo_module=ufo_module)

    assert len(designspace.variableFonts) == 1
    info = designspace.variableFonts[0].lib["public.fontInfo"]
    assert info.get("postscriptFontName") == "VFBaseVF"
    assert info.get("openTypeNamePreferredFamilyName") == "VFBase Pref"

    # Static sibling on the same file still expands.
    assert designspace.instances[0].postScriptFontName == "VFBase-Bold"


def test_expand_font_level_tokens_in_instance_context(ufo_module):
    from glyphsLib.builder.instances import apply_instance_data_to_ufo

    font, instance = _token_test_font("Acme", "Bold")
    instance.properties["familyNames"] = "Other"
    font.copyright = "(c) {{{familyName}}}"
    font.properties["trademarks"] = "TM {{{familyName}}}"
    font.properties["descriptions"] = "Desc {{{familyName}}}"
    font.properties["licenses"] = "Lic {{{familyName}}}"
    font.properties["sampleTexts"] = "Sample {{{familyName}}}"
    font.properties["versionString"] = "Version {{{familyName}}}"
    font.properties["manufacturers"] = "Mfg {{{familyName}}}"
    font.properties["designers"] = "Des {{{familyName}}}"

    designspace = glyphsLib.to_designspace(font, ufo_module=ufo_module)
    ds_instance = designspace.instances[0]
    assert ds_instance.familyName == "Other"

    ufo = ufo_module.Font()
    master_info = designspace.sources[0].font.info
    for attr in (
        "copyright",
        "trademark",
        "openTypeNameDescription",
        "openTypeNameLicense",
        "openTypeNameSampleText",
        "openTypeNameVersion",
        "openTypeNameManufacturer",
        "openTypeNameDesigner",
        "familyName",
        "styleName",
    ):
        value = getattr(master_info, attr, None)
        if value is not None:
            setattr(ufo.info, attr, value)

    apply_instance_data_to_ufo(ufo, ds_instance, designspace)
    if ds_instance.familyName is not None:
        ufo.info.familyName = ds_instance.familyName
    if ds_instance.styleName is not None:
        ufo.info.styleName = ds_instance.styleName

    assert ufo.info.familyName == "Other"
    assert ufo.info.copyright == "(c) Other"
    assert ufo.info.trademark == "TM Other"
    assert ufo.info.openTypeNameDescription == "Desc Other"
    assert ufo.info.openTypeNameLicense == "Lic Other"
    assert ufo.info.openTypeNameSampleText == "Sample Other"
    assert ufo.info.openTypeNameVersion == "Version Other"
    assert ufo.info.openTypeNameManufacturer == "Mfg Other"
    assert ufo.info.openTypeNameDesigner == "Des Other"
