# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Florent Fourcot
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

from __future__ import print_function

from decimal import Decimal

from weboob.capabilities.base import empty
from weboob.capabilities.shop import CapShop, Order, Payment, Item
from weboob.tools.application.repl import ReplApplication, defaultcount
from weboob.tools.application.formatters.iformatter import PrettyFormatter, IFormatter
from weboob.tools.application.base import MoreResultsAvailable
from weboob.core import CallErrors

__all__ = ['Shopoob']


class OrdersFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'discount', 'shipping', 'tax', 'total')

    def start_format(self, **kwargs):
        self.output('%sId                Date      Discount   Shipping     Tax       Total  ' % ((' ' * 15) if not self.interactive else ''))
        self.output('-------------%s+------------+----------+----------+----------+----------' % (('-' * 15) if not self.interactive else ''))

    def format_obj(self, obj, alias):
        date = obj.date.strftime('%Y-%m-%d') if not empty(obj.date) else ''
        discount = obj.discount or Decimal('0')
        shipping = obj.shipping or Decimal('0')
        tax = obj.tax or Decimal('0')
        total = obj.total or Decimal('0')
        result = u'%s  %s  %s  %s  %s  %s' % (self.colored('%-28s' % obj.fullid, 'yellow'),
                                 self.colored('%-10s' % date, 'blue'),
                                 self.colored('%9.2f' % discount, 'green'),
                                 self.colored('%9.2f' % shipping, 'green'),
                                 self.colored('%9.2f' % tax, 'green'),
                                 self.colored('%9.2f' % total, 'green'))

        return result

    def flush(self):
        self.output(u'-------------%s+------------+----------+----------+----------+----------' % (('-' * 15) if not self.interactive else ''))

class ItemsFormatter(IFormatter):
    MANDATORY_FIELDS = ('label', 'url', 'price')

    def start_format(self, **kwargs):
        self.output('                                    Label                                                           Url                       Price   ')
        self.output('---------------------------------------------------------------------------+---------------------------------------------+----------')

    def format_obj(self, obj, alias):
        price = obj.price or Decimal('0')
        result = u'%s  %s  %s' % (self.colored('%-75s' % obj.label[:75], 'yellow'),
                                 self.colored('%-43s' % obj.url, 'magenta'),
                                 self.colored('%9.2f' % price, 'green'))

        return result

    def flush(self):
        self.output(u'---------------------------------------------------------------------------+---------------------------------------------+----------')

class PaymentsFormatter(IFormatter):
    MANDATORY_FIELDS = ('date', 'method', 'amount')

    def start_format(self, **kwargs):
        self.output('   Date          Method        Amount  ')
        self.output('-----------+-----------------+----------')

    def format_obj(self, obj, alias):
        date = obj.date.strftime('%Y-%m-%d') if not empty(obj.date) else ''
        amount = obj.amount or Decimal('0')
        result = u'%s  %s  %s' % (self.colored('%-10s' % date, 'blue'),
                                 self.colored('%-17s' % obj.method, 'yellow'),
                                 self.colored('%9.2f' % amount, 'green'))

        return result

    def flush(self):
        self.output(u'-----------+-----------------+----------')
        
class Shopoob(ReplApplication):
    APPNAME = 'shopoob'
    VERSION = '1.1'
    COPYRIGHT = 'Copyright(C) 2015 Christophe Lampin'
    DESCRIPTION = 'Console application to obtain details and status of e-commerce orders.'
    SHORT_DESCRIPTION = "obtain details and status of e-commerce orders"
    CAPS = CapShop
    COLLECTION_OBJECTS = (Order, )
    EXTRA_FORMATTERS = {'orders':   OrdersFormatter,
                        'items':   ItemsFormatter,
                        'payments':   PaymentsFormatter
                        }
    DEFAULT_FORMATTER = 'table'
    COMMANDS_FORMATTERS = {'orders':    'orders',
                           'items':     'items',
                           'payments':  'payments',
                           'ls':        'orders',
                          }

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    @defaultcount(10)
    def do_orders(self, line):
        """
        orders

        List all orders.
        """
        self.start_format()
        for order in self.do('iter_orders'):
            self.format(order)

    def do_items(self, id):
        """
        items [ID]

        Get items of orders.
        If no ID given, display all details of all backends.
        """
        l = []
        id, backend_name = self.parse_id(id)

        if not id:
            for order in self.get_object_list('iter_orders'):
                l.append((order.id, order.backend))
        else:
            l.append((id, backend_name))

        for id, backend in l:
            names = (backend,) if backend is not None else None
            # XXX: should be generated by backend? -Flo
            # XXX: no, but you should do it in a specific formatter -romain
            # TODO: do it, and use exec_method here. Code is obsolete
            mysum = Item()
            mysum.label = u"Sum"
            mysum.url = u"Generated by shopoob"
            mysum.price = Decimal("0.")

            self.start_format()
            for item in self.do('iter_items', id, backends=names):
                self.format(item)
                mysum.price = item.price + mysum.price

            self.format(mysum)

    def do_payments(self, id):
        """
        payments [ID]

        Get payments of orders.
        If no ID given, display payment of all backends.
        """
        self.start_format()
        for payment in self.do('iter_payments', id):
            self.format(payment)

