# -*- coding: utf-8 -*-

# Copyright(C) 2009-2016  Romain Bignon
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

from __future__ import unicode_literals

from collections import Counter
import re
from io import BytesIO
from random import randint
from decimal import Decimal
from datetime import datetime, timedelta

from weboob.browser.elements import DictElement, ListElement, TableElement, ItemElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Format, Eval, Regexp, CleanText, Date, CleanDecimal, Field
from weboob.browser.filters.html import TableCell
from weboob.browser.pages import JsonPage, LoggedPage, HTMLPage
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import (
    Account, Investment, Recipient, Transfer, TransferError, TransferBankError,
    AddRecipientBankError,
)
from weboob.capabilities.contact import Advisor
from weboob.capabilities.profile import Person, ProfileMissing
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, BrowserPasswordExpired, ActionNeeded
from weboob.tools.capabilities.bank.iban import rib2iban, rebuild_rib, is_iban_valid
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import GridVirtKeyboard
from weboob.tools.date import parse_french_date
from weboob.tools.capabilities.bank.investments import is_isin_valid
from weboob.tools.compat import unquote_plus
from weboob.tools.html import html2text


class ConnectionThresholdPage(HTMLPage):
    NOT_REUSABLE_PASSWORDS_COUNT = 3
    """BNP disallows to reuse one of the three last used passwords."""

    def make_date(self, yy, m, d):
        current = datetime.now().year
        if yy > current - 2000:
            yyyy = 1900 + yy
        else:
            yyyy = 2000 + yy
        return datetime(yyyy, m, d)

    def looks_legit(self, password):
        # the site says:
        # no more than 2 repeats
        for v in Counter(password).values():
            if v > 2:
                return False

        # not the birthdate (but we don't know it)
        first, mm, end = map(int, (password[0:2], password[2:4], password[4:6]))
        now = datetime.now()
        try:
            delta = now - self.make_date(first, mm, end)
        except ValueError:
            pass
        else:
            if 10 < delta.days / 365 < 70:
                return False

        try:
            delta = now - self.make_date(end, mm, first)
        except ValueError:
            pass
        else:
            if 10 < delta.days / 365 < 70:
                return False

        # no sequence (more than 4 digits?)
        password = list(map(int, password))
        up = 0
        down = 0
        for a, b in zip(password[:-1], password[1:]):
            up += int(a + 1 == b)
            down += int(a - 1 == b)
        if up >= 4 or down >= 4:
            return False

        return True

    def on_load(self):
        msg = CleanText('//div[@class="confirmation"]//span[span]')(self.doc)

        self.logger.warning('Password expired.')
        if not self.browser.rotating_password:
            raise BrowserPasswordExpired(msg)

        if not self.looks_legit(self.browser.password):
            # we may not be able to restore the password, so reject it
            self.logger.warning('Unable to restore it, it is not legit.')
            raise BrowserPasswordExpired(msg)

        new_passwords = []
        for i in range(self.NOT_REUSABLE_PASSWORDS_COUNT):
            new_pass = ''.join([str((int(l) + i + 1) % 10) for l in self.browser.password])
            if not self.looks_legit(new_pass):
                self.logger.warning('One of rotating password is not legit')
                raise BrowserPasswordExpired(msg)
            new_passwords.append(new_pass)

        current_password = self.browser.password
        for new_pass in new_passwords:
            self.logger.warning('Renewing with temp password')
            if not self.browser.change_pass(current_password, new_pass):
                self.logger.warning('New temp password is rejected, giving up')
                raise BrowserPasswordExpired(msg)
            current_password = new_pass

        if not self.browser.change_pass(current_password, self.browser.password):
            self.logger.error('Could not restore old password!')

        self.logger.warning('Old password restored.')


def cast(x, typ, default=None):
    try:
        return typ(x or default)
    except ValueError:
        return default


