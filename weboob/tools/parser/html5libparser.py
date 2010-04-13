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

class Html5libParser(HTMLParser):
    def __init__(self, api='etree'):
        HTMLParser.__init__(self, tree=treebuilders.getTreeBuilder(api, ElementTree))

    def parse(self, data, encoding):
        return HTMLParser.parse(self, data, encoding=encoding)
