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

from __future__ import unicode_literals

from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Coalesce, Currency, Date, Map, Field, Regexp
from weboob.browser.filters.html import AbsoluteLink, Link
from weboob.browser.pages import LoggedPage, pagination
from weboob.capabilities.bank import Account
from weboob.capabilities.profile import Company
from weboob.capabilities.base import NotAvailable

from .accounthistory import Transaction
from .base import MyHTMLPage


class RedirectPage(LoggedPage, MyHTMLPage):
    def check_for_perso(self):
        return self.doc.xpath('''//p[contains(text(), "L'identifiant utilisé est celui d'un compte de Particuliers")]''')

    def get_error(self):
        return CleanText('//div[contains(@class, "bloc-erreur")]/h3')(self.doc)


ACCOUNT_TYPES = {
    'Comptes titres': Account.TYPE_MARKET,
    'Comptes épargne': Account.TYPE_SAVINGS,
    'Comptes courants': Account.TYPE_CHECKING,
}


class ProAccountsList(LoggedPage, MyHTMLPage):

    # TODO Be careful about connections with personnalized account groups
    # According to their presentation video (https://www.labanquepostale.fr/pmo/nouvel-espace-client-business.html),
    # on the new website people are able to make personnalized groups of account instead of the usual drop-down categories on which to parse to find a match in ACCOUNT_TYPES
    # If clients use the functionnality we might need to add entries new in ACCOUNT_TYPES

    def get_errors(self):
        # Full message for the second error is :
        # Vous êtes uniquement habilité à accéder à OPnet.
        # Pour toute modification de vos accès, veuillez-vous rapprocher
        # du Mandataire Principal de votre contrat de banque en ligne.
        return (
            CleanText('//div[@id="erreur_generale"]//p[contains(text(), "Le service est momentanément indisponible")]')(self.doc)
            or CleanText('//p[contains(text(), "veuillez-vous rapprocher du Mandataire Principal de votre contrat")]')(self.doc)
        )

    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@id="mainContent"]//div[h3/a]'

        class item(ItemElement):
            klass = Account

            obj_id = Regexp(CleanText('./h3/a/@title'), r'([A-Z\d]{4}[A-Z\d\*]{3}[A-Z\d]{4})')
            obj_balance = CleanDecimal.French('./span/text()[1]')  # This website has the good taste of leaving hard coded HTML comments. This is the way to pin point to the righ text item.
            obj_currency = Currency('./span')
            obj_url = AbsoluteLink('./h3/a')

            # account are grouped in /div based on their type, we must fetch the closest one relative to item_xpath
            obj_type = Map(CleanText('./ancestor::div[1]/preceding-sibling::h2[1]/button/div[@class="title-accordion"]'), ACCOUNT_TYPES, Account.TYPE_UNKNOWN)

            def obj_label(self):
                """ Need to get rid of the id wherever we find it in account labels like "LIV A 0123456789N MR MOMO" (livret A) as well as "0123456789N MR MOMO" (checking account) """
                return CleanText('./h3/a/@title')(self).replace('%s ' % Field('id')(self), '')


class ProAccountHistory(LoggedPage, MyHTMLPage):
    @pagination
    @method
    class iter_history(ListElement):
        item_xpath = '//div[@id="tabReleve"]//tbody/tr'

        def next_page(self):
            # The next page on the website can return pages already visited without logical mechanism
            # Nevertheless we can skip these pages with the comparaison of the first transaction of the page
            next_page_xpath = '//div[@class="pagination"]/a[@title="Aller à la page suivante"]'
            tr_xpath = '//tbody/tr[1]'
            self.page.browser.first_transactions.append(CleanText(tr_xpath)(self.el))
            next_page_link = Link(next_page_xpath)(self.el)
            next_page = self.page.browser.location(next_page_link)
            first_transaction = CleanText(tr_xpath)(next_page.page.doc)
            count = 0  # avoid an infinite loop

            while first_transaction in self.page.browser.first_transactions and count < 30:
                next_page = self.page.browser.location(next_page_link)
                next_page_link = Link(next_page_xpath)(next_page.page.doc)
                first_transaction = CleanText(tr_xpath)(next_page.page.doc)
                count += 1

            if count < 30:
                return next_page.page

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText('.//td[@headers="date"]'), dayfirst=True)
            obj_raw = Transaction.Raw('.//td[@headers="libelle"]')
            obj_amount = Coalesce(
                CleanDecimal.French('.//td[@headers="debit"]', default=NotAvailable),
                CleanDecimal.French('.//td[@headers="credit"]', default=NotAvailable),
            )


class DownloadRib(LoggedPage, MyHTMLPage):
    def get_rib_value(self, acc_id):
        opt = self.doc.xpath('//select[@id="idxSelection"]/optgroup//option')
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
