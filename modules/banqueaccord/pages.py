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


from decimal import Decimal
import re

from weboob.capabilities.bank import Account
from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['LoginPage', 'IndexPage', 'AccountsPage', 'OperationsPage']


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
        img = page.document.find("//img[@usemap='#cv']")
        img_file = page.browser.openurl(img.attrib['src'])
        MappedVirtKeyboard.__init__(self, img_file, page.document, img, self.color, 'href', convert='RGB')

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def check_color(self, pixel):
        for p in pixel:
            if p >= 0xd5:
                return False

        return True

    def get_symbol_coords(self, (x1, y1, x2, y2)):
        # strip borders
        return MappedVirtKeyboard.get_symbol_coords(self, (x1+10, y1+10, x2-10, y2-10))

    def get_symbol_code(self, md5sum_list):
        for md5sum in md5sum_list:
            try:
                code = MappedVirtKeyboard.get_symbol_code(self,md5sum)
            except VirtKeyboardError:
                continue
            else:
                return ''.join(re.findall("'(\d+)'", code)[-2:])
        raise VirtKeyboardError('Symbol not found')

    def get_string_code(self, string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code

class LoginPage(BasePage):
    def login(self, login, password):
        vk = VirtKeyboard(self)

        form = self.document.xpath('//form[@id="formulaire-login"]')[0]
        code = vk.get_string_code(password)
        assert len(code)==10, BrokenPageError("Wrong number of character.")
        self.browser.location(self.browser.buildurl(form.attrib['action'], identifiant=login, code=code), no_login=True)

class IndexPage(BasePage):
    def get_list(self):
        for line in self.document.xpath('//li[@id="menu-n2-mesproduits"]//li//a'):
            if line.get('onclick') is None:
                continue
            account = Account()
            account.id = line.get('onclick').split("'")[1]
            account.label = self.parser.tocleanstring(line)
            yield account

    def get_loan_balance(self):
        xpath = '//table//td/strong[contains(text(), "Montant emprunt")]/../../td[2]'
        try:
            return - Decimal(FrenchTransaction.clean_amount(self.parser.tocleanstring(self.document.xpath(xpath)[0])))
        except IndexError:
            return None

    def get_card_name(self):
        return self.parser.tocleanstring(self.document.xpath('//h1')[0])

class AccountsPage(BasePage):
    def get_balance(self):
        balance = Decimal('0.0')
        for line in self.document.xpath('//div[@class="detail"]/table//tr'):
            try:
                left = line.xpath('./td[@class="gauche"]')[0]
                right = line.xpath('./td[@class="droite"]')[0]
            except IndexError:
                #useless line
                continue

            if len(left.xpath('./span[@class="precision"]')) == 0 and (left.text is None or not 'total' in left.text.lower()):
                continue

            balance -= Decimal(FrenchTransaction.clean_amount(right.text))
        return balance


class OperationsPage(BasePage):
    def get_history(self):
        for tr in self.document.xpath('//div[contains(@class, "mod-listeoperations")]//table/tbody/tr'):
            cols = tr.findall('td')

            date = self.parser.tocleanstring(cols[0])
            raw = self.parser.tocleanstring(cols[1])
            label = re.sub(u' - traité le \d+/\d+', '', raw)

            debit = self.parser.tocleanstring(cols[3])
            if len(debit) > 0:
                t = FrenchTransaction(0)
                t.parse(date, raw)
                t.label = label
                t.set_amount(debit)
                yield t

            amount = self.parser.tocleanstring(cols[2])
            if len(amount) > 0:
                t = FrenchTransaction(0)
                t.parse(date, raw)
                t.label = label
                t.set_amount(amount)
                t.amount = - t.amount
                yield t
