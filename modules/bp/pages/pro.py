# -*- coding: utf-8 -*-

# Copyright(C) 2014  Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

import re
from decimal import Decimal

from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Date
from weboob.browser.filters.html import Link
from weboob.browser.pages import LoggedPage, pagination
from weboob.capabilities.bank import Account
from weboob.capabilities.profile import Company
from weboob.capabilities.base import NotAvailable
from weboob.tools.compat import urljoin, unicode
from weboob.exceptions import BrowserUnavailable

from .accounthistory import Transaction
from .base import MyHTMLPage


class RedirectPage(LoggedPage, MyHTMLPage):
    def check_for_perso(self):
        return self.doc.xpath(u'//p[contains(text(), "L\'identifiant utilisé est celui d\'un compte de Particuliers")]')


class ProAccountsList(LoggedPage, MyHTMLPage):
    def on_load(self):
        if self.doc.xpath('//div[@id="erreur_generale"]'):
            raise BrowserUnavailable(CleanText(u'//div[@id="erreur_generale"]//p[contains(text(), "Le service est momentanément indisponible")]')(self.doc))

    ACCOUNT_TYPES = {u'comptes titres': Account.TYPE_MARKET,
                     u'comptes Ã©pargne':    Account.TYPE_SAVINGS,
                     # wtf? ^
                     u'comptes épargne':     Account.TYPE_SAVINGS,
                     u'comptes courants':    Account.TYPE_CHECKING,
                    }
    def get_accounts_list(self):
        for table in self.doc.xpath('//div[@class="comptestabl"]/table'):
            try:
                account_type = self.ACCOUNT_TYPES[table.get('summary').lower()]
                if not account_type:
                    account_type = self.ACCOUNT_TYPES[table.xpath('./caption/text()')[0].strip().lower()]
            except (IndexError,KeyError):
                account_type = Account.TYPE_UNKNOWN
            for tr in table.xpath('./tbody/tr'):
                cols = tr.findall('td')

                link = cols[0].find('a')
                if link is None:
                    continue

                a = Account()
                a.type = account_type
                a.id = unicode(re.search('([A-Z\d]{4}[A-Z\d\*]{3}[A-Z\d]{4})', link.attrib['title']).group(1))
                a.label = unicode(link.attrib['title'].replace('%s ' % a.id, ''))
                tmp_balance = CleanText(None).filter(cols[1])
                a.currency = a.get_currency(tmp_balance)
                if not a.currency:
                    a.currency = u'EUR'
                a.balance = Decimal(Transaction.clean_amount(tmp_balance))
                a._has_cards = False
                a.url = urljoin(self.url, link.attrib['href'])
                yield a


class ProAccountHistory(LoggedPage, MyHTMLPage):
    @pagination
    @method
    class iter_history(ListElement):
        item_xpath = u'//div[@id="tabReleve"]//tbody/tr'
        next_page = Link('//div[@class="pagination"]//li[@class="pagin-on-right"]/a')

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText('.//td[@headers="date"]'), dayfirst=True)
            obj_raw = Transaction.Raw('.//td[@headers="libelle"]')
            obj_amount = CleanDecimal('.//td[@headers="debit" or @headers="credit"]',
                                      replace_dots=True, default=NotAvailable)


class DownloadRib(LoggedPage, MyHTMLPage):
    def get_rib_value(self, acc_id):
        opt = self.doc.xpath('//div[@class="rechform"]//option')
        for o in opt:
            if acc_id in o.text:
                return o.xpath('./@value')[0]
        return None


class RibPage(LoggedPage, MyHTMLPage):
    def get_iban(self):
        if self.doc.xpath('//div[@class="blocbleu"][2]//table[@class="datalist"]'):
            return CleanText()\
                .filter(self.doc.xpath('//div[@class="blocbleu"][2]//table[@class="datalist"]')[0])\
                .replace(' ', '').strip()
        return None

    @method
    class get_profile(ItemElement):
        klass = Company

        obj_name = CleanText('//table[@class="datalistecart"]//td[@class="nom"]')
        obj_address = CleanText('//table[@class="datalistecart"]//td[@class="adr"]')
