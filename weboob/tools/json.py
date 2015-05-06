# -*- coding: utf-8 -*-

# Copyright(C) 2012 Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

# because we don't want to import this file by "import json"
from __future__ import absolute_import

__all__ = ['json', 'mini_jsonpath']

try:
    # try simplejson first because it is faster
    import simplejson as json
except ImportError:
    # Python 2.6+ has a module similar to simplejson
    import json


def mini_jsonpath(node, path):
    """
    Evaluates a dot separated path against JSON data. Path can contains
    star wilcards. Always returns a generator.

    Relates to http://goessner.net/articles/JsonPath/ but in a really basic
    and simpler form.

    >>> list(mini_jsonpath({"x": 95, "y": 77, "z": 68}, 'y'))
    [77]
    >>> list(mini_jsonpath({"x": {"y": {"z": "nested"}}}, 'x.y.z'))
    ['nested']
    >>> list(mini_jsonpath('{"data": [{"x": "foo", "y": 13}, {"x": "bar", "y": 42}, {"x": "baz", "y": 128}]}', 'data.*.y'))
    [13, 42, 128]
    """

    def iterkeys(i):
        return range(len(i)) if type(i) is list else i.iterkeys()

    def cut(s):
        p = s.split('.', 1) if s else [None]
        return p + [None] if len(p) == 1 else p

    if isinstance(node, basestring):
        node = json.loads(node)

    queue = [(node, cut(path))]
    while queue:
        node, (name, rest) = queue.pop(0)
        if name is None:
            yield node
            continue
        elif type(node) not in (dict, list):
            continue
        if name == '*':
            keys = iterkeys(node)
        else:
            keys = [int(name) if type(node) is list else name]
        for k in keys:
            queue.append((node[k], cut(rest)))
