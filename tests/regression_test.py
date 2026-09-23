import difflib
import filecmp
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest
from fontTools.designspaceLib import DesignSpaceDocument

import glyphsLib


# https://stackoverflow.com/a/24860799
class dircmp(filecmp.dircmp):
    def phase3(self):
        fcomp = filecmp.cmpfiles(
            self.left, self.right, self.common_files, shallow=False
        )
        self.same_files, self.diff_files, self.funny_files = fcomp


def diff_directories(dir1, dir2, expected_text=None):
    # Overrides apply only to files in this directory, not its subdirectories.
    expected_text = expected_text or {}
    compared = dircmp(dir1, dir2)
    report = []
    for l in compared.left_only:
        report.append("< %s" % l)
    for r in compared.right_only:
        report.append("> %s" % r)
    for f in compared.funny_files:
        report.append("? %s" % f)
    files = set(compared.diff_files) | (expected_text.keys() & set(compared.same_files))
    for d in sorted(files):
        left = expected_text[d] if d in expected_text else Path(dir1, d).read_text()
        right = Path(dir2, d).read_text()
        if d not in expected_text or left != right:
            report.append(
                "! {} - {}".format(os.path.join(dir1, d), os.path.join(dir2, d))
            )
            report.append(
                "".join(
                    difflib.unified_diff(
                        left.splitlines(keepends=True), right.splitlines(keepends=True)
                    )
                )
            )
    for subdir in compared.common_dirs:
        report.extend(
            diff_directories(os.path.join(dir1, subdir), os.path.join(dir2, subdir))
        )
    return report


def diff_files(file1, file2):
    if filecmp.cmp(file1, file2, shallow=False):
        left = Path(file1).read_text().splitlines()
        right = Path(file2).read_text().splitlines()
        return "".join(difflib.unified_diff(left, right))


TEST_FILES_GLYPHS = Path("tests/data/gf").glob("*.glyphs")
TEST_FILES_DESIGNSPACE = Path("tests/data/designspace").glob("**/*.designspace")


def lexend_arabic_expected_designspace(reference):
    # main generates the reference output at the start of the CI job. Allow
    # only the default knot introduced to survive designspace serialization.
    old_axis = (
        '    <axis tag="wght" name="Weight" minimum="300" maximum="700"'
        ' default="580.851064">\n'
        '      <map input="300" output="42"/>\n'
        '      <map input="700" output="136"/>\n'
        "    </axis>"
    )
    new_axis = old_axis.replace(
        '      <map input="700"',
        '      <map input="580.851064" output="108"/>\n      <map input="700"',
    )
    if old_axis in reference:
        return reference.replace(old_axis, new_axis, 1)
    # Once main includes the fix, the generated reference already has the knot.
    assert new_axis in reference
    return reference


@pytest.mark.parametrize("actual", ["old\n", "expected\n", "unexpected\n"])
def test_diff_directories_expected_text(tmp_path, actual):
    reference = tmp_path / "reference"
    output = tmp_path / "output"
    reference.mkdir()
    output.mkdir()
    (reference / "font.designspace").write_text("old\n")
    (output / "font.designspace").write_text(actual)
    overrides = {"font.designspace": "expected\n"}
    assert bool(diff_directories(reference, output, overrides)) == (
        actual != "expected\n"
    )

    # A permitted designspace change must not hide differences inside a UFO.
    (reference / "font.ufo").mkdir()
    (output / "font.ufo").mkdir()
    (reference / "font.ufo" / "lib.plist").write_text("old\n")
    (output / "font.ufo" / "lib.plist").write_text("unexpected\n")
    assert diff_directories(reference, output, overrides)


def test_diff_directories_preserves_line_endings(tmp_path):
    reference = tmp_path / "reference"
    output = tmp_path / "output"
    reference.mkdir()
    output.mkdir()
    (reference / "lib.plist").write_bytes(b"same\r\n")
    (output / "lib.plist").write_bytes(b"same\n")
    assert diff_directories(reference, output)


@pytest.mark.regression_test
@pytest.mark.parametrize("filename", TEST_FILES_GLYPHS, ids=lambda p: p.name)
def test_glyphs_to_designspace(filename: Path, caplog: Any) -> None:
    with tempfile.TemporaryDirectory() as outputdir:
        tmp_dir = Path(outputdir)
        ds = tmp_dir / filename.with_suffix(".designspace").name

        # Conversion can generate lots of warnings that we are not interested
        # in here and which can clog up error logs.
        with caplog.at_level(logging.ERROR):
            glyphsLib.build_masters(filename, tmp_dir, None, designspace_path=ds)

        reference_output_dir = filename.parent / filename.stem
        expected_text = {}
        if filename.name == "Lexend-Arabic.glyphs":
            expected_text[ds.name] = lexend_arabic_expected_designspace(
                (reference_output_dir / ds.name).read_text()
            )
            reloaded = DesignSpaceDocument.fromfile(ds)
            weight = next(axis for axis in reloaded.axes if axis.tag == "wght")
            assert weight.default == 580.851064
            assert dict(weight.map)[weight.default] == 108
            assert weight.map_forward(weight.default) == 108
            default = reloaded.findDefault()
            assert default is not None
            assert default.designLocation == {"Weight": 108, "Lexend": 0}

        report = diff_directories(reference_output_dir, tmp_dir, expected_text)
        if report:
            print("".join(report))
        assert not report


@pytest.mark.regression_test
@pytest.mark.parametrize("filename", TEST_FILES_DESIGNSPACE, ids=lambda p: p.name)
def test_designspace_to_glyphs(filename: Path, caplog: Any) -> None:
    with tempfile.TemporaryDirectory() as outputdir:
        ds = DesignSpaceDocument.fromfile(filename)

        # Conversion can generate lots of warnings that we are not interested
        # in here and which can clog up error logs.
        with caplog.at_level(logging.ERROR):
            glyphs = glyphsLib.to_glyphs(ds, minimize_ufo_diffs=True)

        gs = Path(outputdir) / filename.with_suffix(".glyphs").name
        glyphs.save(gs)

        report = diff_files(filename.with_suffix(".glyphs"), gs)
        if report:
            print("".join(report))
        assert not report
