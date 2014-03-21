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

from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['AccountsList']


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^retrait dab (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^carte (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_CARD),
                (re.compile(u'^virement (sepa )?(emis vers|recu|emis)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(u'^cheque (?P<text>.*)'), FrenchTransaction.TYPE_CHECK),
                (re.compile(u'^prelevement (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^prélèvement sepa en faveur de (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
                ]


class AccountsList(BasePage):
    def on_loaded(self):
        pass

    monthvalue = {u'janv.': '01', u'févr.': '02', u'mars': '03', u'avr.': '04',
            u'mai': '05', u'juin': '06', u'juil.': '07', u'août': '08',
            u'sept.': '09', u'oct.': '10', u'nov.': '11', u'déc.': '12',
            }
    catvalue = {u'virt': u"Virement", u'autre': u"Autre",
            u'plvt': u'Prélèvement', u'cb_ret': u"Carte retrait",
            u'cb_ach': u'Carte achat', u'chq': u'Chèque',
            u'frais': u'Frais bancaire', u'sepaplvt': u'Prélèvement'}

    def get_list(self):
        # TODO: no idea abount how proxy account are displayed
        for a in self.document.xpath('//a[@class="mainclic"]'):
            account = Account()
            account.currency = u'EUR'
            account.id = unicode(a.find('span[@class="account-number"]').text)
            account._id = account.id
            account.label = unicode(a.find('span[@class="title"]').text)
            balance = a.find('span[@class="solde"]/label').text
            account.balance = Decimal(FrenchTransaction.clean_amount(balance))
            account.coming = NotAvailable
            if "Courant" in account.label:
                account.id = "CC-" + account.id
                account.type = Account.TYPE_CHECKING
            elif "Livret A" in account.label:
                account.id = "LA-" + account.id
                account.type = Account.TYPE_SAVINGS
            elif "Orange" in account.label:
                account.id = "LEO-" + account.id
                account.type = Account.TYPE_SAVINGS
            elif "Durable" in account.label:
                account.id = "LDD-" + account.id
                account.type = Account.TYPE_SAVINGS
            elif "Titres" in account.label:
                account.id = "TITRE-" + account.id
                account.type = Account.TYPE_MARKET
            elif "PEA" in account.label:
                account.id = "PEA-" + account.id
                account.type = Account.TYPE_MARKET
            jid = self.document.find('//input[@name="javax.faces.ViewState"]')
            account._jid = jid.attrib['value']
            yield account

    def get_transactions(self, index):
        i = 0
        for table in self.document.xpath('//table'):
            try:
                textdate = table.find('.//td[@class="date"]').text_content()
            except AttributeError:
                continue
            # Do not parse transactions already parsed
            if i < index:
                i += 1
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
            textraw = self.parser.tocleanstring(table.find('.//td[@class="lbl"]')).lower()
            # The id will be rewrite
            op = Transaction(1)
            amount = op.clean_amount(table.xpath('.//td[starts-with(@class, "amount")]')[0].text_content())
            id = hashlib.md5(textdate.encode('utf-8') + textraw.encode('utf-8')
                    + amount.encode('utf-8')).hexdigest()
            op.id = id
            op.parse(date = date(*reversed([int(x) for x in textdate.split('/')])),
                     raw = textraw)
            category = table.find('.//td[@class="picto"]/span')
            category = unicode(category.attrib['class'].split('-')[0].lower())
            try:
                op.category = self.catvalue[category]
            except:
                op.category = category
            op.amount = Decimal(amount)
            yield op

    def get_history_jid(self):
        span = self.document.xpath('//span[@id="index:panelASV"]')
        if len(span) > 1:
            # Assurance Vie, we do not support this kind of account.
            return None

        span = self.document.xpath('//span[starts-with(@id, "index:j_id")]')[0]
        jid = span.attrib['id'].split(':')[1]
        return jid

    def islast(self):
        havemore = self.document.getroot().cssselect('.show-more-transactions')
        if len(havemore) == 0:
            return True

        nomore = self.document.getroot().cssselect('.no-more-transactions')
        if len(nomore) > 0:
            return True
        else:
            return False
