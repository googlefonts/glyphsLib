__all__ = [
    'cast_data', 'cast_noto_data'
]


from datetime import datetime
import json
import re


DEFAULTS = {
    'widthValue': 100,
    'weightValue': 100}


def cast_data(data, types=None):
    """Cast the attributes of parsed glyphs file content.

    Returns the casted data, so that the type-casting functions used by
    cast_data (which are expected to return a casted value) can themselves call
    cast_data and then return the result."""

    if types is None:
        types = get_type_structure()

    for key, cur_type in types.items():
        if key not in data:
            try:
                data[key] = DEFAULTS[key]
            except KeyError:
                pass
            continue
        if type(cur_type) == dict:
            for cur_data in data[key]:
                cast_data(cur_data, dict(cur_type))
        else:
            data[key] = cur_type(data[key])
    return data


def cast_noto_data(data):
    """Cast data which is specific to Noto font glyphs files."""

    for param in data['customParameters']:
        if param['name'] == 'openTypeOS2Type':
            param['value'] = map(int, param['value'])


def get_type_structure():
    """Generate and return the highest-level type hierarchy for glyphs data."""

    return {
        'DisplayStrings': list,
        'classes': {
            'automatic': truthy,
            'code': feature_syntax,
            'name': str
        },
        'copyright': str,
        'customParameters': {
            'name': str,
            'value': default
        },
        'date': glyphs_datetime,
        'designer': str,
        'designerURL': str,
        'familyName': str,
        'featurePrefixes': {
            'code': feature_syntax,
            'name': str
        },
        'features': {
            'automatic': truthy,
            'code': feature_syntax,
            'name': str
        },
        'fontMaster': {
            'alignmentZones': pointlist,
            'ascender': int,
            'capHeight': int,
            'customParameters': {
                'name': str,
                'value': default
            },
            'descender': int,
            'horizontalStems': intlist,
            'id': str,
            'userData': dict,
            'verticalStems': intlist,
            'weight': str,  # undocumented
            'weightValue': int,
            'width': str,  # undocumented
            'widthValue': int,
            'xHeight': int
        },
        'glyphs': {
            'glyphname': str,
            'lastChange': glyphs_datetime,
            'layers': get_glyph_layer_type_structure(),
            'leftKerningGroup': str,
            'leftMetricsKey': str,
            'rightKerningGroup': str,
            'rightMetricsKey': str,
            'unicode': hex_int
        },
        'instances': {
            'customParameters': {
                'name': str,
                'value': default
            }
        },
        'kerning': kerning,
        'manufacturer': str,
        'manufacturerURL': str,
        'unitsPerEm': int,
        'userData': dict,
        'versionMajor': int,
        'versionMinor': int
    }


def get_glyph_layer_type_structure(background=False):
    """Generate and return the type hierarchy for glyph layer data.

    This is used for layer backgrounds as well, so it's abstracted out.
    """

    structure = {
        'anchors': {
            'name': str,
            'position': point
        },
        'components': {
            'anchor': str,
            'name': str,
            'transform': transform
        },
        'leftMetricsKey': str,
        'rightMetricsKey': str,
        'name': str,
        'paths': {
            'closed': truthy,
            'nodes': nodelist
        },
        'width': num
    }
    if not background:
        structure.update({
            'associatedMasterId': str,
            'background': layer_background,
            'layerId': str
        })
    return structure


def default(value):
    """Just return the value (i.e. don't cast it to anything)."""
    return value


def truthy(string):
    """Determine if an int stored in a string is truthy."""
    return bool(int(string))


def num(string):
    """Prefer casting to int, but use float if necessary."""

    val = float(string)
    int_val = int(val)
    return int_val if int_val == val else val


def hex_int(string):
    """Return the hexidecimal value represented by a string."""
    return int(string, 16)


def vector(string, dimension):
    """Parse a vector from a string with format {X, Y, Z, ...}."""

    rx = '{%s}' % ', '.join(['([-.e\d]+)'] * dimension)
    return [num(i) for i in re.match(rx, string).groups()]


def point(string):
    return vector(string, 2)


def transform(string):
    return vector(string, 6)


def node(string):
    """Cast a node from a string with format X Y TYPE [SMOOTH]."""

    rx = '([-.e\d]+) ([-.e\d]+) (LINE|CURVE|OFFCURVE)(?: (SMOOTH))?'
    m = re.match(rx, string).groups()
    return [num(m[0]), num(m[1]), m[2], m[3]]


def intlist(strlist):
    return map(int, strlist)


def pointlist(strlist):
    return map(point, strlist)


def nodelist(strlist):
    return map(node, strlist)


def glyphs_datetime(string):
    """Parse a datetime object from a string, ignoring the timezone."""
    return datetime.strptime(string[:string.rfind(' ')], '%Y-%m-%d %H:%M:%S')


def layer_background(data):
    """Cast the background of a layer."""
    return cast_data(data, get_glyph_layer_type_structure(background=True))


def kerning(kerning_data):
    """Cast the values in kerning data to ints."""

    new_data = {}
    for master_id, master_map in kerning_data.items():
        new_data[master_id] = {}
        for left_glyph, glyph_map in master_map.items():
            new_data[master_id][left_glyph] = {}
            for right_glyph, value in glyph_map.items():
                new_data[master_id][left_glyph][right_glyph] = int(value)
    return new_data


def version_minor(string):
    """Ensure that the minor version number is between 0 and 999."""

    num = int(string)
    assert num >= 0 and num <= 999
    return num


def feature_syntax(string):
    """Replace un-escaped characters with their intended characters."""
    return string.replace('\\012', '\n').replace('\\011', '\t')
