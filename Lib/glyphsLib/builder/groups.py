# Copyright 2016 Google Inc. All Rights Reserved.
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


from typing import Any, Dict, List, Set, Optional, Tuple
from collections import defaultdict
import os

from glyphsLib import classes
from .constants import (
    UFO_ORIGINAL_KERNING_GROUPS_KEY,
    UFO_GROUPS_NOT_IN_FEATURE_KEY,
    UFO_KERN_GROUP_PATTERN,
    BRACKET_GLYPH_RE,
)


def _get_glyphs_with_rtl_kerning(font: Any) -> Set[str]:
    """Return a set of all glyph names referenced from font.kerningRTL,
    either directly as single glyphs or as part of kerning groups.
    """
    rtl_glyphs: Set[str] = set()
    if not font.kerningRTL:
        return rtl_glyphs

    # sets of group names keyed by {left,right}KerningGroup
    rtl_groups: Dict[str, Set[str]] = defaultdict(set)
    glyph_kerning_attr: Dict[str, str] = {"R": "leftKerningGroup", "L": "rightKerningGroup"}

    def mark_as_rtl(s: str, side: str) -> None:
        if s.startswith(f"@MMK_{side}_"):
            rtl_groups[glyph_kerning_attr[side]].add(s[7:])
        else:  # single glyph
            assert not s.startswith("@MMK_"), f"unexpected key in kerningRTL: {s}"
            rtl_glyphs.add(s)

    for kerning_id in {
        m.id if m.metricsSource is None else m.metricsSource.id for m in font.masters
    }:
        for kern1, subtable in font.kerningRTL.get(kerning_id, {}).items():
            mark_as_rtl(kern1, side="R")
            for kern2 in subtable.keys():
                mark_as_rtl(kern2, side="L")

    for glyph in font.glyphs.values():
        if glyph.name not in rtl_glyphs and any(
            getattr(glyph, attr) in rtl_groups[attr] for attr in glyph_kerning_attr.values()
        ):
            rtl_glyphs.add(glyph.name)

    return rtl_glyphs


def to_ufo_groups(self) -> None:
    """Build and apply groups for all UFOs."""
    groups: Dict[str, List[str]] = defaultdict(list)

    # Classes usually go to the feature file, unless we have our custom flag
    group_names: Optional[Set[str]] = None
    if UFO_GROUPS_NOT_IN_FEATURE_KEY in self.font.userData.keys():
        group_names = set(self.font.userData[UFO_GROUPS_NOT_IN_FEATURE_KEY])

    if group_names:
        for gsclass in self.font.classes.values():
            if gsclass.name in group_names:
                groups[gsclass.name] = gsclass.code.split(" ") if gsclass.code else []

    # Rebuild kerning groups from `left/rightKerningGroup`s
    # Use the original list of kerning groups as a base, to recover
    #  - the original ordering
    #  - the kerning groups of glyphs that were not in the font (which can be
    #    stored in a UFO but not by Glyphs)

    recovered: Set[Tuple[str, int]] = set()
    orig_groups: Optional[Dict[str, List[str]]] = self.font.userData.get(UFO_ORIGINAL_KERNING_GROUPS_KEY)
    if orig_groups:
        for group, glyphs in orig_groups.items():
            if not glyphs:
                # Restore empty group
                groups[group] = []
            for glyph_name in glyphs:
                # Check that the original value is still valid
                match = UFO_KERN_GROUP_PATTERN.match(group)
                if match:
                    side = int(match.group(1))
                    group_name = match.group(2)
                    glyph = self.font.glyphs[glyph_name]
                    if not glyph or getattr(glyph, _glyph_kerning_attr(side)) == group_name:
                        groups[group].append(glyph_name)
                        recovered.add((glyph_name, side))

    # Read new/modified grouping values.
    # For glyphs that are used in Glyphs3's kerningRTL dict, take the opposite side:
    # NOTE: Not only this breaks Glyphs<=>UFO round-tripping, but also it makes
    # impossible for the same glyph to be kerned in both LTR and RTL dictionaries.
    # While this is unfortunate, we believe it's better than completely ignoring
    # all Glyphs3's RTL kerning.
    # For more info: https://github.com/googlefonts/glyphsLib/pull/778

    rtl_glyphs: Set[str] = _get_glyphs_with_rtl_kerning(self.font)
    for glyph in self.font.glyphs.values():
        is_rtl = glyph.name in rtl_glyphs
        for side in (1, 2):
            if (glyph.name, side) not in recovered:
                attr = _glyph_kerning_attr(side, is_rtl)
                group = getattr(glyph, attr)
                if group:
                    groups[f"public.kern{side}.{group}"].append(glyph.name)

    # Update all UFOs with the same info
    for source in self._sources.values():
        for name, glyphs in groups.items():
            # Shallow copy to prevent unexpected object sharing
            source.font.groups[name] = glyphs[:]


