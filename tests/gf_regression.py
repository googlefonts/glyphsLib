import sys
import glyphsLib
import glob
import os
import filecmp
import difflib
import unittest
import tempfile
import logging


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


TEST_FILES = glob.glob("tests/data/gf/*.glyphs")


def generate_ufos():
    for t in TEST_FILES:
        outputdir = os.path.splitext(t)[0]
        ds = os.path.join(
            outputdir, os.path.basename(os.path.splitext(t)[0]) + ".designspace"
        )
        glyphsLib.build_masters(t, outputdir, None, designspace_path=ds)


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
        test_name = "test_{}".format(file_basename.replace(r"[^a-zA-Z]", ""),)
        test_method.__name__ = test_name
        setattr(cls, test_name, test_method)


def run_tests():
    for t in TEST_FILES:
        GlyphsToDesignspace.add_test(t)
    import pytest

    pytest.main([sys.argv[0]] + sys.argv[2:])


if sys.argv[1] == "--generate":
    generate_ufos()
elif sys.argv[1] == "--test":
    logging.basicConfig(level=logging.ERROR)
    run_tests()