class BNPKeyboard(GridVirtKeyboard):
    color = (0x1f, 0x27, 0x28)
    margin = 3, 3
    symbols = {'0': '43b2227b92e0546d742a1f087015e487',
               '1': '2914e8cc694de26756096d0d0d4c6e0f',
               '2': 'aac54304a7bb850805d29f54557be366',
               '3': '0376d9f8419efee42e253d195a152547',
               '4': '3719595f15b1ac1c5a73d84aa290b5f6',
               '5': '617597f07a6530479927536671485439',
               '6': '4f5dce7bd0d9213fdae54b79bb8dd33a',
               '7': '49e07fa52b9bcee798f3a663f86e6cc1',
               '8': 'c60b723b3d95a46416b34c2cbefba3ed',
               '9': 'a13b8c3617a7bf854590833ddfb97f1f'}

    def __init__(self, browser, image):
        symbols = list('%02d' % x for x in range(1, 11))

        super(BNPKeyboard, self).__init__(symbols, 5, 2, BytesIO(image.content), self.color, convert='RGB')
        self.check_symbols(self.symbols, browser.responses_dirname)


class ListErrorPage(JsonPage):
    def get_error_message(self, error):
        key = 'app.identification.erreur.' + str(error)
        try:
            return html2text(self.doc[key])
        except KeyError:
            return None


class LoginPage(JsonPage):
    @staticmethod
    def render_template(tmpl, **values):
        for k, v in values.items():
            tmpl = tmpl.replace('{{ ' + k + ' }}', v)
        return tmpl

    @staticmethod
    def generate_token(length=11):
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz'
        return ''.join((chars[randint(0, len(chars)-1)] for _ in range(length)))

    def build_doc(self, text):
        try:
            return super(LoginPage, self).build_doc(text)
        except ValueError:
            # XXX When login is successful, server sends HTML instead of JSON,
            #     we can ignore it.
            return {}

    def on_load(self):
        if self.url.startswith('https://mabanqueprivee.'):
            self.browser.switch('mabanqueprivee')

        # Some kind of internal server error instead of normal wrongpass errorCode.
        if self.get('errorCode') == 'INTO_FACADE ERROR: JDF_GENERIC_EXCEPTION':
            raise BrowserIncorrectPassword()

        error = cast(self.get('errorCode'), int, 0)
        # you can find api documentation on errors here : https://mabanque.bnpparibas/rsc/contrib/document/properties/identification-fr-part-V1.json
        if error:
            error_page = self.browser.list_error_page.open()
            msg = error_page.get_error_message(error)
            if not msg:
                msg = self.get('message')

            wrongpass_codes = [201, 21510, 203, 202, 7]
            actionNeeded_codes = [21501, 3, 4, 50]
            websiteUnavailable_codes = [207, 1001]
            if error in wrongpass_codes:
                raise BrowserIncorrectPassword(msg)
            elif error == 21: # "Ce service est momentanément indisponible. Veuillez renouveler votre demande ultérieurement." -> In reality, account is blocked because of too much wrongpass
                raise ActionNeeded(u"Compte bloqué")
            elif error in actionNeeded_codes:
                raise ActionNeeded(msg)
            elif error in websiteUnavailable_codes:
                raise BrowserUnavailable(msg)
            else:
                assert False, 'Unexpected error at login: "%s" (code=%s)' % (msg, error)

    def login(self, username, password):
        url = '/identification-wspl-pres/grille/%s' % self.get('data.grille.idGrille')
        keyboard = self.browser.open(url)
        vk = BNPKeyboard(self.browser, keyboard)

        target = self.browser.BASEURL + 'SEEA-pa01/devServer/seeaserver'
        user_agent = self.browser.session.headers.get('User-Agent') or ''
        auth = self.render_template(self.get('data.authTemplate'),
                                    idTelematique=username,
                                    password=vk.get_string_code(password),
                                    clientele=user_agent)
        # XXX useless?
        csrf = self.generate_token()

        response = self.browser.location(target, data={'AUTH': auth, 'CSRF': csrf})
        if response.url.startswith('https://pro.mabanque.bnpparibas'):
            self.browser.switch('pro.mabanque')
        if response.url.startswith('https://banqueprivee.mabanque.bnpparibas'):
            self.browser.switch('banqueprivee.mabanque')


