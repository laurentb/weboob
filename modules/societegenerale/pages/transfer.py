# -*- coding: utf-8 -*-

# Copyright(C) 2016 Baptiste Delpey
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

from datetime import datetime
import re

from weboob.browser.pages import LoggedPage, JsonPage, FormNotFound
from weboob.browser.elements import method, ItemElement, DictElement
from weboob.capabilities.bank import (
    Recipient, Transfer, TransferBankError, AddRecipientBankError, AddRecipientStep,
)
from weboob.capabilities.base import NotAvailable
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Env, Date, Field, Format,
)
from weboob.browser.filters.html import Link
from weboob.browser.filters.json import Dict
from weboob.tools.value import Value, ValueBool
from weboob.tools.json import json
from weboob.exceptions import BrowserUnavailable

from .base import BasePage
from .login import LoginPage


class TransferJson(LoggedPage, JsonPage):
    def on_load(self):
        if Dict('commun/statut')(self.doc).upper() == 'NOK':
            if self.doc['commun'].get('action'):
                raise TransferBankError(message=Dict('commun/action')(self.doc))
            elif self.doc['commun'].get('raison') == 'err_tech':
                # on SG website, there is unavalaible message 'Le service est momentanément indisponible.'
                raise BrowserUnavailable()
            else:
                assert False, 'Something went wrong, transfer is not created: %s' % self.doc['commun'].get('raison')

    def get_acc_transfer_id(self, account):
        for acc in self.doc['donnees']['listeEmetteursBeneficiaires']['listeDetailEmetteurs']:
            if account.id == Format('%s%s', Dict('codeGuichet'), Dict('numeroCompte'))(acc):
                # return json_id to do transfer
                return acc['id']
        return False

    def is_able_to_transfer(self, account):
        return self.get_acc_transfer_id(account)

    @method
    class iter_recipients(DictElement):
        item_xpath = 'donnees/listeEmetteursBeneficiaires/listeDetailBeneficiaires'
        # Some recipients can be internal and external
        ignore_duplicate = True

        class Item(ItemElement):
            klass = Recipient

            # Assume all recipients currency is euros.
            obj_currency = u'EUR'
            obj_iban = Dict('iban')
            obj_label = Dict('libelleToDisplay')
            obj_enabled_at = datetime.now().replace(microsecond=0)

            # needed for transfer
            obj__json_id = Dict('id')

            def obj_category(self):
                if Dict('groupeRoleToDisplay')(self) == 'Comptes personnels':
                    return u'Interne'
                return u'Externe'

            # for retrocompatibility
            def obj_id(self):
                if Field('category')(self) == 'Interne':
                    return Format('%s%s', Dict('codeGuichet'), Dict('numeroCompte'))(self)
                return Dict('iban')(self)

            def condition(self):
                return Field('id')(self) != Env('account_id')(self)

    def init_transfer(self, account, recipient, transfer):
        assert self.is_able_to_transfer(account), 'Account %s seems to be not able to do transfer' % account.id

        # SCT : standard transfer
        data = [
            ('an200_montant', transfer.amount),
            ('an200_typeVirement', 'SCT'),
            ('b64e200_idCompteBeneficiaire', recipient._json_id),
            ('b64e200_idCompteEmetteur', self.get_acc_transfer_id(account)),
            ('cl200_devise', u'EUR'),
            ('cl200_nomBeneficiaire', recipient.label),
            ('cl500_motif', transfer.label),
            ('dt10_dateExecution', transfer.exec_date.strftime('%d/%m/%Y')),
        ]

        headers = {'Referer': self.browser.absurl('/com/icd-web/vupri/virement.html')}
        self.browser.location(self.browser.absurl('/icd/vupri/data/vupri-check.json'), headers=headers, data=data)

    def handle_response(self, recipient):
        json_response = self.doc['donnees']

        transfer = Transfer()
        transfer.id = json_response['idVirement']
        transfer.label = json_response['motif']
        transfer.amount = CleanDecimal.French((CleanText(Dict('montantToDisplay'))))(json_response)
        transfer.currency = json_response['devise']
        transfer.exec_date = Date(Dict('dateExecution'), dayfirst=True)(json_response)

        transfer.account_id = Format('%s%s', Dict('codeGuichet'), Dict('numeroCompte'))(json_response['compteEmetteur'])
        transfer.account_iban = json_response['compteEmetteur']['iban']
        transfer.account_label = json_response['compteEmetteur']['libelleToDisplay']

        assert recipient._json_id == json_response['compteBeneficiaire']['id']
        transfer.recipient_id = recipient.id
        transfer.recipient_iban = json_response['compteBeneficiaire']['iban']
        transfer.recipient_label = json_response['compteBeneficiaire']['libelleToDisplay']

        return transfer

    def is_transfer_validated(self):
        return Dict('commun/statut')(self.doc).upper() == 'OK'


