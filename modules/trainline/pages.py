# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight

from __future__ import unicode_literals

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.standard import Date, CleanDecimal, Format, Env, Currency, Eval
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Subscription, Bill


class SigninPage(JsonPage):
    @property
    def logged(self):
        return bool(self.get_token())

    def get_token(self):
        return self.doc.get('meta', {}).get('token', {})


class UserPage(LoggedPage, JsonPage):
    def get_subscription(self):
        user = self.doc['user']
        sub = Subscription()
        sub.subscriber = '%s %s' % (user['first_name'], user['last_name'])
        sub.id = user['id']
        sub.label = user['email']

        return sub


class DocumentsPage(LoggedPage, JsonPage):
    def build_doc(self, text):
        """
        this json contains several important lists
        - pnrs
        - proofs
        - folders
        - trips

        each bill has data inside theses lists
        this function rebuild doc to put data within same list we call 'bills'
        """
        doc = super(DocumentsPage, self).build_doc(text)

        pnrs_dict = {pnr['id']: pnr for pnr in doc['pnrs']}
        proofs_dict = {proof['pnr_id']: proof for proof in doc['proofs']}
        folders_dict = {folder['pnr_id']: folder for folder in doc['folders']}
        trips_dict = {trip['folder_id']: trip for trip in doc['trips']}

        bills = []
        for key, pnr in pnrs_dict.items():
            proof = proofs_dict[key]
            folder = folders_dict[key]
            trip = trips_dict[folder['id']]

            bills.append({
                'pnr': pnr,
                'proof': proof,
                'folder': folder,
                'trip': trip,
            })

        return {'bills': bills}

    @method
    class iter_documents(DictElement):
        item_xpath = 'bills'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), Dict('pnr/id'))
            obj_url = Dict('proof/url')
            obj_date = Date(Dict('proof/created_at'))
            obj_format = 'pdf'
            obj_label = Format('Trajet du %s', Date(Dict('trip/departure_date')))
            obj_price = Eval(lambda x: x / 100, CleanDecimal(Dict('pnr/cents')))
            obj_currency = Currency(Dict('pnr/currency'))
