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

from weboob.backends.aum.pages.base import PageBase
import re

class ProfilesListBase(PageBase):

    PROFILE_REGEXP = re.compile(".*window\.location='(.*)'")
    PHOTO_REGEXP = re.compile(".*background-image:url\(([A-Za-z0-9_\-:/\.]+)\).*")
    WITHOUT_PHOTO = 'http://s.adopteunmec.com/img/thumb0.gif'
    SHOW_WITHOUT_PHOTO = True

    def loaded(self):

        self.id_list = []

        a_list = self.document.getElementsByTagName('div')
        for a in a_list:
            if a.hasAttribute('onclick') and a.hasAttribute('class') and a.getAttribute('class') in ('small', 'mini'):
                m = self.PROFILE_REGEXP.match(a.getAttribute('onclick'))
                if m:
                    url = m.group(1).split('/')[-1]
                    m = self.PHOTO_REGEXP.match(a.getElementsByTagName('div')[0].getAttribute('style'))
                    if url != 'home.php' and not url in self.id_list and \
                       m and (self.SHOW_WITHOUT_PHOTO or m.group(1) != self.WITHOUT_PHOTO):
                        self.id_list.append(url)

    def getProfilesIDs(self):
        return set(self.id_list)

    def getProfilesIDsList(self):
        return self.id_list
