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

from weboob.backends.aum.pages.profileslist_base import ProfilesListBase

class SearchPage(ProfilesListBase):
    SHOW_WITHOUT_PHOTO = False

    def search(self, **kwargs):
        self.browser.select_form(name="form")
        self.browser.set_all_readonly(False)

        self.browser.set_field(kwargs, 'ageMin', is_list=True)
        self.browser.set_field(kwargs, 'ageMax', is_list=True)
        self.browser.set_field(kwargs, 'country', is_list=True)
        self.browser.set_field(kwargs, 'dist', is_list=True)
        self.browser.set_field(kwargs, 'nickname', field='pseudo')
        self.browser.set_field(kwargs, 'save', value='true')
        self.browser['originsV[]'] = ['1'] # excludes niggers (it doesn't work :( )

        self.browser.submit()
