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


__all__ = ['AccountComing']


class AccountComing(BasePage):
    LABEL_PATTERNS = [('^FACTURE CARTE DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)',
                          u'CB %(yy)s-%(mm)s-%(dd)s: %(text)s'),
                      ('^PRELEVEMENT(?P<text>.*)', 'Order: %(text)s'),
                      ('^ECHEANCEPRET(?P<text>.*)', u'Loan payment n°%(text)s'),
                     ]

    def on_loaded(self):
        self.operations = []

        for tr in self.document.xpath('//table[@id="tableauOperations"]//tr'):
            if 'typeop' in tr.attrib:
                tds = tr.findall('td')
                if len(tds) != 3:
                    continue
                d = tr.attrib['dateop']
                d = date(int(d[4:8]), int(d[2:4]), int(d[0:2]))
                label = tds[1].text or u''
                label = label.replace(u'\xa0', u'')
                for child in tds[1].getchildren():
                    if child.text: label += child.text
                    if child.tail: label += child.tail
                label = label.strip()

                for pattern, text in self.LABEL_PATTERNS:
                    m = re.match(pattern, label)
                    if m:
                        label = text % m.groupdict()

                amount = tds[2].text.replace('.','').replace(',','.').strip(u' \t\u20ac\xa0€\n')

                operation = Operation(len(self.operations))
                operation.date = d
                operation.label = label
                operation.amount = float(amount)
                self.operations.append(operation)

    def get_operations(self):
        return self.operations