class BNPPage(LoggedPage, JsonPage):
    def build_doc(self, text):
        try:
            return self.response.json(parse_float=Decimal)
        except ValueError:
            raise BrowserUnavailable()

    def on_load(self):
        code = cast(self.get('codeRetour'), int, 0)

        if code == -30:
            self.logger.debug('End of session detected, try to relog...')
            self.browser.do_login()
        elif code:
            self.logger.debug('Unexpected error: "%s" (code=%s)' % (self.get('message'), code))
            return (self.get('message'), code)


class ProfilePage(LoggedPage, JsonPage):
    ENCODING = 'utf-8'

    def get_error_message(self):
        return Dict('message')(self.doc)

    @method
    class get_profile(ItemElement):
        def condition(self):
            return Dict('codeRetour')(self) == '0'

        item_path = 'data/initialisation/informationsClient/'

        klass = Person

        def parse(self, el):
            if not Dict(self.item_path + 'etatCivil/prenom')(el).strip() and not Dict(self.item_path + 'etatCivil/nom')(el).strip():
                raise ProfileMissing()
        obj_name = Format('%s %s', Dict(item_path + 'etatCivil/prenom'), Dict(item_path + 'etatCivil/nom'))
        obj_spouse_name = Dict(item_path + 'etatCivil/nomMarital', default=NotAvailable)
        obj_birth_date = Date(Dict(item_path + 'etatCivil/dateNaissance'), dayfirst=True)
        obj_nationality = Dict(item_path + 'etatCivil/nationnalite')
        obj_phone = Dict(item_path + 'etatCivil/numMobile')
        obj_email = Dict(item_path + 'etatCivil/mail')
        obj_job = Dict(item_path + 'situationPro/activiteExercee')
        obj_job_start_date = Date(Dict(item_path + 'situationPro/dateDebut'), dayfirst=True, default=NotAvailable)
        obj_company_name = Dict(item_path + 'situationPro/nomEmployeur')

        def obj_company_siren(self):
            siren = Dict('data/initialisation/informationsClient/monEntreprise/siren')(self.page.doc)
            return siren or NotAvailable


class AccountsPage(BNPPage):
    FAMILY_TO_TYPE = {
        1: Account.TYPE_CHECKING,
        2: Account.TYPE_SAVINGS,
        3: Account.TYPE_DEPOSIT,
        4: Account.TYPE_MARKET,
        5: Account.TYPE_LIFE_INSURANCE,
        6: Account.TYPE_LIFE_INSURANCE,
        8: Account.TYPE_LOAN,
        9: Account.TYPE_LOAN,
    }

    LABEL_TO_TYPE = {
        u'PEA Espèces':                       Account.TYPE_PEA,
        u'PEA Titres':                        Account.TYPE_PEA,
        u'PEL':                               Account.TYPE_SAVINGS,
        u'Plan Epargne Retraite Particulier': Account.TYPE_PERP,
    }

    def iter_accounts(self, ibans):
        for f in self.path('data.infoUdc.familleCompte.*'):
            for a in f.get('compte'):
                iban = ibans.get(a.get('key'))
                if iban is not None and not is_iban_valid(iban):
                    iban = rib2iban(rebuild_rib(iban))

                acc = Account.from_dict({
                    'id': a.get('key'),
                    'label': a.get('libellePersoProduit') or a.get('libelleProduit'),
                    'currency': a.get('devise'),
                    'type': self.LABEL_TO_TYPE.get(' '.join(a.get('libelleProduit').split())) or \
                            self.FAMILY_TO_TYPE.get(f.get('idFamilleCompte')) or Account.TYPE_UNKNOWN,
                    'balance': a.get('soldeDispo'),
                    'coming': a.get('soldeAVenir'),
                    'iban': iban,
                    'number': a.get('value')
                })
                # softcap not used TODO don't pass this key when backend is ready
                # deferred cb can disappear the day after the appear, so 0 as day_for_softcap
                acc._bisoftcap = {'deferred_cb': {'softcap_day': 1000, 'day_for_softcap': 0, 'date_field': 'rdate'}}
                yield acc


