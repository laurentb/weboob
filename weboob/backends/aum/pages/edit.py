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

class EditPhotoPage(PageBase):
    def addPhoto(self, name, f):
        self.browser.select_form(name="form")
        self.browser.find_control('uploaded').add_file(f, 'image/jpeg', name)
        self.browser.submit()
        self.browser.openurl('http://www.adopteunmec.com/home.php')

class EditPhotoCbPage(PageBase):
    # Do nothing
    pass

class EditAnnouncePage(PageBase):
    def setNickname(self, nickname):
        self.browser.select_form(name="form")
        self.browser['pseudo'] = nickname
        self.browser.submit()

    def setAnnounce(self, title=None, description=None, lookingfor=None):
        self.browser.select_form(name="form")
        if title is not None:
            self.browser['title'] = title
        if description is not None:
            self.browser['about1'] = description
        if lookingfor is not None:
            self.browser['about2'] = lookingfor

        self.browser.submit()

class EditDescriptionPage(PageBase):
    pass

class EditSexPage(PageBase):
    pass

class EditPersonalityPage(PageBase):
    pass
