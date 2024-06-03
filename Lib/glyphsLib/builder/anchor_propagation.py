from fontTools.misc.transform import Transform
import fontTools.pens.boundsPen

from glyphsLib import glyphdata

from .constants import COMPONENT_INFO_KEY, GLYPHLIB_PREFIX


def to_ufo_propagate_font_anchors(self, ufo):
    """Copy anchors from parent glyphs' components to the parent."""

    processed = set()
    for glyph in ufo:
        _propagate_glyph_anchors(self, ufo, glyph, processed)


def _is_ligature_sub_category(glyph):
    # copied from glyphsLib.builder.features._build_public_opentype_categories
    subCategory_key = GLYPHLIB_PREFIX + "subCategory"
    glyphinfo = glyphdata.get_glyph(
        glyph.name, unicodes=[f"{c:04X}" for c in glyph.unicodes]
    )
    subCategory = glyph.lib.get(subCategory_key) or glyphinfo.subCategory
    return subCategory == "Ligature"


def _propagate_glyph_anchors(self, ufo, parent, processed, parent_is_liga=False):
    """Propagate anchors for a single parent glyph."""

    if parent.name in processed:
        return
    processed.add(parent.name)

    parent_is_liga |= _is_ligature_sub_category(parent)

    base_components = []
    mark_components = []
    anchor_names = set()
    to_add = {}
    for component in parent.components:
        try:
            glyph = ufo[component.baseGlyph]
        except KeyError:
            self.logger.warning(
                "Anchors not propagated for inexistent component {} in glyph {}".format(
                    component.baseGlyph, parent.name
                )
            )
        else:
            _propagate_glyph_anchors(self, ufo, glyph, processed, parent_is_liga)
            if any(a.name.startswith("_") for a in glyph.anchors):
                mark_components.append(component)
            else:
                base_components.append(component)
                anchor_names |= {a.name for a in glyph.anchors}

    if not base_components and (
        len(mark_components) == 1
        or (len(mark_components) > 1 and _is_ligature_mark(parent))
    ):
        # The composite is a mark that is composed of one or more mark components:
        # "cedilla" <- "cedillacomb", or a 'ligature mark' (sic) such as
        # "circumflexcomb_tildecomb".
        # Promote the mark that is positioned closest to the origin to a base.
        # TODO: Double-check if Glyphs.app actually cares about the component closer
        # to origin, I suspect it just takes the first one whatever that is. Do we care
        # to keep this closest-to-origin logic or should simply match Glyphs.app?
        try:
            component = _component_closest_to_origin(mark_components, ufo)
        except Exception as e:
            raise Exception(
                "Error while determining which component of composite "
                "'{}' is the lowest: {}".format(parent.name, str(e))
            ) from e
        mark_components.remove(component)
        base_components.append(component)
        glyph = ufo[component.baseGlyph]
        anchor_names |= {a.name for a in glyph.anchors}

    for anchor_name in anchor_names:
        # don't add if parent already contains this anchor OR any associated
        # ligature anchors (e.g. "top_1, top_2" for "top")
        if not any(a.name.startswith(anchor_name) for a in parent.anchors):
            _get_anchor_data(to_add, ufo, base_components, anchor_name, parent_is_liga)

    for component in mark_components:
        _adjust_anchors(to_add, ufo, parent, component)

    # we sort propagated anchors to append in a deterministic order
    for name, (x, y) in sorted(to_add.items()):
        anchor_dict = {"name": name, "x": x, "y": y}
        parent.appendAnchor(anchor_dict)


