# -*- coding: utf-8 -*-

# Copyright(C) 2017      Tony Malto
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

import re
import string
from io import BytesIO
from PIL import ImageOps

from weboob.browser.pages import FormNotFound, HTMLPage, LoggedPage, XMLPage
from weboob.browser.elements import ItemElement, method, ListElement, TableElement
from weboob.capabilities.bank import Account, Investment
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Currency, Date, Eval, Field, Regexp,
)
from weboob.browser.filters.html import Attr, TableCell
from weboob.capabilities.base import NotAvailable
from weboob.tools.captcha.virtkeyboard import SimpleVirtualKeyboard
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.exceptions import ActionNeeded


class Transaction(FrenchTransaction):
    PATTERNS = [
        (re.compile(r'Versement'), FrenchTransaction.TYPE_TRANSFER),
        (re.compile(r'Arbitrage'), FrenchTransaction.TYPE_ORDER)
    ]


class GMFVirtKeyboard(SimpleVirtualKeyboard):
    symbols = {
        '0': ('8926111c633bcb9095c9e16f08d5f2d6', 'b33872502b24a22963914e16e34e316c'),
        '1': ('00ab2ee44993c8473c4ac102b81e0a0c', 'c08194001275e1210c22e41e03213b36'),
        '2': ('5dcd16b8df5b320dbaa553fd462d50d1', '7db944b56030919af515ebc400c718f4'),
        '3': ('5d4200f641e875393f94a2659dc064c0', '7e413c45e1a23f8ed6e27e97724643d3', '9f9fcbb1567b4545800d1c3ef8b64107'),
        '4': ('0ab49e6c7f7f335e7f372cd650e172bf', '72b3bc4bd1c7f8f3ca952921eeeaac89'),
        '5': ('bfb7fc8b7c6e32827bf225ff6622f823', 'e5ad397c3e2b6f62708b21feb247c722'),
        '6': ('33da87aa31641ccba95021dd3f6a9934', 'b6ed461acff4f0f390a3305fce960deb'),
        '7': ('1504a24af0e55059c005cb14b47867c4', 'eb0db140e0389d00a1424ff0591babff'),
        '8': ('a3a1eb1209f7d411a74cdcc1033b3a08', 'cf7c8f2786cf5ea63eba0e44e2711e33'),
        '9': ('4bbca204ddfe9145e0d1a976237d7bd0', '718a9890b2e197113cf8e1b0a38ee973')
    }
    nrow = 4
    ncol = 4
    tile_margin = 17
    convert = 'RGBA'

    def __init__(self, browser, img_url):
        f = BytesIO(browser.open(img_url).content)
        # Symbols are the 16 letters 'abcdefghijklmnop'
        matching_symbols = string.ascii_lowercase[:16]
        super(GMFVirtKeyboard, self).__init__(f, self.ncol, self.nrow, matching_symbols=matching_symbols)

    def alter_image(self):
        # We must add a margin all around the image
        self.image = ImageOps.expand(self.image, border=(3, 4, 4, 3), fill='white')


class LoginPage(HTMLPage):
    VK_CLASS = GMFVirtKeyboard

    def get_vk_url(self):
        return Attr('//p[@class="keypad js-keypad"]//img', 'src')(self.doc)

    def login(self, login, password):
        vk_url = self.get_vk_url()
        # Note: there are only 20 different possible virtual keyboards.
        # We need to pass the vk_id when posting the credentials.
        vk_id = re.search(r'keypad-(\d+)\.png', vk_url).group(1)

        vk = self.VK_CLASS(self.browser, vk_url)
        password_positions = vk.get_string_code(password)

        data = {
            'username': login,
            'password': password_positions,
            'xzyz': vk_id
        }
        self.browser.home.go(data=data)

    def get_error(self):
        return CleanText('//div[contains(text(), "Erreur")]')(self.doc)


class HomePage(LoggedPage, HTMLPage):
    pass


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@class="bk-contrat theme-epargne"]'

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('.//div[@class="infos-contrat"]//strong')
            obj_label = CleanText('.//div[@class="type-contrat"]//h2')
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj_balance = CleanDecimal(CleanText('.//div[@class="col-right"]', children=False), replace_dots=True, default=NotAvailable)
            obj_currency = Currency(CleanText('.//div[@class="col-right"]', children=False,
                                              replace=[("Au", "")]))

    def get_detail_page_parameters(self, account):
        """
        Get parameters for the request that leads to the transactions/investments page
        """
        data = []

        # parameter 1
        el = self.doc.xpath('//div[@class="infos-contrat"][descendant::strong[contains(text(), $contract_id)]]/parent::div//div[@class="zone-detail"]//span/a', contract_id=account.id)
        assert len(el) == 1
        parameter = Regexp(Attr('.', 'onclick'), r".*,\{'(.*)':'(.*)'\},.*\);return false",
                                                 '\\1 \\2')(el[0]).split(' ')
        data.append((parameter[0], parameter[1]))

        form = self.get_form('//form[contains(@id, "j_idt")]')
        form_value = CleanText('//form[contains(@id, "j_idt")]/@id')(self.doc)
        # parameter 2
        data.append(('javax.faces.ViewState', form['javax.faces.ViewState']))
        # parameter 3
        data.append((form_value, form[form_value]))
        return form.url, data


