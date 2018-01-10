# -*- coding: utf-8 -*-

# Copyright(C) 2014 Budget Insight
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

from decimal import Decimal
import re
from io import BytesIO

import requests

from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction, sorted_transactions
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.date import parse_french_date
from weboob.browser.pages import HTMLPage, LoggedPage, pagination, XLSPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import Env, CleanDecimal, CleanText, Field, Format
from weboob.browser.filters.html import Attr
from weboob.exceptions import BrowserIncorrectPassword


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(ur'^(?P<text>Retrait .*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(ur'^(?P<text>Prélèvement .*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_ORDER),
                (re.compile(ur'^(?P<text>.*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_CARD)]


class VirtKeyboard(MappedVirtKeyboard):
    symbols={'0':('8664b9cdfa66b4c3a1ec99c35a2bf64b','9eb80c6e99410eaac32905b2c77e65e5','37717277dc2471c8a7bf37e2068a8f01'),
             '1':('1f36986f9d27dde54ce5b08e8e285476','9d0aa7a0a2bbab4f2c01ef1e820cb3f1'),
             '2':('b560b0cce2ca74d3d499d73775152ab7',),
             '3':('d16e426e71fc29b1b55d0fbded99a473',),
             '4':('19c68066e414e08d17c86fc5c4acc949','c43354a7f7739508f76c538d5b3bce26'),
             '5':('4b9abf98e30a1475997ec770cbe5e702','2059b4aa95c7b3156b171255fa10bbdd'),
             '6':('804be4171d61f9cc10e9978c43b1d2a0','a41b091d4a11a318406a5a8bd3ed3837'),
             '7':('8adf951f4eea5f446f714214e101d555',),
             '8':('568135f3844213c30f2c7880be867d3d',),
             '9':('a3750995c511ea1492ac244421109e77','eeb3a8ba804f19380dfe94a91a37595b'),
            }

    color=(0,0,0)

    def __init__(self, page):
        img = page.doc.find("//img[@usemap='#cv']")
        res = page.browser.open(img.attrib['src'])
        MappedVirtKeyboard.__init__(self, BytesIO(res.content), page.doc, img, self.color, 'href', convert='RGB')

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def check_color(self, pixel):
        for p in pixel:
            if p >= 0xd5:
                return False

        return True

    def get_symbol_coords(self, coords):
        # strip borders
        x1, y1, x2, y2 = coords
        return MappedVirtKeyboard.get_symbol_coords(self, (x1+10, y1+10, x2-10, y2-10))

    def get_symbol_code(self, md5sum_list):
        for md5sum in md5sum_list:
            try:
                code = MappedVirtKeyboard.get_symbol_code(self,md5sum)
            except VirtKeyboardError:
                continue
            else:
                return ''.join(re.findall(r"'(\d+)'", code)[-2:])
        raise VirtKeyboardError('Symbol not found')

    def get_string_code(self, string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code


class LoginPage(HTMLPage):
    def login(self, login, password):
        if login.isdigit():
            vk = VirtKeyboard(self)

            form = self.get_form('//form[@id="formulaire-login"]')
            code = vk.get_string_code(password)
            try:
                assert len(code)==10
            except AssertionError:
                raise BrowserIncorrectPassword("Wrong number of character")
            form['accordirect.identifiant'] = login
            form['accordirect.code'] = code
        else:
            form = self.get_form('//form[@id="formulaire-login-email"]')
            form['email.identifiant'] = login
            form['email.code'] = password
        form.submit()


class ChoicePage(LoggedPage, HTMLPage):
    def get_pages(self):
        for page_attrib in self.doc.xpath('//a[@data-site]/@data-site'):
            yield self.browser.open('/site/s/login/loginidentifiant.html',
                                    data={'selectedSite': page_attrib}).page


class DetailPage(LoggedPage, HTMLPage):

    def iter_accounts(self):
        return []


class ClientPage(LoggedPage, HTMLPage):
    is_here = "//div[@id='situation']"

    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@id="situation"]//div[@class="synthese-produit"]'

        class item(ItemElement):
            klass = Account

            obj_currency = u'EUR'
            obj_type = Account.TYPE_CARD
            obj_label = Env('label')
            obj__num = Env('_num')
            obj_id = Env('id')
            obj_balance = Env('balance')
            obj__site = 'oney'

            def parse(self, el):
                self.env['label'] = CleanText('./h3/a')(self) or u'Carte Oney'
                self.env['_num'] = Attr('%s%s%s' % ('//option[contains(text(), "', Field('label')(self).replace('Ma ', ''), '")]'), 'value', default=u'')(self)
                self.env['id'] = Format('%s%s' % (self.page.browser.username, Field('_num')(self)))(self)

                # On the multiple accounts page, decimals are separated with dots, and separated with commas on single account page.
                amount_due = CleanDecimal('./p[@class = "somme-due"]/span[@class = "synthese-montant"]', default=None)(self)
                if amount_due is None:
                    amount_due = CleanDecimal('./div[@id = "total-sommes-dues"]/p[contains(text(), "sommes dues")]/span[@class = "montant"]', replace_dots=True)(self)
                self.env['balance'] = - amount_due


class OperationsPage(LoggedPage, HTMLPage):
    is_here = "//div[@id='releve-reserve-credit'] | //div[@id='operations-recentes'] | //select[@id='periode']"

    @pagination
    @method
    class iter_transactions(ListElement):
        item_xpath = '//table[@class="tableau-releve"]/tbody/tr[not(node()//span[@class="solde-initial"])]'
        flush_at_end = True

        def flush(self):
            # As transactions are unordered on the page, we flush only at end
            # the sorted list of them.
            return sorted_transactions(self.objects.values())

        def store(self, obj):
            # It stores only objects with an ID. To be sure it works, use the
            # uid of transaction as object ID.
            obj.id = obj.unique_id(seen=self.env['seen'])
            return ListElement.store(self, obj)

        class credit(ItemElement):
            klass = Transaction
            obj_type = Transaction.TYPE_CARD
            obj_date = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = Env('amount')

            def condition(self):
                self.env['amount'] = Transaction.Amount('./td[3]')(self.el)
                return self.env['amount'] > 0

        class debit(ItemElement):
            klass = Transaction
            obj_type = Transaction.TYPE_CARD
            obj_date = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = Env('amount')

            def condition(self):
                self.env['amount'] = Transaction.Amount('', './td[4]')(self.el)
                return self.env['amount'] < 0

        def next_page(self):
            options = self.page.doc.xpath('//select[@id="periode"]//option[@selected="selected"]/preceding-sibling::option[1]')
            if options:
                data = {'numReleve':options[0].values(),'task':'Releve','process':'Releve','eventid':'select','taskid':'','hrefid':'','hrefext':''}
                return requests.Request("POST", self.page.url, data=data)


class CreditHome(LoggedPage, HTMLPage):
    def get_name(self):
        # boulanger/auchan/etc.
        return CleanText('//div[@class="conteneur"]/h1')(self.doc)


class CreditAccountPage(LoggedPage, HTMLPage):
    @method
    class get_account(ItemElement):
        klass = Account

        obj_type = Account.TYPE_CARD
        obj__site = 'other'

        def obj_label(self):
            return self.page.browser.card_name

        obj_id = CleanText('//tr[td[text()="Mon numéro de compte"]]/td[@class="droite"]', replace=[(' ', '')])
        obj_balance = CleanDecimal('''//div[@id="mod-paiementcomptant"]//tr[td[starts-with(normalize-space(text()),"Disponible jusqu'au")]]/td[@class="droite"]''')
        obj_coming = CleanDecimal('''//div[@id="mod-paiementcomptant"]//tr[td[span[contains(text(),"prélevé le")]]]/td[@class="droite"]''', sign=lambda _: -1, default=0)
        # what's the balance anyway?
        # there's "Paiements au comptant" and sometimes "Retraits d'argent au comptant"


class CreditHistory(LoggedPage, XLSPage):
    # this history doesn't contain the monthly recharges, so the balance isn't consistent with the transactions?
    def iter_history(self):
        header, lines = self.doc[0], self.doc[1:][::-1]
        assert header == ['Date', "Libellé de l'opération ", ' Débit', 'Credit'], "wrong columns"

        for line in lines:
            tr = Transaction()
            tr.raw = line[1]

            assert not (line[2] and line[3]), "cannot have both debit and credit"
            amount = float(line[3] or 0) - abs(float(line[2] or 0))
            tr.amount = Decimal(str(amount))
            tr.date = parse_french_date(line[0])
            yield tr
