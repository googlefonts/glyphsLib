from collections import OrderedDict, defaultdict
import re

from glyphsLib.builder.constants import OBJECT_LIBS_KEY
from ufo2ft.featureWriters import ast
from ufo2ft.featureWriters.markFeatureWriter import (
    MARK_PREFIX,
    LIGA_SEPARATOR,
    LIGA_NUM_RE,
    MarkToBasePos,
    NamedAnchor,
    MarkFeatureWriter,
    quantize,
)


class ContextuallyAwareNamedAnchor(NamedAnchor):
    __slots__ = (
        "name",
        "x",
        "y",
        "isMark",
        "key",
        "number",
        "markClass",
        "isContextual",
        "libData",
    )

    @classmethod
    def parseAnchorName(
        cls,
        anchorName,
        markPrefix=MARK_PREFIX,
        ligaSeparator=LIGA_SEPARATOR,
        ligaNumRE=LIGA_NUM_RE,
        ignoreRE=None,
    ):
        """Parse anchor name and return a tuple that specifies:
        1) whether the anchor is a "mark" anchor (bool);
        2) the "key" name of the anchor, i.e. the name after stripping all the
           prefixes and suffixes, which identifies the class it belongs to (str);
        3) An optional number (int), starting from 1, which identifies that index
           of the ligature component the anchor refers to.

        The 'ignoreRE' argument is an optional regex pattern (str) identifying
        sub-strings in the anchor name that should be ignored when parsing the
        three elements above.
        """
        number = None
        isContextual = False
        if ignoreRE is not None:
            anchorName = re.sub(ignoreRE, "", anchorName)

        if anchorName[0] == "*":
            isContextual = True
            anchorName = anchorName[1:]
            anchorName = re.sub(r"\..*", "", anchorName)

        m = ligaNumRE.match(anchorName)
        if not m:
            key = anchorName
        else:
            number = m.group(1)
            key = anchorName.rstrip(number)
            separator = ligaSeparator
            if key.endswith(separator):
                assert separator
                key = key[: -len(separator)]
                number = int(number)
            else:
                # not a valid ligature anchor name
                key = anchorName
                number = None

        if anchorName.startswith(markPrefix) and key:
            if number is not None:
                raise ValueError("mark anchor cannot be numbered: %r" % anchorName)
            isMark = True
            key = key[len(markPrefix) :]
            if not key:
                raise ValueError("mark anchor key is nil: %r" % anchorName)
        else:
            isMark = False

        return isMark, key, number, isContextual

    def __init__(self, name, x, y, markClass=None, libData=None):
        self.name = name
        self.x = x
        self.y = y
        isMark, key, number, isContextual = self.parseAnchorName(
            name,
            markPrefix=self.markPrefix,
            ligaSeparator=self.ligaSeparator,
            ligaNumRE=self.ligaNumRE,
            ignoreRE=self.ignoreRE,
        )
        if number is not None:
            if number < 1:
                raise ValueError("ligature component indexes must start from 1")
        else:
            assert key, name
        self.isMark = isMark
        self.key = key
        self.number = number
        self.markClass = markClass
        self.isContextual = isContextual
        self.libData = libData


