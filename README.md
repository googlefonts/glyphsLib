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
