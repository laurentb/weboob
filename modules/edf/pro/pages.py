# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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

from datetime import date

from weboob.browser.pages import JsonPage, HTMLPage, RawPage, LoggedPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.standard import CleanDecimal, CleanText
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import DocumentTypes, Subscription, Bill
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


class ErrorPage(HTMLPage):
    def get_message(self):
        return CleanText('//div[@id="div_text"]/h1 | //div[@id="div_text"]/p')(self.doc)


class HomePage(LoggedPage, HTMLPage):
    pass


class JsonCguPage(JsonPage):
    def build_doc(self, text):
        if text == 'REDIRECT_CGU':  # JSON can always be decoded in UTF-8 so testing text is fine
            raise ActionNeeded("Vous devez accepter les conditions générales d'utilisation.")
        return super(JsonCguPage, self).build_doc(text)


class LireSitePage(LoggedPage, JsonCguPage):
    # id site is not about website but geographical site
    def get_id_site_list(self):
        return [site['idSite'] for site in self.doc['site']]


class SubscriptionsPage(LoggedPage, JsonPage):
    @method
    class get_subscriptions(DictElement):
        item_xpath = 'profilFacturation'

        class item(ItemElement):
            klass = Subscription

            obj_id = CleanText(Dict('idPFLabel'))
            # this label will be override if we find a good contract with _get_similarity_among_id,
            # but it's not always the case, so take it here for now
            obj_label = CleanText(Dict('idPFLabel'))
            obj__account_id = CleanText(Dict('idCompteDeFacturation'))


class SubscriptionsAccountPage(LoggedPage, JsonCguPage):
    @classmethod
    def _get_similarity_among_id(cls, sub_id, account_id):
        """
        sometimes there are several sub_id and several account_id
        sub_id looks like 1-UD8Z6FPO
           and account_id 1-UD8Z6F7S
        when a sub_id and an account_id are related their id are not completely identical but close
        this function count numbers of char that are identical from the beginning until one char is different
        more the count value is high more there is a chance that both id are from related objects (subscription and account)
        """
        _, sub_id_value = sub_id.split('-', 1)
        _, account_id_value = account_id.split('-', 1)

        count = 0
        for idx, c in enumerate(sub_id_value):
            if idx >= len(account_id_value):
                return count
            if account_id_value[idx] != c:
                return count
            count += 1

        return count

    def update_subscription(self, subscription):
        good_con = None
        best_matching = 0
        for con in self.doc['listeContrat']:
            matching = self._get_similarity_among_id(subscription.id, con['refDevisLabel'])
            if matching > best_matching:
                best_matching = matching
                good_con = con

        if good_con:
            subscription.label = good_con['nomOffreModele']
            subscription.subscriber = (good_con['prenomIntPrinc'] + ' ' + good_con['nomIntPrinc']).title()


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
            doc.type = DocumentTypes.BILL
            doc.price = CleanDecimal().filter(document['montantTTC'])
            doc.currency = 'EUR'
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
