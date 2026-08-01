# Copyright 2026 Google Inc. All Rights Reserved.
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

import logging
import math
import re
from types import SimpleNamespace

from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.misc.fixedTools import floatToFixedToStr
from fontTools.misc.roundTools import otRound
from fontTools.varLib.featureVars import overlayFeatureVariations
from fontTools.varLib.models import piecewiseLinearMap

from .axes import to_designspace_axes

logger = logging.getLogger(__name__)

_tag = r"[a-zA-Z0-9]{4}"
_number = r"-?\d+(?:\.\d+)?"

_axis_spec = rf"{_tag}\s*:\s*{_number}"
# Comment | "string": matched first by the passes below and left unchanged.
_skip = r"\#[^\n]*|\"[^\"\n]*\""
# A value record, allowing a nested <...> (e.g. a device table).
_value_record = r"<\s*((?:[^<>;]|<[^<>;]*>)*?)\s*>"

_feaLib_vf_pos_re = re.compile(rf"{_tag}\s*=\s*{_number}\s*:{_number}")
_token_re = re.compile(rf"\([\s\S]*?\)|{_number}")
# condition ...; (as a whole word, not part of a glyph name like a.condition
# or condition.alt)
_condition_re = re.compile(r"(?<![\w.])condition(?![\w.])\s*([^;]*);")


def _format_value(value):
    # feaLib scalar values must be integers.
    return str(otRound(float(value)))


# Strip static-only code. No “#ifdef”/“#ifndef” may appear in the body, so an
# unterminated block does not take over the following block’s “#endif”.
_ifndef_re = re.compile(
    r"""
    [^\S\n]*\#ifndef\s+VARIABLE[^\n]*\n  # “#ifndef VARIABLE” line.
    (?:(?!\#ifn?def)[\s\S])*?            # Body.
    \#endif[^\n]*\n?                     # “#endif” line.
    """,
    re.VERBOSE,
)
_ifndef_start_re = re.compile(r"#ifndef\s+VARIABLE")


def _strip_ifndef(fea):
    fea = _ifndef_re.sub("", fea)
    # An unterminated #ifndef VARIABLE runs to the end of the enclosing
    # feature code, like in Glyphs.
    while m := _ifndef_start_re.search(fea):
        masked = _blank_comments_and_strings(fea)
        end = len(fea)
        depth = 0
        for i in range(m.end(), len(fea)):
            if masked[i] == "{":
                depth += 1
            elif masked[i] == "}":
                if depth == 0:
                    end = i
                    break
                depth -= 1
        fea = fea[: m.start()] + fea[end:]
    return fea


# Comments and strings may contain braces that do not open or close a block.
# Block scanning uses a copy with them blanked out.
_comment_or_string_re = re.compile(_skip)


def _blank_comments_and_strings(fea):
    return _comment_or_string_re.sub(lambda m: " " * len(m.group()), fea)


