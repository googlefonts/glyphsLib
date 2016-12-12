|Travis Build Status| |PyPI Version|

glyphsLib
=========

This library provides a bridge from Glyphs source files (.glyphs) to
UFOs via `defcon <https://github.com/typesupply/defcon/tree/ufo3>`__.

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

Load Glyphs data as a Python dictionary
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    with open('MyFont.glyphs', 'rb') as glyphs_file:
        glyphs_data = glyphsLib.load(glyphs_file)

.. |Travis Build Status| image:: https://travis-ci.org/googlei18n/glyphsLib.svg
   :target: https://travis-ci.org/googlei18n/glyphsLib
.. |PyPI Version| image:: https://img.shields.io/pypi/v/glyphsLib.svg
   :target: https://pypi.org/project/glyphsLib/
