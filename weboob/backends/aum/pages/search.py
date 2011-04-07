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
        # XXX ho, it doesn't work anymore :(
        #self.browser['originsV[]'] = ['1'] # excludes niggers (it doesn't work :( )

        self.browser.submit()
