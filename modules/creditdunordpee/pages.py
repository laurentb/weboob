# -*- coding: utf-8 -*-

# Copyright(C) 2016      Bezleputh
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

from io import BytesIO
import re

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard
from weboob.browser.elements import ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Format, Regexp, Date, Env, TableCell, Currency, Eval
from weboob.browser.filters.html import CleanHTML
from weboob.capabilities.bank import Account, Transaction, Investment
from weboob.capabilities.base import NotAvailable


class VirtKeyboard(MappedVirtKeyboard):
    symbols = {'0': ('8adee734aaefb163fb008d26bb9b3a42', '922d79345bf824b1186d0aa523b37a7c'),
               '1': ('b815d6ce999910d48619b5912b81ddf1', '4730473dcd86f205dff51c59c97cf8c0'),
               '2': ('54255a70694787a4e1bd7dd473b50228', '2d8b1ab0b5ce0b88abbc0170d2e85b7e'),
               '3': ('ba06373d2bfba937d00bf52a31d475eb', '08e7e7ab7b330f3cfcb819b95eba64c6'),
               '4': ('3fa795ac70247922048c514115487b10', 'ffb3d035a3a335cfe32c59d8ee1302ad'),
               '5': ('788963d15fa05832ee7640f7c2a21bc3', 'c4b12545020cf87223901b6b35b9a9e2'),
               '6': ('c8bf62dfaed9feeb86934d8617182503', '473357666949855a0794f68f3fc40127'),
               '7': ('f7543fdda3039bdd383531954dd4fc46', '5f3a71bd2f696b8dc835dfeb7f32f92a'),
               '8': ('5c4210e2d8e39f7667d7a9e5534b18b7', 'b9a1a73430f724541108ed5dd862431b'),
               '9': ('94520ac801883fbfb700f43cd4172d41', '12c18ca3d4350acd077f557ac74161e5')}

    def __init__(self, page):
        self.img_id = page.doc.find("//input[@id='identifiantClavierVirtuel']").attrib['value']
        img = page.doc.find("//img[@id='clavier_virtuel']")
        res = page.browser.open('/portal/rest/clavier_virtuel/%s' % self.img_id)
        MappedVirtKeyboard.__init__(self, BytesIO(res.content), page.doc, img, (0, 0, 0), convert='RGB')

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def get_symbol_code(self, md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self, md5sum)
        return ''.join(re.findall(r"'(\d+)'", code)[-2:])

    def get_string_code(self, string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code


class LoginPage(HTMLPage):
    pass


class HomePage(HTMLPage):
    def get_coded_passwd(self, password):
        vk = VirtKeyboard(self)
        return '%s|%s|#006#' % (vk.get_string_code(password), vk.img_id)

    def is_logged(self):
        return len(self.doc.find('//a[@class="btn-deconnexion"]'))


class AvoirPage(LoggedPage, HTMLPage):
    @method
    class get_account(ItemElement):
        klass = Account

        obj_label = Format('PEE %s', CleanText('//div[@id="pbGp_df83b8bd_2dd787_2d4d10_2db608_2d69c44af91e91_j_id1:j_idt1:j_idt2:j_idt15_body"]'))

        def obj_balance(self):
            return CleanDecimal('.', replace_dots=True).filter(self.fetch_total())

        def obj_currency(self):
            return Currency('.').filter(self.fetch_total())

        obj_type = Account.TYPE_PEE

        def fetch_total(self):
            table, = self.el.xpath('//table[has-class("operation-bloc-content-tableau-synthese")]')
            assert CleanText('(./thead//th)[3]')(table) == 'Total'
            tr, = table.xpath('./tbody[1]/tr')
            return CleanText('./td[3]/div')(tr)

    @method
    class iter_investment(TableElement):
        head_xpath = '//div[has-class("detail-epargne-par-support")]//table/thead//th'
        item_xpath = '//div[has-class("detail-epargne-par-support")]//table/tbody[1]/tr'

        col_misc = 'Mes supports de placement'
        col_portfolio_share = 'Répartition'
        col_valuation = 'Montant brut (1)'
        col_diff = '+ ou - value potentielle'

        class item(ItemElement):
            klass = Investment

            obj_label = Regexp(CleanText(CleanHTML(TableCell('misc'))), r'^(.*? - \d+)')
            obj_vdate = Date(Regexp(CleanHTML(TableCell('misc')), r'(\d{2}/\d{2}/\d{4})'))
            obj_unitvalue = CleanDecimal(Regexp(CleanText(TableCell('misc')), r'([\d,]+) €'), replace_dots=True)
            obj_portfolio_share = Eval(lambda x: x / 100, CleanDecimal(CleanHTML(TableCell('portfolio_share')), replace_dots=True))
            obj_valuation = CleanDecimal(CleanHTML(TableCell('valuation')), replace_dots=True)
            obj_diff = CleanDecimal(CleanHTML(TableCell('diff')), replace_dots=True)


class HistoryPage(LoggedPage, HTMLPage):
    @method
    class get_history(TableElement):
        head_xpath = u'//table[has-class("operation-bloc-content-tableau")]/thead/tr/th/div/div/div/div/div/div/a/text()'
        item_xpath = u'//table[has-class("operation-bloc-content-tableau")]/tbody/tr[has-class("rf-dt-r")]'

        col_date = u'Date de création'
        col_reference = u'Référence'
        col_montant = u'Montant net'
        col_type = u'Type d’opération'

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText(TableCell('date')), Env('date_guesser'))
            obj_type = Transaction.TYPE_UNKNOWN
            obj_id = CleanText(TableCell('reference'))
            obj_label = CleanText(TableCell('type'))
            obj_amount = CleanDecimal(CleanHTML(TableCell('montant')),
                                      replace_dots=True, default=NotAvailable)