def to_glyphs_groups(self) -> None:
    """Convert UFO groups to GSClasses in Glyphs."""
    groups: List[str] = []
    for source in self._sources.values():
        for name, glyphs in source.font.groups.items():
            # Filter out all BRACKET glyphs first, as they are created at
            # to_designspace time to inherit glyph kerning to their bracket
            # variants. They need to be removed because Glpyhs.app handles that
            # on its own.
            glyphs = [g for g in glyphs if not BRACKET_GLYPH_RE.match(g)]
            if _is_kerning_group(name):
                _to_glyphs_kerning_group(self, name, glyphs)
            else:
                gsclass = classes.GSClass(name, " ".join(glyphs))
                self.font.classes.append(gsclass)
                groups.append(name)
        if self.minimize_ufo_diffs and groups:
            self.font.userData[UFO_GROUPS_NOT_IN_FEATURE_KEY] = groups
        break

    # Check that other UFOs are identical and print a warning if not.
    for index, source in enumerate(self._sources.values()):
        if index == 0:
            reference_ufo = source.font
        else:
            _assert_groups_are_identical(self, reference_ufo, source.font)


def _is_kerning_group(name: str) -> bool:
    return name.startswith(("public.kern1.", "public.kern2."))


def _to_glyphs_kerning_group(self, name: str, glyphs: List[str]) -> None:
    """Convert UFO kerning group to Glyphs kerning group."""
    if self.minimize_ufo_diffs:
        # Preserve ordering when going from UFO group
        # to left/rightKerningGroup disseminated in GSGlyphs
        # back to UFO group.
        self.font.userData.setdefault(UFO_ORIGINAL_KERNING_GROUPS_KEY, {})[name] = glyphs

    match = UFO_KERN_GROUP_PATTERN.match(name)
    if not match:
        return
    side = match.group(1)
    group_name = match.group(2)
    for glyph_name in glyphs:
        glyph = self.font.glyphs[glyph_name]
        if glyph:
            setattr(glyph, _glyph_kerning_attr(int(side)), group_name)


def _glyph_kerning_attr(side: int, is_rtl: bool = False) -> str:
    """Return rightKerningGroup or leftKerningGroup depending on the UFO
    group's side (1 or 2).

    Flip values for RTL kerning.
    """

    assert side in (1, 2), f"Invalid kerning side: {side}"
    if is_rtl:
        side = 2 if side == 1 else 1
    return "rightKerningGroup" if side == 1 else "leftKerningGroup"


def _assert_groups_are_identical(self, reference_ufo: Any, ufo: Any) -> None:
    """Check that all UFO groups are identical, logging warnings otherwise."""
    first_time = [True]

    def _warn(message: str, *args: Any) -> None:
        if first_time:
            self.logger.warning(
                "Using UFO `%s` as a reference for groups:", _ufo_logging_ref(reference_ufo)
            )
            first_time.clear()
        self.logger.warning("   " + message, *args)

    # Check for inconsistencies
    for group, glyphs in ufo.groups.items():
        if group not in reference_ufo.groups:
            _warn("group `%s` from `%s` will be lost because it's not in the reference UFO",
                  group, _ufo_logging_ref(ufo))
            continue
        reference_glyphs = reference_ufo.groups[group]
        if set(glyphs) != set(reference_glyphs):
            _warn("group `%s` from `%s` differs from reference UFO", group, _ufo_logging_ref(ufo))
            _warn("    reference = %s", " ".join(sorted(reference_glyphs)))
            _warn("    current   = %s", " ".join(sorted(glyphs)))


def _ufo_logging_ref(ufo: Any) -> str:
    """Return a string identifying this UFO in logs."""
    return os.path.basename(ufo.path) if ufo.path else ufo.info.styleName
