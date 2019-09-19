# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
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

from weboob.browser.elements import method, ListElement, ItemElement
from weboob.browser.filters.html import Attr, Link
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal, Currency, Field, Format, Env
from weboob.browser.pages import LoggedPage, HTMLPage, PartialHTMLPage
from weboob.capabilities.bill import Subscription, Bill
from weboob.exceptions import BrowserUnavailable
from weboob.tools.date import parse_french_date
from weboob.tools.json import json


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(id='connexioncompte_2connexionCompteForm')
        form['connexioncompte_2numSecuriteSociale'] = username
        form['connexioncompte_2codeConfidentiel'] = password
        form.submit()


class ErrorPage(HTMLPage):
    def on_load(self):
        msg = CleanText('//div[@id="backgroundId"]//p')(self.doc)
        raise BrowserUnavailable(msg)


class SubscriptionPage(LoggedPage, HTMLPage):
    @method
    class iter_subscriptions(ListElement):
        item_xpath = '//div[@id="corps-de-la-page"]//div[@class="tableau"]/div'

        class item(ItemElement):
            klass = Subscription

            obj__labelid = Attr('.', 'aria-labelledby')

            def obj__birthdate(self):
                return CleanText('//button[@id="%s"]//td[@class="dateNaissance"]' % Field('_labelid')(self))(self)

            def obj_id(self):
                # DON'T TAKE social security number for id because it's a very confidential data, take birth date instead
                return ''.join(re.findall(r'\d+', Field('_birthdate')(self)))

            def obj__param(self):
                reversed_date = ''.join(reversed(re.findall(r'\d+', Field('_birthdate')(self))))
                name = CleanText('//button[@id="%s"]//td[@class="nom"]' % Field('_labelid')(self))(self)
                return '%s!-!%s!-!1' % (reversed_date, name)

            obj_subscriber = CleanText('.//span[@class="NomEtPrenomLabel"]')
            obj_label = obj_subscriber


class DocumentsPage(LoggedPage, PartialHTMLPage):
    ENCODING = 'utf-8'

    def build_doc(self, content):
        res = json.loads(content)
        return super(DocumentsPage, self).build_doc(res['tableauPaiement'].encode('utf-8'))

    @method
    class iter_documents(ListElement):
        item_xpath = '//ul[@id="unordered_list"]//li[has-class("rowitem")]'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), Regexp(Field('url'), r'idPaiement=(.*)'))
            obj_label = CleanText('.//div[has-class("col-label")]')
            obj_price = CleanDecimal.French('.//div[has-class("col-montant")]/span')
            obj_currency = Currency('.//div[has-class("col-montant")]/span')
            obj_url = Link('.//div[@class="col-download"]/a')
            obj_format = 'pdf'

            def obj_date(self):
                year = Regexp(CleanText('./preceding-sibling::li[@class="rowdate"]//span[@class="mois"]'), r'(\d+)')(self)
                day_month = CleanText('.//div[has-class("col-date")]/span')(self)

                return parse_french_date(day_month + ' ' + year)
