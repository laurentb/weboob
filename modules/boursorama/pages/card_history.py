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


import re

from weboob.tools.browser import BasePage
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['CardHistory']


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^(ACHAT |PAIEMENT )?CARTE (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (\d{2} )?(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL)
               ]


class CardHistory(BasePage):
    def get_operations(self):
        for form in self.document.xpath('//form[@name="marques"]'):
            for tr in form.xpath('.//tbody/tr'):
                tds = tr.xpath('./td')

                if tr.attrib.get('class', '') in ('total gras', 'visible-phone') or 'style' in tr.attrib or len(tds) < 3:
                    continue

                date = self.parser.tocleanstring(tds[0])
                label = self.parser.tocleanstring(tds[1])
                amount = self.parser.tocleanstring(tds[2])

                try:
                    _id = tr.xpath('.//input[@type="hidden"]')[0].attrib['id'].split('_')[1]
                except (KeyError,IndexError):
                    _id = 0

                operation = Transaction(_id)
                operation.parse(date=date, raw=label)
                operation.set_amount(amount)

                yield operation

    def get_next_url(self):
        items = self.document.getroot().cssselect('ul.menu-lvl-1 li')

        current = False
        for li in reversed(items):
            if li.attrib.get('class', '') == 'active':
                current = True
            elif current:
                a = li.find('a')
                if 'year' in a.attrib.get('href', ''):
                    return a.attrib['href']
                else:
                    return None
