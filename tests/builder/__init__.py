


import filecmp
from pathlib import Path
import difflib

def diff_files(file1, file2):
    if filecmp.cmp(file1, file2, shallow=False):
        left = Path(file1).read_text().splitlines()
        right = Path(file2).read_text().splitlines()
        return "".join(difflib.unified_diff(left, right))
        
def diff_lists(list1, list2):
    return "".join(difflib.unified_diff(list1, list2))