class SignTransferPage(LoggedPage, LoginPage):
    def get_token(self):
        result_page = json.loads(self.content)
        assert result_page['commun']['statut'].upper() == 'OK', 'Something went wrong: %s' % result_page['commun']['raison']
        return result_page['donnees']['jeton']

    def get_confirm_transfer_data(self, password):
        token = self.get_token()
        authentication_data = self.get_authentication_data()

        pwd = authentication_data['img'].get_codes(password[:6])
        t = pwd.split(',')
        newpwd = ','.join(t[self.strange_map[j]] for j in range(6))

        return {
            'codsec': newpwd,
            'cryptocvcs': authentication_data['infos']['crypto'].encode('iso-8859-1'),
            'vkm_op': 'sign',
            'cl1000_jtn': token,
        }


class RecipientJson(LoggedPage, JsonPage):
    pass


class AddRecipientPage(LoggedPage, BasePage):
    def on_load(self):
        error_msg = CleanText(u'//span[@class="error_msg"]')(self.doc)
        if error_msg:
            raise AddRecipientBankError(message=error_msg)

    def is_here(self):
        return bool(CleanText(u'//h3[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) or \
                bool(CleanText(u'//h1[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) or \
                bool(CleanText(u'//h3[contains(text(), "Veuillez vérifier les informations du compte à ajouter")]')(self.doc)) or \
                bool(Link('//a[contains(@href, "per_cptBen_ajouter")]', default=NotAvailable)(self.doc))

    def post_iban(self, recipient):
        form = self.get_form(name='persoAjoutCompteBeneficiaire')
        form['codeIBAN'] = recipient.iban
        form['n10_form_etr'] = '1'
        form.submit()

    def post_label(self, recipient):
        form = self.get_form(name='persoAjoutCompteBeneficiaire')
        form['nomBeneficiaire'] = recipient.label
        form['codeIBAN'] = form['codeIBAN'].replace(' ', '')
        form['n10_form_etr'] = '1'
        form.submit()

    def get_action_level(self):
        for script in self.doc.xpath('//script'):
            if 'actionLevel' in CleanText('.')(script):
                return re.search("'actionLevel': (\d{3}),", script.text).group(1)

    def double_auth(self, recipient):
        try:
            form = self.get_form(id='formCache')
        except FormNotFound:
            assert False, 'Double auth form not found'

        self.browser.context = form['context']
        self.browser.dup = form['dup']
        self.browser.logged = 1

        getsigninfo_data = {}
        getsigninfo_data['b64_jeton_transaction'] = form['context']
        getsigninfo_data['action_level'] = self.get_action_level()
        r = self.browser.open('https://particuliers.secure.societegenerale.fr/sec/getsigninfo.json', data=getsigninfo_data)
        assert r.page.doc['commun']['statut'] == 'ok'

        recipient = self.get_recipient_object(recipient, get_info=True)
        self.browser.page = None
        if r.page.doc['donnees']['sign_proc'] == 'csa':
            send_data = {}
            send_data['csa_op'] = 'sign'
            send_data['context'] = form['context']
            r = self.browser.open('https://particuliers.secure.societegenerale.fr/sec/csa/send.json', data=send_data)
            assert r.page.doc['commun']['statut'] == 'ok'
            raise AddRecipientStep(recipient, Value('code', label=u'Cette opération doit être validée par un Code Sécurité.'))
        elif r.page.doc['donnees']['sign_proc'] == 'OOB':
            oob_data = {}
            oob_data['b64_jeton_transaction'] = form['context']
            r = self.browser.open('https://particuliers.secure.societegenerale.fr/sec/oob_sendoob.json', data=oob_data)
            assert r.page.doc['commun']['statut'] == 'ok'
            self.browser.id_transaction = r.page.doc['donnees']['id-transaction']
            raise AddRecipientStep(recipient, ValueBool('pass', label=u'Valider cette opération sur votre applicaton société générale'))
        else:
            assert False, 'Sign process unknown: %s' % r.page.doc['donnees']['sign_proc']

    def get_recipient_object(self, recipient, get_info=False):
        r = Recipient()
        if get_info:
            recap_iban = CleanText('//div[div[contains(text(), "IBAN")]]/div[has-class("recapTextField")]', replace=[(' ', '')])(self.doc)
            assert recap_iban == recipient.iban
            recipient.bank_name = CleanText('//div[div[contains(text(), "Banque du")]]/div[has-class("recapTextField")]', default=NotAvailable)(self.doc)
        r.iban = recipient.iban
        r.id = recipient.iban
        r.label = recipient.label
        r.category = recipient.category
        # On societe generale recipients are immediatly available.
        r.enabled_at = datetime.now().replace(microsecond=0)
        r.currency = u'EUR'
        r.bank_name = recipient.bank_name
        return r
