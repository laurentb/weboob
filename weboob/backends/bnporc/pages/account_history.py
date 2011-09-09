# -*- coding: utf-8 -*-

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


import re
from datetime import date

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Operation
from weboob.capabilities.base import NotAvailable


__all__ = ['AccountHistory']


class AccountHistory(BasePage):
    LABEL_PATTERNS = [(u'^CHEQUEN°(?P<no>.*)', u'CHEQUE', u'N°%(no)s')]

    def on_loaded(self):
        self.operations = []

        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class', '') == 'hdoc1' or tr.attrib.get('class', '') == 'hdotc1':
                tds = tr.findall('td')
                if len(tds) != 4:
                    continue
                d = date(*reversed([int(x) for x in tds[0].text.split('/')]))
                label = u''
                label += tds[1].text
                label = label.replace(u'\xa0', u'')
                for child in tds[1].getchildren():
                    if child.text: label += child.text
                    if child.tail: label += child.tail
                if tds[1].tail: label += tds[1].tail

                label = label.strip()
                category = NotAvailable
                for pattern, _cat, _lab in self.LABEL_PATTERNS:
                    m = re.match(pattern, label)
                    if m:
                        category = _cat % m.groupdict()
                        label = _lab % m.groupdict()
                        break
                else:
                    if '  ' in label:
                        category, useless, label = [part.strip() for part in label.partition('  ')]

                amount = tds[2].text.replace('.', '').replace(',', '.')

                # if we don't have exactly one '.', this is not a floatm try the next
                operation = Operation(len(self.operations))
                if amount.count('.') != 1:
                    amount = tds[3].text.replace('.', '').replace(',', '.')
                    operation.amount = float(amount)
                else:
                    operation.amount = - float(amount)

                operation.date = d
                operation.label = label
                operation.category = category
                self.operations.append(operation)

    def get_operations(self):
        return self.operations
