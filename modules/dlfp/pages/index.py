# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser.pages import HTMLPage, FormNotFound


class DLFPPage(HTMLPage):
    @property
    def logged(self):
        try:
            self.get_form(id='new_account_sidebar')
            return False
        except FormNotFound:
            return True


class IndexPage(DLFPPage):
    def get_login_token(self):
        form = self.get_form(id="new_account_sidebar")
        return form.get('authenticity_token')


class LoginPage(DLFPPage):
    pass