class InvestmentsParser(TableElement):
        col_label = 'Support'
        col_share = 'Répartition en %'
        col_valuation = 'Montant'
        col_unitvalue = "Valeur de l'unité de compte"

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_portfolio_share = Eval(lambda x: x/100, CleanDecimal(TableCell('share'), replace_dots=True))
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True, default=NotAvailable)
            obj_quantity = CleanDecimal(TableCell('quantity'), default=NotAvailable)


class TransactionsParser(object):
    @method
    class iter_history(ListElement):
        item_xpath = '//div[contains(@id, "listeMouvements")]/table//tr[position()>1]'

        class item(ItemElement):
            klass = Transaction

            obj_rdate = obj_date = Date(CleanText('./td[1]'))
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = CleanDecimal('./td[3]', replace_dots=True)
            obj__detail_id = Regexp(Attr('./td[4]/a', 'href'), r'popin(\d+)')

            def obj_investments(self):
                detail_id = Field('_detail_id')(self)
                investment_details = self.page.doc.xpath('//div[@id="popin{}"]'.format(detail_id))
                assert len(investment_details) == 1
                return list(self.get_investments(self.page, el=investment_details[0]))

            class get_investments(InvestmentsParser):
                item_xpath = './p[strong[contains(text(), "Répartition de votre versement") or contains(text(), "Réinvestissement") or contains(text(), "Désinvestissement")]]/following-sibling::table//tr[position()>1]'
                head_xpath = './p[strong[contains(text(), "Répartition de votre versement") or contains(text(), "Réinvestissement") or contains(text(), "Désinvestissement")]]/following-sibling::table//tr[1]/th'
                col_quantity = re.compile("Nombre")  # use regex because the column name tends to be inconsistent between the tables


class TransactionsInvestmentsPage(LoggedPage, HTMLPage, TransactionsParser):
    def show_all_transactions(self):
        # show all transactions if many of them
        if self.doc.xpath('//span[contains(text(), "Plus de mouvements financiers")]'):
            try:
                form = self.get_form(name="formStep1")

                # have a look to the javascript file called 'jsf.js.faces' and
                # to the js listener "mojarra.ab" to understand
                # All parameters can be hardcoded
                form['javax.faces.source'] = 'formStep1:tabOnglets:plusDeMouvementFinancier'
                form['javax.faces.partial.event'] = 'click'
                form['javax.faces.partial.execute'] = 'formStep1:tabOnglets:plusDeMouvementFinancier'
                form['javax.faces.partial.render'] = 'formStep1:tabOnglets:listeMouvements formStep1:tabOnglets:gPlusDeMouvementFinancier formStep1:tabOnglets:gMoinsDeMouvementFinancier formStep1:tabOnglets:listPopinMouvement'
                form['javax.faces.behavior.event'] = 'click'
                form['javax.faces.partial.ajax'] = "true"

                form.submit()
            except FormNotFound:
                pass

    def has_investments(self):
        if self.doc.xpath('//li/a[text()="Portefeuille"]'):
            return True

    @method
    class iter_investments(InvestmentsParser):
        item_xpath = '//div[h3[text()="Répartition de votre portefeuille"]]/table//tr[position()>1]'
        head_xpath = '//div[h3[text()="Répartition de votre portefeuille"]]/table//tr[1]/th'
        col_quantity = "Nombre d'unités de comptes"


class AllTransactionsPage(LoggedPage, XMLPage, HTMLPage, TransactionsParser):
    def build_doc(self, content):
        # HTML embedded in XML: parse XML first then extract the html
        xml = XMLPage.build_doc(self, content)
        transactions_html = (xml.xpath('//partial-response/changes/update[1]')[0].text
                             .encode(encoding=self.encoding))
        investments_html = (xml.xpath('//partial-response/changes/update[2]')[0].text
                            .encode(encoding=self.encoding))
        html = transactions_html + investments_html
        return HTMLPage.build_doc(self, html)


class DocumentsSignaturePage(LoggedPage, HTMLPage):
    def on_load(self):
        if self.doc.xpath('//span[contains(text(), "VO(S) DOCUMENT(S) A SIGNER")]'):
            raise ActionNeeded(CleanText('//div[@class="block"]/p[contains(text(), "Vous avez un ou plusieurs document(s) à signer")]')(self.doc))


class RedirectToUserAgreementPage(LoggedPage, HTMLPage):
    MAX_REFRESH = 0


class UserAgreementPage(LoggedPage, HTMLPage):
    def on_load(self):
        message = CleanText('//fieldset//legend|//fieldset//label')(self.doc)
        if 'conditions générales' in message:
            raise ActionNeeded(message)
