# -*- coding: utf-8 -*-

# Copyright(C) 2015      Romain Bignon
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

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.pages import LoggedPage, HTMLPage, pagination
from weboob.browser.elements import method, ListElement, ItemElement
from weboob.capabilities.bank import Account
from weboob.browser.filters.standard import CleanText, CleanDecimal, Map, Async, AsyncLoad, Regexp, Join
from weboob.browser.filters.html import Attr, Link
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form()
        form['identifiant'] = username
        form['motpasse'] = password
        form.submit()


class LoginConfirmPage(HTMLPage):
    def on_load(self):
        error = CleanText('//td[has-class("ColonneLibelle")]')(self.doc)
        if len(error) > 0:
            raise BrowserIncorrectPassword(error)

class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//table[has-class("TableBicolore")]//tr[@id and count(td) > 4]'

        class item(ItemElement):
            klass = Account

            TYPE = {'COMPTE COURANT ORDINAIRE': Account.TYPE_CHECKING,
                   }

            obj_id = CleanText('./td[1]')
            obj_label = CleanText('./td[2]')
            obj_currency = FrenchTransaction.Currency('./td[4]')
            obj_balance = CleanDecimal('./td[5]', replace_dots=True)
            obj_type = Map(CleanText('./td[3]'), TYPE, default=Account.TYPE_UNKNOWN)
            obj__link = Attr('./td[1]/a', 'href')

            load_iban = Link('./td[last()]/a[img[starts-with(@alt, "RIB")]]') & AsyncLoad
            obj_iban = Async('iban') & Join('', Regexp(CleanText('//td[has-class("ColonneCode")][starts-with(text(), "IBAN")]'), r'\b((?!IBAN)[A-Z0-9]+)\b', nth='*'))


class RibPage(LoggedPage, HTMLPage):
    pass


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)?( SEPA)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>.*) CARTE \d+ PAIEMENT CB\s+(?P<dd>\d{2})(?P<mm>\d{2}) ?(.*)$'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE [\*\d]+'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CHEQUE( (?P<text>.*))?$'),  FrenchTransaction.TYPE_CHECK),
                (re.compile('^(F )?COTIS\.? (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile('^(REMISE|REM.CHQ) (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class HistoryPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class get_operations(Transaction.TransactionsElement):
        def next_page(self):
            for script in self.page.doc.xpath('//script'):
                m = re.search(r"getCodePagination\('(\d+)','(\d+)','([^']+)'.*", script.text or '', re.MULTILINE)
                if m:
                    cur_page = int(m.group(1))
                    nb_pages = int(m.group(2))
                    baseurl = m.group(3)

                    if cur_page < nb_pages:
                        return baseurl + '&numeroPage=%s&nbrPage=%s' % (cur_page + 1, nb_pages)

        head_xpath = '//div[has-class("TableauBicolore")]/table/tr[not(@id)]/td'
        item_xpath = '//div[has-class("TableauBicolore")]/table/tr[@id and count(td) > 4]'

        col_date = ['Date comptable']
        col_vdate = ['Date de valeur']
        col_raw = [u'Libellé de l\'opération']

        class item(Transaction.TransactionElement):
            pass
