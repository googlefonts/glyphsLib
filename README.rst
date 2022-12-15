|CI Build Status| |PyPI Version| |Codecov| |Gitter Chat|

glyphsLib
=========

This Python 3.7+ library provides a bridge from Glyphs source files (.glyphs) to
UFOs and Designspace files via `defcon <https://github.com/typesupply/defcon/>`__ and `designspaceLib <https://github.com/fonttools/fonttools>`__.

The main methods for conversion are found in ``__init__.py``.
Intermediate data can be accessed without actually writing UFOs, if
needed.

Write and return UFOs
^^^^^^^^^^^^^^^^^^^^^

The following code will write UFOs and a Designspace file to disk.

.. code:: python

    import glyphsLib

    master_dir = "master_ufos"
    ufos, designspace_path = glyphsLib.build_masters("MyFont.glyphs", master_dir)

If you want to interpolate instances, please use fontmake instead. It uses this library under the hood when dealing with Glyphs files.

Load UFO objects without writing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    import glyphsLib

    ufos = glyphsLib.load_to_ufos("MyFont.glyphs")

Read and write Glyphs data as Python objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    from glyphsLib import GSFont

    font = GSFont(glyphs_file)
    font.save(glyphs_file)

The ``glyphsLib.classes`` module aims to provide an interface similar to
Glyphs.app's `Python Scripting API <https://docu.glyphsapp.com>`__.

Note that currently not all the classes and methods may be fully
implemented. We try to keep up to date, but if you find something that
is missing or does not work as expected, please open a issue.

.. TODO Briefly state how much of the Glyphs.app API is currently covered,
   and what is not supported yet.

Go back and forth between UFOs and Glyphs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1.  You can use the ``ufo2glyphs`` and ``glyphs2ufo`` command line scripts to
    round-trip your source files. By default, the scripts try to preserve as
    much metadata as possible.

    .. code::

        # Generate master UFOs and Designspace file
        glyphs2ufo Example.glyphs

        # Go back
        ufo2glyphs Example.designspace

        # You can also combine single UFOs into a Glyphs source file.
        ufo2glyphs Example-Regular.ufo Example-Bold.ufo

2.  Without a designspace file, using for example the
    `Inria fonts by Black[Foundry] <https://github.com/BlackFoundry/InriaFonts/tree/master/masters/INRIA-SANS>`__:

    .. code:: python

        import glob
        from defcon import Font
        from glyphsLib import to_glyphs

        ufos = [Font(path) for path in glob.glob("*Italic.ufo")]
        # Sort the UFOs because glyphsLib will create masters in the same order
        ufos = sorted(ufos, key=lambda ufo: ufo.info.openTypeOS2WeightClass)
        font = to_glyphs(ufos)
        font.save("InriaSansItalic.glyphs")

    `Here is the resulting glyphs file <https://gist.githubusercontent.com/belluzj/cc3d43bf9b1cf22fde7fd4d2b97fdac4/raw/3222a2bfcf6554aa56a21b80f8fba82f1c5d7444/InriaSansItalic.glyphs>`__

3.  With a designspace, using
    `Spectral from Production Type <https://github.com/productiontype/Spectral/tree/master/sources>`__:

    .. code:: python

        import glob
        from fontTools.designspaceLib import DesignSpaceDocument
        from glyphsLib import to_glyphs

        doc = DesignSpaceDocument()
        doc.read("spectral-build-roman.designspace")
        font = to_glyphs(doc)
        font.save("SpectralRoman.glyphs")

    `Here is the resulting glyphs file <https://gist.githubusercontent.com/belluzj/cc3d43bf9b1cf22fde7fd4d2b97fdac4/raw/3222a2bfcf6554aa56a21b80f8fba82f1c5d7444/SpectralRoman.glyphs>`__

4.  In both programmatic cases, if you intend to go back to UFOs after modifying
    the file with Glyphs, you should use the ``minimize_ufo_diffs`` parameter to
    minimize the amount of diffs that will show up in git after the back and
    forth. To do so, the glyphsLib will add some bookkeeping values in various
    ``userData`` fields. For example, it will try to remember which GSClass came
    from groups.plist or from the feature file.

