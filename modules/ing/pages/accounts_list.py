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


from decimal import Decimal
from datetime import date, timedelta
import re
import hashlib

from weboob.capabilities.bank import Account, Currency, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage, BrowserUnavailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['AccountsList']

class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^retrait dab (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^carte (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), Transaction.TYPE_CARD),
                (re.compile(u'^virement ((sepa emis vers|emis vers|recu|emis)?) (?P<text>.*)'), Transaction.TYPE_TRANSFER),
                (re.compile(u'^prelevement (?P<text>.*)'), Transaction.TYPE_ORDER),
                ]


class AccountsList(BasePage):
    def on_loaded(self):
        pass

    monthvalue = {u'janv.': '01', u'févr.': '02', u'mars': '03', u'avr.': '04',
            u'mai': '05', u'juin': '06', u'juil.': '07', u'août': '08',
            u'sept.': '09', u'oct.': '10', u'nov.': '11', u'déc.': '12',
            }
    def get_list(self):
        # TODO: no idea abount how proxy account are displayed
        for a in self.document.xpath('//a[@class="mainclic"]'):
            account = Account()
            account.currency = Currency.CUR_EUR
            account.id = unicode(a.find('span[@class="account-number"]').text)
            account._id = account.id
            account.label = unicode(a.find('span[@class="title"]').text)
            balance = a.find('span[@class="solde"]/label').text
            account.balance = Decimal(FrenchTransaction.clean_amount(balance))
            account.coming = NotAvailable
            if "Courant" in account.label:
                account.id = "CC-" + account.id
            elif "Livret A" in account.label:
                account.id = "LA-" + account.id
            elif "Orange" in account.label:
                account.id = "LEO-" + account.id
            elif "Titres" in account.label:
                account.id = "TITRE-" + account.id
            elif "PEA" in account.label:
                account.id = "PEA-" + account.id
            jid = self.document.find('//input[@name="javax.faces.ViewState"]')
            account._jid = jid.attrib['value']
            yield account

    def get_transactions(self):
        for table in self.document.xpath('//table[@cellpadding="0"]'):
            try:
                textdate = table.find('.//td[@class="elmt tdate"]').text_content()
            except AttributeError:
                continue
            if textdate == 'hier':
                textdate = (date.today() - timedelta(days=1)).strftime('%d/%m/%Y')
            elif textdate == "aujourd'hui":
                textdate = date.today().strftime('%d/%m/%Y')
            else:
                frenchmonth = textdate.split(' ')[1]
                month = self.monthvalue[frenchmonth]
                textdate = textdate.replace(' ', '')
                textdate = textdate.replace(frenchmonth, '/%s/' %month)
            # We use lower for compatibility with old website
            textraw = table.find('.//td[@class="elmt lbl"]').text_content().strip().lower()
            # The id will be rewrite
            op = Transaction(1)
            amount = op.clean_amount(table.xpath('.//td[starts-with(@class, "elmt amount")]')[0].text_content())
            id = hashlib.md5(textdate.encode('utf-8') + textraw.encode('utf-8')
                    + amount.encode('utf-8')).hexdigest()
            op.id = id
            op.parse(date = date(*reversed([int(x) for x in textdate.split('/')])),
                    raw = textraw)
            # force the use of website category
            #op.category = unicode(tr.find('td[@class="op_type"]').text)
            op.amount = Decimal(amount)
            yield op

    def islast(self):
        return True
