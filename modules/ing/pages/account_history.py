# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Florent Fourcot
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

import re
import hashlib

from decimal import Decimal
from datetime import date

from weboob.tools.browser import BasePage
from weboob.tools.mech import ClientForm
from weboob.capabilities.bank import Transaction
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['AccountHistory']


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^retrait dab (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^carte (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), Transaction.TYPE_CARD),
                (re.compile(u'^virement ((sepa emis vers|emis vers|recu|emis)?) (?P<text>.*)'), Transaction.TYPE_TRANSFER),
                (re.compile(u'^prelevement (?P<text>.*)'), Transaction.TYPE_ORDER),
                ]


class AccountHistory(BasePage):
    def on_loaded(self):
        pass

    def get_transactions(self):
        table = self.document.findall('//tbody')[0]
        for tr in table.xpath('tr'):
            textdate = tr.find('td[@class="op_date"]').text_content()
            textraw = tr.find('td[@class="op_label"]').text_content().strip()
            textraw = re.sub(' +', ' ', textraw)
            # The id will be rewrite
            op = Transaction(1)
            amount = op.clean_amount(tr.find('td[@class="op_amount"]').text_content())
            id = hashlib.md5(textdate + textraw.encode('utf-8') + amount.encode('utf-8')).hexdigest()
            op.id = id
            op.parse(date = date(*reversed([int(x) for x in textdate.split('/')])),
                     raw = textraw)
            # force the use of website category
            op.category = unicode(tr.find('td[@class="op_type"]').text)

            op.amount = Decimal(amount)

            yield op

    def islast(self):
        form = self.document.find('//form[@id="navigation_form"]')
        alinks = form.xpath('div/a')
        for a in alinks:
            if u'Page Suivante' in a.text:
                self.next = a.attrib['id']
                return False
        return True

    def next_page(self):
        self.browser.select_form('navigation_form')
        self.browser.set_all_readonly(False)
        self.browser.controls.append(ClientForm.TextControl('text', 'AJAXREQUEST', {'value': ''}))
        self.browser['AJAXREQUEST'] = '_viewRoot'
        self.browser.controls.append(ClientForm.TextControl('text', self.next, {'value': ''}))
        self.browser[self.next] = self.next
        self.browser.submit()
