# glyphsLib.builder sketch

Here is an of overview of how `glyphsLib.builder` converts a Glyphs `GSFont` object into a set of UFO and Designspace files.

## To convert each master

* Create base UFOs using the GSFont metadata and per-master metadata
    * Also store names, user data, custom parameters, custom filters
* Convert the main layer of each master; convert also bracket/brace layers. (See [To convert each layer](#To_convert_each_layer) below)
* Propagate anchors. How we should do this is… disputed.
    * [https://github.com/googlefonts/glyphsLib/issues/368#issuecomment-491939617](https://github.com/googlefonts/glyphsLib/issues/368#issuecomment-491939617)
    * [https://github.com/googlefonts/fontmake/issues/682#issuecomment-658079871](https://github.com/googlefonts/fontmake/issues/682#issuecomment-658079871)
    * We currently (but shouldn’t) find the component closest to the origin: [https://github.com/googlefonts/ufo2ft/pull/316#issuecomment-1178961730](https://github.com/googlefonts/ufo2ft/pull/316#issuecomment-1178961730)
* Store font and master userData in “layerLib” (why?)
* Convert color layer IDs into layer names if there is a mapping in com.github.googlei18n.ufo2ft.colorLayerMapping (how would there be one here at this point?)
* Convert the features into a feature file
* Apply any custom parameters to the lib, including:
    * codePageRanges/openTypeOS2CodePageRanges/codePageRangesUnsupportedBits
    * GASP table
    * Color Palettes (converted and stored in a ufo2ft key)
    * Name records
    * Don't use Production Names
    * disablesNiceNames/useNiceNames
    * "Use Typo Metrics"/"Has WWS Names" /"openTypeOS2SelectionUnsupportedBits"
    * glyphOrder
    * Filters
    * Replace Prefix / Replace Feature (modifies feature file)
    * Reencode Glyphs
* Fix up color layers:
    * Create color palette layers of {glyphname}.color{i}, convert UFO glyphs for each
    * Create COLRv1 layers, convert UFO glyphs for each and apply paint/stroke
* Write out any skipExportGlyphs list gathered when converting glyphs
* Convert feature groups and kerning groups
* Convert kerning

## To convert each layer

* For each glyph, look at all its Glyphs layers and, for master layers only, create/select appropriate UFO layers. Then convert each glyph. (See [To convert each glyph](#To_convert_each_glyph) below)
* For non-master layers, collect a list of Glyphs layers and glyphs associated with them.
* Out of that list, discard those which have no master associated with them and no name; gather up bracket layers (which will be processed during designspace generation); discard other irrelevant layers; convert other glyphs to glyphs in appropriate UFO layers.

## To convert each glyph

* For color glyphs, create a mapping between layers and palette IDs; clone any layers with components shared between them; gather into a list of color layers.
* Set unicodes
* Add to skipExportGlyphs if not exported
* Determine production name, category and subcategory; write production name into lib.
* Use category to zero out width if it’s a mark glyph; otherwise, check if the width is determined from the “Link Metrics With Master”/Link Metrics With First Master custom parameters.
* Convert hints.
* Stash any user data (is this necessary?)
* Resolve/decompose smart components (currently we just store this info - don’t do anything with it?)
* Draw paths with a pen onto the UFO glyph
* Convert any components to UFO
* Convert any anchors to UFO
* If the font is vertical, set the height and vertical origin in the UFO

## To create the designspace file

* Convert Glyphs axes to designspace axes (Looking carefully at the custom parameters “Axis Mappings”, “Axes” - for older Glyphs versions - “Axis Location”, and “Variable Font Origin”/”Variation Font Origin” (again for older Glyphs)
* Convert Glyphs masters to designspace sources
* Convert Glyphs instances to designspace instances
* Copy userdata into the designspace lib, add feature writers unless there is a manual kern feature. (this may be a bug - [https://github.com/googlefonts/glyphsLib/issues/764](https://github.com/googlefonts/glyphsLib/issues/764) )
* Extract bracket layers into free-standing UFO glyphs with Designspace substitution rules. Check the “Feature for Feature Variations” custom parameter to set the OT feature for the rule.
