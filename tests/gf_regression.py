import sys
import glyphsLib
import glob
import os
import filecmp
import difflib
import unittest
import tempfile
import logging
from pathlib import Path

from fontTools.designspaceLib import DesignSpaceDocument


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


TEST_FILES_GLYPHS = glob.glob("tests/data/gf/*.glyphs")
TEST_FILES_DESIGNSPACE = glob.glob(
    "tests/data/designspace/**/*.designspace", recursive=True
)


def generate():
    for t in TEST_FILES_GLYPHS:
        outputdir = os.path.splitext(t)[0]
        ds = os.path.join(
            outputdir, os.path.basename(os.path.splitext(t)[0]) + ".designspace"
        )
        glyphsLib.build_masters(t, outputdir, None, designspace_path=ds)
    for t in TEST_FILES_DESIGNSPACE:
        path = Path(t)
        gs = path.with_suffix(".glyphs")
        ds = DesignSpaceDocument.fromfile(path)
        glyphs = glyphsLib.to_glyphs(ds, minimize_ufo_diffs=True)
        glyphs.save(gs)
        print(f"Saved {gs}")


class GlyphsToDesignspace(unittest.TestCase):
    @classmethod
    def run_test(cls, filename):
        with tempfile.TemporaryDirectory() as outputdir:
            ds = os.path.join(
                outputdir,
                os.path.basename(os.path.splitext(filename)[0]) + ".designspace",
            )
            glyphsLib.build_masters(filename, outputdir, None, designspace_path=ds)

            realoutputdir = os.path.splitext(filename)[0]
            report = diff_directories(outputdir, realoutputdir)
            if report:
                print("".join(report))
            assert not report

    @classmethod
    def add_test(cls, filename):
        def test_method(self, filename=filename):
            self.run_test(filename)

        file_basename = os.path.basename(filename)
        test_name = "test_{}".format(file_basename.replace(r"[^a-zA-Z]", ""))
        test_method.__name__ = test_name
        setattr(cls, test_name, test_method)


class DesignspaceToGlyphs(unittest.TestCase):
    @classmethod
    def run_test(cls, filename):
        filename = Path(filename)
        with tempfile.TemporaryDirectory() as outputdir:
            outputdir = Path(outputdir)
            ds = DesignSpaceDocument.fromfile(filename)
            glyphs = glyphsLib.to_glyphs(ds, minimize_ufo_diffs=True)
            gs = outputdir / filename.with_suffix(".glyphs").name
            glyphs.save(gs)

            report = diff_files(filename.with_suffix(".glyphs"), gs)
            if report:
                print("".join(report))
            assert not report

    @classmethod
    def add_test(cls, filename):
        def test_method(self, filename=filename):
            self.run_test(filename)

        file_basename = os.path.basename(filename)
        test_name = "test_{}".format(file_basename.replace(r"[^a-zA-Z]", ""))
        test_method.__name__ = test_name
        setattr(cls, test_name, test_method)


def register_tests():
    for t in TEST_FILES_GLYPHS:
        GlyphsToDesignspace.add_test(t)
    for t in TEST_FILES_DESIGNSPACE:
        DesignspaceToGlyphs.add_test(t)


if sys.argv[1] == "--generate":
    generate()
elif sys.argv[1] == "--test":
    import pytest

    logging.basicConfig(level=logging.ERROR)
    register_tests()
    sys.exit(pytest.main([sys.argv[0]] + sys.argv[2:]))
