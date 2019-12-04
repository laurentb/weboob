# -*- coding: utf-8 -*-

# Copyright(C) 2019      Vincent A
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

from weboob.browser.pages import LoggedPage, HTMLPage
from weboob.browser.filters.html import TableCell
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp
from weboob.browser.elements import method, ItemElement, TableElement
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Investment
from weboob.tools.capabilities.bank.investments import create_french_liquidity


class LoginPage(HTMLPage):
    def do_login(self, login, password):
        form = self.get_form(id='recaptcha')  # wtf
        form['emailConnexion'] = login
        form['motDePasseConnexion'] = password
        form.submit()

    def raise_error(self):
        msg = CleanText('//div[has-class("alert-danger")]')(self.doc)
        if 'Email ou mot de passe invalide' in msg:
            raise BrowserIncorrectPassword(msg)
        assert False, 'unhandled message %r' % msg


class LandPage(LoggedPage, HTMLPage):
    pass


class InvestPage(LoggedPage, HTMLPage):
    def get_user_id(self):
        return Regexp(
            CleanText('//span[contains(text(), "ID Client")]'),
            r'ID Client : (\d+)'
        )(self.doc)

    def get_liquidities(self):
        value = CleanDecimal.French(CleanText('//a[starts-with(text(),"Compte de paiement")]'))(self.doc)
        return create_french_liquidity(value)

    @method
    class iter_funded_stock(TableElement):
        item_xpath = '//table[@id="portefeuilleAction"]/tbody/tr'

        head_xpath = '//table[@id="portefeuilleAction"]/thead//th'
        col_bought = 'Vous avez investi'
        col_label = 'Investissement dans'
        col_valuation = 'Valeur estimée à date'
        col_diff_ratio = 'Coef. de performance intermediaire'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))

            # text is "0000000000000100 100,00 €", wtf
            obj_valuation = CleanDecimal.SI(
                Regexp(CleanText(TableCell('valuation')), r'^000(\d+)\b')
            )

            obj_diff_ratio = CleanDecimal.SI(
                Regexp(CleanText(TableCell('diff_ratio')), r'^000(\d+)\b')
            )

    @method
    class iter_funded_bond(TableElement):
        item_xpath = '//div[@id="panel-OBLIGATIONS"]//table[has-class("portefeuille-liste")]/tbody/tr'

        head_xpath = '//div[@id="panel-OBLIGATIONS"]//table[has-class("portefeuille-liste")]/thead//th'
        col_bought = 'Vous avez investi'
        col_label = 'Investissement dans'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))

            obj_valuation = CleanDecimal.SI(
                Regexp(CleanText(TableCell('bought')), r'^000(\d+)\b')
            )

    @method
    class iter_funding(TableElement):
        def find_elements(self):
            for el in self.page.doc.xpath('//div[has-class("panel")]'):
                if 'souscription(s) en cours' in CleanText('.')(el):
                    for sub in el.xpath('.//table[has-class("portefeuille-liste") and not(@id)]/tbody/tr'):
                        yield sub
                    return

        head_xpath = '//table[has-class("portefeuille-liste") and not(@id)]/thead//th'
        col_label = 'Opération / Cible'
        col_details = 'Détails'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_valuation = CleanDecimal.French(Regexp(
                CleanText(TableCell('details')),
                r'^(.*?) €',  # can be 100,00 € + Frais de 0,90 €
            ))
