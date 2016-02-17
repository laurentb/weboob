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


import re
from decimal import Decimal

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Investment
from weboob.browser.pages import RawPage, HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanDecimal, CleanText, Date
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class NetissimaPage(HTMLPage):
    pass

class Transaction(FrenchTransaction):
    pass


class TitreValuePage(LoggedPage, HTMLPage):
    def get_isin(self):
        return unicode(self.doc.xpath('//div[@id="headFiche"]//span[@id="test3"]/text()')[0].split(' - ')[0].strip())


class TitrePage(LoggedPage, RawPage):
    def iter_investments(self):
        # We did not get some html, but something like that (XX is a quantity, YY a price):
        # message='[...]
        # popup=2{6{E:ALO{PAR{{reel{695{380{ALSTOM REGROUPT#XX#YY,YY &euro;#YY,YY &euro;#1 YYY,YY &euro;#-YYY,YY &euro;#-42,42%#-0,98 %#42,42 %#|1|AXA#cotationValeur.php?val=E:CS&amp;pl=6&amp;nc=1&amp;
        # popup=2{6{E:CS{PAR{{reel{695{380{AXA#XX#YY,YY &euro;#YY,YYY &euro;#YYY,YY &euro;#YY,YY &euro;#3,70%#42,42 %#42,42 %#|1|blablablab #cotationValeur.php?val=P:CODE&amp;pl=6&amp;nc=1&amp;
        # [...]
        lines = self.doc.split("popup=2")
        lines.pop(0)
        for line in lines:
            columns = line.split('#')
            _pl = columns[0].split('{')[1]
            _id = columns[0].split('{')[2]
            invest = Investment(_id)
            invest.label = unicode(columns[0].split('{')[-1])
            invest.code = unicode(_id)
            if ':' in invest.code:
                invest.code = self.browser.titrevalue.open(val=invest.code,pl=_pl).get_isin()
            # The code we got is not a real ISIN code.
            if not re.match('^[A-Z]{2}[\d]{10}$|^[A-Z]{2}[\d]{5}[A-Z]{1}[\d]{4}$', invest.code):
                m = re.search('\{([A-Z]{2}[\d]{10})\{|\{([A-Z]{2}[\d]{5}[A-Z]{1}[\d]{4})\{', line)
                if m:
                    invest.code = unicode(m.group(1) or m.group(2))

            quantity = FrenchTransaction.clean_amount(columns[1])
            invest.quantity = CleanDecimal(default=NotAvailable).filter(quantity)

            unitprice = FrenchTransaction.clean_amount(columns[2])
            invest.unitprice = CleanDecimal(default=NotAvailable).filter(unitprice)

            unitvalue = FrenchTransaction.clean_amount(columns[3])
            invest.unitvalue = CleanDecimal(default=NotAvailable).filter(unitvalue)

            valuation = FrenchTransaction.clean_amount(columns[4])
            # valuation is not nullable, use 0 as default value
            invest.valuation = CleanDecimal(default=Decimal('0')).filter(valuation)

            diff = FrenchTransaction.clean_amount(columns[5])
            invest.diff = CleanDecimal(default=NotAvailable).filter(diff)

            yield invest


class TitreHistory(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//table[@class="datas retour"]/tr'

        class item(ItemElement):
            klass = Transaction

            condition = lambda self: len(self.el.xpath('td[@class="impaire"]')) > 0

            obj_raw = Transaction.Raw('td[4] | td[3]/a')
            obj_date = Date(CleanText('td[2]'), dayfirst=True)
            obj_amount = CleanDecimal('td[7]', replace_dots=True)


class ASVHistory(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//table[@class="Tableau"]/tr[td[not(has-class("enteteTableau"))]]'

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText('./td[1]'), dayfirst=True)
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = CleanDecimal('./td[3]', replace_dots=True)
