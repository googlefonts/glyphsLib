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


def clear_data(data):
    """Clear empty list or dict attributes in data.

    This is used to determine what input data provided to to_ufos was not
    loaded into an UFO."""

    if isinstance(data, dict):
        for key, val in data.items():
            if not clear_data(val):
                del data[key]
        return data
    elif isinstance(data, list):
        i = 0
        while i < len(data):
            val = data[i]
            if not clear_data(val):
                del data[i]
            else:
                i += 1
        return data
    return True