def _get_anchor_data(anchor_data, ufo, components, anchor_name, parent_is_liga):
    """Get data for an anchor from a list of components."""

    anchors = []
    for component in components:
        for anchor in ufo[component.baseGlyph].anchors:
            if anchor.name == anchor_name:
                anchors.append((anchor, component))
                break
    if len(anchors) > 1:
        if parent_is_liga:
            # if the parent composite glyph is classed as a 'ligature',
            # enumerate anchors and append _1, _2, suffixes.
            # TODO: naive enumeration won't work all the time (e.g. imagine
            # a ligature which uses multiple other ligature as components)
            for i, (anchor, component) in enumerate(anchors):
                t = Transform(*component.transformation)
                name = "%s_%d" % (anchor.name, i + 1)
                anchor_data[name] = t.transformPoint((anchor.x, anchor.y))
        else:
            # not a ligature, the last wins:
            # https://github.com/googlefonts/glyphsLib/issues/368#issuecomment-2103376997
            anchor, component = anchors[-1]
            t = Transform(*component.transformation)
            anchor_data[anchor.name] = t.transformPoint((anchor.x, anchor.y))
    elif anchors:
        anchor, component = anchors[0]
        t = Transform(*component.transformation)
        anchor_data[anchor.name] = t.transformPoint((anchor.x, anchor.y))


def _componentAnchorFromLib(_glyph, _targetComponent):
    """Pull component’s named anchor from Glyph.lib"""
    if COMPONENT_INFO_KEY in _glyph.lib:
        for _anchorLib in _glyph.lib[COMPONENT_INFO_KEY]:
            if (
                "anchor" in _anchorLib
                and "name" in _anchorLib
                and _anchorLib["name"] == _targetComponent.baseGlyph
                and _anchorLib["index"] == _glyph.components.index(_targetComponent)
            ):
                return _anchorLib["anchor"] or None
    return None


def _adjust_anchors(anchor_data, ufo, parent, component):
    """Adjust anchors to which a mark component may have been attached."""
    glyph = ufo[component.baseGlyph]
    anchor_names = {a.name for a in glyph.anchors}
    t = Transform(*component.transformation)
    component_anchor = _componentAnchorFromLib(parent, component)
    # ignore the component's named anchor if we don't have it
    if component_anchor not in anchor_data:
        component_anchor = None
    # For each base anchor in the mark component glyph
    for anchor in (a for a in glyph.anchors if not a.name.startswith("_")):
        # adjust either if component is attached to a specific named anchor
        # (e.g. top_2 for a ligature glyph)
        # rather than to the standard anchors (top/bottom)
        if (
            component_anchor
            and component_anchor.startswith(anchor.name + "_")
            and "_" + anchor.name in anchor_names
        ):
            anchor_data[component_anchor] = t.transformPoint((anchor.x, anchor.y))
        # ... or this anchor has data and the component also contains
        # the associated mark anchor (e.g. "_top" for "top") ...
        elif anchor.name in anchor_data and "_" + anchor.name in anchor_names:
            anchor_data[anchor.name] = t.transformPoint((anchor.x, anchor.y))


def _is_ligature_mark(glyph):
    return not glyph.name.startswith("_") and "_" in glyph.name


def _component_closest_to_origin(components, glyph_set):
    """Return the component whose (xmin, ymin) bounds are closest to origin.

    This ensures that a component that is moved below another is
    actually recognized as such. Looking only at the transformation
    offset can be misleading.
    """
    if len(components) == 1:
        return components[0]
    return min(components, key=lambda comp: _distance((0, 0), _bounds(comp, glyph_set)))


def _distance(pos1, pos2):
    x1, y1 = pos1
    x2, y2 = pos2
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def _bounds(component, glyph_set):
    """Return the (xmin, ymin) of the bounds of `component`."""
    if hasattr(component, "bounds"):  # e.g. defcon
        return component.bounds[:2]
    elif hasattr(component, "draw"):  # e.g. ufoLib2
        pen = fontTools.pens.boundsPen.BoundsPen(glyphSet=glyph_set)
        component.draw(pen)
        return pen.bounds[:2]
    else:
        raise ValueError(
            "Don't know to to compute the bounds of component '{}' ".format(component)
        )
