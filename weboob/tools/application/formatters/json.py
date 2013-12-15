# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Hebert
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


from weboob.tools.json import json

from .iformatter import IFormatter

__all__ = ['JsonFormatter']


class Encoder(json.JSONEncoder):
    "generic weboob object encoder"

    def default(self, obj):
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            try:
                dct = obj.to_dict()
            except AttributeError:
                return str(obj)
            for z in dct:
                return z


class JsonFormatter(IFormatter):
    def __init__(self):
        IFormatter.__init__(self)
        self.queue = []

    def flush(self):
        if len(self.queue) == 0:
            return
        elif len(self.queue) == 1:
            print self.queue[0]
        else:
            result = u""
            first = False
            result += u"["
            for item in self.queue:
                if not first:
                    first = True
                else:
                    result += u","
                result += item
            result += "]"
            print result

    def format_dict(self, item):
        self.queue.append(json.dumps(item, cls=Encoder))
