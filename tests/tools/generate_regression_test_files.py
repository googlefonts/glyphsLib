import logging
import multiprocessing
from pathlib import Path

from fontTools.designspaceLib import DesignSpaceDocument

import glyphsLib


def generate_from_glyphs(gs_path: Path):
    # Conversion outputs a lot of warnings we aren't interested in here.
    logging.basicConfig(level=logging.ERROR)

    output_dir = gs_path.parent / gs_path.stem
    ds_path = output_dir / gs_path.with_suffix(".designspace").name
    glyphsLib.build_masters(gs_path, output_dir, None, designspace_path=ds_path)
    print(f"Saved {ds_path}")


def generate_from_designspace(ds_path: Path):
    # Conversion outputs a lot of warnings we aren't interested in here.
    logging.basicConfig(level=logging.ERROR)

    gs_path = ds_path.with_suffix(".glyphs")
    ds = DesignSpaceDocument.fromfile(ds_path)
    glyphs = glyphsLib.to_glyphs(ds, minimize_ufo_diffs=True)
    glyphs.save(gs_path)
    print(f"Saved {gs_path}")


if __name__ == "__main__":
    # Recursively look for test files to convert.
    TEST_FILES_GLYPHS = Path("tests/data/gf").glob("*.glyphs")
    TEST_FILES_DESIGNSPACE = Path("tests/data/designspace").glob("**/*.designspace")

    # Generate in parallel because we can.
    pool = multiprocessing.Pool()
    processes = []

    for gs_path in TEST_FILES_GLYPHS:
        processes.append(pool.apply_async(generate_from_glyphs, (gs_path,)))
    for ds_path in TEST_FILES_DESIGNSPACE:
        processes.append(pool.apply_async(generate_from_designspace, (ds_path,)))

    pool.close()
    pool.join()
    for process in processes:
        process.get()
