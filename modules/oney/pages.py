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

import re
from cStringIO import StringIO

import requests

from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError

from weboob.tools.browser2.page import HTMLPage, method, LoggedPage, pagination
from weboob.tools.browser2.elements import ListElement, ItemElement
from weboob.tools.browser2.filters import Env, CleanDecimal
from weboob.tools.exceptions import ParseError

__all__ = ['LoginPage', 'IndexPage', 'OperationsPage']

class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(ur'^(?P<text>.*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_CARD)]


class VirtKeyboard(MappedVirtKeyboard):
    symbols={'0':('069f9dd5e75d8419476b18f1551e59ce','4d3d5662b2a85ab7f0dc33b234eeaa12','9dbc8f4af61329c68cb53f62570ab213',
                  'c375d0349a6b097ac2708cc12736651a','15997d39cbdceecf8fc3050f86811ded',),
             '1':('ddc9036ea2ae1bdfbb15616a0e3a0d90',),
             '2':('27638b6ebedf6a23149990495ef4c1c5','f602ee70136eb2331275a8ac8cd636de','ff1f44c05a5eab4569bef7bde84e5b66',
                  '3b0795e3fc0af85c4838279847cb87f7','ac27be9df781cc8756f999d61f7a46f3',),
             '3':('45101362592c07bc94f8449a1f4479f1','b24990f89de3454038b7c7940bc1053f','bf0d6bd4f13ea9b57a72f76c6dad0b41',
                  '743762655b13c97908b17ce7b36a1f5a','53f9b643c228e99723c384fe12390a0e','f206adf0be6f3c6613452c19a7b0babe',
                  'f206adf0be6f3c6613452c19a7b0babe',),
             '4':('9d5d871b405465218cc892dc015ea6d8','fed023bedd046b9f4d169c6ab12f6d4c','5069a391893fb107fbc39923a9d108ef',),
             '5':('5ef102b78f5dc642ee98e9bdcf42a02e','496418730424d7f40d2b137d56bcbfe8','139186da206acf5344362ed86da42a7f',
                  'e080cd4fbda1493034f1444eae484887',),
             '6':('ab1fff097099fb395fe73470f7afcae0','70c64ac427435d40d2713128e8735b4d','bbb6fc3d0f23fa5104e2ea602ecc2d18',
                  '5d8c50960dd1f50457697fd8a8d5622e',),
             '7':('30f11190e1772dd0f93740190aaa7608','ef5477640cf97de373e49e13caef8f5c','05dfb006e2668d7dfd210b2fdf74fef8',
                  '8efb472abef04ac9bcd1ba02b49ed6a5',),
             '8':('8a8258f63f816888b550d704f4c6a068','69cade726c4d6c8e6a72e96df059c8c7','675972437c7733747146a0851bbb5727',
                  '01ce8b70eb0761b7f4047c365faa9cf5','08e6113ad8ac2f74d104c156047819a8','c2278d5c10b9903aff14f1a6516a583b',
                  'bbba856f115bf8a45ef944a5e41ee436','f365fa7628ef15f172d40f07e54c327a',),
             '9':('bf8e09357cd69275cbc6fdef42610ea0','212af59d8bc81dff176e02c0f001aa81','a3bc28250187c34a46757f2ab01e436b',
                  '9c0ab75a491e6a64dca57543efe5012c','62bedc16830a5602e26d9a050b13d2df','2b79fff64f55c027d23895baa5d2c66b',
                  '9d5d871b405465218cc892dc015ea6d8',),
            }

    color=(0,0,0)

    def __init__(self, page):
        img = page.doc.find("//img[@usemap='#cv']")
        res = page.browser.open(img.attrib['src'])
        MappedVirtKeyboard.__init__(self, StringIO(res.content), page.doc, img, self.color, 'href', convert='RGB')

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def check_color(self, pixel):
        for p in pixel:
            if p >= 200:
                return False

        return True

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
    is_here ="//form[@id='formulaire-login']"

    def login(self, login, password):
        vk = VirtKeyboard(self)

        form = self.get_form('//form[@id="formulaire-login"]')
        code = vk.get_string_code(password)
        assert len(code)==10, ParseError("Wrong number of character.")
        form['identifiant'] = login
        form['codePinpad'] = code
        form['task'] = 'Login'
        form['process'] = 'Login'
        form['eventid'] = 'suivant'
        form['modeCodeSecret'] = 'pinpad'
        form['personneIdentifiee'] = 'N'
        form.submit()

class IndexPage(LoggedPage, HTMLPage):
    is_here = "//div[@id='situation']"

    def get_balance(self):
        return  -CleanDecimal('.')(self.doc.xpath('//div[@id = "total-sommes-dues"]/p[contains(text(), "sommes dues")]/span[@class = "montant"]')[0])

class OperationsPage(LoggedPage, HTMLPage):
    is_here = "//div[@id='releve-reserve-credit']"

    @pagination
    @method
    class iter_transactions(ListElement):
        item_xpath = '//table[@class="tableau-releve"]/tbody/tr[not(node()//span[@class="solde-initial"])]'
        flush_at_end = True

        def flush(self):
            # As transactions are unordered on the page, we flush only at end
            # the sorted list of them.
            return sorted(self.objects.itervalues(), key=lambda tr: tr.rdate, reverse=True)

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
