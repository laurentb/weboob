# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

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

# XXX Currently, elementtidy segfaults when there are no error, because of
# the behavior of libtidy.
# A patch has been sent to Debian:
# http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=576343
#
# As it is not integrated in Debian yet, and as this problem persists on other
# systems, using elementtidy is for now to avoid.

from elementtidy import TidyHTMLTreeBuilder
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

from .iparser import IParser


__all__ = ['ElementTidyParser']


class ElementTidyParser(IParser):
    def parse(self, data, encoding=None):
        TidyHTMLTreeBuilder.ElementTree = ElementTree
        HTMLTreeBuilder = TidyHTMLTreeBuilder.TidyHTMLTreeBuilder
        parser = HTMLTreeBuilder(encoding)
        tree = ElementTree.parse(data, parser)
        for elem in tree.getiterator():
            if elem.tag.startswith('{'):
                elem.tag = elem.tag[elem.tag.find('}')+1:]
        return tree

    def tostring(self, element):
        e = ElementTree.Element('body')
        e.text = element.text
        e.tail = element.tail
        for sub in element.getchildren():
            e.append(sub)
        s = ''
        # XXX OK if it doesn't work with utf-8, the result will be fucking ugly.
        for encoding in ('utf-8', 'ISO-8859-1'):
            try:
                s = ElementTree.tostring(e, encoding)
            except UnicodeError:
                continue
            else:
                break
        return unicode(s)
