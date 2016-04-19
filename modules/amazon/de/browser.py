# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.browser import URL
from ..browser import Amazon

from weboob.exceptions import BrowserIncorrectPassword

from .pages import OrderNewPageDE
from ..pages import HomePage

__all__ = ['AmazonDE']


class AmazonDE(Amazon):
    BASEURL = 'https://www.amazon.de'
    CURRENCY = u'€'
    home = URL(r'/$', r'.*/homepage\.html.*', HomePage)
    order_new = URL(r'/gp/css/summary.*$',
                    r'/gp/your-account/order-details.*$',
                    r'/gp/your-account/order-details\?orderID=%\(order_id\)s',
                    OrderNewPageDE)

    def do_login(self):
        self.session.cookies.clear()

        self.home.go().to_login().login(self.username, self.password)

        # Switch language to english
        self.page.to_switchlanguage()

        if not self.page.logged:
            raise BrowserIncorrectPassword()
