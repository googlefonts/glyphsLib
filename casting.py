__all__ = [
    'cast_data'
]


from datetime import datetime
import json
import re


def cast_data(data, types=None, print_dbg=False):
    """Cast the attributes of parsed glyphs file content."""

    if types is None:
        types = get_type_structure()

    new_data = {}
    for key, cur_type in types.items():
        if key not in data:
            continue
        if type(cur_type) == dict:
            new_data[key] = []
            for cur_data in data[key]:
                new_data[key].append(cast_data(cur_data, dict(cur_type)))
            data[key] = [dict(cur_data) for cur_data in data[key] if cur_data]
            if not data[key]:
                del data[key]
        else:
            new_data[key] = cur_type(data[key])
            del data[key]

    if print_dbg:
        print 'not casted in data:', json.dumps(data, indent=2, sort_keys=True)
    return new_data


# should see: DisplayStrings not found, fontMaster/weight not casted
def get_type_structure():
    """Generate and return the highest-level type hierarchy for glyphs data."""

    return {
        'DisplayStrings': list,
        'classes': {
            'automatic': bool,
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
            'automatic': bool,
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
            'weightValue': int,
            'xHeight': int
        },
        'glyphs': {
            'glyphname': str,
            'lastChange': glyphs_datetime,
            'layers': {
                'anchors': {
                    'name': str,
                    'position': point
                },
                'components': {
                    'anchor': str,
                    'name': str,
                    'transform': transform
                },
                'associatedMasterId': str,
                'background': dict,  #TODO has same children as layer
                'layerId': str,
                'leftMetricsKey': str,
                'rightMetricsKey': str,
                'name': str,
                'paths': {
                    'closed': bool,
                    'nodes': nodelist
                },
                'width': float
            },
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


def default(value):
    """Just return the value (i.e. don't cast it to anything)."""
    return value


def hex_int(string):
    """Return the hexidecimal value represented by a string."""
    return int(string, 16)


def vector(string, dimension):
    """Parse a vector from a string with format {X, Y, Z, ...}."""

    rx = '{%s}' % ', '.join(['([-.\d]+)'] * dimension)
    return [float(i) for i in re.match(rx, string).groups()]


def point(string):
    return vector(string, 2)


def transform(string):
    return vector(string, 6)


def node(string):
    """Cast a node from a string with format X Y TYPE [SMOOTH]."""

    rx = '([-.\d]+) ([-.\d]+) (LINE|CURVE|OFFCURVE)(?: (SMOOTH))?'
    m = re.match(rx, string).groups()
    return [float(m[0]), float(m[1]), m[2], m[3]]


def castlist(strlist, cast):
    """Cast a list of strings."""
    return [cast(string) for string in strlist]


def intlist(strlist):
    return castlist(strlist, int)


def pointlist(strlist):
    return castlist(strlist, point)


def nodelist(strlist):
    return castlist(strlist, node)


def glyphs_datetime(string):
    """Parse a datetime object from a string, ignoring the timezone."""
    return datetime.strptime(string[:string.rfind(' ')], '%Y-%m-%d %H:%M:%S')


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
