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

from __future__ import unicode_literals

import re

from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Format, Date, Env
from weboob.browser.pages import JsonPage, LoggedPage
from weboob.capabilities.bill import Document, DocumentTypes

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


class DocumentsPage(LoggedPage, JsonPage):
    @method
    class iter_documents(DictElement):
        item_xpath = 'data/rechercheCriteresDemat/*/*/listeDocument'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Document

            def condition(self):
                if 'ibanCrypte' in self.el:
                    return Env('sub_id')(self) in Dict('ibanCrypte')(self)
                else:
                    return Env('sub_number')(self) in Dict('idContrat')(self)

            obj_date = Date(Dict('dateDoc'), dayfirst=True)
            obj_format = 'pdf'
            obj_id = Format('%s_%s', Env('sub_id'), Dict('idDoc'))

            def obj_label(self):
                if 'ibanCrypte' in self.el:
                    return '%s %s N° %s' % (Dict('dateDoc')(self), Dict('libelleSousFamille')(self), Dict('numeroCompteAnonymise')(self))
                else:
                    return '%s %s N° %s' % (Dict('dateDoc')(self), Dict('libelleSousFamille')(self), Dict('idContrat')(self))

            def obj_url(self):
                # For most of the cases on the json
                if 'ibanCrypte' in self.el:
                    ibanCrypte = Dict('ibanCrypte')(self)
                    idDoc = Dict('idDoc')(self)
                    typeCompte = Dict('typeCompte')(self)
                    typeDoc = Dict('typeDoc')(self)
                    typeFamille = 'R001' # add typeFamille correctly for professional and private pages
                    idLocalisation = Dict('idLocalisation')(self)
                    viDocDocument = Dict('viDocDocument')(self)
                    famDoc = Dict('famDoc')(self)
                    consulted = Dict('consulted')(self)
                    dateDoc = Dict('dateDoc')(self)

                    return '%sdemat-wspl/rest/consultationDocumentDemat?'\
                    'ibanCrypte=%s&idDocument=%s&typeCpt=%s&typeDoc=%s&typeFamille=%s&idLocalisation=%s'\
                    '&viDocDocument=%s&familleDoc=%s&consulted=%s&dateDocument=%s&ikpiPersonne=' % (Env('baseurl')(self), ibanCrypte, idDoc, typeCompte,
                    typeDoc, typeFamille, idLocalisation, viDocDocument, famDoc, consulted, dateDoc)
                # For the cases present on privee.mabanque where sometimes the doc url is the different
                else:
                    idDoc = Dict('idDoc')(self)
                    numClient = Dict('numClient')(self)
                    heureDoc = Dict('heureDoc')(self)
                    idLocalisation = Dict('idLocalisation')(self)
                    viDocDocument = Dict('viDocDocument')(self)
                    typeReport = Dict('typeReport')(self)
                    dateDoc = Dict('dateDoc')(self)

                    return '%sdemat-wspl/rest/consultationDocumentSpecialBpfDemat?'\
                    'ibanCrypte=&idDocument=%s&numClient=%s&heureDocument=%s'\
                    '&idLocalisation=%s&typeReport=%s&viDocDocument=%s&dateDocument=%s' % (Env('baseurl')(self), idDoc, numClient,
                    heureDoc, idLocalisation, typeReport, viDocDocument, dateDoc)

            def obj_type(self):
                return get_document_type(Dict('libelleSousFamille')(self))
