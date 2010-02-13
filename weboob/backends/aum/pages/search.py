# -*- coding: utf-8 -*-

"""
Copyright(C) 2008  Romain Bignon

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

import ClientForm
from weboob.backends.aum.pages.profileslist_base import ProfilesListBase

class SearchPage(ProfilesListBase):

    SHOW_WITHOUT_PHOTO = False

    def set_field(self, args, label, field=None, value=None, is_list=False):
        try:
            if not field:
                field = label
            if args.get(label, None) is not None:
                if not value:
                    if is_list:
                        value = [str(args[label])]
                    else:
                        value = str(args[label])
                self.browser[field] = value
        except ClientForm.ControlNotFoundError:
            return

    def search(self, **kwargs):

        self.browser.select_form(name="form")
        self.browser.set_all_readonly(False)

        self.set_field(kwargs, 'ageMin', is_list=True)
        self.set_field(kwargs, 'ageMax', is_list=True)
        self.set_field(kwargs, 'country', is_list=True)
        self.set_field(kwargs, 'dist', is_list=True)
        self.set_field(kwargs, 'nickname', field='pseudo')
        self.set_field(kwargs, 'save', value='true')

        self.browser.submit()
