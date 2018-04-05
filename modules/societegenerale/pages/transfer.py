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

from ast import literal_eval
from datetime import datetime, timedelta
import re
from collections import OrderedDict
from io import BytesIO
from logging import error

from weboob.browser.pages import LoggedPage, JsonPage, FormNotFound
from weboob.browser.elements import method, ListElement, ItemElement, SkipItem
from weboob.capabilities.bank import (
    Recipient, TransferError, TransferBankError, TransferInvalidCurrency, Transfer,
    AddRecipientError, AddRecipientStep,
)
from weboob.capabilities.base import find_object, NotAvailable, empty
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal, \
                                            Env, Date
from weboob.browser.filters.html import Attr, Link, XPathNotFound
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.value import Value, ValueBool
from weboob.tools.json import json

from ..captcha import Captcha, TileError
from .base import BasePage
from .login import PasswordPage


class MyRecipient(ItemElement):
    klass = Recipient

    # Assume all recipients currency is euros.
    obj_currency = u'EUR'

    def obj_enabled_at(self):
        return datetime.now().replace(microsecond=0)


class RecipientsPage(LoggedPage, BasePage):
    @method
    class iter_recipients(ListElement):
        item_xpath = '//div[@class="items-groups"]/a'

        class Item(MyRecipient):
            obj_id = obj_iban = CleanText('./div[1]/div[1]/span[1]')
            obj_bank_name = CleanText('./div[1]/div[2]/span[1]')
            obj_category = u'Externe'

            def obj_label(self):
                first_label = CleanText('./div[1]/div[3]/span[1]')(self)
                second_label = CleanText('./div[1]/div[3]/span[2]')(self)
                return first_label if first_label == second_label else ('%s %s' % (first_label, second_label)).strip()

            validate = lambda self, obj: empty(self.obj_iban(self)) or is_iban_valid(self.obj_iban(self))


