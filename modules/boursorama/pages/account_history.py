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

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Transaction


__all__ = ['AccountHistory']


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
                    label = label.strip(u' \n\t')

                    category = labeldiv.attrib.get('title', '')
                    useless, sep, category = [part.strip() for part in category.partition(':')]

                    amount = tds[3].text
                    if amount == None:
                        amount = tds[4].text
                    amount = amount.strip(u' \n\t\x80').replace(' ', '').replace(',', '.')

                    # if we don't have exactly one '.', this is not a floatm try the next
                    operation = Transaction(len(self.operations))
                    operation.amount = float(amount)

                    operation.date = d
                    operation.label = label
                    operation.category = category
                    self.operations.append(operation)

    def get_operations(self):
        return self.operations
