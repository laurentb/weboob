# -*- coding: utf-8 -*-

# Copyright(C) 2009-2012  Romain Bignon
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
from datetime import date

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Transaction
from weboob.capabilities.base import NotAvailable


__all__ = ['AccountHistory', 'AccountComing']


class TransactionsBasePage(BasePage):
    LABEL_PATTERNS = [(re.compile(u'^CHEQUEN°(?P<no>.*)'),
                                       Transaction.TYPE_CHECK, u'N°%(no)s'),
                      (re.compile('^FACTURE CARTE DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                       Transaction.TYPE_CARD, u'20%(yy)s-%(mm)s-%(dd)s: %(text)s'),
                      (re.compile('^(PRELEVEMENT|TELEREGLEMENT) (?P<text>.*)'),
                                       Transaction.TYPE_ORDER, '%(text)s'),
                      (re.compile('^ECHEANCEPRET(?P<text>.*)'),
                                       Transaction.TYPE_LOAN_PAYMENT, u'n°%(text)s'),
                      (re.compile('^RETRAIT DAB (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2}) (?P<HH>\d+)H(?P<MM>\d+) (?P<text>.*)'),
                                       Transaction.TYPE_WITHDRAWAL, u'20%(yy)s-%(mm)s-%(dd)s %(HH)s:%(MM)s: %(text)s'),
                      (re.compile('^VIREMENT (?P<text>.*)'),
                                       Transaction.TYPE_TRANSFER, u'%(text)s'),
                      (re.compile('^REMBOURST (?P<text>.*)'),
                                       Transaction.TYPE_PAYBACK, '%(text)s'),
                      (re.compile('^COMMISSIONS (?P<text>.*)'),
                                       Transaction.TYPE_BANK, '%(text)s'),
                     ]

    def parse_text(self, op):
        op.category = NotAvailable
        if '  ' in op.text:
            op.category, useless, op.label = [part.strip() for part in op.label.partition('  ')]
        else:
            op.label = op.text

        for pattern, _type, _label in self.LABEL_PATTERNS:
            m = pattern.match(op.text)
            if m:
                op.type = _type
                op.label = (_label % m.groupdict()).strip()
                return

class AccountHistory(TransactionsBasePage):
    def iter_operations(self):
        for tr in self.document.xpath('//table[@id="tableCompte"]//tr'):
            if len(tr.xpath('td[@class="debit"]')) == 0:
                continue

            id = tr.find('td').find('input').attrib['value']
            op = Transaction(id)
            op.text = tr.findall('td')[2].text.replace(u'\xa0', u'').strip()
            op.date = date(*reversed([int(x) for x in tr.findall('td')[1].text.split('/')]))

            self.parse_text(op)

            debit = tr.xpath('.//td[@class="debit"]')[0].text.replace('.','').replace(',','.').strip(u' \t\u20ac\xa0€\n\r')
            credit = tr.xpath('.//td[@class="credit"]')[0].text.replace('.','').replace(',','.').strip(u' \t\u20ac\xa0€\n\r')
            if len(debit) > 0:
                op.amount = - float(debit)
            else:
                op.amount = float(credit)

            yield op

class AccountComing(TransactionsBasePage):
    def iter_operations(self):
        i = 0
        for tr in self.document.xpath('//table[@id="tableauOperations"]//tr'):
            if 'typeop' in tr.attrib:
                tds = tr.findall('td')
                if len(tds) != 3:
                    continue
                d = tr.attrib['dateop']
                d = date(int(d[4:8]), int(d[2:4]), int(d[0:2]))
                text = tds[1].text or u''
                text = text.replace(u'\xa0', u'')
                for child in tds[1].getchildren():
                    if child.text: text += child.text
                    if child.tail: text += child.tail

                amount = tds[2].text.replace('.','').replace(',','.').strip(u' \t\u20ac\xa0€\n\r')

                i += 1
                operation = Transaction(i)
                operation.date = d
                operation.text = text.strip()
                self.parse_text(operation)
                operation.amount = float(amount)
                yield operation
