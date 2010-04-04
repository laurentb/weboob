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

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

try:
    from elementtidy import TidyHTMLTreeBuilder
    TidyHTMLTreeBuilder.ElementTree = ElementTree # force cElementTree if using it.
    HTMLTreeBuilder = TidyHTMLTreeBuilder.TidyHTMLTreeBuilder
except ImportError:
    from HTMLParser import HTMLParser

    class HTMLTreeBuilder(HTMLParser):
        def __init__(self, encoding=None):
            HTMLParser.__init__(self)
            if target is None:
                target = ElementTree.TreeBuilder()
            self._target = target

        def doctype(self, name, pubid, system):
            pass

        def close(self):
            tree = self._target.close()
            return tree

        def handle_starttag(self, tag, attrs):
            self._target.start(tag, dict(attrs))

        def handle_startendtag(self, tag, attrs):
            self._target.start(tag, dict(attrs))
            self._target.end(tag)

        def handle_data(self, data):
            self._target.data(data)

        def handle_endtag(self, tag):
            self._target.end(tag)

class StandardParser(object):
    def parse(self, data, encoding=None):
        parser = HTMLTreeBuilder(encoding)
        tree = ElementTree.parse(data, parser)

        for elem in tree.getiterator():
            if elem.tag.startswith('{'):
                elem.tag = elem.tag[elem.tag.find('}')+1:]
        return tree

def tostring(element):
    e = ElementTree.Element('body')
    e.text = element.text
    e.tail = element.tail
    for sub in element.getchildren():
        e.append(sub)
    s = ElementTree.tostring(e, 'utf-8')
    return unicode(s)
