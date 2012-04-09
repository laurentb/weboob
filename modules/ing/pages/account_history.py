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

from decimal import Decimal
from datetime import date

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Transaction
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['AccountHistoryCC', 'AccountHistoryLA']


class TransactionCC(FrenchTransaction):
    PATTERNS = [(re.compile(u'^retrait dab (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^carte (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), Transaction.TYPE_CARD),
                (re.compile(u'^virement ((sepa emis vers|recu)?) (?P<text>.*)'), Transaction.TYPE_TRANSFER),
                (re.compile(u'^prelevement (?P<text>.*)'), Transaction.TYPE_ORDER),
                ]


class TransactionAA(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<category>VIREMENT (RECU|EMIS VERS)?) (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
               ]


class AccountHistoryCC(BasePage):
    def on_loaded(self):
        self.transactions = []
        table = self.document.findall('//tbody')[0]
        i = 1
        for tr in table.xpath('tr'):
            id = i
            texte = tr.text_content().split('\n')
            op = TransactionCC(id)
            op.parse(date = date(*reversed([int(x) for x in texte[0].split('/')])),
                     raw = texte[2])
            # force the use of website category
            op.category = texte[4]

            op.amount = Decimal(op.clean_amount(texte[5]))

            self.transactions.append(op)
            i += 1

    def get_transactions(self):
        return self.transactions


class AccountHistoryLA(BasePage):

    def on_loaded(self):
        self.transactions = []
        i = 1
        history = self.document.xpath('//tr[@align="center"]')
        history.pop(0)
        for tr in history:
            id = i
            texte = tr.text_content().strip().split('\n')
            op = TransactionAA(id)
            # The size is not the same if there are two dates or only one
            length = len(texte)
            op.parse(date = date(*reversed([int(x) for x in texte[0].split('/')])),
                     raw = unicode(texte[length - 2].strip()))

            op.amount = Decimal(op.clean_amount(texte[length - 1]))

            self.transactions.append(op)
            i += 1

    def get_transactions(self):
        return self.transactions
