# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import logging
from typing import Any, List, Optional, Tuple, Union

from glyphsLib import classes, glyphdata
from glyphsLib.classes import GSFont
from fontTools.designspaceLib import DesignSpaceDocument
from ufoLib2 import Font as UFOFont

from .builders import UFOBuilder, GlyphsBuilder
from .transformations import TRANSFORMATIONS, TRANSFORMATION_CUSTOM_PARAMS

logger = logging.getLogger(__name__)


def to_ufos(
    font: GSFont,
    include_instances: bool = False,
    family_name: Optional[str] = None,
    propagate_anchors: Optional[bool] = None,
    ufo_module: Optional[Any] = None,
    minimize_glyphs_diffs: bool = False,
    generate_GDEF: bool = True,
    store_editor_state: bool = True,
    write_skipexportglyphs: bool = False,
    expand_includes: bool = False,
    minimal: bool = False,
    glyph_data: Optional[glyphdata.GlyphData] = None,
    preserve_original: bool = False,
) -> Union[List[UFOFont], Tuple[List[UFOFont], Any]]:
    """Take a GSFont object and convert it into one UFO per master.

    Takes in data as Glyphs.app-compatible classes, as documented at
    https://docu.glyphsapp.com/. The input ``GSFont`` object is modified
    unless ``preserve_original`` is true.

    If include_instances is True, also returns the parsed instance data.

    If family_name is provided, the master UFOs will be given this name and
    only instances with this name will be returned.

    If generate_GDEF is True, write a `table GDEF {...}` statement in the
    UFO's features.fea, containing GlyphClassDef and LigatureCaretByPos.

    If expand_includes is True, resolve include statements in the GSFont features
    and inline them in the UFO features.fea.

    If minimal is True, it is assumed that the UFOs will only be used in
    font production, and unnecessary steps (e.g. converting background layers)
    will be skipped.

    If preserve_original is True, this works on a copy of the font object
    to avoid modifying the original object.

    The optional glyph_data parameter takes a list of GlyphData.xml paths or
    a pre-parsed GlyphData object that overrides the default one.
    """
    if preserve_original:
        font = copy.deepcopy(font)
    if glyph_data is not None and not isinstance(glyph_data, glyphdata.GlyphData):
        glyph_data = glyphdata.GlyphData.from_files(*glyph_data)
    font = preflight_glyphs(
        font, glyph_data=glyph_data, do_propagate_all_anchors=propagate_anchors
    )
    builder = UFOBuilder(
        font,
        ufo_module=ufo_module,
        family_name=family_name,
        minimize_glyphs_diffs=minimize_glyphs_diffs,
        generate_GDEF=generate_GDEF,
        store_editor_state=store_editor_state,
        write_skipexportglyphs=write_skipexportglyphs,
        expand_includes=expand_includes,
        minimal=minimal,
        glyph_data=glyph_data,
    )

    result = list(builder.masters)

    if include_instances:
        return result, builder.instance_data
    return result


