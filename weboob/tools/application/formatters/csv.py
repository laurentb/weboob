# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from .iformatter import IFormatter


__all__ = ['CSVFormatter']


class CSVFormatter(IFormatter):
    def __init__(self, field_separator=u';'):
        IFormatter.__init__(self)
        self.field_separator = field_separator
        self.count = 0

    def flush(self):
        pass

    def format_dict(self, item):
        result = u''
        if self.count == 0:
            result += self.field_separator.join(item.iterkeys()) + '\n'
        self.count += 1
        result += self.field_separator.join(unicode(v) for v in item.itervalues())
        return result