def _match_block(masked, start):
    # index of the brace closing the block opened before `start`, or None
    depth = 1
    for i in range(start, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def _box_within(a, b):
    for axis in set(a) | set(b):
        a_min, a_max = a.get(axis, (-math.inf, math.inf))
        b_min, b_max = b.get(axis, (-math.inf, math.inf))
        if a_min < b_min or a_max > b_max:
            return False
    return True


# Any of the Glyphs-only syntaxes this module converts.
_has_variable_re = re.compile(
    rf"""
      (?<![\w.])condition(?![\w.])  # “condition” statement
    | \#ifn?def\s+VARIABLE          # “#ifdef” / “#ifndef VARIABLE” block
    | \(\s*{_tag}\s*:               # “(axis:” variable GPOS location
    """,
    re.VERBOSE,
)
_axis_spec_re = re.compile(_axis_spec)
_value_record_keyword_re = re.compile(r"\b(?:device|contourpoint|NULL)\b")
_value_record_re = re.compile(rf"{_skip}|{_value_record}")
_scalar_re = re.compile(
    rf"""
      {_skip}          # Left unchanged.
    | {_value_record}  # Left unchanged so the numbers inside are not scalars.
    | {_number}        # A variable scalar, e.g. “10 (wght:900) 20”.
      (?:              # “(location)” value pairs after the default value.
        \s*\(\s*{_axis_spec}(?:\s*,?\s*{_axis_spec})*\s*\)  # Commas optional.
        \s*{_number}
      )+
    """,
    re.VERBOSE,
)
# “MIN < axis < MAX”, either bound is optional
_axis_range_re = re.compile(
    rf"""
    (?:({_number})\s*<\s*)?  # optional minimum
    ({_tag})                 # axis tag
    (?:\s*<\s*({_number}))?  # optional maximum
    """,
    re.VERBOSE,
)
_feature_start_re = re.compile(rf"feature\s+({_tag})(\s+useExtension)?\s*\{{")


class VariableFeatureConverter:
    def __init__(self, font):
        # We don’t have access to axes definitions yet, so we get them here the
        # same way they will be generated for the Designspace.
        shim = SimpleNamespace(
            font=font,
            designspace=DesignSpaceDocument(),
            minimize_glyphs_diffs=False,
        )
        to_designspace_axes(shim)
        axes = shim.designspace.axes
        self.axes = {axis.tag: axis for axis in axes}
        self.default_coords = ",".join(f"{a.tag}={a.default}" for a in axes)
        self.condition_sets = {}

    def convert(self, fea):
        if not _has_variable_re.search(fea):
            return fea

        fea = _strip_ifndef(fea)
        fea = self._translate_gpos(fea)
        fea = self._translate_gsub(fea)

        # every condition must sit inside a feature block; a leftover means one
        # appeared at top level (e.g. in a prefix) and was not converted
        if _condition_re.search(_blank_comments_and_strings(fea)):
            raise ValueError(
                "condition statements outside feature blocks are not supported"
            )

        return fea

    def _axis(self, tag):
        if tag not in self.axes:
            raise ValueError(
                f"unknown axis '{tag}' in feature code, expected one of "
                f"{sorted(self.axes)}"
            )
        return self.axes[tag]

    def _map_coordinate(self, tag, value):
        # Glyphs coordinates are design-space; feaLib wants user-space.
        mapping = self._axis(tag).map  # [(userCoord, designCoord), ...]
        if mapping:
            mapping = {float(design): float(user) for user, design in mapping}
            value = piecewiseLinearMap(value, mapping)
        return floatToFixedToStr(value, 16)

    # GPOS

    def _translate_axis_spec(self, spec):
        # Converts `(wdth:80)` to `wdth=80`.
        spec = spec.strip("() ")
        converted = []
        for part in _axis_spec_re.findall(spec):
            axis, val = part.split(":")
            axis = axis.strip()
            val = self._map_coordinate(axis, float(val))
            converted.append(f"{axis}={val}")
        return ",".join(converted)

    def _translate_scalar(self, match):
        # Converts `10 (wdth:80) 20` to `(wght=400:10 wdth=80:20)`.
        tokens = _token_re.findall(match.group(0))
        if not tokens:
            return match.group(0)

        default_val = tokens.pop(0)
        entries = [f"{self.default_coords}:{_format_value(default_val)}"]

        for i in range(0, len(tokens), 2):
            if not tokens[i].startswith("("):
                raise ValueError(f"invalid variable position value: {match.group(0)!r}")
            axes = self._translate_axis_spec(tokens[i])
            entries.append(f"{axes}:{_format_value(tokens[i + 1])}")

        return f"({' '.join(entries)})"

    def _variable_scalars(self, tokens, num_components, record, kind):
        # The tokens are num_components values for the default master, then a
        # (location) and num_components values for each other master, e.g.
        # “10 0 5 0 (wght:900) 20 10 5 2”. Returns one scalar per component.
        # A component with the same value in all masters stays a plain number.
        if (
            len(tokens) < 2 * num_components + 1
            or (len(tokens) - num_components) % (num_components + 1) != 0
        ):
            raise ValueError(f"invalid variable {kind}: <{record}>")

        def value(token):
            if token.startswith("("):
                raise ValueError(f"invalid variable {kind}: <{record}>")
            return _format_value(token)

        default_vals = [value(v) for v in tokens[:num_components]]
        masters = []
        for i in range(num_components, len(tokens), num_components + 1):
            if not tokens[i].startswith("("):
                raise ValueError(f"invalid variable {kind}: <{record}>")
            axes = self._translate_axis_spec(tokens[i])
            if not axes:
                raise ValueError(
                    f"invalid axis location {tokens[i]} in {kind}: <{record}>"
                )
            vals = [value(v) for v in tokens[i + 1 : i + 1 + num_components]]
            masters.append((axes, vals))

        scalars = []
        for i in range(num_components):
            if all(vals[i] == default_vals[i] for _, vals in masters):
                scalars.append(default_vals[i])
            else:
                entries = [f"{self.default_coords}:{default_vals[i]}"]
                for axes, vals in masters:
                    entries.append(f"{axes}:{vals[i]}")
                scalars.append(f"({' '.join(entries)})")
        return scalars

    def _translate_anchor(self, match, record):
        # Converts `<anchor 100 200 (wght:900) 150 260>` to
        # `<anchor (wght=400:100 wght=900:150) (wght=400:200 wght=900:260)>`.
        if (
            "(" not in record
            or "NULL" in record
            or "contourpoint" in record
            or _feaLib_vf_pos_re.search(record)
        ):
            return match.group(0)
        tokens = _token_re.findall(record.strip()[len("anchor") :])
        scalars = self._variable_scalars(tokens, 2, record, "anchor")
        return f"<anchor {' '.join(scalars)}>"

    def _translate_value_record(self, match):
        # Converts `<10 0 5 0 (wdth:80) 20 10 5 2 ...>` to
        # `<(wdth=400:10 wdth=80:20) (wdth=400:0 wdth=80:10)
        #   (wdth=400:5 wdth=80:5) (wdth=400:0 wdth=80:2)>`.
        record = match.group(1)
        if record.strip().startswith("anchor"):
            return self._translate_anchor(match, record)
        if (
            "(" not in record
            or _value_record_keyword_re.search(record)
            or _feaLib_vf_pos_re.search(record)
        ):
            return match.group(0)

        tokens = _token_re.findall(record.strip())
        scalars = self._variable_scalars(tokens, 4, record, "value record")
        return f"<{' '.join(scalars)}>"

    def _translate_gpos(self, fea):
        fea = _value_record_re.sub(
            lambda m: (
                m.group(0) if m.group(0)[0] in '#"' else self._translate_value_record(m)
            ),
            fea,
        )
        fea = _scalar_re.sub(
            lambda m: (
                m.group(0) if m.group(0)[0] in '#"<' else self._translate_scalar(m)
            ),
            fea,
        )
        return fea

    # GSUB

    def _parse_conditions(self, params):
        # Returns ((tag, min, max), ...), or None for a bare `condition;`
        if not params.strip():
            return None

        ranges = {}
        for part in params.split(","):
            match = _axis_range_re.fullmatch(part.strip())
            if match is None or (match.group(1) is None and match.group(3) is None):
                raise ValueError(f"invalid condition axis range: '{part.strip()}'")
            c_min, tag, c_max = match.groups()
            axis = self._axis(tag)
            c_min = self._map_coordinate(tag, float(c_min)) if c_min else axis.minimum
            c_max = self._map_coordinate(tag, float(c_max)) if c_max else axis.maximum
            if tag in ranges:
                raise ValueError(f"condition for axis '{tag}' already specified")
            ranges[tag] = (c_min, c_max)

        return tuple(
            sorted(
                (t, str(axis_min), str(axis_max))
                for t, (axis_min, axis_max) in ranges.items()
            )
        )

    def _condition_set(self, conditions):
        if conditions in self.condition_sets:
            return self.condition_sets[conditions], None
        name = f"conditionset_{len(self.condition_sets) + 1}"
        body = ";\n    ".join(" ".join(c) for c in conditions)
        definition = f"conditionset {name} {{\n    {body};\n}} {name};\n"
        self.condition_sets[conditions] = name
        return name, definition

    def _split_at_conditions(self, body, masked_body):
        segments = []
        last, conditions = 0, None
        for m in _condition_re.finditer(masked_body):
            segments.append((conditions, body[last : m.start()]))
            conditions = self._parse_conditions(m.group(1))
            last = m.end()
        segments.append((conditions, body[last:]))
        return segments

    def _translate_feature(self, body, masked_body, tag, use_extension=""):
        # Emit unconditional rules in the feature block, then a variation block
        # per conditional region.
        for m in _condition_re.finditer(masked_body):
            depth = masked_body.count("{", 0, m.start()) - masked_body.count(
                "}", 0, m.start()
            )
            if depth > 0:
                raise ValueError(
                    f"condition statements inside lookup blocks are not supported "
                    f"in feature '{tag}': {m.group(0).strip()}"
                )

        segments = self._split_at_conditions(body, masked_body)
        base = [segments[0][1]]
        conditional = []
        for conditions, text in segments[1:]:
            if conditions is None:
                # Rules after a bare `condition;` are unconditional again and
                # go in the feature block.
                base.append(text)
            elif text.strip():
                if all(
                    float(axis_min) <= float(axis_max)
                    for _, axis_min, axis_max in conditions
                ):
                    conditional.append((conditions, text))
                else:
                    # An inverted range. Glyphs allows these but feaLib rejects
                    # them. They wouldn’t be applied any way, so dropping them
                    # is equivalent.
                    ranges = ", ".join(
                        f"{axis_min} < {t} < {axis_max}"
                        for t, axis_min, axis_max in conditions
                    )
                    logger.warning(
                        "dropping rules in feature '%s': condition '%s' can "
                        "never match",
                        tag,
                        ranges,
                    )

        # useExtension is only valid on the feature block, not variation blocks
        parts = [
            f"feature {tag}{use_extension} {{\n{''.join(base).strip()}\n}} {tag};\n"
        ]

        # non-overlapping regions, most specific first
        overlaid = overlayFeatureVariations(
            [
                (
                    [
                        {
                            t: (float(axis_min), float(axis_max))
                            for t, axis_min, axis_max in conds
                        }
                    ],
                    {i: text},
                )
                for i, (conds, text) in enumerate(conditional)
            ]
        )
        # overlayFeatureVariations skips single-point overlaps. ٫eep a pinned
        # region ahead of any broader one that contains it
        ordered = []
        for item in overlaid:
            index = len(ordered)
            for i, other in enumerate(ordered):
                if _box_within(item[0], other[0]):
                    index = i
                    break
            ordered.insert(index, item)

        for box, _ in ordered:
            conditions = tuple(
                sorted(
                    (t, str(axis_min), str(axis_max))
                    for t, (axis_min, axis_max) in box.items()
                )
            )
            name, definition = self._condition_set(conditions)
            if definition is not None:
                parts.append(f"\n{definition}")
            # Rules of the containing region also apply inside this one. The
            # overlay skips single-point intersections, so merge them here.
            # Sorting by the segment index restores source order.
            merged = {}
            for other_box, other_values in ordered:
                if other_box is box or _box_within(box, other_box):
                    for d in other_values:
                        merged.update(d)
            rules = "\n".join(text.strip() for _, text in sorted(merged.items()))
            parts.append(f"\nvariation {tag} {name} {{\n{rules}\n}} {tag};\n")

        return "".join(parts)

    def _translate_gsub(self, fea):
        masked = _blank_comments_and_strings(fea)
        out = []
        pos = 0
        while m := _feature_start_re.search(masked, pos):
            tag = m.group(1)
            if (close := _match_block(masked, m.end())) is None:
                break
            tail = re.match(rf"\s*{tag}\s*;", masked[close + 1 :])
            end = close + 1 + (tail.end() if tail else 0)
            masked_body = masked[m.end() : close]
            if tail is None or not _condition_re.search(masked_body):
                out.append(fea[pos:end])
            else:
                out.append(fea[pos : m.start()])
                out.append(
                    self._translate_feature(
                        fea[m.end() : close],
                        masked_body,
                        tag,
                        use_extension=" useExtension" if m.group(2) else "",
                    )
                )
            pos = end
        out.append(fea[pos:])
        return "".join(out)