class ContextualMarkFeatureWriter(MarkFeatureWriter):
    NamedAnchor = ContextuallyAwareNamedAnchor

    def _getAnchorLists(self):
        gdefClasses = self.context.gdefClasses
        if gdefClasses.base is not None:
            # only include the glyphs listed in the GDEF.GlyphClassDef groups
            include = gdefClasses.base | gdefClasses.ligature | gdefClasses.mark
        else:
            # no GDEF table defined in feature file, include all glyphs
            include = None
        result = OrderedDict()
        for glyphName, glyph in self.getOrderedGlyphSet().items():
            if include is not None and glyphName not in include:
                continue
            anchorDict = OrderedDict()
            for anchor in glyph.anchors:
                anchorName = anchor.name
                if not anchorName:
                    self.log.warning(
                        "unnamed anchor discarded in glyph '%s'", glyphName
                    )
                    continue
                if anchorName in anchorDict:
                    self.log.warning(
                        "duplicate anchor '%s' in glyph '%s'", anchorName, glyphName
                    )
                x = quantize(anchor.x, self.options.quantization)
                y = quantize(anchor.y, self.options.quantization)
                libData = None
                if anchor.identifier:
                    libData = glyph.lib[OBJECT_LIBS_KEY].get(anchor.identifier)
                a = self.NamedAnchor(name=anchorName, x=x, y=y, libData=libData)
                if a.isContextual and not libData:
                    continue
                anchorDict[anchorName] = a
            if anchorDict:
                result[glyphName] = list(anchorDict.values())
        return result

    def _makeFeatures(self):
        features = super()._makeFeatures()
        # Now do the contextual ones

        # Arrange by context
        by_context = defaultdict(list)
        markGlyphNames = self.context.markGlyphNames

        for glyphName, anchors in sorted(self.context.anchorLists.items()):
            if glyphName in markGlyphNames:
                continue
            for anchor in anchors:
                if not anchor.isContextual:
                    continue
                anchor_context = anchor.libData["GPOS_Context"].strip()
                by_context[anchor_context].append((glyphName, anchor))
        if not by_context:
            return features, []

        # Pull the lookups from the feature and replace them with lookup references,
        # to ensure the order is correct
        lookups = features["mark"].statements
        features["mark"].statements = [
            ast.LookupReferenceStatement(lu) for lu in lookups
        ]

        dispatch_lookups = {}
        # We sort the full context by longest first. This isn't perfect
        # but it gives us the best chance that more specific contexts
        # (typically longer) will take precedence over more general ones.
        for ix, (fullcontext, glyph_anchor_pair) in enumerate(
            sorted(by_context.items(), key=lambda x: -len(x[0]))
        ):
            # Make the contextual lookup
            lookupname = "ContextualMark_%i" % ix
            if ";" in fullcontext:
                before, after = fullcontext.split(";")
                # I know it's not really a comment but this is the easiest way
                # to get the lookup flag in there without reparsing it.
            else:
                after = fullcontext
                before = ""
            after = after.strip()
            if before not in dispatch_lookups:
                dispatch_lookups[before] = ast.LookupBlock(
                    "ContextualMarkDispatch_%i" % len(dispatch_lookups.keys())
                )
                if before:
                    dispatch_lookups[before].statements.append(
                        ast.Comment(f"{before};")
                    )
                features["mark"].statements.append(
                    ast.LookupReferenceStatement(dispatch_lookups[before])
                )
            lkp = dispatch_lookups[before]
            lkp.statements.append(ast.Comment(f"# {after}"))
            lookup = ast.LookupBlock(lookupname)
            for glyph, anchor in glyph_anchor_pair:
                lookup.statements.append(MarkToBasePos(glyph, [anchor]).asAST())
            lookups.append(lookup)

            for glyph, anchor in glyph_anchor_pair:
                marks = ast.GlyphClass(
                    self.context.markClasses[anchor.key].glyphs.keys()
                ).asFea()
                if "&" not in after:
                    after = after.replace("*", "* &")
                # Replace & with mark name if present
                contextual = after.replace("*", f"{glyph}")
                contextual = contextual.replace("&", f"{marks}' lookup {lookupname}")
                lkp.statements.append(
                    ast.Comment(f"pos {contextual}; # {glyph}/{anchor.name}")
                )

        lookups.extend(dispatch_lookups.values())

        return features, lookups

    def _write(self):
        self._pruneUnusedAnchors()

        newClassDefs = self._makeMarkClassDefinitions()
        self._setBaseAnchorMarkClasses()

        features, lookups = self._makeFeatures()
        if not features:
            return False

        feaFile = self.context.feaFile

        self._insert(
            feaFile=feaFile,
            markClassDefs=newClassDefs,
            features=[features[tag] for tag in sorted(features.keys())],
            lookups=lookups,
        )

        return True
