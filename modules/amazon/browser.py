# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
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


from requests.exceptions import Timeout, ConnectionError

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ServerError, HTTPNotFound
from weboob.capabilities.shop import OrderNotFound
from weboob.exceptions import BrowserIncorrectPassword

from .pages import HomePage, LoginPage, AmazonPage, HistoryPage, \
    OrderOldPage, OrderNewPage

__all__ = ['Amazon']


class Amazon(LoginBrowser):
    BASEURL = 'https://www.amazon.com'
    MAX_RETRIES = 10
    CURRENCY = u'$'
    home = URL(r'/$', r'http://www.amazon.com/$', HomePage)
    login = URL(r'/ap/signin/.*$', LoginPage)
    history = URL(r'/gp/css/order-history.*$', HistoryPage)
    order_old = URL(r'/gp/css/summary.*$',
                    r'/gp/css/summary/edit.html\?orderID=%\(order_id\)s',
                    r'/gp/digital/your-account/order-summary.html.*$',
                    r'/gp/digital/your-account/orderPe-summary.html\?orderID=%\(order_id\)s',
                    OrderOldPage)
    order_new = URL(r'/gp/css/summary.*$',
                    r'/gp/your-account/order-details.*$',
                    r'/gp/your-account/order-details\?orderID=%\(order_id\)s',
                    OrderNewPage)
    unknown = URL(r'/.*$', AmazonPage)

    def get_currency(self):
        return self.CURRENCY

    def get_order(self, id_):
        order = self.to_order(id_).order()
        if order:
            return order
        else:
            raise OrderNotFound()

    def iter_orders(self):
        histRoot = self.to_history()
        for histYear in histRoot.iter_years():
            for order in histYear.iter_orders():
                if order.order():
                    yield order.order()

    def iter_payments(self, order):
        return self.to_order(order.id).payments()

    def iter_items(self, order):
        return self.to_order(order.id).items()

    @need_login
    def to_history(self):
        self.history.stay_or_go()
        assert self.history.is_here()
        return self.page

    @need_login
    def to_order(self, order_id):
        """
        Amazon updates its website in stages: they reroute a random part of
        their users to new pages, and the rest to old ones.
        """
        if (not self.order_new.is_here() and not self.order_old.is_here()) \
                or self.page.order_number() != order_id:
            try:
                self.order_new.go(order_id=order_id)
            except HTTPNotFound:
                self.order_old.go(order_id=order_id)
        if (not self.order_new.is_here() and not self.order_old.is_here()) \
                or self.page.order_number() != order_id:
            raise OrderNotFound()
        return self.page

    def do_login(self):
        self.session.cookies.clear()
        self.home.go().to_login().login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

    def location(self, *args, **kwargs):
        """
        Amazon throws 500 HTTP status code for apparently valid requests
        from time to time. Requests eventually succeed after retrying.
        """
        for i in xrange(self.MAX_RETRIES):
            try:
                return super(Amazon, self).location(*args, **kwargs)
            except (ServerError, Timeout, ConnectionError) as e:
                pass
        raise e
