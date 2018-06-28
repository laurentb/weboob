# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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

import re

from weboob.capabilities.bill import Document, Subscription
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Env, Date
from weboob.browser.filters.html import Link, TableCell, Attr
from weboob.browser.pages import LoggedPage

from .base import BasePage

class BankStatementPage(LoggedPage, BasePage):
    @method
    class iter_subscription(TableElement):
        item_xpath = '//table//tr[@class="fond_ligne"]'
        head_xpath = '//table//td[contains(@class, "titre_tab") and div[@align="center"]]'

        col_id = 'Numéro de Compte'
        col_label = 'Libellé'
        col_rad_button = 'Sélection'

        class item(ItemElement):
            klass = Subscription

            def condition(self):
                return CleanText(TableCell('label'))(self)

            obj_id = CleanText(TableCell('id'), replace=[(' ', '')])
            obj_label = CleanText(TableCell('label'))
            obj_subscriber = Env('subscriber')

            def obj__rad_button_id(self):
                return Attr('.//div/input','name')(TableCell('rad_button')(self)[0])

    def post_form(self, subscription, end_month, year):
        form = self.get_form(name='abo_rce')
        form[subscription._rad_button_id] = 'on'

        # from january to the last month
        # the last month may be the current one or december
        form['rechDebMM'] = '1'
        form['rechDebYY'] = year
        form['rechFinMM'] = end_month
        form['rechFinYY'] = year

        m = re.search(r"surl='src=(.*)&sign=(.*)'", CleanText('//script[contains(text(), "surl")]')(self.doc))
        form['src'] = m.group(1)
        form['sign'] = m.group(2)

        form.submit()

    def iter_documents(self, subscription):
        for a in self.doc.xpath('//a[contains(@href, "pdf")]'):
            d = Document()

            date_filter = Regexp(CleanText('.'), r'(\d{2}/\d{2}/\d{4})')
            d.date = Date(date_filter, dayfirst=True)(a)

            d.format = 'pdf'
            d.label = CleanText('.')(a)
            d.url = Regexp(Link('.'), r"= '(.*)';")(a)
            d.id = '%s_%s' % (subscription.id, date_filter(a).replace('/', ''))
            d.type = 'document'

            yield d

    def has_error_msg(self):
        return CleanText('//div[@class="MessageErreur"]')(self.doc)
