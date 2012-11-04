# -*- coding: utf-8 -*-

# Copyright(C) 2011       Gabriel Kerneis
# Copyright(C) 2009-2011  Romain Bignon
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


from datetime import date
import re

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Transaction
from weboob.tools.capabilities.bank.transactions import FrenchTransaction



__all__ = ['AccountHistory']

class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^CHQ\. (?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(ACHAT|PAIEMENT) CARTE (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(PRLV|TIP) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^VIR( SEPA)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^AVOIR (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),   FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^REM CHQ (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]

class AccountHistory(BasePage):

    def on_loaded(self):
        self.operations = []

        for form in self.document.getiterator('form'):
            if form.attrib.get('name', '') == 'marques':
                for tr in form.getiterator('tr'):
                    tds = tr.findall('td')
                    if len(tds) != 6:
                        continue
                    # tds[0]: operation
                    # tds[1]: valeur
                    d = date(*reversed([int(x) for x in tds[1].text.split('/')]))
                    labeldiv = tds[2].find('div')
                    label = u''
                    label += labeldiv.text
                    if labeldiv.find('a') is not None:
                        label += labeldiv.find('a').text
                    label = label.strip(u' \n\t')

                    category = labeldiv.attrib.get('title', '')
                    useless, sep, category = [part.strip() for part in category.partition(':')]

                    debit = tds[3].text or ""
                    credit = tds[4].text or ""

                    operation = Transaction(len(self.operations))
                    operation.parse(date=d, raw=label)
                    operation.set_amount(credit, debit)
                    operation.category = category

                    self.operations.append(operation)

    def get_operations(self):
        return self.operations
