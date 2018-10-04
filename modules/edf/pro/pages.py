# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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

from datetime import date

from weboob.browser.pages import JsonPage, HTMLPage, RawPage, LoggedPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.standard import CleanDecimal, CleanText
from weboob.browser.filters.html import CleanHTML
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Subscription, Bill
from weboob.exceptions import ActionNeeded
from weboob.capabilities.profile import Profile


class LoginPage(JsonPage):
    def get_data(self, login, password):
        login_data = self.doc
        login_data['callbacks'][0]['input'][0]['value'] = login
        login_data['callbacks'][1]['input'][0]['value'] = password
        return login_data


class AuthPage(RawPage):
    pass


class HomePage(LoggedPage, HTMLPage):
    pass


class LireSitePage(LoggedPage, JsonPage):
    def build_doc(self, text):
        if text == 'REDIRECT_CGU':  # JSON can always be decoded in UTF-8 so testing text is fine
            raise ActionNeeded("Vous devez accepter les conditions générales d'utilisation sur le site de votre banque.")
        else:
            return super(LireSitePage, self).build_doc(text)
    # id site is not about website but geographical site
    def get_id_site_list(self):
        return [site['idSite'] for site in self.doc['site']]


class SubscriptionsPage(LoggedPage, JsonPage):
    def build_doc(self, text):
        if text == 'REDIRECT_CGU':
            raise ActionNeeded("Vous devez accepter les conditions générales d'utilisation sur le site de votre banque.")
        return super(SubscriptionsPage, self).build_doc(text)

    @method
    class get_subscriptions(DictElement):
        item_xpath = 'listeContrat'

        class item(ItemElement):
            klass = Subscription

            obj_id = CleanText(Dict('refDevisLabel'))
            obj__refdevis =  CleanText(Dict('refDevis'))
            obj_label = CleanText(CleanHTML(Dict('nomOffreModele')))

            def obj_subscriber(self):
                return ('%s %s' % (Dict('prenomIntPrinc')(self).lower(),
                                   Dict('nomIntPrinc')(self).lower())).title()


class BillsPage(LoggedPage, JsonPage):
    def get_bill_name(self):
        return Dict('nomFichier')(self.doc)


class DocumentsPage(LoggedPage, JsonPage):
    def get_documents(self):
        documents = []

        for document in self.doc:
            doc = Bill()

            doc.id = document['numFactureLabel']
            doc.date = date.fromtimestamp(int(document['dateEmission'] / 1000))
            doc.format = 'PDF'
            doc.label = 'Facture %s' % document['numFactureLabel']
            doc.type = 'bill'
            doc.price = CleanDecimal().filter(document['montantTTC'])
            doc.currency = '€'
            doc._account_billing = document['compteFacturation']
            doc._bill_number = document['numFacture']

            documents.append(doc)

        return documents


class ProfilePage(LoggedPage, JsonPage):
    def get_profile(self):
        data = self.doc
        p = Profile()

        p.name = '%s %s %s' % (data['civilite'], data['nom'], data['prenom'])
        p.address = '%s %s %s' % (data['adresse'], data['codeSpcPostal'], data['commune'])
        p.phone = data['telMobile'] or data['telBureau']
        p.email = data['email'].replace('&#x40;', '@')

        return p
