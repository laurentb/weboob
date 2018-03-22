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


from datetime import date

from weboob.browser.pages import JsonPage, HTMLPage, RawPage, LoggedPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.standard import CleanDecimal, CleanText
from weboob.browser.filters.html import CleanHTML
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Subscription, Bill
from weboob.exceptions import ActionNeeded


class LoginPage(JsonPage):
    def get_json_data(self, login, password):
        login_data = self.doc
        login_data['callbacks'][0]['input'][0]['value'] = login
        login_data['callbacks'][1]['input'][0]['value'] = password
        return login_data


class AuthPage(RawPage):
    pass


class HomePage(LoggedPage, HTMLPage):
    pass


class LireSitePage(LoggedPage, JsonPage):
    # id site is not about website but geographical site
    def get_id_site_list(self):
        return [site['idSite'] for site in self.doc['site']]


class SubscriptionsPage(LoggedPage, JsonPage):
    def build_doc(self, text):
        if self.content == 'REDIRECT_CGU':
            raise ActionNeeded(u"Vous devez accepter les conditions générales d'utilisation sur le site de votre banque.")
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
                return ('%s %s' % (Dict('prenomIntPrinc')(self).lower(), Dict('nomIntPrinc')(self).lower())).title()


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
            doc.format = u'PDF'
            doc.label = 'Facture %s' % document['numFactureLabel']
            doc.type = u'bill'
            doc.price = CleanDecimal().filter(document['montantTTC'])
            doc.currency = u'€'
            doc._account_billing = document['compteFacturation']
            doc._bill_number = document['numFacture']

            documents.append(doc)

        return documents