class TransferPage(LoggedPage, BasePage, PasswordPage):
    def is_here(self):
        return not bool(CleanText(u'//h3[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) and\
            not bool(CleanText(u'//h1[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc))

    def get_add_recipient_link(self):
        try:
            link = Regexp(Link('//a[img[@src="/img/personnalisation/btn_ajouter_beneficiaire.jpg"]]'), 'javascript:window.location="([^"]+)"')(self.doc)
        except XPathNotFound:
            link = Regexp(Link(u'//a[contains(text(), "Ajouter un compte b")]'), 'javascript:window.location="([^"]+)"')(self.doc)
        else:
            # XXX check in logs if this message is visible. If not, we can remove the first xpath.
            self.logger.debug('Old link found to add a recipient.')

        return link

    def on_load(self):
        excluded_errors = [
            u"Vous n'avez pas la possibilité d'accéder à cette fonction. Veuillez prendre contact avec votre Conseiller.",
            u"Aucun compte de la liste n'est autorisé à la passation d'ordres de virement.",
        ]
        error_msg = CleanText('//span[@class="error_msg"]')(self.doc)
        if error_msg and error_msg not in excluded_errors:
            raise TransferBankError(message=error_msg)

    def is_able_to_transfer(self, account):
        numbers = [''.join(Regexp(CleanText('.'), '(\d+)', nth='*', default=None)(opt)) for opt in self.doc.xpath('.//select[@id="SelectEmet"]//option')]
        return bool(CleanText('.//select[@id="SelectEmet"]//option[contains(text(), "%s")]' % account.label)(self.doc)) or bool(account.id in numbers)

    @method
    class iter_recipients(ListElement):
        item_xpath = '//select[@id="SelectDest"]/optgroup[@label="Vos comptes"]/option | //select[@id="SelectDest"]/optgroup[@label="Procurations"]/option'

        class Item(MyRecipient):
            def validate(self, obj):
                return self.obj.id != self.env['account_id'] and self.obj.id not in self.parent.objects

            obj_id = Env('id')
            obj_label = Env('label')
            obj_bank_name = u'Société Générale'
            obj_category = u'Interne'
            obj_iban = Env('iban')

            def parse(self, el):
                _id = Regexp(CleanText('.', replace=[(' ', '')]), '(\d+)', default=NotAvailable)(self)
                if _id and len(_id) >= min(len(acc.id) for acc in self.page.browser.get_accounts_list()):
                    account = find_object(self.page.browser.get_accounts_list(), id=_id)
                    if not account:
                        accounts = [acc for acc in self.page.browser.get_accounts_list() if acc.id in _id or _id in acc.id]
                        assert len(accounts) == 1
                        account = accounts[0]
                    self.env['id'] = _id
                else:
                    rcpt_label = CleanText('.')(self)
                    account = None

                    # the recipients selector contains "<type> - <label>"
                    # the js contains "<part_of_id>", ... "<label>", ... "<type>"
                    # the accounts list contains "<label>" and the id
                    # put all this data together
                    for params in self.page.iter_params_by_type('Emetteurs'):
                        if not params['ordre']:
                            continue  # ignore the first js entry, it's empty
                        param_label = '%s - %s' % (params['liprem'], params['libeem'])
                        if param_label != rcpt_label:
                            continue
                        param_id = params['cdbqem'] + params['cdguem'] + params['nucpem']
                        for ac in self.page.browser.get_accounts_list():
                            if ac.id in param_id:
                                account = ac
                                break

                    if account is None:
                        self.page.logger.warning('the internal %r recipient could not be found in js or accounts list', rcpt_label)
                        raise SkipItem()

                    self.env['id']= account.id
                self.env['label'] = account.label
                self.env['iban'] = account.iban

    # param names can be found in: https://particuliers.secure.societegenerale.fr/js/v28/virement/vipon_saisie_opAVenir.js
    EMITTER_PARAMS = ['solde', 'Alterna', 'SRD', 'cdbqem', 'cdguem', 'nucpem', 'clriem',
                      'libeem', 'grroem', 'cdprem', 'liprem', 'codeBICEmet', 'codeIBANEmet', 'formatCpteEmet']
    RECIPIENT_PARAMS = ['solde', 'Alterna', 'PEP', 'SRD', 'toprib', 'idprde', 'cdbqde',
                        'cdgude', 'nucpde', 'clride', 'libede', 'grrode', 'cdprde',
                        'liprde', 'tycpde', 'libqde', 'formatCompteBenef', 'nomBenef',
                        'paysBenef', 'adresseBenef', 'villeBenef', 'codePaysBenef',
                        'codeBICBenef', 'codeIBANBenef']

    def iter_params_by_type(self, _type):
        for script in [sc for sc in self.doc.xpath('//script') if sc.text]:
            accounts = re.findall('TableauComptes%s.*?\);' % _type, script.text)
            if accounts:
                break
        for n, account in enumerate(accounts):
            params = re.search(r'\(indic\d?,(.*)\)', account).group(1)
            params = literal_eval('[%s]' % params)
            assert len(params) > 12

            if _type == 'Emetteurs':
                assert len(params) == len(self.EMITTER_PARAMS)
                ret = OrderedDict(zip(self.EMITTER_PARAMS, params))
            elif _type == 'Destinataires':
                assert len(params) == len(self.RECIPIENT_PARAMS)
                ret = OrderedDict(zip(self.RECIPIENT_PARAMS, params))
            else:
                assert False, 'unhandled param type'

            ret['ordre'] = n
            yield ret

    def get_params(self, _id, _type):
        for params in self.iter_params_by_type(_type):
            if _type == 'Emetteurs' and (params['cdguem'] + params['nucpem']) == _id:
                return params
            elif _type == 'Destinataires' and ((params['cdgude'] + params['nucpde']) == _id or params['codeIBANBenef'] == _id):
                return params

        raise TransferError(u'Paramètres pour le compte %s numéro %s introuvable.' % (_type, _id))

    def get_account_value(self, _id):
        for option in self.doc.xpath('//select[@id="SelectEmet"]//option'):
            if _id in CleanText('.', replace=[(' ', '')])(option):
                attr = Attr('.', 'value')(option)
                return attr

    def get_account_value_by_label(self, label):
        l = [Attr('.', 'value')(option) for option in self.doc.xpath('//select[@id="SelectEmet"]//option') if label in CleanText('.')(option)]
        if len(l) == 1:
            return l[0]

    def init_transfer(self, account, recipient, transfer):
        if not (account.currency == recipient.currency == 'EUR'):
            raise TransferInvalidCurrency('wrong currency')
        origin_params = self.get_params(account.id, 'Emetteurs')
        recipient_params = self.get_params(recipient.id, 'Destinataires')
        data = OrderedDict()
        value = self.get_account_value(account.id) or self.get_account_value_by_label(account.label)
        if value is None:
            raise TransferError("Couldn't retrieve origin account in list")
        data['dup'] = re.search('dup=(.*?)(&|$)', value).group(1)
        data['src'] = re.search('src=(.*?)(&|$)', value).group(1)
        data['sign'] = re.search('sign=(.*?)(&|$)', value).group(1)

        # order of params does not seem to matter
        emit_keys = ('cdbqem', 'cdguem', 'nucpem', 'clriem', 'libeem', 'grroem', 'cdprem', 'liprem', 'codeBICEmet', 'codeIBANEmet', 'formatCpteEmet')
        for k in emit_keys:
            data[k] = origin_params[k]
        rcpt_keys = ('idprde', 'tycpde', 'libqde', 'cdbqde', 'cdgude', 'nucpde', 'clride', 'libede', 'grrode', 'paysBenef', 'cdprde', 'liprde', 'formatCompteBenef', 'nomBenef', 'adresseBenef', 'villeBenef', 'codePaysBenef', 'codeBICBenef', 'codeIBANBenef')
        for k in rcpt_keys:
            data[k] = recipient_params[k]

        # This one seem to be set in stone.
        data['inrili'] = 'N'

        # TODO vipon_saisie_opAVenir.js seems to define different behaviours depending on that value
        data['toprib'] = recipient_params['toprib']

        # This needs the currency to be euro.
        data['mntval'] = int(transfer.amount * 100)
        data['mntcdc'] = '2'
        data['mntcdv'] = 'EUR'
        data['datvir'] = transfer.exec_date.strftime('%Y%m%d')
        data['motvir'] = transfer.label

        data['ordre'] = recipient_params['ordre']
        data['nomMem'] = ''

        data['banqueBenef'] = recipient_params['libqde']

        # Initiate transfer
        self.browser.location('/lgn/url.html', params=data)

    def check_data_consistency(self, transfer):
        amount = CleanDecimal('.//td[@headers="virement montant"]', replace_dots=True)(self.doc)
        label = CleanText('.//td[@headers="virement motif"]')(self.doc)
        exec_date = Date(CleanText('.//td[@headers="virement date"]'), dayfirst=True)(self.doc)
        if transfer.amount != amount:
            raise TransferError('data consistency failed, %s changed from %s to %s' % ('amount', transfer.amount, amount))
        if transfer.label not in label:
            raise TransferError('data consistency failed, %s changed from %s to %s' % ('label', transfer.label, label))
        if not (transfer.exec_date <= exec_date <= transfer.exec_date + timedelta(days=4)):
            raise TransferError('data consistency failed, %s changed from %s to %s' % ('exec_date', transfer.exec_date, exec_date))

    def create_transfer(self, account, recipient, transfer):
        transfer = Transfer()
        transfer.currency = FrenchTransaction.Currency('.//td[@headers="virement montant"]')(self.doc)
        transfer.amount = CleanDecimal('.//td[@headers="virement montant"]', replace_dots=True)(self.doc)
        transfer.account_iban = CleanText('//td[@headers="emetteur IBAN"]', replace=[(' ', '')])(self.doc)
        transfer.recipient_iban = CleanText('//td[@headers="beneficiaire IBAN"]', replace=[(' ','')])(self.doc)
        transfer.account_id = account.id
        transfer.recipient_id = recipient.id
        transfer.exec_date = Date(CleanText('.//td[@headers="virement date"]'), dayfirst=True)(self.doc)
        transfer.label = CleanText('.//td[@headers="virement motif"]')(self.doc)
        transfer.account_label = account.label
        transfer.recipient_label = recipient.label
        transfer._account = account
        transfer._recipient = recipient
        transfer.account_balance = account.balance
        return transfer

    def confirm(self):
        form = self.get_form(id='authentification')

        url = self.browser.BASEURL + '//sec/vkm/gen_crypto?estSession=0'
        infos_data = self.browser.open(url).text
        infos_data = re.match('^_vkCallback\((.*)\);$', infos_data).group(1)
        infos = json.loads(infos_data.replace("'", '"'))
        infos['grid'] = self.decode_grid(infos)
        url = self.browser.BASEURL + '/sec/vkm/gen_ui?modeClavier=0&cryptogramme=' + infos["crypto"]
        content = self.browser.open(url).content
        img = Captcha(BytesIO(content), infos)

        try:
            img.build_tiles()
        except TileError as err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        pwd = img.get_codes(self.browser.password[:6])
        t = pwd.split(',')
        newpwd = ','.join(t[self.strange_map[j]] for j in range(6))
        form['codsec'] = newpwd
        form['cryptocvcs'] = infos["crypto"].encode('iso-8859-1')
        form['vkm_op'] = 'sign'
        form.submit()


class RecipientJson(LoggedPage, JsonPage):
    pass


class AddRecipientPage(LoggedPage, BasePage):
    def on_load(self):
        error_msg = CleanText(u'//span[@class="error_msg"]')(self.doc)
        if error_msg:
            raise AddRecipientError(message=error_msg)

    def is_here(self):
        return bool(CleanText(u'//h3[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) or \
                bool(CleanText(u'//h1[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) or \
                bool(CleanText(u'//h3[contains(text(), "Veuillez vérifier les informations du compte à ajouter")]')(self.doc)) or \
                bool(Link('//a[contains(@href, "per_cptBen_ajouterFrBic")]', default=NotAvailable)(self.doc))

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
            raise AddRecipientError('form not found')

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
            raise AddRecipientError('sign process unknown')

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
