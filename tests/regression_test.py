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


def diff_directories(dir1, dir2):
    compared = dircmp(dir1, dir2)
    report = []
    for l in compared.left_only:
        report.append("< %s" % l)
    for r in compared.right_only:
        report.append("> %s" % r)
    for f in compared.funny_files:
        report.append("? %s" % f)
    for d in compared.diff_files:
        report.append("! {} - {}".format(os.path.join(dir1, d), os.path.join(dir2, d)))
        left = open(os.path.join(dir1, d))
        right = open(os.path.join(dir2, d))
        report.append(
            "".join(difflib.unified_diff(left.readlines(), right.readlines()))
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
        report = diff_directories(tmp_dir, reference_output_dir)
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
