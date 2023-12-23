import filecmp
from pathlib import Path
import difflib


def diff_files(file1, file2):
    """Takes two file paths, compares the contents and returns a formatted diff
    if there are any differences, an empty string otherwise.
    """
    if filecmp.cmp(file1, file2, shallow=False):
        left = Path(file1).read_text().splitlines()
        right = Path(file2).read_text().splitlines()
        return "\n".join(difflib.unified_diff(left, right))
    return ""


def diff_lists(list1, list2):
    return "\n".join(difflib.unified_diff(list1, list2))
