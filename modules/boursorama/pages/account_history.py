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


from urlparse import urlparse
import re

from weboob.deprecated.browser import Page
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^CHQ\. (?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(ACHAT|PAIEMENT) CARTE (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(PRLV|TIP) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^VIR( SEPA)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^AVOIR (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),   FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^REM CHQ (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class AccountHistory(Page):
    def get_operations(self):
        for form in self.document.xpath('//form[@name="marques"]'):
            for tr in form.xpath('.//tbody/tr'):
                if 'total' in tr.attrib.get('class', '') or 'style' in tr.attrib:
                    continue

                date = self.parser.tocleanstring(tr.cssselect('td.operation span.DateOperation')[0])
                span = tr.cssselect('td.operation span, td.operation a')[-1]
                # remove links
                for font in span.xpath('./font'):
                    font.drop_tree()
                label = self.parser.tocleanstring(span)
                amount = self.parser.tocleanstring(tr.cssselect('td.amount')[0])

                try:
                    _id = tr.xpath('.//input[@type="hidden"]')[0].attrib['id'].split('_')[1]
                except (KeyError,IndexError):
                    _id = 0

                operation = Transaction(_id)
                operation.parse(date=date, raw=label)
                operation.set_amount(amount)

                yield operation

    def get_next_url(self):
        items = self.document.getroot().cssselect('ul.menu-lvl-0 li')

        current = False
        for li in reversed(items):
            if li.attrib.get('class', '') == 'active':
                current = True
            elif current:
                a = li.find('a')
                if 'year' in a.attrib.get('href', ''):
                    url = urlparse(self.url)
                    return url.path + a.attrib['href']
                else:
                    return None
