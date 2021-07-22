import difflib
import filecmp
import logging
import os
import tempfile
import unittest
from pathlib import Path

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
        report.append("! %s" % d)
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
class GlyphsToDesignspace(unittest.TestCase):
    # https://stackoverflow.com/a/50375022
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    @staticmethod
    def run_test(filename: Path, caplog):
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

    @classmethod
    def add_test(cls, filename):
        def test_method(self, filename=filename):
            self.run_test(filename, self._caplog)

        file_basename = os.path.basename(filename)
        test_name = "test_{}".format(file_basename.replace(r"[^a-zA-Z]", ""))
        test_method.__name__ = test_name
        setattr(cls, test_name, test_method)


@pytest.mark.regression_test
class DesignspaceToGlyphs(unittest.TestCase):
    # https://stackoverflow.com/a/50375022
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    @staticmethod
    def run_test(filename: Path, caplog):
        filename = Path(filename)
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

    @classmethod
    def add_test(cls, filename):
        def test_method(self, filename=filename):
            self.run_test(filename, self._caplog)

        file_basename = os.path.basename(filename)
        test_name = "test_{}".format(file_basename.replace(r"[^a-zA-Z]", ""))
        test_method.__name__ = test_name
        setattr(cls, test_name, test_method)


def register_tests():
    for t in TEST_FILES_GLYPHS:
        GlyphsToDesignspace.add_test(t)
    for t in TEST_FILES_DESIGNSPACE:
        DesignspaceToGlyphs.add_test(t)


register_tests()
