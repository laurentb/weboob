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
from datetime import date

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Operation
from weboob.capabilities.base import NotAvailable


__all__ = ['AccountHistory']


class AccountHistory(BasePage):

    def on_loaded(self):
        self.operations = []
        table = self.document.findall('//tbody')[0]
        i = 1
        for tr in table.xpath('tr'):
            id = i
            texte = tr.text_content().split('\n')
            op = Operation(id)
            op.label = texte[2]
            op.date = date(*reversed([int(x) for x in texte[0].split('/')]))
            op.category = texte[4]

            amount = texte[5].replace('\t','').strip().replace(u'€', '').replace(',', '.').replace(u'\xa0', u'')
            op.amount = float(amount)

            self.operations.append(op)
            i += 1

    def get_operations(self):
        return self.operations
