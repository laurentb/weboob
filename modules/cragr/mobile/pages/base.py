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


from weboob.deprecated.browser import Page
from weboob.deprecated.browser import BrowserUnavailable


class CragrBasePage(Page):
    def on_loaded(self):
        # Check for an error
        for div in self.document.getiterator('div'):
            if div.attrib.get('class', '') == 'dv' and div.getchildren()[0].tag in ('img') and div.getchildren()[0].attrib.get('alt', '') == 'Attention':
                # Try to find a detailed error message
                if div.getchildren()[1].tag == 'span':
                    raise BrowserUnavailable(div.find('span').find('b').text)
                elif div.getchildren()[1].tag == 'b':
                    # I haven't encountered this variation in the wild,
                    # but I wouldn't be surprised if it existed
                    # given the similar differences between regions.
                    raise BrowserUnavailable(div.find('b').find('span').text)
                raise BrowserUnavailable()

    def is_logged(self):
        return not self.document.xpath('/html/body//form//input[@name = "code"]') and \
           not self.document.xpath('/html/body//form//input[@name = "userPassword"]')
