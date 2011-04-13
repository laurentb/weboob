# -*- coding: utf-8 -*-

# Copyright(C) 2011 Laurent Bachelier
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


from weboob.tools.browser import BasePage

from urlparse import urlparse
import re

__all__ = ['PastePage']

class PastePage(BasePage):
    def fill_paste(self, paste):
        root = self.document.getroot()
        header = self.parser.select(root, 'id("content")//h3', 1, 'xpath')
        matches = re.match(r'Posted by (?P<author>.+) on (?P<date>.+) \(', header.text)
        paste.title = matches.groupdict().get('author')
        paste.contents = self.parser.select(root, '//textarea[@id="code"]', 1, 'xpath').text
        return paste

    def get_id(self):
        """
        Find out the ID from the URL
        """
        path = urlparse(self.url).path
        return path[1:]
