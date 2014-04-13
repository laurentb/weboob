# -*- coding: utf-8 -*-

# Copyright(C) 2013-2014  Florent Fourcot
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

from weboob.capabilities.bank import Investment
from weboob.tools.browser2.page import RawPage, HTMLPage, method, ListElement, ItemElement
from weboob.tools.browser2.filters import CleanDecimal, CleanText, Date
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

__all__ = ['TitrePage']


class Transaction(FrenchTransaction):
    pass


class TitrePage(RawPage):
    def iter_investments(self):
        # We did not get some html, but something like that (XX is a quantity, YY a price):
        # message='[...]
        #popup=2{6{E:ALO{PAR{{reel{695{380{ALSTOM REGROUPT#XX#YY,YY &euro;#YY,YY &euro;#1 YYY,YY &euro;#-YYY,YY &euro;#-42,42%#-0,98 %#42,42 %#|1|AXA#cotationValeur.php?val=E:CS&amp;pl=6&amp;nc=1&amp;
        #popup=2{6{E:CS{PAR{{reel{695{380{AXA#XX#YY,YY &euro;#YY,YYY &euro;#YYY,YY &euro;#YY,YY &euro;#3,70%#42,42 %#42,42 %#|1|blablablab #cotationValeur.php?val=P:CODE&amp;pl=6&amp;nc=1&amp;
        # [...]
        lines = self.doc.split("popup=2")
        lines.pop(0)
        for line in lines:
            columns = line.split('#')
            code = columns[0].split('{')[2]
            invest = Investment(code)
            invest.code = unicode(code)
            invest.label = unicode(columns[0].split('{')[-1])
            # XXX sometimes there are decimal (!) quantities
            invest.quantity = int(columns[1].split(',')[0])
            invest.unitprice = Decimal(FrenchTransaction.clean_amount(columns[2]))
            invest.unitvalue = Decimal(FrenchTransaction.clean_amount(columns[3]))
            invest.valuation = Decimal(FrenchTransaction.clean_amount(columns[4]))
            invest.diff = Decimal(FrenchTransaction.clean_amount(columns[5]))

            yield invest


class TitreHistory(HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//table[@class="datas retour"]/tr'

        class item(ItemElement):
            klass = Transaction

            condition = lambda self: len(self.el.xpath('td[@class="impaire"]')) > 0

            obj_raw = Transaction.Raw('td[4] | td[3]/a')
            obj_date = Date(CleanText('td[2]'), dayfirst=True)
            obj_amount = CleanDecimal('td[7]')
