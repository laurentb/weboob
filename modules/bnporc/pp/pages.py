# -*- coding: utf-8 -*-

# Copyright(C) 2009-2015  Romain Bignon
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


import re
from cStringIO import StringIO
from random import randint
from decimal import Decimal
from datetime import datetime

from weboob.browser.pages import JsonPage, LoggedPage, HTMLPage
from weboob.tools.captcha.virtkeyboard import GridVirtKeyboard
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.json import json
from weboob.tools.date import parse_french_date as Date


class ConnectionThresholdPage(HTMLPage):
    def change_pass(self, oldpass, newpass):
        res = self.browser.open('/identification-wspl-pres/grille?accessible=false')
        url = '/identification-wspl-pres/grille/%s' % res.json()['data']['idGrille']
        keyboard = self.browser.open(url)
        vk = BNPKeyboard(self, keyboard)
        data = {}
        data['codeAppli'] = 'PORTAIL'
        data['idGrille'] = res.json()['data']['idGrille']
        data['typeGrille'] = res.json()['data']['typeGrille']
        data['confirmNouveauPassword'] = vk.get_string_code(newpass)
        data['nouveauPassword'] = vk.get_string_code(newpass)
        data['passwordActuel'] = vk.get_string_code(oldpass)
        self.browser.location('/mcs-wspl/rpc/modifiercodesecret', data=data)

    def on_load(self):
        new_pass = ''.join([str((int(l) + 1) % 10) for l in self.browser.password])
        self.logger.warning('Password expired. Renewing it...')
        self.change_pass(self.browser.password, new_pass)
        self.change_pass(new_pass, self.browser.password)

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

    def __init__(self, page, image):
        symbols = list('%02d' % x for x in range(1, 11))

        super(BNPKeyboard, self).__init__(symbols, 5, 2, StringIO(image.content), self.color, convert='RGB')
        self.check_symbols(self.symbols, page.browser.responses_dirname)


class LoginPage(JsonPage):
    @staticmethod
    def render_template(tmpl, **values):
        for k, v in values.iteritems():
            tmpl = tmpl.replace('{{ ' + k + ' }}', v)
        return tmpl

    @staticmethod
    def generate_token(length=11):
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz'
        return ''.join((chars[randint(0, len(chars)-1)] for _ in xrange(length)))

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

        error = cast(self.get('errorCode'), int, 0)

        if error:
            codes = [201, 21510, 203, 202, 1001]
            msg = self.get('message')
            if error in codes:
                raise BrowserIncorrectPassword(msg)
            self.logger.debug('Unexpected error at login: "%s" (code=%s)' % (msg, error))

    def login(self, username, password):
        url = '/identification-wspl-pres/grille/%s' % self.get('data.grille.idGrille')
        keyboard = self.browser.open(url)
        vk = BNPKeyboard(self, keyboard)

        target = self.browser.BASEURL + 'SEEA-pa01/devServer/seeaserver'
        user_agent = self.browser.session.headers.get('User-Agent') or ''
        auth = self.render_template(self.get('data.authTemplate'),
                                    idTelematique=username,
                                    password=vk.get_string_code(password),
                                    clientele=user_agent)
        # XXX useless ?
        csrf = self.generate_token()

        response = self.browser.location(target, data={'AUTH': auth, 'CSRF': csrf})
        if response.url.startswith('https://pro.mabanque.bnpparibas'):
            self.browser.switch('pro.mabanque')
        if response.url.startswith('https://banqueprivee.mabanque.bnpparibas'):
            self.browser.switch('banqueprivee.mabanque')


class BNPPage(LoggedPage, JsonPage):
    def build_doc(self, text):
        try:
            return json.loads(text, parse_float=Decimal)
        except ValueError:
            raise BrowserUnavailable()

    def on_load(self):
        code = cast(self.get('codeRetour'), int, 0)

        if code == -30:
            self.logger.debug('End of session detected, try to relog...')
            self.browser.do_login()
        elif code:
            self.logger.debug('Unexpected error: "%s" (code=%s)' % (self.get('message'), code))


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
        u'PEA Espèces':    Account.TYPE_SAVINGS,
    }

    def iter_accounts(self, ibans):
        for f in self.path('data.infoUdc.familleCompte.*'):
            for a in f.get('compte'):
                yield Account.from_dict({
                    'id': a.get('key'),
                    'label': a.get('libellePersoProduit') or a.get('libelleProduit'),
                    'currency': a.get('devise'),
                    'type': self.LABEL_TO_TYPE.get(a.get('libelleProduit')) or self.FAMILY_TO_TYPE.get(f.get('idFamilleCompte')) or Account.TYPE_UNKNOWN,
                    'balance': a.get('soldeDispo'),
                    'coming': a.get('soldeAVenir'),
                    'iban': ibans.get(a.get('key')),
                    'number': a.get('value')
                })


class AccountsIBANPage(BNPPage):
    def get_ibans_dict(self):
        return dict([(a['ibanCrypte'], a['iban']) for a in self.path('data.listeRib.*.infoCompte')])


class TransferInitPage(BNPPage):
    def get_ibans_dict(self):
        return dict([(a['ibanCrypte'], a['iban']) for a in self.path('data.infoVirement.listeComptesCrediteur.*')])


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
                     date=Date(op.get('dateOperation')),
                     vdate=Date(self.one('montant.valueDate', op)))
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
            tr.parse(date=Date(op.get('dateOperation')),
                     vdate=Date(op.get('valueDate')),
                     raw=op.get('libelle'))
            yield tr


class LifeInsurancesPage(BNPPage):
    investments_path = 'data.infosContrat.repartition.listeSupport.*'

    def iter_investments(self):
        for support in self.path(self.investments_path):
            inv = Investment()
            if 'codeIsin' in support:
                inv.code = inv.id = support['codeIsin']
                inv.quantity = support['nbUC']
                inv.unitvalue = support['valUC']

            inv.label = support['libelle']
            inv.valuation = support['montant']
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

            tr.parse(date=Date(op.get('dateSaisie')),
                     vdate=Date(op.get('dateEffet')),
                     raw='%s %s' % (op.get('libelleMouvement'), op.get('canalSaisie') or ''))
            tr._op = op

            if (op.get('statut') == u'Traité') ^ coming:
                yield tr


class LifeInsurancesDetailPage(LifeInsurancesPage):
    investments_path = 'data.detailMouvement.listeSupport.*'


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
