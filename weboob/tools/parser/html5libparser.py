# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon, Christophe Benz

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from html5lib import treebuilders, HTMLParser
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

from .iparser import IParser

class Html5libParser(HTMLParser, IParser):
    """
    Parser using html5lib.

    Note that it is not available on every systems.
    """

    # Default implementation for each type of API.
    defaults = {'etree': ElementTree,
               }
    def __init__(self, api='etree'):
        # if no default implementation is defined for this api, set it to None
        # to let getTreeBuilder() using the corresponding implementation.
        implementation = self.defaults.get(api, None)
        HTMLParser.__init__(self, tree=treebuilders.getTreeBuilder(api, implementation))

    def parse(self, data, encoding):
        return HTMLParser.parse(self, data, encoding=encoding)

    def dump(self, elem):
        # TODO
        raise NotImplementedError()
