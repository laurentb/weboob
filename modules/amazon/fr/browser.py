# -*- coding: utf-8 -*-

# Copyright(C) 2015      Christophe Lampin
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

from .pages import HomePage, LoginPage, AmazonPage, HistoryPage, \
    OrderOldPage, OrderNewPage

__all__ = ['AmazonFR']


class AmazonFR(Amazon):
    BASEURL = 'https://www.amazon.fr'
    CURRENCY = u'€'
    home = URL(r'/$', r'.*/homepage\.html.*', HomePage)
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
