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


from requests.exceptions import Timeout, ConnectionError, TooManyRedirects

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ServerError, HTTPNotFound
from weboob.capabilities.bill import Subscription, Bill
from weboob.capabilities.shop import OrderNotFound
from weboob.capabilities.base import NotAvailable
from weboob.tools.decorators import retry
from weboob.tools.value import Value
from weboob.exceptions import BrowserIncorrectPassword, CaptchaQuestion

from .pages import HomePage, LoginPage, AmazonPage, HistoryPage, \
    OrderOldPage, OrderNewPage

__all__ = ['Amazon']


class Amazon(LoginBrowser):
    BASEURL = 'https://www.amazon.com'
    MAX_RETRIES = 10
    CURRENCY = u'$'
    home = URL(r'/$', r'http://www.amazon.com/$', HomePage)
    login = URL(r'/ap/signin.*$', LoginPage)
    history = URL(r'/gp/css/order-history.*$',
                  r'/gp/your-account/order-history.*$', HistoryPage)
    order_old = URL(r'/gp/css/summary.*$',
                    r'/gp/css/summary/edit.html\?orderID=%\(order_id\)s',
                    r'/gp/digital/your-account/order-summary.html.*$',
                    r'/gp/digital/your-account/orderPe-summary.html\?orderID=%\(order_id\)s',
                    OrderOldPage)
    order_new = URL(r'/gp/css/summary.*$',
                    r'/gp/your-account/order-details.*$',
                    r'/gp/your-account/order-details\?orderID=%\(order_id\)s',
                    OrderNewPage)
    unknown = URL(r'*', AmazonPage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['email'].get()
        kwargs['password'] = self.config['password'].get()
        super(Amazon, self).__init__(*args, **kwargs)

    def get_currency(self):
        return self.CURRENCY

    def get_order(self, id_):
        order = self.to_order(id_)
        if order:
            return order
        else:
            raise OrderNotFound()

    def iter_orders(self):
        histRoot = self.to_history()
        for histYear in histRoot.iter_years():
            for order in histYear.iter_orders():
                if order:
                    yield order

    def iter_payments(self, order):
        return self.to_order_page(order.id).payments()

    def iter_items(self, order):
        return self.to_order_page(order.id).items()

    @need_login
    def to_history(self):
        self.history.stay_or_go()
        assert self.history.is_here()
        return self.page

    @need_login
    def to_order_page(self, order_id):
        """
        Amazon updates its website in stages: they reroute a random part of
        their users to new pages, and the rest to old ones.
        """
        for i in xrange(self.MAX_RETRIES):
            if (self.order_new.is_here() or self.order_old.is_here()) \
                    and self.page.order_number() == order_id:
                return self.page
            try:
                self.order_new.go(order_id=order_id)
            except HTTPNotFound:
                self.order_old.go(order_id=order_id)
        self.logger.warning('Order %s not found' % order_id)

    @need_login
    def to_order(self, order_id):
        """
        Amazon updates its website in stages: they reroute a random part of
        their users to new pages, and the rest to old ones.
        """

        try:
            return self.to_order_page(order_id).order()
        except AttributeError:
            self.logger.warning('Order %s not found' % order_id)

    def do_login(self):
        if self.config['captcha_response'].get() is not None and self.login.is_here():
            self.page.login(self.username, self.password, self.config['captcha_response'].get())
            self.config['captcha_response'] = Value(value=None)
            if not self.page.logged:
                raise BrowserIncorrectPassword()
            return

        self.session.cookies.clear()
        self.home.go().to_login().login(self.username, self.password)

        if self.login.is_here():
            has_captcha = self.page.has_captcha()
            if not has_captcha:
                raise BrowserIncorrectPassword()
            else:
                raise CaptchaQuestion('image_captcha', image_url=has_captcha)

    def location(self, *args, **kwargs):
        """
        Amazon throws 500 HTTP status code for apparently valid requests
        from time to time. Requests eventually succeed after login again and retrying.
        """
        for i in xrange(self.MAX_RETRIES):
            try:
                return super(Amazon, self).location(*args, **kwargs)
            except (ServerError, Timeout, ConnectionError, TooManyRedirects) as e:
                self.do_login()
                self.logger.warning('Exception %s was caught, retry %d' % (type(e).__name__, i))
                pass
        raise e



    @need_login
    def get_subscription_list(self):
        sub = Subscription()
        sub.label = u'amazon'
        sub.id = u'amazon'
        yield sub

    @need_login
    def iter_documents(self, subscription):
        orders = self.iter_orders()
        for o in orders:
            b = Bill()
            b.url = unicode(o._bill['url'])
            b.id = '%s.%s' % (subscription.id, o.id)
            b.date = o.date
            b.price = o.total
            b.format = o._bill['format']
            b.type = u'bill'
            b.currency = b.get_currency(self.get_currency())
            b.label = '%s %s' % (subscription.label, o.date)
            b.vat = o.tax
            yield b

    @retry(HTTPNotFound)
    @need_login
    def download_document(self, url):
        doc = self.location(url)
        if not self.order_new.is_here():
            return doc.content
        return NotAvailable
