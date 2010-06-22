# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import lxml.html

from .iparser import IParser


__all__ = ['LxmlHtmlParser']


class LxmlHtmlParser(IParser):
    """
    Parser using lxml.

    Note that it is not available on every systems.
    """

    def parse(self, data, encoding=None):
        parser = lxml.html.HTMLParser(encoding=encoding)
        return lxml.html.parse(data, parser)

    def tostring(self, element):
        return lxml.html.tostring(element, encoding=unicode)
