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
from weboob.capabilities.bill import Subscription, Bill
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
        for i in xrange(self.MAX_RETRIES):
            if (self.order_new.is_here() or self.order_old.is_here()) \
                    and self.page.order_number() == order_id:
                return self.page
            try:
                self.order_new.go(order_id=order_id)
            except HTTPNotFound:
                self.order_old.go(order_id=order_id)
        raise OrderNotFound()

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

    @need_login
    def get_subscription_list(self):
        sub = Subscription()
        sub.label = u'amazon'
        sub.id = u'amazon'
        yield sub

    @need_login
    def iter_bills(self, subscription):
        orders = self.iter_orders()
        for o in orders:
            b = Bill()
            b._url = o._bill['url']
            b.id = '%s.%s' % (subscription.id, o.id)
            b.date = o.date
            b.price = o.total
            b.format = o._bill['format']
            b.currency = b.get_currency(self.get_currency())
            b.vat = o.tax
            yield b

LOGIN_JS = u'''\
var TIMEOUT = %(timeout)s*1000; // milliseconds
var page = require('webpage').create();
page.settings.userAgent = "%(agent)s";
page.open('%(baseurl)s');

var waitForForm = function() {
  var hasForm1 = page.evaluate(function(){
    return !!document.getElementById('ap_signin_form')
  });
  var hasForm2 = page.evaluate(function(){
    return document.getElementsByName('signIn').length > 0;
  });
  if (hasForm1) {
    page.evaluate(function(){
      document.getElementById('ap_email').value = '%(username)s';
      document.getElementById('ap_password').value = '%(password)s';
      document.getElementById('ap_signin_form').submit();
    });
  } else if (hasForm2) {
    page.evaluate(function(){
      document.getElementById('ap_email').value = '%(username)s';
      document.getElementById('ap_password').value = '%(password)s';
      document.getElementsByName('signIn').item(0).submit();
    });
  } else {
    setTimeout(waitForForm, 1000);
  }
}

var waitForLink = function() {
  var hasLink1 = page.evaluate(function(){
    return !!document.getElementById('nav-link-yourAccount');
  });
  var hasLink2 = page.evaluate(function(){
    return !!document.getElementById('nav-your-account');
  });
  var hasLink3 = page.evaluate(function(){
    return !!document.getElementById('nav-signin-tooltip');
  });
  if (hasLink1) {
    page.evaluate(function(){
      var a = document.getElementById('nav-link-yourAccount');
      window.location = a.getAttribute('href');
    });
  } else if (hasLink2) {
    page.evaluate(function(){
      var a = document.getElementById('nav-your-account');
      window.location = a.getAttribute('href');
    });
  } else if (hasLink3) {
    page.evaluate(function(){
      var d = document.getElementById('nav-signin-tooltip');
      var a = d.getElementsByClassName('nav-action-button')[0];
      window.location = a.getAttribute('href');
    });
  } else {
    setTimeout(waitForLink, 1000);
  }
}

var waitForLogin = function() {
  var hasSignOut = page.content.indexOf('Sign Out') != -1;
  if (hasSignOut) {
    var cookies = JSON.stringify(phantom.cookies);
    require('fs').write('%(output)s', cookies, 'w');
    phantom.exit();
  } else {
    setTimeout(waitForLogin, 2000);
  }
}

waitForForm();
waitForLink();
waitForLogin();
setTimeout(function(){phantom.exit(-1);}, TIMEOUT);
'''
