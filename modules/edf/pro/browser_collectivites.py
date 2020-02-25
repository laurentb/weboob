# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight


from __future__ import unicode_literals

from weboob.browser import LoginBrowser, URL, need_login
from weboob.tools.json import json

from .collectivites_pages import (
    ClientSpace, CnicePage, AuraPage, PdfPage,
)


class EdfproCollectivitesBrowser(LoginBrowser):
    BASEURL = 'https://entreprises-collectivites.edf.fr'

    client_space = URL(r'/espaceclient/s/$', ClientSpace)
    cnice = URL(r'/espaceclient/services/authcallback/CNICE', CnicePage)
    aura = URL(r'/espaceclient/s/sfsites/aura', AuraPage)
    download_page = URL(r'/espaceclient/sfc/servlet.shepherd/version/download/(?P<id_download>.*)', PdfPage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(EdfproCollectivitesBrowser, self).__init__(*args, **kwargs)
        self.token = None
        self.context = None

    def do_login(self):
        # here we are already logged, we have been logged in EdfproBrowser, but we have detected a new BASEURL
        # and new pages
        # manually handle response because we were unable to handle it the first time due to another BASEURL
        page = self.client_space.handle(self.response)
        url = page.handle_redirect()
        self.location(url)
        frontdoor_url = self.page.get_frontdoor_url()
        self.location(frontdoor_url)
        self.client_space.go()
        self.token = self.page.get_token()
        aura_config = self.page.get_aura_config()
        self.context = aura_config['context']

    def go_aura(self, message, page_uri):
        context = {
            'mode': self.context['mode'],
            'fwuid': self.context['fwuid'],  # this value changes sometimes, (not at every synchronization)
            'app': self.context['app'],
            'loaded': self.context['loaded'],
            'dn': [],
            'globals': {},
            'uad': False
        }
        data = {
            'aura.pageURI': page_uri,
            'aura.token': self.token,
            'aura.context': json.dumps(context),
            'message': json.dumps(message),  # message determines kind of response
        }
        self.aura.go(data=data)

    def get_subscriber(self):
        message = {
            "actions":[
                {
                    "id": "894;a",
                    "descriptor": "apex://CNICE_VFC172_DisplayUserProfil/ACTION$getContactInfo",
                    "callingDescriptor": "markup://c:CNICE_LC265_DisplayUserProfil",
                    "params": {}
                }
            ]
        }
        self.go_aura(message, '/espaceclient/s/historique-factures')
        return self.page.get_subscriber()

    @need_login
    def get_subscription_list(self):
        subscriber = self.get_subscriber()
        message = {
            "actions":[
                {
                    "id": "557;a",
                    "descriptor": "apex://CNICE_VFC151_CompteurListe/ACTION$getCarouselInfos",
                    "callingDescriptor": "markup://c:CNICE_LC218_CompteurListe",
                    "params": {}
                }
            ]
        }

        self.go_aura(message, '/espaceclient/s/')
        return self.page.iter_subscriptions(subscriber=subscriber)

    @need_login
    def iter_documents(self, subscription):
        message = {
            "actions":[
                {
                    "id": "685;a",
                    "descriptor": "apex://CNICE_VFC158_HistoFactu/ACTION$initializeReglementSolde",
                    "callingDescriptor": "markup://c:CNICE_LC230_HistoFactu",
                    "params": {}
                },
                {
                    "id": "751;a",
                    "descriptor": "apex://CNICE_VFC160_ListeFactures/ACTION$getFacturesbyId",
                    "callingDescriptor": "markup://c:CNICE_LC232_ListeFactures2",
                    "params":
                        {
                            "moeid": subscription._moe_idpe,
                            "originBy": "byMoeIdPE"
                        }
                }
            ]
        }
        self.go_aura(message, '/espaceclient/s/')
        return sorted(self.page.iter_documents(subid=subscription.id), key=lambda doc: doc.date, reverse=True)

    @need_login
    def download_document(self, document):
        self.go_aura(document._message, '/espaceclient/s/historique-factures')
        id = self.page.get_id_for_download()
        self.download_page.go(id_download=id)
        return self.page.content

    @need_login
    def get_profile(self):
        raise NotImplementedError()