class AccountsIBANPage(BNPPage):
    def get_ibans_dict(self):
        return dict([(a['ibanCrypte'], a['iban']) for a in self.path('data.listeRib.*.infoCompte')])


class MyRecipient(ItemElement):
    klass = Recipient

    def obj_currency(self):
        return Dict('devise')(self) or NotAvailable

    def validate(self, el):
        # For the moment, we skip this kind of recipient:
        # {"nomBeneficiaire":"Aircraft Guaranty Holdings LLC","idBeneficiaire":"00002##00002##FRSTUS44XXX##130018430","ibanNumCompte":"130018430","typeIban":"0","bic":"FRSTUS44XXX","statut":"1","numListe":"00002","typeBeneficiaire":"INTER","devise":"USD","tauxConversion":"1.047764","nbDecimale":"2","typeFrais":"","adresseBeneficiaire":"","nomBanque":"Frost National Bank","adresseBanque":"100 West Houston Street San Antonio, Texas 78205 USA ","canalActivation":"1","libelleStatut":"Activé"}
        return is_iban_valid(el.iban)


class TransferInitPage(BNPPage):
    def on_load(self):
        message_code = BNPPage.on_load(self)
        if message_code is not None:
            raise TransferError('%s, code=%s' % (message_code[0], message_code[1]))

    def get_ibans_dict(self, account_type):
        return dict([(a['ibanCrypte'], a['iban']) for a in self.path('data.infoVirement.listeComptes%s.*' % account_type)])

    def can_transfer_to_recipients(self, origin_account_id):
        return next(a['eligibleVersBenef'] for a in self.path('data.infoVirement.listeComptesDebiteur.*') if a['ibanCrypte'] == origin_account_id) == '1'

    @method
    class transferable_on(DictElement):
        item_xpath = 'data/infoVirement/listeComptesCrediteur'

        class item(MyRecipient):
            condition = lambda self: Dict('ibanCrypte')(self.el) != self.env['origin_account_ibancrypte']

            obj_id = Dict('ibanCrypte')
            obj_label = Dict('libelleCompte')
            obj_iban = Dict('iban')
            obj_category = u'Interne'

            def obj_bank_name(self):
                return u'BNP PARIBAS'

            def obj_enabled_at(self):
                return datetime.now().replace(microsecond=0)


class RecipientsPage(BNPPage):
    @method
    class iter_recipients(DictElement):
        item_xpath = 'data/infoBeneficiaire/listeBeneficiaire'

        class item(MyRecipient):
            # For the moment, only yield ready to transfer on recipients.
            condition = lambda self: Dict('libelleStatut')(self.el) in [u'Activé', u'Temporisé']

            obj_id = Dict('idBeneficiaire')
            obj_label = Dict('nomBeneficiaire')
            obj_iban = Dict('ibanNumCompte')
            obj_category = u'Externe'

            def obj_bank_name(self):
                return Dict('nomBanque')(self) or NotAvailable

            def obj_enabled_at(self):
                return datetime.now().replace(microsecond=0) if Dict('libelleStatut')(self) == u'Activé' else (datetime.now() + timedelta(days=5)).replace(microsecond=0)


