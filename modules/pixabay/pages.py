# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
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


from weboob.browser.filters.html import Attr
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage


class AccountPage(LoggedPage, HTMLPage):
    pass


class LoginPage(HTMLPage):
    pass


class SearchAPI(JsonPage):
    def get(self):
        return self.doc


class ViewPage(HTMLPage):
    @property
    def type(self):
        return Attr('//*[@class="download_menu"]', 'data-type')(self.doc)

    @property
    def filename(self):
        return Attr('//*[@class="download_menu"]//input[@data-perm="auth"]', 'value')(self.doc)
