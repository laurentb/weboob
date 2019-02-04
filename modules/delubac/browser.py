# -*- coding: utf-8 -*-

# Copyright(C) 2015 Romain Bignon
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

from __future__ import unicode_literals

import time

from weboob.browser import URL, need_login, AbstractBrowser

from .pages import LoginPage, MenuPage


__all__ = ['DelubacBrowser']


class DelubacBrowser(AbstractBrowser):
    PARENT = 'themisbanque'
    PARENT_ATTR = 'package.browser.ThemisBrowser'

    BASEURL = 'https://e.delubac.com'

    login = URL('/es@b/fr/codeident.jsp',
                '/es@b/servlet/internet0.ressourceWeb.servlet.Login', LoginPage)
    menu = URL('/es@b/fr/menuConnecte1.jsp\?c&deploye=false&pulseMenu=false&styleLien=false&dummyDate=(?P<date>.*)', MenuPage)

    @need_login
    def iter_accounts(self):
        self.menu.go(date=int(time.time()*1000))
        self.location(self.page.accounts_url)
        for account in self.page.iter_accounts():
            yield account
