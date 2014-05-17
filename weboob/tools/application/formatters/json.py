# -*- coding: utf-8 -*-

# Copyright(C) 2013-2014 Julien Hebert, Laurent Bachelier
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


from __future__ import print_function

from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.json import json

from .iformatter import IFormatter

__all__ = ['JsonFormatter', 'JsonLineFormatter']


class Encoder(json.JSONEncoder):
    "generic weboob object encoder"

    def default(self, obj):
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            if obj is NotAvailable or obj is NotLoaded:
                return None

            try:
                dct = obj.to_dict()
            except AttributeError:
                return str(obj)
            return dct


class JsonFormatter(IFormatter):
    """
    Formats the whole list as a single JSON list object.
    """
    def __init__(self):
        IFormatter.__init__(self)
        self.queue = []

    def flush(self):
        print(json.dumps(self.queue, cls=Encoder))

    def format_dict(self, item):
        self.queue.append(item)


class JsonLineFormatter(IFormatter):
    """
    Formats the list as received, with a JSON object per line.
    The advantage is that it can be streamed.
    """
    def format_dict(self, item):
        print(json.dumps(item, cls=Encoder))
