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

from weboob.browser.pages import HTMLPage, JsonPage, RawPage, LoggedPage
from weboob.browser.filters.standard import CleanDecimal, CleanText
from weboob.browser.filters.html import CleanHTML
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Subscription, Bill
from weboob.exceptions import ActionNeeded


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form(id='form-authenticate-entreprise')

        form['IDToken1'] = login
        form['IDToken2'] = password

        form.submit(allow_redirects=False)

class AuthPage(RawPage):
    pass

class SubscriptionsPage(LoggedPage, JsonPage):
    def build_doc(self, text):
        if self.content == 'REDIRECT_CGU':
            raise ActionNeeded(u"Vous devez accepter les conditions générales d'utilisation sur le site de votre banque.")
        return super(SubscriptionsPage, self).build_doc(text)

    def get_subscriptions(self):
        subscriptions = []

        for contract in self.doc['listeContrat']:
            sub = Subscription()

            sub.id = contract['refDevis']
            sub.label = CleanText().filter(CleanHTML().filter(contract['nomOffreModele']))
            sub.subscriber = ('%s %s' % (contract['prenomIntPrinc'].lower(), contract['nomIntPrinc'].lower())).title()

            subscriptions.append(sub)

        return subscriptions

class BillsPage(LoggedPage, JsonPage):
    def get_bill_name(self):
        return Dict('nomFichier')(self.doc)

class DocumentsPage(LoggedPage, JsonPage):
    def get_documents(self, subid):
        documents = []

        for document in self.doc:
            doc = Bill()

            doc.id = u'%s_%s' % (subid, document['numFactureLabel'])
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
