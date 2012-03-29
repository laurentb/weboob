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
from datetime import date

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Transaction
from weboob.capabilities.base import NotAvailable

__all__ = ['AccountHistoryCC', 'AccountHistoryLA']


class AccountHistoryCC(BasePage):
    types = {
        'Carte achat': Transaction.TYPE_CARD,
        'Virement': Transaction.TYPE_TRANSFER,
        'Carte retrait': Transaction.TYPE_WITHDRAWAL,
        u'Prélèvement': Transaction.TYPE_ORDER,
        'Autre': Transaction.TYPE_UNKNOWN,
         }

    def on_loaded(self):
        self.transactions = []
        table = self.document.findall('//tbody')[0]
        i = 1
        for tr in table.xpath('tr'):
            id = i
            texte = tr.text_content().split('\n')
            op = Transaction(id)
            op.label = texte[2]
            op.raw = texte[2]  # nothing to parse
            op.date = date(*reversed([int(x) for x in texte[0].split('/')]))
            op.category = texte[4]
            op.type = self.types.get(texte[4], Transaction.TYPE_UNKNOWN)

            amount = texte[5].replace('\t', '').strip().replace(u'€', '').\
                              replace(',', '.').replace(u'\xa0', u'')
            op.amount = Decimal(amount)

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
            op = Transaction(id)
            # The size is not the same if there are two dates or only one
            length = len(texte)
            op.raw = unicode(texte[length - 2].strip())
            op.date = date(*reversed([int(x) for x in texte[0].split('/')]))
            op.category = NotAvailable

            amount = texte[length - 1].replace('\t', '').strip().\
                                       replace('.', '').replace(u'€', '').\
                                       replace(',', '.').replace(u'\xa0', u'')
            op.amount = Decimal(amount)

            self.transactions.append(op)
            i += 1

    def get_transactions(self):
        return self.transactions
