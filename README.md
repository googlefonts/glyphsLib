# glyphs2ufo

This library provides a bridge from Glyphs source files (.glyphs) to UFOs via
[RoboFab](http://robofab.com/).

The main methods for conversion are found in `glyphslib.py`. Intermediate data
can be accessed without actually writing UFOs, if needed.

#### Write and return UFOs

Masters:

```python
master_dir = 'master_ufos'
ufos = glyphslib.build_masters('MyFont.glyphs', master_dir)
```

Interpolated instances (depends on
[MutatorMath](https://github.com/LettError/mutatorMath)):

```python
master_dir = 'master_ufos'
instance_dir = 'instance_ufos'
ufos = glyphslib.build_instances('MyFont.glyphs', master_dir, instance_dir)
```

You must designate a font as italic when calling `glyphslib`:

```python
glyphslib.build_masters('MyFont-Italic.glyphs', master_dir, italic=True)
```

#### Load UFO objects without writing

```python
ufos = glyphslib.load_to_ufos('MyFont.glyphs')
italic_ufos = glyphslib.load_to_ufos('MyFont-Italic.glyphs', italic=True)
```

#### Load Glyphs data as a Python dictionary

```python
with open('MyFont.glyphs', 'rb') as glyphs_file:
    glyphs_data = glyphslib.load(glyphs_file)
```

# Notes

glyphs2ufo tries to be round-trip compatible with Glyphs, though round-trip
compatibility is currently impossible in Glyphs with UFOs. Here is a current
list of data glyphs2ufo will catch that Glyphs drops/ignores:

- Feature notes and whether a feature is disabled
- Whether a font or glyph component has automatic alignment disabled
- Whether guidelines and components are locked
- Annotations
- Glyph hints
- Glyph timestamps
- Tabs to display when opened

Though this data is loaded into UFOs by glyphs2ufo, it still will not be
available if the UFO is opened in Glyphs. It may however be useful if a
ufo2glyphs tool is created.

glyphs2ufo will set some additional UFO data that Glyphs does not, including:

- Name table version and unique ID strings
- Postscript names

Glyphs sets a couple of fontinfo.plist values which are not and have never been
part of the UFO specification. These values are impossible to load via RoboFab:

- "DisableAllAutomaticBehaviour" (put into lib.plist by glyphs2ufo)
- "description" (stored in "openTypeNameDescription" by glyphs2ufo)
- "vendorID" (stored in "openTypeOS2VendorID" by glyphs2ufo)
- "fsType" (stored in "openTypeOS2Type" by glyphs2ufo)
