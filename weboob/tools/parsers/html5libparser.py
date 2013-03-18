# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Christophe Benz
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


from html5lib import treebuilders, HTMLParser
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

from .iparser import IParser


__all__ = ['Html5libParser']


class Html5libParser(HTMLParser, IParser):
    """
    Parser using html5lib.

    Note that it is not available on every systems.
    """

    # Default implementation for each type of API.
    defaults = {'etree': ElementTree}

    def __init__(self, api='etree'):
        # if no default implementation is defined for this api, set it to None
        # to let getTreeBuilder() using the corresponding implementation.
        implementation = self.defaults.get(api, None)
        HTMLParser.__init__(self, tree=treebuilders.getTreeBuilder(api, implementation))

    def parse(self, data, encoding):
        return HTMLParser.parse(self, data, encoding=encoding)

    def tostring(self, element):
        return element.toxml()
