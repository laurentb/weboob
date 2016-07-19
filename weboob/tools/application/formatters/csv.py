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

from __future__ import absolute_import
import csv

from .iformatter import IFormatter

__all__ = ['CSVFormatter']


class CSVFormatter(IFormatter):
    def __init__(self, field_separator=";"):
        super(CSVFormatter, self).__init__()
        self.started = False
        self.field_separator = field_separator

    def flush(self):
        self.started = False

    def format_dict(self, item):
        if not isinstance(self.outfile, basestring):
            return self.write_dict(item, self.outfile)

        with open(self.outfile, "a+") as fp:
            return self.write_dict(item, fp)

    def write_dict(self, item, fp):
        writer = csv.writer(fp, delimiter=self.field_separator)
        if not self.started:
            writer.writerow([unicode(v).encode('utf-8') for v in item.keys()])
            self.started = True

        writer.writerow([unicode(v).encode('utf-8') for v in item.itervalues()])
