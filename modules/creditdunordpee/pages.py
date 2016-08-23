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
from cStringIO import StringIO
import re
from decimal import Decimal
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard
from weboob.browser.elements import ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Format, Regexp, Date, Env, TableCell, Field
from weboob.browser.filters.html import CleanHTML
from weboob.capabilities.bank import Account, Transaction, Investment


class VirtKeyboard(MappedVirtKeyboard):
    symbols = {'0': '8adee734aaefb163fb008d26bb9b3a42',
               '1': 'b815d6ce999910d48619b5912b81ddf1',
               '2': '54255a70694787a4e1bd7dd473b50228',
               '3': 'ba06373d2bfba937d00bf52a31d475eb',
               '4': '3fa795ac70247922048c514115487b10',
               '5': '788963d15fa05832ee7640f7c2a21bc3',
               '6': 'c8bf62dfaed9feeb86934d8617182503',
               '7': 'f7543fdda3039bdd383531954dd4fc46',
               '8': '5c4210e2d8e39f7667d7a9e5534b18b7',
               '9': '94520ac801883fbfb700f43cd4172d41',
    }

    def __init__(self, page):
        self.img_id = page.doc.find("//input[@id='identifiantClavierVirtuel']").attrib['value']
        img = page.doc.find("//img[@id='clavier_virtuel']")
        res = page.browser.open('/portal/rest/clavier_virtuel/%s' % self.img_id)
        MappedVirtKeyboard.__init__(self, StringIO(res.content), page.doc, img, (0, 0, 0), convert='RGB')

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
        obj_balance = CleanDecimal('//div[@id="pbGp_3f1d2af7_2ddd41_2d45d2_2dbb9d_2d8f27b33a375f_j_id1:j_idt1:form:j_idt2:j_idt14:j_idt23:0:j_idt65:j_idt47_body"]',
                                   default=0,
                                   replace_dots=True)
        obj_currency = Regexp(CleanText('//div[@id="pbGp_3f1d2af7_2ddd41_2d45d2_2dbb9d_2d8f27b33a375f_j_id1:j_idt1:form:j_idt2:j_idt14:j_idt23:0:j_idt65:j_idt47_body"]'),
                              '.*(.)$', default=u'€')
        obj_type = Account.TYPE_PEE

    @method
    class iter_investment(TableElement):
        head_xpath = u'//table[@id="pbGp_3f1d2af7_2ddd41_2d45d2_2dbb9d_2d8f27b33a375f_j_id1:j_idt1:form:j_idt2:j_idt413:j_idt447"]/thead/tr/th/@id'
        item_xpath = u'//table[@id="pbGp_3f1d2af7_2ddd41_2d45d2_2dbb9d_2d8f27b33a375f_j_id1:j_idt1:form:j_idt2:j_idt413:j_idt447"]/tbody/tr[@id]'

        col_reference = u'pbGp_3f1d2af7_2ddd41_2d45d2_2dbb9d_2d8f27b33a375f_j_id1:j_idt1:form:j_idt2:j_idt413:j_idt447:j_idt450'
        col_montant = u'pbGp_3f1d2af7_2ddd41_2d45d2_2dbb9d_2d8f27b33a375f_j_id1:j_idt1:form:j_idt2:j_idt413:j_idt447:j_idt456'
        col_repartition = u'pbGp_3f1d2af7_2ddd41_2d45d2_2dbb9d_2d8f27b33a375f_j_id1:j_idt1:form:j_idt2:j_idt413:j_idt447:j_idt460'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(Regexp(CleanHTML(TableCell('reference')),
                                         '(.*)\n\n'))

            obj_vdate = Date(Regexp(CleanHTML(TableCell('reference')),
                                    '(\d{2}/\d{2}/\d{4})'))

            obj_unitvalue = CleanDecimal(Regexp(CleanHTML(TableCell('reference')),
                                                '.*\n\n(.*)\n\n'),
                                         replace_dots=True)

            obj_description = CleanText(CleanHTML(TableCell('reference')))

            obj_portfolio_share = CleanDecimal(CleanHTML(TableCell('repartition')),
                                               replace_dots=True)

            obj_valuation = CleanDecimal(CleanHTML(TableCell('montant')),
                                         replace_dots=True)

            def obj_quantity(self):
                return Decimal(Field('valuation')(self)/Field('unitvalue')(self))


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
                                      replace_dots=True)
