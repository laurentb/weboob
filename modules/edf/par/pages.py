# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from datetime import datetime
from decimal import Decimal

from weboob.browser.filters.html import Attr
from weboob.browser.pages import LoggedPage, JsonPage, HTMLPage, RawPage
from weboob.browser.filters.standard import Env, Format, Date, Eval, CleanText, Regexp
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import DocumentTypes, Bill, Subscription
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.profile import Profile


class HomePage(HTMLPage):
    pass


class AuthenticatePage(JsonPage):
    def has_captcha_request(self):
        return self.doc['stage'] == "RecaptchaModuleS1"

    def get_data(self):
        return self.doc

    def get_token(self):
        return self.doc['tokenId']


class AuthorizePage(HTMLPage):
    def on_load(self):
        if Attr('//body', 'onload', default=NotAvailable)(self.doc):
            self.get_form().submit()


class WrongPasswordPage(HTMLPage):
    def get_wrongpass_message(self, attempt_number):
        # edf website block access after 5 wrong password, and user will have to change his password
        # this is very important because it can tell to user how much attempt it remains
        script = CleanText('//script[contains(text(), "Mot de passe incorrect")]')

        if attempt_number > 0:
            return Format('%s %s %s',
                          Regexp(script, r">(Mot de passe incorrect.*?)<"),
                          CleanText('//div[@class="arrow_box--content"]', children=False), int(attempt_number))(self.doc)
        return Regexp(script, r">(Vous avez atteint.*?)<")(self.doc)



class WelcomePage(LoggedPage, HTMLPage):
    pass


class CheckAuthenticatePage(LoggedPage, RawPage):
    pass


class UnLoggedPage(HTMLPage):
    pass


class ProfilPage(JsonPage):
    @property
    def logged(self):
        return self.doc['errorCode'] == 0

    @method
    class iter_subscriptions(DictElement):
        item_xpath = 'customerAccordContracts'

        class item(ItemElement):
            klass = Subscription

            obj_subscriber = Format('%s %s', Dict('bp/identity/firstName'),
                                             Dict('bp/identity/lastName'))
            obj_id = Dict('number')
            obj_label = obj_id

    def get_token(self):
        return Dict('data')(self.doc)


class DocumentsPage(LoggedPage, JsonPage):
    @method
    class iter_bills(DictElement):
        def parse(self, el):
            for i, sub_group in enumerate(self.el):
                for j, sub in enumerate(Dict('listOfBillsByAccDTO')(sub_group)):
                    if Dict('accDTO/numAcc')(sub) in Env('subid')(self):
                        self.item_xpath = "%d/listOfBillsByAccDTO/%d/listOfbills" % (i, j)
                        self.env['bpNumber'] = Dict('%d/bpDto/bpNumber' % i)(self)
                        break

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), Dict('documentNumber'))
            obj_date = Date(Eval(lambda t: datetime.fromtimestamp(int(t) / 1000) \
                                 .strftime('%Y-%m-%d'), Dict('creationDate')))
            obj_format = 'pdf'
            obj_label = Format('Facture %s', Dict('documentNumber'))
            obj_type = DocumentTypes.BILL
            obj_price = Env('price')
            obj_currency = 'EUR'
            obj_vat = NotAvailable
            obj__doc_number = Dict('documentNumber')
            obj__par_number = Dict('parNumber')
            obj__num_acc = Env('numAcc')
            obj__bp = Env('bpNumber')

            def parse(self, el):
                self.env['price'] = Decimal(Dict('billAmount')(self))
                self.env['numAcc'] = str(int(Env('subid')(self)))

    def get_bills_informations(self):
        return {
            'bpNumber': Dict('bpNumber')(self.doc),
            'docId': Dict('docId')(self.doc),
            'docName': Dict('docName')(self.doc),
            'numAcc': Dict('numAcc')(self.doc),
            'parNumber': Dict('parNumber')(self.doc)
        }


class ProfilePage(LoggedPage, JsonPage):
    def get_profile(self):
        data = self.doc['bp']
        p = Profile()

        p.address = '%s %s %s %s' % (data['streetNumber'], data['streetName'],
                                     data['postCode'], data['city'])
        p.name = '%s %s %s' % (data['civility'], data['lastName'], data['firstName'])
        p.phone = data['mobilePhoneNumber'] or data['fixPhoneNumber']
        p.email = data['mail']

        return p


class BillDownload(LoggedPage, RawPage):
    pass
