# -*- coding: utf-8 -*-

# Copyright(C) 2009-2019  Romain Bignon
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

# yapf-compatible

from __future__ import unicode_literals

import re

from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Format, Date, Env, Field
from weboob.browser.pages import JsonPage, LoggedPage
from weboob.capabilities.bill import Document, Bill, DocumentTypes
from weboob.tools.compat import urlencode

patterns = {
    r'Relevé': DocumentTypes.STATEMENT,
    r'Livret(s) A': DocumentTypes.STATEMENT,
    r'développement durable': DocumentTypes.STATEMENT,
    r'Synthèse': DocumentTypes.STATEMENT,
    r'Echelles/Décomptes': DocumentTypes.STATEMENT,
    r'épargne logement': DocumentTypes.STATEMENT,
    r'Livret(s) jeune': DocumentTypes.STATEMENT,
    r'Compte(s) sur Livret': DocumentTypes.STATEMENT,
    r'Récapitulatifs annuels': DocumentTypes.REPORT,
    r"Avis d'exécution": DocumentTypes.REPORT,
    r'Factures': DocumentTypes.BILL,
}


def get_document_type(family):
    for patt, type in patterns.items():
        if re.search(re.escape(patt), family):
            return type
    return DocumentTypes.OTHER


class TitulairePage(LoggedPage, JsonPage):
    def get_titulaires(self):
        return set([t['idKpiTitulaire'] for t in self.doc['data']['listeTitulairesDemat']['listeTitulaires']])


class ItemDocument(ItemElement):
    def build_object(self):
        if Field('type')(self) == DocumentTypes.BILL:
            return Bill()
        return Document()

    def condition(self):
        # There is two type of json, the one with the ibancrypte in it
        # and the one with the idcontrat in it, here we check if
        # the document belong to the subscription.
        if 'ibanCrypte' in self.el:
            return Env('sub_id')(self) in Dict('ibanCrypte')(self)
        else:
            return Env('sub_number')(self) in Dict('idContrat')(self)

    obj_date = Date(Dict('dateDoc'), dayfirst=True)
    obj_format = 'pdf'
    obj_id = Format('%s_%s', Env('sub_id'), Dict('idDoc'))

    def obj_label(self):
        if 'ibanCrypte' in self.el:
            return '%s %s N° %s' % (
                Dict('dateDoc')(self), Dict('libelleSousFamille')(self), Dict('numeroCompteAnonymise')(self)
            )
        else:
            return '%s %s N° %s' % (Dict('dateDoc')(self), Dict('libelleSousFamille')(self), Dict('idContrat')(self))

    def obj_url(self):
        keys_to_copy = {
            'idDocument': 'idDoc',
            'dateDocument': 'dateDoc',
            'idLocalisation': 'idLocalisation',
            'viDocDocument': 'viDocDocument',
        }
        # Here we parse the json with ibancrypte in it, for most cases
        if 'ibanCrypte' in self.el:
            url = 'demat-wspl/rest/consultationDocumentDemat?'
            keys_to_copy.update({
                'typeCpt': 'typeCompte',
                'familleDoc': 'famDoc',
                'ibanCrypte': 'ibanCrypte',
                'typeDoc': 'typeDoc',
                'consulted': 'consulted',
            })
            request_params = {'typeFamille': 'R001', 'ikpiPersonne': ''}
        # Here we parse the json with idcontrat in it. For the cases present
        # on privee.mabanque where sometimes the doc url is different
        else:
            url = 'demat-wspl/rest/consultationDocumentSpecialBpfDemat?'
            keys_to_copy.update({
                'heureDocument': 'heureDoc',
                'numClient': 'numClient',
                'typeReport': 'typeReport',
            })
            request_params = {'ibanCrypte': ''}

        for k, v in keys_to_copy.items():
            request_params[k] = Dict(v)(self)

        return Env('baseurl')(self) + url + urlencode(request_params)

    def obj_type(self):
        return get_document_type(Dict('libelleSousFamille')(self))


class DocumentsPage(LoggedPage, JsonPage):
    @method
    class iter_documents(DictElement):
        # * refer to the account, it can be 'Comptes chèques', 'Comptes d'épargne', etc...
        item_xpath = 'data/listerDocumentDemat/mapReleves/*/listeDocument'
        ignore_duplicate = True

        class item(ItemDocument):
            pass

    @method
    class iter_documents_pro(DictElement):
        # * refer to the account, it can be 'Comptes chèques', 'Comptes d'épargne', etc...
        item_xpath = 'data/listerDocumentDemat/mapRelevesPro/*/listeDocument'
        ignore_duplicate = True

        class item(ItemDocument):
            pass


class DocumentsResearchPage(LoggedPage, JsonPage):
    @method
    class iter_documents(DictElement):
        # * refer to the account, it can be 'Comptes chèques', 'Comptes d'épargne', etc...
        item_xpath = 'data/rechercheCriteresDemat/*/*/listeDocument'
        ignore_duplicate = True

        class item(ItemDocument):
            pass
