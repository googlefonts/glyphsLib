|Travis Build Status| |PyPI Version| |Codecov|

glyphsLib
=========

This library provides a bridge from Glyphs source files (.glyphs) to
UFOs via `defcon <https://github.com/typesupply/defcon/>`__.

The main methods for conversion are found in ``__init__.py``.
Intermediate data can be accessed without actually writing UFOs, if
needed.

Write and return UFOs
^^^^^^^^^^^^^^^^^^^^^

Masters:

.. code:: python

    master_dir = 'master_ufos'
    ufos = glyphsLib.build_masters('MyFont.glyphs', master_dir)

Interpolated instances (depends on
`MutatorMath <https://github.com/LettError/mutatorMath>`__):

.. code:: python

    master_dir = 'master_ufos'
    instance_dir = 'instance_ufos'
    ufos = glyphsLib.build_instances('MyFont.glyphs', master_dir, instance_dir)

Load UFO objects without writing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    ufos = glyphsLib.load_to_ufos('MyFont.glyphs')

Read and write Glyphs data as Python objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    with open('MyFont.glyphs', 'rb') as glyphs_file:
        font = glyphsLib.load(glyphs_file)

    with open('MyFont.glyphs', 'wb') as glyphs_file:
        glyphsLib.dump(font, glyphs_file)

The ``glyphsLib.classes`` module aims to provide an interface similar to
Glyphs.app's `Python Scripting API <https://docu.glyphsapp.com>`__.

Note that currently not all the classes and methods may be fully
implemented. We try to keep up to date, but if you find something that
is missing or does not work as expected, please open a issue.

.. TODO Briefly state how much of the Glyphs.app API is currently covered,
   and what is not supported yet.

.. |Travis Build Status| image:: https://travis-ci.org/googlei18n/glyphsLib.svg
   :target: https://travis-ci.org/googlei18n/glyphsLib
.. |PyPI Version| image:: https://img.shields.io/pypi/v/glyphsLib.svg
   :target: https://pypi.org/project/glyphsLib/
.. |Codecov| image:: https://codecov.io/gh/googlei18n/glyphsLib/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/googlei18n/glyphsLib
