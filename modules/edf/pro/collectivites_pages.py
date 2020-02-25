# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight

from __future__ import unicode_literals

from weboob.browser.filters.html import Attr
from weboob.browser.pages import JsonPage, HTMLPage, LoggedPage, RawPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.standard import CleanDecimal, CleanText, Regexp, Env, Format, Date, Field
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Subscription, Bill
from weboob.tools.json import json


class ClientSpace(HTMLPage):
    def handle_redirect(self):
        return Regexp(CleanText('//script[contains(text(), "handleRedirect")]'), r"handleRedirect\('(.*?)'\)")(self.doc)

    def get_aura_config(self):
        aura_config = Regexp(CleanText('//script[contains(text(), "token")]'), r'auraConfig = (\{.*?\});')(self.doc)
        return json.loads(aura_config)

    def get_token(self):
        aura_config = self.get_aura_config()
        return aura_config['token']


class CnicePage(HTMLPage):
    def get_frontdoor_url(self):
        return Regexp(Attr('//head/meta[@http-equiv="Refresh"]', 'content'), r'URL=(.*)')(self.doc)


class AuraPage(LoggedPage, JsonPage):
    # useful tip, when request is malformed this page contains a malformed json (yes i know)
    # and it crash on build_doc, hope that can help you to debug
    def build_doc(self, text):
        doc = super(AuraPage, self).build_doc(text)

        if doc['actions'][0]['id'] == '685;a':  # this is the code when we get documents
            # they are also encoded in json
            value = doc['actions'][1]['returnValue']
            if value is None:
                return {'factures': []}
            return json.loads(value)

        return doc

    def get_subscriber(self):
        return Format(
            "%s %s",
            Dict('actions/0/returnValue/FirstName'),
            Dict('actions/0/returnValue/LastName')
        )(self.doc)

    @method
    class iter_subscriptions(DictElement):
        item_xpath = 'actions/0/returnValue/energyMeters'

        class item(ItemElement):
            klass = Subscription

            obj_id = CleanText(Dict('contractReference'))
            obj_label = CleanText(Dict('siteName'))
            obj_subscriber = Env('subscriber')
            obj__moe_idpe = CleanText(Dict('ids/epMoeId'))

    @method
    class iter_documents(DictElement):
        item_xpath = 'factures'

        class item(ItemElement):
            klass = Bill

            obj__id = CleanText(Dict('identiteFacture/identifiant'))
            obj_id = Format('%s_%s', Env('subid'), Field('_id'))
            obj_price = CleanDecimal.SI(Dict('montantFacture/montantTTC'))
            obj_vat = CleanDecimal.SI(Dict('taxesFacture/montantTVA'))
            obj_date = Date(Dict('caracteristiquesFacture/dateLegaleFacture'))
            obj_duedate = Date(Dict('caracteristiquesFacture/dateEcheanceFacture'))
            obj_format = 'pdf'

            def obj_label(self):
                return 'Facture du %s' % Field('date')(self).strftime('%d/%m/%Y')

            def obj__message(self):
                # message is needed to download file
                message = {
                    'actions':[
                        {
                            'id': '864;a',
                            'descriptor': 'apex://CNICE_VFC160_ListeFactures/ACTION$getFacturePdfLink',
                            'callingDescriptor': 'markup://c:CNICE_LC232_ListeFactures2',
                            'params': {
                                'factureId': Field('_id')(self)
                            }
                        }
                    ]
                }
                return message

    def get_id_for_download(self):
        return self.doc['actions'][0]['returnValue']


class PdfPage(LoggedPage, RawPage):
    pass
