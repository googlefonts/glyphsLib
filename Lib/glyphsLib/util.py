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

import logging
import os
import shutil
from fontTools.misc.textTools import num2binary

logger = logging.getLogger(__name__)


def build_ufo_path(out_dir, family_name, style_name):
    """Build string to use as a UFO path."""

    return os.path.join(
        out_dir, '%s-%s.ufo' % (
            family_name.replace(' ', ''),
            style_name.replace(' ', '')))


def write_ufo(ufo, out_dir):
    """Write a UFO."""

    out_path = build_ufo_path(
        out_dir, ufo.info.familyName, ufo.info.styleName)

    logger.info('Writing %s' % out_path)
    clean_ufo(out_path)
    ufo.save(out_path)


def clean_ufo(path):
    """Make sure old UFO data is removed, as it may contain deleted glyphs."""

    if path.endswith('.ufo') and os.path.exists(path):
        shutil.rmtree(path)


def cast_to_number_or_bool(inputstr):
    """Cast a string to int, float or bool. Return original string if it can't be
    converted.

    Scientific expression is converted into float.
    """
    if inputstr.strip().lower() == 'true':
        return True
    elif inputstr.strip().lower() == 'false':
        return False
    try:
        return int(inputstr)
    except ValueError:
        try:
            return float(inputstr)
        except ValueError:
            return inputstr


def bin_to_int_list(value):
    string = num2binary(value)
    return [i for i, v in enumerate(reversed(string)) if v == "1"]
