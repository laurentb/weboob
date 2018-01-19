# -*- coding: utf-8 -*-

# Copyright(C) 2013-2014      Romain Bignon
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


from dateutil.relativedelta import relativedelta
from decimal import Decimal, InvalidOperation
import re
from io import BytesIO

from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal, Env, \
                                            Currency
from weboob.browser.filters.html import Attr
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.exceptions import BrowserIncorrectPassword


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(ur'^(?P<text>.*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_CARD)]


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
        vk = VirtKeyboard(self)

        form = self.get_form('//form[@id="formulaire-login"]')
        code = vk.get_string_code(password)
        if not len(code)==10:
            BrowserIncorrectPassword()
        form['accordirect.identifiant'] = login
        form['accordirect.code'] = code
        form.submit()


class IndexPage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        item_xpath = '(//li[@id="menu-n2-mesproduits"])[1]//li//a'

        class item(ItemElement):
            klass = Account
            obj_id = Regexp(Attr('.', 'onclick'), r"^[^']+'([^']+)'.*", r"\1")
            obj_label = CleanText('.')

            def condition(self):
                return self.el.get('onclick') is not None

    loan_init_date = Transaction.Date(CleanText('//table//td[contains(text(), "Date de sous")]/../td[2]'))
    loan_next_date = Transaction.Date(CleanText('//table//td[contains(text(), "Prochaine")]/../td[2]'))
    loan_nb = CleanText('//table//td[contains(text(), "Nombre de mensu") and contains(text(), "rembours")]/../td[2]')
    loan_total_amount = CleanDecimal('//table//td/strong[contains(text(), "Montant emprunt")]/../../td[2]', replace_dots=False)
    loan_amount = CleanDecimal('//table//td/strong[contains(text(), "Montant de la")]/../../td[2]', replace_dots=False)

    def get_loan_balance(self):
        try:
            total_amount = - self.loan_total_amount(self.doc)
        except InvalidOperation:
            return None

        nb = int(self.loan_nb(self.doc))
        amount = self.loan_amount(self.doc)

        return total_amount + (nb*amount)

    def iter_loan_transactions(self):
        init_date = self.loan_init_date(self.doc)
        next_date = self.loan_next_date(self.doc)
        nb = int(self.loan_nb(self.doc))
        total_amount = - self.loan_total_amount(self.doc)
        amount = self.loan_amount(self.doc)

        if init_date is NotAvailable and total_amount == Decimal('0.0'):
            return

        for _ in xrange(nb):
            next_date = next_date - relativedelta(months=1)
            tr = Transaction()
            tr.raw = tr.label = u'Mensualité'
            tr.date = tr.rdate = tr.vdate = next_date
            tr.amount = amount
            yield tr

        tr = Transaction()
        tr.raw = tr.label = u'Emprunt initial'
        tr.date = tr.rdate = init_date
        tr.amount = total_amount
        yield tr

    def get_card_name(self):
        return CleanText('//h1[1]')(self.doc)


class AccountsPage(LoggedPage, HTMLPage):
    def get_balance(self):
        balance = Decimal('0.0')
        lines = self.doc.xpath('//div[@class="detail"]/table//tr')
        if len(lines) == 0:
            return None

        for line in lines:
            try:
                left = line.xpath('./td[@class="gauche"]')[0]
                right = line.xpath('./td[@class="droite"]')[0]
            except IndexError:
                #useless line
                continue

            if len(left.xpath('./span[@class="precision"]')) == 0 or \
               (left.text is None or 'total' not in left.text.lower()):
                continue

            balance -= CleanDecimal('.', replace_dots=False)(right)
        return balance

    def get_currency(self):
        return Currency().filter(self.doc.xpath('//section[@id="onglet-detailcompte"]//td[@class="droite"]')[0])

class OperationsPage(LoggedPage, HTMLPage):
    @method
    class iter_transactions(ListElement):
        item_xpath = '//div[contains(@class, "mod-listeoperations")]//table/tbody/tr'

        class credit(ItemElement):
            klass = Transaction
            obj_type = Transaction.TYPE_CARD
            obj_date = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = Env('amount')

            def condition(self):
                self.env['amount'] = Transaction.Amount('./td[4]')(self.el)
                return self.env['amount'] > 0

        class debit(ItemElement):
            klass = Transaction
            obj_type = Transaction.TYPE_CARD
            obj_date = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = Env('amount')

            def condition(self):
                self.env['amount'] = - Transaction.Amount('./td[3]')(self.el)
                return self.env['amount'] != 0
