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

import hashlib

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.filters.standard import (
    CleanText, Env, Field, Regexp, Format, Date, Coalesce,
)
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.html import Attr
from weboob.capabilities.bill import DocumentTypes, Document, Subscription
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
        obj_firstname = CleanText('//div[span[contains(text(), "Prénom")]]/following-sibling::div/span')
        obj_lastname = CleanText('//div[span[contains(text(), "Nom")]]/following-sibling::div/span')
        obj_email = CleanText('//div[span[contains(text(), "Adresse électronique")]]/following-sibling::div/span')
        obj_mobile = CleanText('//div[span[text()="Téléphone portable"]]/following-sibling::div/span', default=NotAvailable)
        obj_phone = CleanText('//div[span[text()="Téléphone fixe"]]/following-sibling::div/span', default=NotAvailable)

        def obj_birth_date(self):
            return parse_french_date(CleanText('//div[span[text()="Date de naissance"]]/following-sibling::div/span')(self)).date()


class DocumentsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_documents(ListElement):
        item_xpath = '//ul[has-class("documents")]/li'

        def next_page(self):
            previous_year = CleanText('//li[has-class("blocAnnee") and has-class("selected")]/following-sibling::li[1]/a')(self.page.doc)
            # only if previous_year, else we return to page with current year and fall to an infinite loop
            if previous_year:
                return self.page.browser.documents.build(params={'n': previous_year})

        class item(ItemElement):
            klass = Document

            obj__idEnsua = Attr('.//form/input[@name="idEnsua"]', 'value')  # can be 64 or 128 char length

            def obj_id(self):
                # hash _idEnsua to reduce his size at 32 char
                hash = hashlib.sha1(Field('_idEnsua')(self).encode('utf-8')).hexdigest()
                return '%s_%s' % (Env('subid')(self), hash)

            obj_date = Date(Env('date'))
            obj_label = Env('label')
            obj_type = DocumentTypes.INCOME_TAX
            obj_format = 'pdf'
            obj_url = Format('/enp/ensu/Affichage_Document_PDF?idEnsua=%s', Field('_idEnsua'))

            def parse(self, el):
                label_ct = CleanText('./div[has-class("texte")]')
                date = Regexp(label_ct, 'le ([\w\/]+)', default=None)(self)
                self.env['label'] = label_ct(self)

                if not date:
                    year = Regexp(label_ct, '\s(\d{4})\s', default=None)(self)
                    if 'sur les revenus de' in self.env['label']:
                        # this kind of document always appear un july, (but we don't know the day)
                        date = '%s-07-01' % year
                    else:
                        date = '%s-01-01' % year
                self.env['date'] = date
