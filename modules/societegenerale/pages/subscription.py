# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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
from dateutil.relativedelta import relativedelta

from weboob.capabilities.bill import Document, Subscription
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Env, Date, Format, Field
from weboob.browser.filters.html import Link, TableCell, Attr
from weboob.browser.pages import LoggedPage

from .base import BasePage

class BankStatementPage(LoggedPage, BasePage):
    @method
    class iter_subscription(TableElement):
        item_xpath = '//table[.//th]//tr[td and @class="LGNTableRow"]'
        head_xpath = '//table//th'

        col_id = 'Numéro de Compte'
        col_label = 'Type de Compte'
        col__last_document_label = 'Derniers relevés'

        class item(ItemElement):
            def condition(self):
                return 'Récapitulatif annuel' not in CleanText(TableCell('_last_document_label'))(self)

            klass = Subscription

            obj_id = CleanText(TableCell('id'), replace=[(' ', '')])
            obj_label = CleanText(TableCell('label'))

    @method
    class iter_searchable_subscription(TableElement):
        item_xpath = '//table//tr[@class="fond_ligne"]'
        head_xpath = '//table//td[contains(@class, "titre_tab") and div[@align="center"]]'

        col_id = 'Numéro de Compte'
        col_label = 'Libellé'
        col_rad_button = 'Sélection'
        col_type = 'Type de Compte'

        class item(ItemElement):
            klass = Subscription

            obj_id = CleanText(TableCell('id'), replace=[(' ', '')])
            obj_subscriber = Env('subscriber')

            def obj_label(self):
                label = CleanText(TableCell('label'))(self)
                if not label:
                    return Format('%s %s', CleanText(TableCell('type')), Field('id'))(self)
                return label

            def obj__rad_button_id(self):
                return Attr('.//div/input','name')(TableCell('rad_button')(self)[0])

            def condition(self):
                # has the same id as the main account it depends on
                return 'Points de fidélité' not in Field('label')(self)

    def post_form(self, subscription, date):
        form = self.get_form(name='abo_rce')
        form[subscription._rad_button_id] = 'on'

        # 2 months step
        begin = date - relativedelta(months=+2)

        form['rechDebMM'] = '%s' % begin.month
        form['rechDebYY'] = '%s' % begin.year
        form['rechFinMM'] = '%s' % date.month
        form['rechFinYY'] = '%s' % date.year

        m = re.search(r"surl='src=(.*)&sign=(.*)'", CleanText('//script[contains(text(), "surl")]')(self.doc))
        form['src'] = m.group(1)
        form['sign'] = m.group(2)

        form.submit()

    def iter_documents(self, subscription):
        for a in self.doc.xpath('//a[contains(@href, "pdf")]'):
            d = Document()

            d.format = 'pdf'
            d.label = CleanText('.')(a)

            if 'Récapitulatif annuel' in d.label:
                continue

            date_filter = Regexp(CleanText('.'), r'(\d{2}/\d{2}/\d{4})')
            d.date = Date(date_filter, dayfirst=True)(a)

            d.url = Regexp(Link('.'), r"= '(.*)';")(a)
            d.id = '%s_%s' % (subscription.id, date_filter(a).replace('/', ''))
            d.type = 'document'

            yield d

    def has_error_msg(self):
        return any((CleanText('//div[@class="MessageErreur"]')(self.doc),
                   CleanText('//span[@class="error_msg"]')(self.doc),
                   self.doc.xpath('//div[contains(@class, "error_page")]'), ))
