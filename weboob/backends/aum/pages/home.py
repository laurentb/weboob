# -*- coding: utf-8 -*-

# Copyright(C) 2008-2011  Romain Bignon
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

from weboob.backends.aum.pages.base import PageBase

class HomePage(PageBase):
    MYID_REGEXP = re.compile("http://www.adopteunmec.com/\?mid=(\d+)")

    def get_my_id(self):
        fonts = self.document.getElementsByTagName('font')
        for font in fonts:
            m = self.MYID_REGEXP.match(font.firstChild.data)
            if m:
                return m.group(1)

        self.browser.logger.error("Error: Unable to find my ID")
        return 0

    def __get_home_indicator(self, pos, what):
        tables = self.document.getElementsByTagName('table')
        for table in tables:
            if table.hasAttribute('style') and table.getAttribute('style') == 'background-color:black;background-image:url(http://s.adopteunmec.com/img/barmec.gif);background-repeat:no-repeat':
                fonts = table.getElementsByTagName('font')
                i = 0
                for font in fonts:
                    if font.hasAttribute('color') and font.getAttribute('color') == '#ff0198':
                        i += 1
                        if i == pos:
                            return int(font.firstChild.data)
        self.browser.logger.error(u'Could not parse number of %s' % what)
        return 0

    def nb_available_charms(self):
        return self.__get_home_indicator(3, 'available charms')

    def nb_godchilds(self):
        return self.__get_home_indicator(2, 'godchilds')
