# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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


from weboob.browser.pages import HTMLPage


class LoginPage(HTMLPage):
    REFRESH_MAX = 10.0

    def login(self, login, passwd):
        form = self.get_form(xpath='//form[contains(@name, "ident")]')
        form['_cm_user'] = login
        form['_cm_pwd'] = passwd
        form.submit()

    @property
    def logged(self):
        return self.doc.xpath('//div[@id="e_identification_ok"]')
