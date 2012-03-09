# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Nicolas Duhamel
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

from weboob.capabilities.bank import Transaction
from weboob.tools.browser import BasePage


__all__ = ['AccountHistory']


class AccountHistory(BasePage):

    def get_history(self):
        mvt_table = self.document.xpath("//table[@id='mouvements']", smart_strings=False)[0]
        mvt_ligne = mvt_table.xpath("./tbody/tr")

        operations = []

        for mvt in mvt_ligne:
            operation = Transaction(len(operations))

            d = mvt.xpath("./td/span")[0].text.strip().split('/')
            operation.date = date(*reversed([int(x) for x in d]))

            tmp = mvt.xpath("./td/span")[1]
            operation.raw = unicode(self.parser.tocleanstring(tmp).strip())

            r = re.compile(r'\d+')

            tmp = mvt.xpath("./td/span/strong")
            if not tmp:
                tmp = mvt.xpath("./td/span")
            amount = None
            for t in tmp:
                if r.search(t.text):
                    amount = t.text
            amount =  ''.join( amount.replace('.', '').replace(',', '.').split() )
            if amount[0] == "-":
                operation.amount = -float(amount[1:])
            else:
                operation.amount = float(amount)

            operations.append(operation)
        return operations
