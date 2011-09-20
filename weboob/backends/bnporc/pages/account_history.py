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

        for tr in self.document.xpath('//table[@id="tableCompte"]//tr'):
            if len(tr.xpath('td[@class="debit"]')) == 0:
                continue

            id = tr.find('td').find('input').attrib['value']
            op = Operation(id)
            op.label = tr.findall('td')[2].text.replace(u'\xa0', u'').strip()
            op.date = date(*reversed([int(x) for x in tr.findall('td')[1].text.split('/')]))

            op.category = NotAvailable
            for pattern, _cat, _lab in self.LABEL_PATTERNS:
                m = re.match(pattern, op.label)
                if m:
                    op.category = _cat % m.groupdict()
                    op.label = _lab % m.groupdict()
                    break
            else:
                if '  ' in op.label:
                    op.category, useless, op.label = [part.strip() for part in op.label.partition('  ')]

            debit = tr.xpath('.//td[@class="debit"]')[0].text.replace('.','').replace(',','.').strip(u' \t\u20ac\xa0€\n')
            credit = tr.xpath('.//td[@class="credit"]')[0].text.replace('.','').replace(',','.').strip(u' \t\u20ac\xa0€\n')
            if len(debit) > 0:
                op.amount = - float(debit)
            else:
                op.amount = float(credit)

            self.operations.append(op)

    def get_operations(self):
        return self.operations
