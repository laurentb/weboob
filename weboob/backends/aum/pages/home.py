# -*- coding: utf-8 -*-

"""
Copyright(C) 2008-2010  Romain Bignon

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

import re

from weboob.backends.aum.pages.base import PageBase
from logging import error

class HomePage(PageBase):

    MYID_REGEXP = re.compile("http://www.adopteunmec.com/\?mid=(\d+)")

    def get_my_id(self):
        fonts = self.document.getElementsByTagName('font')
        for font in fonts:
            m = self.MYID_REGEXP.match(font.firstChild.data)
            if m:
                return m.group(1)

        error("Error: Unable to find my ID")
        return 0

    def nb_available_charms(self):
        tables = self.document.getElementsByTagName('table')
        for table in tables:
            if table.hasAttribute('style') and table.getAttribute('style') == 'background-color:black;background-image:url(http://s.adopteunmec.com/img/barmec.gif);background-repeat:no-repeat':

                fonts = table.getElementsByTagName('font')
                i = 0

                for font in fonts:
                    if font.hasAttribute('color') and font.getAttribute('color') == '#ff0198':
                        i += 1
                        if i == 3:
                            return int(font.firstChild.data)

        error('Error: Unable to find the available charms counter')
        return 0
