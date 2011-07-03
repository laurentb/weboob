# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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

from weboob.capabilities.bank import Operation
from weboob.tools.browser import BasePage
from weboob.tools.misc import remove_html_tags


__all__ = ['AccountHistory']


class AccountHistory(BasePage):

    def get_history(self):
        mvt_table = self.document.xpath("//table[@id='mouvements']", smart_strings=False)[0]
        mvt_ligne = mvt_table.xpath("./tbody/tr")

        operations = []

        for mvt in mvt_ligne:
            operation = Operation(len(operations))
            operation.date = mvt.xpath("./td/span")[0].text
            tmp = mvt.xpath("./td/span")[1]
            operation.label = remove_html_tags(self.parser.tostring(tmp)).strip()

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
