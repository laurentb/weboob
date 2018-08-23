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

from __future__ import unicode_literals

import re
from decimal import Decimal

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Investment
from weboob.browser.pages import RawPage, HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, TableElement, ItemElement, method
from weboob.browser.filters.standard import CleanDecimal, CleanText, Date, Regexp, Env
from weboob.browser.filters.html import Link, Attr, TableCell
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.compat import unicode

class NetissimaPage(HTMLPage):
    pass

class Transaction(FrenchTransaction):
    pass


class TitreValuePage(LoggedPage, HTMLPage):
    def get_isin(self):
        return unicode(self.doc.xpath('//div[@id="headFiche"]//span[@id="test3"]/text()')[0].split(' - ')[0].strip())


class TitrePage(LoggedPage, RawPage):
    def build_doc(self, content):
        return content.decode(self.encoding)

    def get_balance(self):
        return CleanDecimal(default=None, replace_dots=True).filter(self.doc.split('{')[0])

    def iter_investments(self, account):
        # We did not get some html, but something like that (XX is a quantity, YY a price):
        # "message='<total> &euro;{<total> &euro;{0,01 &euro;{<liquidity> &euro;{0,00{{05/17{{03/05/2017{11:06{-XX &euro;{710TI81000029397EUR{XX &euro;{XX &euro;{|OPHTHOTECH(NASDAQ)#cotationValeur.php?val=OPHT&amp;pl=11&amp;nc=2&amp;
        # popup=2{6{E:ALO{PAR{{reel{695{380{ALSTOM REGROUPT#XX#YY,YY &euro;#YY,YY &euro;#1 YYY,YY &euro;#-YYY,YY &euro;#-42,42%#-0,98 %#42,42 %#|1|AXA#cotationValeur.php?val=E:CS&amp;pl=6&amp;nc=1&amp;
        # popup=2{6{E:CS{PAR{{reel{695{380{AXA#XX#YY,YY &euro;#YY,YYY &euro;#YYY,YY &euro;#YY,YY &euro;#3,70%#42,42 %#42,42 %#|1|blablablab #cotationValeur.php?val=P:CODE&amp;pl=6&amp;nc=1&amp;
        # [...]
        data = self.browser.cache["investments_data"].get(account.id, self.doc)
        lines = data.split("|1|")
        message = lines[0]
        if len(lines) > 1:
            start = 1
            lines[0] = lines[0].split("|")[1]
        else:
            start = 0
            lines = data.split("popup=2")
            lines.pop(0)
        invests = []
        for line in lines:
            _id, _pl = None, None
            columns = line.split('#')
            if columns[1] != '':
                _pl = columns[start].split('{')[1]
                _id = columns[start].split('{')[2]
            invest = Investment()
            invest.label = columns[start].split('{')[-1]
            invest.code = _id or NotAvailable
            if invest.code and ':' in invest.code:
                invest.code = self.browser.titrevalue.open(val=invest.code,pl=_pl).get_isin()
            # The code we got is not a real ISIN code.
            if invest.code and not re.match('^[A-Z]{2}[\d]{10}$|^[A-Z]{2}[\d]{5}[A-Z]{1}[\d]{4}$', invest.code):
                m = re.search('\{([A-Z]{2}[\d]{10})\{|\{([A-Z]{2}[\d]{5}[A-Z]{1}[\d]{4})\{', line)
                if m:
                    invest.code = m.group(1) or m.group(2)

            for x, attr in enumerate(['quantity', 'unitprice', 'unitvalue', 'valuation', 'diff'], 1):
                currency = FrenchTransaction.Currency().filter(columns[start + x])
                amount = CleanDecimal(default=NotAvailable).filter(FrenchTransaction.clean_amount(columns[start + x]))
                if currency and currency != account.currency:
                    invest.original_currency = currency
                    attr = "original_" + attr
                setattr(invest, attr, amount)
            # valuation is not nullable, use 0 as default value
            if not invest.valuation:
                invest.valuation = Decimal('0')

            # On some case we have a multine investment with a total column
            # for now we have only see this on 2 lines, we will need to adapt it when o
            if columns[9 if start == 0 else 0] == u'|Total' and _id == 'fichevaleur':
                prev_inv = invest
                invest = invests.pop(-1)
                if prev_inv.quantity:
                    invest.quantity = invest.quantity + prev_inv.quantity
                if prev_inv.valuation:
                    invest.valuation = invest.valuation + prev_inv.valuation
                if prev_inv.diff:
                    invest.diff = invest.diff + prev_inv.diff

            invests.append(invest)

        # There is no investment on life insurance in the process to be created.
        if len(message.split('&')) >= 4:
            # We also have to get the liquidity as an investment.
            invest = Investment()
            invest.label = "Liquidités"
            invest.code = "XX-liquidity"
            invest.valuation = CleanDecimal(None, True).filter(message.split('&')[3].replace('euro;{','').strip())
            invests.append(invest)
        for invest in invests:
            yield invest


class TitreHistory(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//table[@class="datas retour"]/tr'

        class item(ItemElement):
            klass = Transaction

            condition = lambda self: len(self.el.xpath('td[@class="impaire"]')) > 0

            obj_raw = Transaction.Raw('td[4] | td[3]')
            obj_date = Date(CleanText('td[2]'), dayfirst=True)
            obj_amount = CleanDecimal('td[7]', replace_dots=True)


class ASVHistory(LoggedPage, HTMLPage):
    @method
    class get_investments(TableElement):
        item_xpath = '//table[@class="Tableau"]/tr[td[not(has-class("enteteTableau"))]]'
        head_xpath = '//table[@class="Tableau"]/tr[td[has-class("enteteTableau")]]/td'

        col_label = u'Support(s)'
        col_vdate = u'Date de valeur'
        col_unitvalue = u'Valeur de part'
        col_quantity = [u'(*) Nb de parts', u'Nb de parts']
        col_valuation = [u'Montant', u'Montant versé']

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_quantity = CleanDecimal(TableCell('quantity'), replace_dots=True, default=NotAvailable)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True, default=NotAvailable)
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True)

            obj__code_url = Regexp(Attr('./td/a', 'onclick', default=""), r'PageExterne\(\'([^\']+)', default=None)


    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table[@class="Tableau"]/tr[td[not(has-class("enteteTableau"))]]'
        head_xpath = '//table[@class="Tableau"]/tr[td[has-class("enteteTableau")]]/td'

        col_date = u'Date d\'effet'
        col_raw = u'Nature du mouvement'
        col_amount = u'Montant brut'

        next_page = Link('//a[contains(@href, "PageSuivante")]', default=None)

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_raw = Transaction.Raw(TableCell('raw'))
            obj_amount = CleanDecimal(TableCell('amount'), replace_dots=True)
            obj__detail = Env('detail')

            def obj_id(self):
                try:
                    return Regexp(Link('./td/a', default=None), 'numMvt=(\d+)', default=None)(self)
                except TypeError:
                    return NotAvailable

            def parse(self, el):
                link = Link('./td/a', default=None)(self)
                page = self.page.browser.async_open(link) if link else None
                self.env['detail'] = page
