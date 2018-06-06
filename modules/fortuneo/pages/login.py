# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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


from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import CleanText
from weboob.exceptions import BrowserUnavailable


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        msg = CleanText(".//*[@id='message_client']/text()")(self.doc)

        if "maintenance" in msg:
            raise BrowserUnavailable(msg)

        form = self.get_form(name="acces_identification")
        form['login'] = login
        form['passwd'] = passwd
        form.submit()


class UnavailablePage(HTMLPage):
    def on_load(self):
        raise BrowserUnavailable(CleanText('//h2[@class="titre"]')(self.doc))
