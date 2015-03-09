# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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


import csv

from weboob.tools.log import getLogger
from .iparser import IParser


class Csv(object):
    """
    CSV parser result.
    header contains the first row if it is a header
    rows contains the raw rows
    drows contains the rows with cells indexed by header title
    """

    def __init__(self):
        self.header = None
        self.rows = []
        self.drows = []


class CsvParser(IParser):
    """
    CSV Parser.
    Since CSV files are not normalized, this parser is intended to be derived.
    """
    DIALECT = 'excel'
    FMTPARAMS = {}

    """
    If True, will consider the first line as a header.
    This means the rows will be also available as dictionnaries.
    """
    HEADER = False

    def parse(self, data, encoding=None):
        reader = csv.reader(data, dialect=self.DIALECT, **self.FMTPARAMS)
        c = Csv()
        try:
            for row in reader:
                row = self.decode_row(row, encoding)
                if c.header is None and self.HEADER:
                    c.header = row
                else:
                    c.rows.append(row)
                    if c.header:
                        drow = {}
                        for i, cell in enumerate(row):
                            drow[c.header[i]] = cell
                        c.drows.append(drow)
        except csv.Error as error:
            # If there are errors in CSV, for example the file is truncated, do
            # not crash as there already are lines parsed.
            logger = getLogger('csv')
            logger.warning('Error during parse of CSV: %s', error)
        return c

    def decode_row(self, row, encoding):
        if encoding:
            return [unicode(cell, encoding) for cell in row]
        else:
            return row

    def tostring(self, element):
        if not isinstance(element, basestring):
            return unicode(element)
        return element
