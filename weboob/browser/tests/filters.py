# -*- coding: utf-8 -*-
# Copyright(C) 2016 Matthieu Weber
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.
from unittest import TestCase
from lxml.html import fromstring

from weboob.browser.filters.standard import RawText


class RawTextTest(TestCase):
    # Original RawText behaviour:
    # - the content of <p> is empty, we return the default value
    def test_first_node_is_element(self):
        e = fromstring('<html><body><p></p></body></html>')
        self.assertEqual("foo", RawText('//p', default="foo")(e))

    # - the content of <p> starts with text, we retrieve only that text
    def test_first_node_is_text(self):
        e = fromstring('<html><body><p>blah: <span>229,90</span> EUR</p></body></html>')
        self.assertEqual("blah: ", RawText('//p', default="foo")(e))

    # - the content of <p> starts with a sub-element, we retrieve the default value
    def test_first_node_has_no_recursion(self):
        e = fromstring('<html><body><p><span>229,90</span> EUR</p></body></html>')
        self.assertEqual("foo", RawText('//p', default="foo")(e))

    # Recursive RawText behaviour
    # - the content of <p> starts with text, we retrieve all text, also the text from sub-elements
    def test_first_node_is_text_recursive(self):
        e = fromstring('<html><body><p>blah: <span>229,90</span> EUR</p></body></html>')
        self.assertEqual("blah: 229,90 EUR", RawText('//p', default="foo", children=True)(e))

    # - the content of <p> starts with a sub-element, we retrieve all text, also the text from sub-elements
    def test_first_node_is_element_recursive(self):
        e = fromstring('<html><body><p><span>229,90</span> EUR</p></body></html>')
        self.assertEqual("229,90 EUR", RawText('//p', default="foo", children=True)(e))