The same option exists for people who want to do Glyphs->UFOs->Glyphs:
``minimize_glyphs_diffs``, which will add some bookkeeping data in UFO ``lib``.
For example, it will keep the same UUIDs for Glyphs layers, and so will need
to store those layer UUIDs in the UFOs.

.. code:: python

    import glob
    import os
    from fontTools.designspaceLib import DesignSpaceDocument
    from glyphsLib import to_glyphs, to_designspace, GSFont

    doc = DesignSpaceDocument()
    doc.read("spectral-build-roman.designspace")
    font = to_glyphs(doc, minimize_ufo_diffs=True)
    doc2 = to_designspace(font, propagate_anchors=False)
    # UFOs are in memory only, attached to the doc via `sources`
    # Writing doc2 over the original doc should generate very few git diffs (ideally none)
    doc2.write(doc.path)
    for source in doc2.sources:
        path = os.path.join(os.path.dirname(doc.path), source.filename)
        # You will want to use ufoNormalizer after
        source.font.save(path)

    font = GSFont("SpectralRoman.glyphs")
    doc = to_designspace(font, minimize_glyphs_diffs=True, propagate_anchors=False)
    font2 = to_glyphs(doc)
    # Writing font2 over font should generate very few git diffs (ideally none):
    font2.save(font.filepath)

In practice there are always a few diffs on things that don't really make a
difference, like optional things being added/removed or whitespace changes or
things getting reordered...

Kerning interaction between Glyphs 3 and UFO
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Glyphs 3 introduced the attribute ``.kerningRTL`` for the storage of RTL kerning pairs
which breaks with the UFO spec of storing kerning as logical first/second pairs
regardless of writing direction.
As of `PR #838 <https://github.com/googlefonts/glyphsLib/pull/838>`__ glyphsLib
reverts this separate Glyphs 3-style RTL kerning back to Glyphs 2/UFO-style kerning
upon conversion of a Glyphs object to a UFO object, *but it does not convert the kerning
back to Glyphs 3-style when converting a UFO object to a Glyphs object.* 

This means that if you convert a UFO to a Glyphs file and subsequently open that file
in Glyphs 3, the RTL kerning will initially not be visible in the UI, but be hidden
in the LTR kerning. This is identical to opening a Glyphs 2 file with RTL kerning
in Glyphs 3. It is in the responsibility of Glyphs 3 and the user to convert the kerning
back to Glyphs 3's separate RTL kerning.

Make a release
^^^^^^^^^^^^^^

Use ``git tag -a`` to make a new annotated tag, or ``git tag -s`` for a GPG-signed
annotated tag, if you prefer.

Name the new tag with with a leading ‘v’ followed by three ``MAJOR.MINOR.PATCH``
digits, like in semantic versioning. Look at the existing tags for examples.

In the tag message write some short release notes describing the changes since the
previous tag.

Finally, push the tag to the remote repository (e.g. assuming your upstream is
called ``origin``):

.. code::

    $ git push origin v0.4.3

This will trigger the CI to build the distribution packages and upload them to
the Python Package Index automatically, if all the tests pass successfully.


.. |CI Build Status| image:: https://github.com/googlefonts/glyphsLib/workflows/Test%20+%20Deploy/badge.svg
   :target: https://github.com/googlefonts/glyphsLib/actions
.. |PyPI Version| image:: https://img.shields.io/pypi/v/glyphsLib.svg
   :target: https://pypi.org/project/glyphsLib/
.. |Codecov| image:: https://codecov.io/gh/googlefonts/glyphsLib/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/googlefonts/glyphsLib
.. |Gitter Chat| image:: https://badges.gitter.im/fonttools-dev/glyphsLib.svg
   :alt: Join the chat at https://gitter.im/fonttools-dev/glyphsLib
   :target: https://gitter.im/fonttools-dev/glyphsLib?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
