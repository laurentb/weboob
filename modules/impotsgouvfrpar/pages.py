# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight
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

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Env, Field, Regexp, Format, Date, Async,
    AsyncLoad, Coalesce,
)
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.html import Attr
from weboob.capabilities.bill import DocumentTypes, Document, Bill, Subscription
from weboob.capabilities.profile import Person
from weboob.capabilities.base import NotAvailable
from weboob.tools.date import parse_french_date


class LoginAccessPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form(id='formulairePrincipal')
        form.url = self.browser.login_ael.build()
        form['spi'] = login
        form['pwd'] = password
        form.submit()


class LoginAELPage(HTMLPage):
    def is_login_successful(self):
        is_login_ok = CleanText('//head/title')(self.doc) == 'lmdp'
        if not is_login_ok:
            return 'wrong login'

        state = Regexp(CleanText('//script'), r"parent.postMessage\('(.*?),.*\)")(self.doc)
        if state != 'ok':
            return 'wrong password'

    def get_redirect_url(self):
        return Regexp(CleanText('//body/script'), r"postMessage\('ok,(.*)',")(self.doc)


class ProfilePage(LoggedPage, HTMLPage):
    def get_documents_link(self):
        return self.doc.xpath('//a[contains(@title, "déclarations")]/@href')[0]

    def get_bills_link(self):
        return self.doc.xpath('//a[contains(@title, "résumé")]/@href')[0]

    @method
    class get_subscriptions(ListElement):
        class item(ItemElement):
            klass = Subscription

            obj_subscriber = CleanText('//span[@class="cssTitrePrincipal"]')
            obj_id = Env('id')
            obj_label = obj_id

            def parse(self, el):
                self.env['id'] = self.page.browser.username

    @method
    class get_profile(ItemElement):
        klass = Person

        obj_name = Regexp(CleanText('//span[contains(@class, "TitrePrincipal")]'), r'^\w+ (.*)')
        obj_address = Coalesce(
            Regexp(CleanText('//td[contains(text(), "Taxe d\'habitation principale")]'), r"Taxe d'habitation principale (.*)", default=NotAvailable),
            CleanText('//td[contains(@class, "TextePrincipalNonJustifie") and text()]'),
        )

    @method
    class fill_profile(ItemElement):
        obj_email = CleanText('//div[span[contains(text(), "Adresse électronique")]]/following-sibling::div/span')
        obj_mobile = CleanText('//div[span[text()="Téléphone portable"]]/following-sibling::div/span', default=NotAvailable)
        obj_phone = CleanText('//div[span[text()="Téléphone fixe"]]/following-sibling::div/span', default=NotAvailable)

        def obj_birth_date(self):
            return parse_french_date(CleanText('//div[span[text()="Date de naissance"]]/following-sibling::div/span')(self)).date()


class BillsPage(LoggedPage, HTMLPage):
    def submit_form(self):
        form = self.get_form('//form[@name="compteForm"]')
        form['date'] = 'gardeDate'
        form['annee'] = 'all'
        form['compte'] = 'compteDetaille'
        form.submit()

    @method
    class get_bills(ListElement):
        item_xpath = '//table[@class="cssTailleTable"]//a[contains(@onclick, "ConsultationDocument")]'

        class item(ItemElement):
            def condition(self):
                return self.el.xpath('./ancestor::tr[1]/following-sibling::tr/td[contains(text(), "avant le")]')

            klass = Bill

            load_url = Field('_loadurl') & AsyncLoad

            obj_id = Format('%s_%s', Env('subid'), Regexp(Attr('.', 'onclick'), 'onis=([\d]+).*Form=([^&]+)', '\\1\\2'))
            obj__loadurl = Regexp(Attr('.', 'onclick'), '[^\']+.([^\']+)')
            obj_date = Env('date')
            obj_price = Env('price')
            obj_currency = 'EUR'

            def obj_label(self):
                year = Regexp(Attr('.', 'onclick'), 'annee=([\d]+)', default=None)(self)
                label = CleanText('./parent::td')(self)
                name = CleanText('./ancestor::tr[1]//following-sibling::tr[1]/td[1]', default=None)(self)
                label = '%s - %s' % (label, name) if name else label
                return '%s - %s' % (year, label) if year else label

            def obj_url(self):
                return Async('url', Attr('//iframe', 'src', default=Field('_loadurl')(self)))(self)

            def obj_format(self):
                return 'pdf' if 'pdf' in Field('url')(self) else 'html'

            def parse(self, el):
                tr = el.xpath('./ancestor::tr[1]/following-sibling::tr/td[contains(text(), "avant le")]')[0]
                self.env['date'] = Date(Regexp(CleanText('.'), '(\d{2}/\d{2}/\d{4})'))(tr)
                self.env['price'] = CleanDecimal('./following-sibling::td[1]', replace_dots=True, default=NotAvailable)(tr)


class DocumentsPage(LoggedPage, HTMLPage):
    def submit_form(self):
        form = self.get_form('//form[@name="documentsForm"]')
        form['annee'] = 'all'
        form.submit()

    @method
    class get_documents(ListElement):
        item_xpath = '//table[@class="cssTailleTable"]//a[contains(@onclick, "ConsultationDocument")]'

        class item(ItemElement):
            klass = Document

            load_url = Field('_loadurl') & AsyncLoad

            obj_id = Format('%s_%s', Env('subid'), Regexp(Attr('.', 'onclick'), 'onis=([\d]+).*Form=([^&]+)', '\\1\\2'))
            obj__loadurl = Regexp(Attr('.', 'onclick'), '[^\']+.([^\']+)')
            obj_date = Date(Env('date'))
            obj_label = Env('label')
            obj_type = DocumentTypes.OTHER
            obj_format = 'pdf'  # Force file format to pdf.

            def obj_url(self):
                default = Field('_loadurl')(self)
                return Async('url', Attr('//iframe', 'src', default=default))(self)

            def parse(self, el):
                year = Regexp(Attr('.', 'onclick'), 'annee=([\d]+)', default=None)(self)
                date = Regexp(CleanText('.'), 'le ([\w\/]+)', default=None)(self)
                label = CleanText('.')(self)
                name = CleanText('./parent::*/preceding-sibling::td[1]', default=None)(self)
                label = '%s - %s' % (label, name) if name else label
                self.env['label'] = '%s - %s' % (year, label) if year else label

                if not date:
                    if 'sur les revenus de' in label:
                        # this kind of document always appear un july, (but we don't know the day)
                        date = '%s-07-01' % year
                    else:
                        date = '%s-01-01' % year
                self.env['date'] = date
