from collections import OrderedDict
from .parser import Parser


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
        return [self._parse(x, 0, new_type) for x in d], 0

    def _parse_dict_into_object(self, res, d, _):
        for name in d.keys():
            sane_name = name.replace(".", "__")
            if hasattr(res, f"_parse_{sane_name}_dict"):
                getattr(res, f"_parse_{sane_name}_dict")(self, d[name])
            elif isinstance(res, (dict, OrderedDict)):
                result = self._parse(d[name], 0)
                print(name, result)
                try:
                    res[name], _ = result
                except (TypeError, KeyError):  # hmmm...
                    res = {}  # ugly, this fixes nested dicts in customparameters
                    res[name], _ = result
            else:
                res[name] = d[name]
        return 0
