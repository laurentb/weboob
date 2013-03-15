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


import re


__all__ = ['IParser', 'RawParser']


class IParser(object):
    def parse(self, data, encoding=None):
        """
        Parse a HTML document with a specific encoding to get a tree.

        @param data  [str] HTML document
        @param encoding  [str] encoding to use
        @return  an object with the structured document
        """
        raise NotImplementedError()

    def tostring(self, elem):
        """
        Get HTML string from an element.
        """
        raise NotImplementedError()

    def tocleanstring(self, elem):
        """
        Get a clean string from an element.
        """
        return self.strip(self.tostring(elem))

    def strip(self, data):
        """
        Strip a HTML string.
        """
        p = re.compile(r'<.*?>')
        return p.sub(' ', data).strip()


class RawParser(IParser):
    def parse(self, data, encoding=None):
        return data.read()

    def tostring(self, elem):
        return elem