def to_designspace(
    font: GSFont,
    family_name: Optional[str] = None,
    instance_dir: Optional[str] = None,
    propagate_anchors: Optional[bool] = None,
    ufo_module: Optional[Any] = None,
    minimize_glyphs_diffs: bool = False,
    generate_GDEF: bool = True,
    store_editor_state: bool = True,
    write_skipexportglyphs: bool = False,
    expand_includes: bool = False,
    minimal: bool = False,
    glyph_data: Optional[glyphdata.GlyphData] = None,
    preserve_original: bool = False,
) -> DesignSpaceDocument:
    """Take a GSFont object and convert it into a Designspace Document + UFOS.
    The UFOs are available as the attribute `font` of each SourceDescriptor of
    the DesignSpaceDocument:

        ufos = [source.font for source in designspace.sources]

    The input object is modified unless ``preserve_original`` is true.

    The designspace and the UFOs are not written anywhere by default, they
    are all in-memory. If you want to write them to the disk, consider using
    the `filename` attribute of the DesignSpaceDocument and of its
    SourceDescriptor as possible file names.

    Takes in data as Glyphs.app-compatible classes, as documented at
    https://docu.glyphsapp.com/

    If include_instances is True, also returns the parsed instance data.

    If family_name is provided, the master UFOs will be given this name and
    only instances with this name will be returned.

    If generate_GDEF is True, write a `table GDEF {...}` statement in the
    UFO's features.fea, containing GlyphClassDef and LigatureCaretByPos.

    If preserve_original is True, this works on a copy of the font object
    to avoid modifying the original object.

    The optional glyph_data parameter takes a list of GlyphData.xml paths or
    a pre-parsed GlyphData object that overrides the default one.
    """
    if preserve_original:
        font = copy.deepcopy(font)
    if glyph_data is not None and not isinstance(glyph_data, glyphdata.GlyphData):
        glyph_data = glyphdata.GlyphData.from_files(*glyph_data)
    font = preflight_glyphs(
        font, glyph_data=glyph_data, do_propagate_all_anchors=propagate_anchors
    )
    builder = UFOBuilder(
        font,
        ufo_module=ufo_module,
        family_name=family_name,
        instance_dir=instance_dir,
        use_designspace=True,
        minimize_glyphs_diffs=minimize_glyphs_diffs,
        generate_GDEF=generate_GDEF,
        store_editor_state=store_editor_state,
        write_skipexportglyphs=write_skipexportglyphs,
        expand_includes=expand_includes,
        minimal=minimal,
        glyph_data=glyph_data,
    )
    return builder.designspace


def preflight_glyphs(
    font: GSFont,
    *,
    glyph_data: Optional[glyphdata.GlyphData] = None,
    **flags: Any
) -> GSFont:
    """Run a set of transformations over a GSFont object to make
    it easier to convert to UFO; resolve all the "smart stuff".

    Currently, the transformations are:
        - `propagate_all_anchors`: copy anchors from components to their parent

    More transformations may be added in the future.

    Some transformations may have custom parameters that can be set in the
    font. For example, the `propagate_all_anchors` transformation can be
    disabled by setting the custom parameter "Propagate Anchors" to False
    (see `TRANSFORMATION_CUSTOM_PARAMS`).

    Args:
        font: a GSFont object
        glyph_data: an optional GlyphData object associating various properties to
            glyph names (e.g. category) that overrides the default one
        **flags: a set of boolean flags to enable/disable specific transformations,
            named `do_<transformation_name>`, e.g. `do_propagate_all_anchors=False`
            will disable the propagation of anchors.

    Returns:
        the modified GSFont object
    """

    for transform in TRANSFORMATIONS:
        do_transform = flags.pop("do_" + transform.__name__, None)
        if do_transform is True:
            pass
        elif do_transform is False:
            continue
        elif do_transform is None:
            if transform in TRANSFORMATION_CUSTOM_PARAMS:
                param = TRANSFORMATION_CUSTOM_PARAMS[transform]
                if not font.customParameters.get(param.name, param.default):
                    continue
        else:
            raise ValueError(f"Invalid value for do_{transform.__name__}")
        logger.info(f"Running '{transform.__name__}' transformation")
        transform(font, glyph_data=glyph_data)

    if flags:
        logger.warning(f"preflight_glyphs has unused `flags` arguments: {flags}")
    return font


def to_glyphs(
    ufos_or_designspace: Union[List[UFOFont], DesignSpaceDocument],
    glyphs_module: Any = classes,
    ufo_module: Optional[Any] = None,
    minimize_ufo_diffs: bool = False,
    expand_includes: bool = False,
    format_version: Optional[int] = None,
) -> GSFont:
    """Convert UFOs or a DesignspaceDocument into a GSFont object.

    Returns:
        A GSFont object.
    """
    assert format_version is None or isinstance(format_version, int)

    if hasattr(ufos_or_designspace, "sources"):
        builder = GlyphsBuilder(
            designspace=ufos_or_designspace,
            glyphs_module=glyphs_module,
            ufo_module=ufo_module,
            minimize_ufo_diffs=minimize_ufo_diffs,
            expand_includes=expand_includes,
            format_version=format_version,
        )
    else:
        builder = GlyphsBuilder(
            ufos=ufos_or_designspace,
            glyphs_module=glyphs_module,
            ufo_module=ufo_module,
            minimize_ufo_diffs=minimize_ufo_diffs,
            expand_includes=expand_includes,
            format_version=format_version,
        )
    return builder.font
