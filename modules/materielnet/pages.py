# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.filters.standard import CleanText, CleanDecimal, Env, Format, Date, Async, AsyncLoad
from weboob.browser.elements import ListElement, ItemElement, TableElement, method
from weboob.browser.filters.html import Attr, Link, TableCell
from weboob.capabilities.bill import Bill, Subscription
from weboob.capabilities.base import NotAvailable

class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@class="login-form"]')
        form['identifier'] = login
        form['credentials'] = password
        form.submit()

    def get_error(self):
        return CleanText('//div[@class="ValidatorError"]')(self.doc)


class CaptchaPage(HTMLPage):
    def get_error(self):
        return CleanText('//div[@class="captcha-block"]/p[1]/text()')(self.doc)


class ProfilPage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        class item(ItemElement):
            klass = Subscription

            obj_subscriber = Format('%s %s', Attr('//input[@id="prenom"]', 'value'), Attr('//input[@id="nom"]', 'value'))
            obj_id = Env('subid')
            obj_label = obj_id

            def parse(self, el):
                self.env['subid'] = self.page.browser.username


class DocumentsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class get_documents(TableElement):
        item_xpath = '//div[@id="ListCmd"]//table//tr[position() > 1]'
        head_xpath = '//div[@id="ListCmd"]//table//tr//th'

        col_id = u'Référence'
        col_date = u'Date'
        col_price = u'Montant'

        def next_page(self):
            m = re.search('([^*]+page=)([^*]+)', self.page.url)
            if m:
                page = int(m.group(2)) + 1
                if self.el.xpath('//a[contains(@href, "commande.html?page=' + str(page) + '")]'):
                    next_page = u"%s%s" % (m.group(1), page)
                    return next_page

        class item(ItemElement):
            klass = Bill

            load_details = Attr('./td/a', 'href') & AsyncLoad

            obj_id = Format('%s_%s', Env('email'), CleanDecimal(TableCell('id')))
            obj_url = Async('details') & Link('//a[contains(@href, "facture")]', default=NotAvailable)
            obj_date = Date(CleanText(TableCell('date')))
            obj_format = u"pdf"
            obj_label = Async('details') & CleanText('//table/tr/td[@class="Prod"]')
            obj_type = u"bill"
            obj_price = CleanDecimal(TableCell('price'), replace_dots=True)
            obj_currency = u'EUR'

            def parse(self, el):
                self.env['email'] = self.page.browser.username