class ValidateTransferPage(BNPPage):
    def check_errors(self):
        if not 'data' in self.doc:
            raise TransferBankError(message=self.doc['message'])

    def abort_if_unknown(self, transfer_data):
        try:
            assert transfer_data['typeOperation'] in ['1', '2']
            assert transfer_data['repartitionFrais'] == '0'
            assert transfer_data['devise'] == 'EUR'
            assert not transfer_data['montantDeviseEtrangere']
        except AssertionError as e:
            raise TransferError(e)

    def handle_response(self, account, recipient, amount, reason):
        self.check_errors()
        transfer_data = self.doc['data']['validationVirement']

        self.abort_if_unknown(transfer_data)

        if 'idBeneficiaire' in transfer_data and transfer_data['idBeneficiaire'] is not None:
            assert transfer_data['idBeneficiaire'] == recipient.id
        elif transfer_data.get('ibanCompteCrediteur'):
            assert transfer_data['ibanCompteCrediteur'] == recipient.iban

        transfer = Transfer()
        transfer.currency = transfer_data['devise']
        transfer.amount = Decimal(transfer_data['montantEuros'])
        transfer.account_iban = transfer_data['ibanCompteDebiteur']
        transfer.account_id = account.id
        try:
            transfer.recipient_iban = transfer_data['ibanCompteCrediteur'] or recipient.iban
        except KeyError:
            # In last version, json contains a key 'idBeneficiaire' containing:
            # "idBeneficiaire" : "00003##00001####FR7610278123456789028070101",
            transfer.recipient_id = transfer_data['idBeneficiaire']
            transfer.recipient_iban = transfer.recipient_id.split('#')[-1] or recipient.iban
        else:
            transfer.recipient_id = recipient.id
        transfer.exec_date = parse_french_date(transfer_data['dateExecution']).date()
        transfer.fees = Decimal(transfer_data.get('montantFrais', '0'))
        transfer.label = transfer_data['motifVirement']

        transfer.account_label = account.label
        transfer.recipient_label = recipient.label
        transfer.id = transfer_data['reference']
        # This is true if a transfer with the same metadata has already been done recently
        transfer._doublon = transfer_data['doublon']
        transfer.account_balance = account.balance

        return transfer


