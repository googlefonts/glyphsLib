# glyphs2ufo

This library provides a bridge from Glyphs source files (.glyphs) to UFOs via
[RoboFab](http://robofab.com/).

The main methods for conversion are found in `glyphslib.py`. Intermediate data
can be accessed without actually generating UFOs, if needed.

#### Generate UFOs

Masters:

```python
glyphslib.build_master_files('MyFont.glyphs')
```

Interpolated instances (depends on
[MutatorMath](https://github.com/LettError/mutatorMath)):

```python
glyphslib.build_instance_files('MyFont.glyphs')
```

#### Load RFonts

Masters:

```python
rfonts = glyphslib.load_to_rfonts('MyFont.glyphs')
```

Instances:

```python
masters, instance_data = glyphslib.load_to_rfonts(
    'MyFont.glyphs', include_instances=True)
rfonts = build_instances(masters, instance_data)
```

#### Load .glyphs data as a Python dictionary

```python
with open('MyFont.glyphs', 'rb') as glyphs_file:
    glyphs_data = glyphslib.load(glyphs_file)
```

#### Saving OTF/TTF

A `save_otf` method is also provided as a convenience. It currently relies on
[ufo2fdk](https://github.com/typesupply/ufo2fdk) for OTF generation and the
[Roboto toolchain](https://github.com/google/roboto/tree/master/scripts/lib/fontbuild)
for TTF generation:

```python
for font in glyphslib.load_to_rfonts('MyFont.glyphs'):
    glyphslib.save_otf(font, True)  # call without second argument for just OTF output
```
