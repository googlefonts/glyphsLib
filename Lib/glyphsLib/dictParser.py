from collections import OrderedDict
from .parser import Parser
import glyphsLib
import logging
import openstep_plist
import sys


logger = logging.getLogger(__name__)


class DictParser(Parser):
    """Parses Python dicts into Glyphs objects mimicking the glyphsLib.parser
    interface."""

    def parse(self, d):
        result, i = self._parse(d, 0)
        return result

    def _parse(self, d, _, new_type=None):
        self.current_type = new_type or self.current_type
        if isinstance(d, list):
            return self._parse_list(d, 0, new_type)
        if isinstance(d, (dict, OrderedDict)):
            return self._parse_dict(d, 0, new_type)
        return d, 0

    def _parse_list(self, d, _, new_type=None):
        self.current_type = new_type or self.current_type
        return [self._parse(x, 0, new_type)[0] for x in d], 0

    def parse_into_object(self, res, value):
        return self._parse_dict_into_object(res, value, 0)

    def _parse_dict_into_object(self, res, d, _):
        for name in d.keys():
            sane_name = name.replace(".", "__")
            if hasattr(res, f"_parse_{sane_name}_dict"):
                getattr(res, f"_parse_{sane_name}_dict")(self, d[name])
            elif isinstance(res, (dict, OrderedDict)):
                result = self._parse(d[name], 0)
                try:
                    res[name], _ = result
                except (TypeError, KeyError):  # hmmm...
                    res = {}  # ugly, this fixes nested dicts in customparameters
                    res[name], _ = result
            else:
                res[name] = d[name]
        return 0


def load(fp):
    """Read a .glyphs file. 'fp' should be (readable) file object.
    Return a GSFont object.
    """
    p = DictParser(current_type=glyphsLib.classes.GSFont)
    logger.info("Parsing .glyphs file")
    res = glyphsLib.classes.GSFont()
    p.parse_into_object(res, openstep_plist.load(fp, use_numbers=True))
    return res


def loads(s):
    """Read a .glyphs file from a (unicode) str object, or from
    a UTF-8 encoded bytes object.
    Return a GSFont object.
    """
    p = DictParser(current_type=glyphsLib.classes.GSFont)
    logger.info("Parsing .glyphs file")
    res = glyphsLib.classes.GSFont()
    p.parse_into_object(res, openstep_plist.loads(s, use_numbers=True))
    return res

def main(args=None):
    """Roundtrip the .glyphs file given as an argument."""
    for arg in args:
        fp = open(arg, "r", encoding="utf-8")
        glyphsLib.dump(load(fp), sys.stdout)
