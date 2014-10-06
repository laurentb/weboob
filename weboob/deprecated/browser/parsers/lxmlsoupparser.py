# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


import lxml.html
import lxml.html.soupparser

from .iparser import IParser


__all__ = ['LxmlSoupParser']


class LxmlSoupParser(IParser):
    """
    Parser using lxml elementsoup.

    Note that it is not available on every systems.
    """

    def parse(self, data, encoding=None):
        return lxml.html.soupparser.parse(data)

    def tostring(self, element):
        return lxml.html.tostring(element, encoding=unicode)
