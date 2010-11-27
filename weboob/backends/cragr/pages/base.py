# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


from weboob.tools.browser import BasePage
from weboob.tools.browser import BrowserUnavailable

class CragrBasePage(BasePage):
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
        for form in self.document.xpath('/html/body//form//input[@name = "code"]'):
            return False

        return True