class RegisterTransferPage(ValidateTransferPage):
    def handle_response(self, transfer):
        self.check_errors()
        transfer_data = self.doc['data']['enregistrementVirement']

        transfer.id = transfer_data['reference']
        transfer.exec_date = parse_french_date(self.doc['data']['enregistrementVirement']['dateExecution']).date()
        # Timestamp at which the bank registered the transfer
        register_date = re.sub(' 24:', ' 00:', self.doc['data']['enregistrementVirement']['dateEnregistrement'])
        transfer._register_date = parse_french_date(register_date)

        return transfer


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<category>CHEQUE)(?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(?P<category>FACTURE CARTE) DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*?)( CA?R?T?E? ?\d*X*\d*)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>(PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>PRLV( EUROPEEN)? SEPA) (?P<text>.*?)( MDT/.*?)?( ECH/\d+)?( ID .*)?$'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>ECHEANCEPRET)(?P<text>.*)'),   FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile('^(?P<category>RETRAIT DAB) (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))?( \d+)? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>VIR(EMEN)?T? (RECU |FAVEUR )?(TIERS )?)\w+ \d+/\d+ \d+H\d+ \w+ (?P<text>.*)$'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>VIR(EMEN)?T? (EUROPEEN )?(SEPA )?(RECU |FAVEUR |EMIS )?(TIERS )?)(/FRM |/DE |/MOTIF |/BEN )?(?P<text>.*?)(/.+)?$'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>REMBOURST) CB DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>REMBOURST)(?P<text>.*)'),     FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>COMMISSIONS)(?P<text>.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>REMUNERATION).*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>REMISE CHEQUES)(?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class HistoryPage(BNPPage):
    CODE_TO_TYPE = {
        1:  Transaction.TYPE_CHECK, # Chèque émis
        2:  Transaction.TYPE_CHECK, # Chèque reçu
        3:  Transaction.TYPE_CASH_DEPOSIT, # Versement espèces
        4:  Transaction.TYPE_ORDER, # Virements reçus
        5:  Transaction.TYPE_ORDER, # Virements émis
        6:  Transaction.TYPE_LOAN_PAYMENT, # Prélèvements / amortissements prêts
        7:  Transaction.TYPE_CARD, # Paiements carte,
        8:  Transaction.TYPE_CARD, # Carte / Formule BNP Net,
        9:  Transaction.TYPE_UNKNOWN,  # Opérations Titres
        10: Transaction.TYPE_UNKNOWN,  # Effets de Commerce
        11: Transaction.TYPE_WITHDRAWAL, # Retraits d'espèces carte
        12: Transaction.TYPE_UNKNOWN, # Opérations avec l'étranger
        13: Transaction.TYPE_CARD, # Remises Carte
        14: Transaction.TYPE_WITHDRAWAL, # Retraits guichets
        15: Transaction.TYPE_BANK, # Intérêts/frais et commissions
        16: Transaction.TYPE_UNKNOWN, # Tercéo
        30: Transaction.TYPE_UNKNOWN, # Divers
    }

    COMING_TYPE_TO_TYPE = {
        2: Transaction.TYPE_ORDER, # Prélèvement
        3: Transaction.TYPE_CHECK, # Chèque
        4: Transaction.TYPE_CARD, # Opération carte
    }

    def one(self, path, context=None):
        try:
            return list(self.path(path, context))[0]
        except IndexError:
            return None

    def iter_history(self):
        for op in self.get('data.listerOperations.compte.operationPassee') or []:
            codeFamille = cast(self.one('operationType.codeFamille', op), int)
            tr = Transaction.from_dict({
                'id': op.get('idOperation'),
                'type': self.CODE_TO_TYPE.get(codeFamille) or Transaction.TYPE_UNKNOWN,
                'category': op.get('categorie'),
                'amount': self.one('montant.montant', op),
            })
            tr.parse(raw=op.get('libelleOperation'),
                     date=parse_french_date(op.get('dateOperation')),
                     vdate=parse_french_date(self.one('montant.valueDate', op)))

            raw_is_summary = re.match(r'FACTURE CARTE SELON RELEVE DU\b|FACTURE CARTE CARTE AFFAIRES \d{4}X{8}\d{4} SUIVANT\b', tr.raw)
            if tr.type == Transaction.TYPE_CARD and raw_is_summary:
                tr.type = Transaction.TYPE_CARD_SUMMARY
                tr.deleted = True
            yield tr

    def iter_coming(self):
        for op in self.path('data.listerOperations.compte.operationAvenir.*.operation.*'):
            codeOperation = cast(op.get('codeOperation'), int, 0)
            # Coming transactions don't have real id
            tr = Transaction.from_dict({
                'type': self.COMING_TYPE_TO_TYPE.get(codeOperation) or Transaction.TYPE_UNKNOWN,
                'amount': op.get('montant'),
                'card': op.get('numeroPorteurCarte'),
            })
            tr.parse(date=parse_french_date(op.get('dateOperation')),
                     vdate=parse_french_date(op.get('valueDate')),
                     raw=op.get('libelle'))
            if tr.type == Transaction.TYPE_CARD:
                tr.type = self.browser.card_to_transaction_type.get(op.get('keyCarte'),
                                                                    Transaction.TYPE_DEFERRED_CARD)
            yield tr


class ListDetailCardPage(BNPPage):
    def get_card_to_transaction_type(self):
        d = {}
        for card in self.path('data.responseRestitutionCarte.listeCartes.*'):
            if 'DIFFERE' in card['typeDebit']:
                tr_type = Transaction.TYPE_DEFERRED_CARD
            else:
                tr_type = Transaction.TYPE_CARD
            d[card['numCarteCrypte']] = tr_type
        return d


class LifeInsurancesPage(BNPPage):
    investments_path = 'data.infosContrat.repartition.listeSupport.*'

    def iter_investments(self):
        for support in self.path(self.investments_path):
            inv = Investment()
            if 'codeIsin' in support:
                inv.code = inv.id = support['codeIsin']
                inv.quantity = support.get('nbUC', NotAvailable)
                inv.unitvalue = support.get('valUC', NotAvailable)

            inv.label = support['libelle']
            inv.valuation = support.get('montant', NotAvailable)
            inv.set_empty_fields(NotAvailable)
            yield inv


class LifeInsurancesHistoryPage(BNPPage):
    def iter_history(self, coming):
        for op in self.get('data.listerMouvements.listeMouvements') or []:
            #We have not date for this statut so we just skit it
            if op.get('statut') == u'En cours':
                continue

            tr = Transaction.from_dict({
                'type': Transaction.TYPE_BANK,
                '_state': op.get('statut'),
                'amount': op.get('montantNet'),
                })

            if op.get('statut') == 'Sans suite':
                continue

            tr.parse(date=parse_french_date(op.get('dateSaisie')),
                     vdate = parse_french_date(op.get('dateEffet')) if op.get('dateEffet') else None,
                     raw='%s %s' % (op.get('libelleMouvement'), op.get('canalSaisie') or ''))
            tr._op = op

            if (op.get('statut') == u'Traité') ^ coming:
                yield tr


class LifeInsurancesDetailPage(LifeInsurancesPage):
    investments_path = 'data.detailMouvement.listeSupport.*'


class NatioVieProPage(BNPPage):
    # This form is required to go to the capitalisation contracts page.
    def get_params(self):
        params = {
            'app':         'BNPNET',
            'hageGroup':   'consultationBnpnet',
            'init':        'true',
            'multiInit':   'false',
        }
        params['a0'] = self.doc['data']['nationVieProInfos']['a0']
        # The number of "p" keys may vary (p0, p1, p2 ... up to p13 or more)
        for key, value in self.doc['data']['nationVieProInfos']['listeP'].items():
            params[key] = value
        # We must decode the values before constructing the URL:
        for k, v in params.items():
            params[k] = unquote_plus(v)
        return params


class CapitalisationPage(LoggedPage, HTMLPage):
    def has_contracts(self):
        # This message will appear if the page "Assurance Vie" contains no contract.
        return not CleanText('//td[@class="message"]/text()[starts-with(., "Pour toute information")]')(self.doc)

    # To be completed with other account labels and types seen on the "Assurance Vie" space:
    ACCOUNT_TYPES = {
        'BNP Paribas Multiplacements':                  Account.TYPE_LIFE_INSURANCE,
        'BNP Paribas Multiciel Privilège':              Account.TYPE_CAPITALISATION,
        'Plan Epargne Retraite Particulier':            Account.TYPE_PERP,
        "Plan d'Épargne Retraite des Particuliers":     Account.TYPE_PERP,
    }

    @method
    class iter_capitalisation(TableElement):
        # Other types of tables may appear on the page (such as Alternative Emprunteur/Capital Assuré)
        # But they do not contain bank accounts so we must avoid them.
        item_xpath = '//table/tr[preceding-sibling::tr[th[text()="Libellé du contrat"]]][td[@class="ligneTableau"]]'

        head_xpath = '//table/tr/th[@class="headerTableau"]'

        col_label = 'Libellé du contrat'
        col_id = 'Numéro de contrat'
        col_balance = 'Montant'
        col_currency = "Monnaie d'affichage"

        class item(ItemElement):
            klass = Account

            obj_label = CleanText(TableCell('label'))
            obj_id = CleanText(TableCell('id'))
            obj_number = CleanText(TableCell('id'))
            obj_balance = CleanDecimal(TableCell('balance'), replace_dots=True)
            obj_coming = None
            obj_iban = None

            def obj_type(self):
                for k, v in self.page.ACCOUNT_TYPES.items():
                    if Field('label')(self).startswith(k):
                        return v
                return Account.TYPE_UNKNOWN

            def obj_currency(self):
                currency = CleanText(TableCell('currency')(self))(self)
                return Account.get_currency(currency)

            # Required to get the investments of each "Assurances Vie" account:
            def obj__details(self):
                raw_details = CleanText((TableCell('balance')(self)[0]).xpath('./a/@href'))(self)
                m = re.search(r"Window\('(.*?)',window", raw_details)
                if m:
                    return m.group(1)

    def get_params(self, account):
        form = self.get_form(xpath='//form[@name="formListeContrats"]')
        form['postValue'] = account._details
        return form

    # The investments vdate is out of the investments table and is the same for all investments:
    def get_vdate(self):
        return parse_french_date(CleanText('//table[tr[th[text()[contains(., "Date de valorisation")]]]]/tr[2]/td[2]')(self.doc))

    @method
    class iter_investments(TableElement):
        # Investment lines contain at least 5 <td> tags
        item_xpath = '//table[tr[th[text()[contains(., "Libellé")]]]]/tr[count(td)>=5]'
        head_xpath = '//table[tr[th[text()[contains(., "Libellé")]]]]/tr/th[@class="headerTableau"]'

        col_label = 'Libellé'
        col_code = 'Code ISIN'
        col_quantity = 'Nombre de parts'
        col_valuation = 'Montant'
        col_portfolio_share = 'Montant en %'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_portfolio_share = Eval(lambda x: x / 100, CleanDecimal(TableCell('portfolio_share'), replace_dots=True))
            # There is no "unitvalue" information available on the "Assurances Vie" space.

            def obj_quantity(self):
                quantity = TableCell('quantity')(self)
                if CleanText(quantity)(self) == '-':
                    return NotAvailable
                return CleanDecimal(quantity, replace_dots=True)(self)

            def obj_code(self):
                isin = CleanText(TableCell('code')(self))(self)
                return isin or NotAvailable

            def obj_code_type(self):
                if is_isin_valid(Field('code')(self)):
                    return Investment.CODE_TYPE_ISIN
                return NotAvailable

            def obj_vdate(self):
                return self.page.get_vdate()


class MarketListPage(BNPPage):
    def get_list(self):
        return self.get('securityAccountsList') or []


class MarketSynPage(BNPPage):
    def get_list(self):
        return self.get('synSecurityAccounts') or []


class MarketPage(BNPPage):
    investments_path = 'listofPortfolios.*'

    def iter_investments(self):
        for support in self.path(self.investments_path):
            inv = Investment()
            inv.code = inv.id = support['securityCode']
            inv.quantity = support['quantityOwned']
            inv.unitvalue = support['currentQuote']
            inv.unitprice = support['averagePrice']
            inv.label = support['securityName']
            inv.valuation = support['valorizationValuation']
            inv.diff = support['profitLossValorisation']
            inv.set_empty_fields(NotAvailable)
            yield inv


class MarketHistoryPage(BNPPage):
    def iter_history(self):
        for op in self.get('contentList') or []:

            tr = Transaction.from_dict({
                'type': Transaction.TYPE_BANK,
                'amount': op.get('movementAmount'),
                'date': datetime.fromtimestamp(op.get('movementDate') / 1000),
                'label': op.get('operationName'),
                })

            tr.investments = []
            inv = Investment()
            inv.code = op.get('securityCode')
            inv.quantity = op.get('movementQuantity')
            inv.label = op.get('securityName')
            inv.set_empty_fields(NotAvailable)
            tr.investments.append(inv)
            yield tr


class AdvisorPage(BNPPage):
    def has_error(self):
        return (self.doc.get('message') == 'Erreur technique')

    @method
    class get_advisor(ListElement):
        class item(ItemElement):
            klass = Advisor

            obj_name = Format('%s %s %s', Dict('data/civilite'), Dict('data/prenom'), Dict('data/nom'))
            obj_email = Regexp(Dict('data/mail'), '(?=\w)(.*)', default=NotAvailable)
            obj_phone = CleanText(Dict('data/telephone'), replace=[(' ', '')])
            obj_mobile = CleanText(Dict('data/mobile'), replace=[(' ', '')])
            obj_fax = CleanText(Dict('data/fax'), replace=[(' ', '')])
            obj_agency = Dict('data/agence')
            obj_address = Format('%s %s %s', Dict('data/adresseAgence'), Dict('data/codePostalAgence'), Dict('data/villeAgence'))


class AddRecipPage(BNPPage):
    def on_load(self):
        code = cast(self.get('codeRetour'), int)
        if code:
            raise AddRecipientBankError(message=self.get('message'))

    def get_recipient(self, recipient):
        r = Recipient()
        r.iban = recipient.iban
        r.id = self.get('data.gestionBeneficiaire.identifiantBeneficiaire')
        r.label = recipient.label
        r.category = u'Externe'
        r.enabled_at = datetime.now().replace(microsecond=0) + timedelta(days=5)
        r.currency = u'EUR'
        r.bank_name = NotAvailable
        return r

class ActivateRecipPage(AddRecipPage):
    def get_recipient(self, recipient):
        r = Recipient()
        r.iban = recipient.iban
        r.id = recipient.id
        r.label = recipient.label
        r.category = u'Externe'
        r.enabled_at = datetime.now().replace(microsecond=0) + timedelta(days=5)
        r.currency = u'EUR'
        r.bank_name = self.get('data.activationBeneficiaire.nomBanque')
        return r
