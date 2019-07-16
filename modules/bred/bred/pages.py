# -*- coding: utf-8 -*-

# Copyright(C) 2018 Célande Adrien
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
from datetime import date
from decimal import Decimal

from weboob.tools.date import parse_french_date
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, ActionNeeded, ParseError
from weboob.capabilities.base import find_object
from weboob.browser.pages import JsonPage, LoggedPage, HTMLPage
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment
from weboob.tools.capabilities.bank.investments import is_isin_valid
from weboob.capabilities.profile import Person
from weboob.browser.filters.standard import CleanText, CleanDecimal, Env, Eval
from weboob.browser.filters.json import Dict
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^.*Virement (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'PRELEV SEPA (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile(r'.*Prélèvement.*'),        FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(REGL|Rgt)(?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(?P<text>.*) Carte \d+\s+ LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile(r'^Débit mensuel.*'), FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile(r"^Retrait d'espèces à un DAB (?P<text>.*) CARTE [X\d]+ LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})"),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^Paiement de chèque (?P<text>.*)'),  FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(Cotisation|Intérêts) (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(Remise Chèque|Remise de chèque)\s*(?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^Versement (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^(?P<text>.*)LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})\s*(?P<text2>.*)'),
                                                          FrenchTransaction.TYPE_UNKNOWN),
    ]


class MyJsonPage(LoggedPage, JsonPage):
    def get_content(self):
        return self.doc.get('content', {})


class HomePage(LoggedPage, HTMLPage):
    pass


class LoginPage(LoggedPage, HTMLPage):
    pass


class UniversePage(MyJsonPage):
    def get_universes(self):
        universe_data = self.get_content()
        universes = {}
        universes[universe_data['universKey']] = universe_data['title']
        for universe in universe_data.get('menus', {}):
            universes[universe['universKey']] = universe['title']

        return universes


class TokenPage(MyJsonPage):
    pass


class MoveUniversePage(LoggedPage, HTMLPage):
    pass


class SwitchPage(LoggedPage, JsonPage):
    pass


class LoansPage(MyJsonPage):
    def iter_loans(self, current_univers):
        for content in self.get_content():
            a = Account()
            a.id = "%s.%s" % (content['comptePrets'].strip(), content['numeroDossier'].strip())
            a.type = Account.TYPE_LOAN
            a.label = ' '.join([content['intitule'].strip(), content['libellePrets'].strip()])
            a.balance = -Decimal(str(content['montantCapitalDu']['valeur']))
            a.currency = content['montantCapitalDu']['monnaie']['code'].strip()
            a._univers = current_univers
            yield a


class AccountsPage(MyJsonPage):
    ACCOUNT_TYPES = {
        '000': Account.TYPE_CHECKING,   # Compte à vue
        '001': Account.TYPE_SAVINGS,    # Livret Ile de France
        '011': Account.TYPE_CARD,       # Carte bancaire
        '020': Account.TYPE_SAVINGS,    # Compte sur livret
        '021': Account.TYPE_SAVINGS,
        '022': Account.TYPE_SAVINGS,    # Livret d'épargne populaire
        '023': Account.TYPE_SAVINGS,    # LDD Solidaire
        '025': Account.TYPE_SAVINGS,    # Livret Fidélis
        '027': Account.TYPE_SAVINGS,    # Livret A
        '037': Account.TYPE_SAVINGS,
        '070': Account.TYPE_SAVINGS,    # Compte Epargne Logement
        '077': Account.TYPE_SAVINGS,    # Livret Bambino
        '078': Account.TYPE_SAVINGS,    # Livret jeunes
        '080': Account.TYPE_SAVINGS,    # Plan épargne logement
        '081': Account.TYPE_SAVINGS,
        '086': Account.TYPE_SAVINGS,    # Compte épargne Moisson
        '097': Account.TYPE_CHECKING,   # Solde en devises
        '730': Account.TYPE_DEPOSIT,    # Compte à terme Optiplus
        '999': Account.TYPE_MARKET,     # no label, we use 'Portefeuille Titres' if needed
    }

    def iter_accounts(self, accnum, current_univers):
        seen = set()

        accounts_list = []

        for content in  self.get_content():
            if accnum != '00000000000' and content['numero'] != accnum:
                continue
            for poste in content['postes']:
                a = Account()
                a._number = content['numeroLong']
                a._nature = poste['codeNature']
                a._codeSousPoste = poste['codeSousPoste'] if 'codeSousPoste' in poste else None
                a._consultable = poste['consultable']
                a._univers = current_univers
                a.id = '%s.%s' % (a._number, a._nature)

                a.type = self.ACCOUNT_TYPES.get(poste['codeNature'], Account.TYPE_UNKNOWN)
                if a.type == Account.TYPE_UNKNOWN:
                    self.logger.warning("unknown type %s" % poste['codeNature'])

                if a.type == Account.TYPE_CARD:
                    a.parent = find_object(accounts_list, _number=a._number, type=Account.TYPE_CHECKING)

                if 'numeroDossier' in poste and poste['numeroDossier']:
                    a._file_number = poste['numeroDossier']
                    a.id += '.%s' % a._file_number

                if poste['postePortefeuille']:
                    a.label = '{} Portefeuille Titres'.format(content['intitule'].strip())
                    a.balance = Decimal(str(poste['montantTitres']['valeur']))
                    a.currency = poste['montantTitres']['monnaie']['code'].strip()
                    if not a.balance and not a.currency and 'dateTitres' not in poste:
                        continue
                    accounts_list.append(a)

                if 'libelle' not in poste:
                    continue

                a.label = ' '.join([content['intitule'].strip(), poste['libelle'].strip()])
                if poste['numeroDossier']:
                    a.label = '{} n°{}'.format(a.label, poste['numeroDossier'])

                a.balance = Decimal(str(poste['solde']['valeur']))
                a.currency = poste['solde']['monnaie']['code'].strip()
                # Some accounts may have balance currency
                if 'Solde en devises' in a.label and a.currency != u'EUR':
                    a.id += str(poste['monnaie']['codeSwift'])

                if a.id in seen:
                    # some accounts like "compte à terme fidélis" have the same _number and _nature
                    # but in fact are kind of closed, so worthless...
                    self.logger.warning('ignored account id %r (%r) because it is already used', a.id, poste.get('numeroDossier'))
                    continue

                seen.add(a.id)
                accounts_list.append(a)

        return accounts_list


class IbanPage(MyJsonPage):
    def set_iban(self, account):
        iban_response = self.get_content()
        account.iban = iban_response.get('iban', NotAvailable)


class LifeInsurancesPage(LoggedPage, JsonPage):

    @method
    class iter_lifeinsurances(DictElement):
        item_xpath = 'content'

        class iter_accounts(DictElement):
            item_xpath = 'avoirs/contrats'

            def get_owner(self):
                return CleanText(Dict('titulaire'))(self)

            class item(ItemElement):
                klass = Account

                obj_balance = CleanDecimal(Dict('valorisation'))
                obj_type = Account.TYPE_LIFE_INSURANCE
                obj_currency = 'EUR'
                obj__univers = Env('univers')

                def obj_id(self):
                    return Eval(str, Dict('numero'))(self)

                def obj_label(self):
                    return '%s - %s' % (CleanText(Dict('libelleProduit'))(self), self.parent.get_owner())

                def obj__parent_number(self):
                    return CleanText(Dict('cptRattachement'))(self).rstrip('0')

                # Investments are already present in this JSON,
                # so we fill the lists of Investment objects now
                class obj__investments(DictElement):
                    item_xpath = 'allocations'

                    class item(ItemElement):
                        klass = Investment

                        obj_label = CleanText(Dict('libelle'))
                        obj_valuation = CleanDecimal(Dict('montant'))

                        def obj_code_type(self):
                            if is_isin_valid(CleanText(Dict('code'))(self)):
                                return Investment.CODE_TYPE_ISIN
                            return NotAvailable

                        def obj_code(self):
                            code = CleanText(Dict('code'))(self)
                            if is_isin_valid(code):
                                return code
                            return NotAvailable


class SearchPage(LoggedPage, JsonPage):
    def get_transaction_list(self):
        result = self.doc
        if int(result['erreur']['code']) != 0:
            raise BrowserUnavailable("API sent back an error code")

        return result['content']['operations']

    def iter_history(self, account, operation_list, seen, today, coming):
        transactions = []
        for op in reversed(operation_list):
            t = Transaction()
            t.id = str(op['id'])
            if op['id'] in seen:
                raise ParseError('There are several transactions with the same ID, probably an infinite loop')

            seen.add(t.id)
            d = date.fromtimestamp(op.get('dateDebit', op.get('dateOperation'))/1000)
            op['details'] = [re.sub(r'\s+', ' ', i).replace('\x00', '') for i in op['details'] if i]  # sometimes they put "null" elements...
            label = re.sub(r'\s+', ' ', op['libelle']).replace('\x00', '')
            raw = ' '.join([label] + op['details'])
            t.rdate = date.fromtimestamp(op.get('dateOperation', op.get('dateDebit'))/1000)
            vdate = date.fromtimestamp(op.get('dateValeur', op.get('dateDebit', op.get('dateOperation')))/1000)
            t.parse(d, raw, vdate=vdate)
            t.amount = Decimal(str(op['montant']))
            if 'categorie' in op:
                t.category = op['categorie']
            t.label = label
            t._coming = op['intraday']
            if t._coming:
                # coming transactions have a random uuid id (inconsistent between requests)
                t.id = ''
            t._coming |= (t.date > today)

            if t.type == Transaction.TYPE_CARD and account.type == Account.TYPE_CARD:
                t.type = Transaction.TYPE_DEFERRED_CARD

            if abs(t.rdate.year - t.date.year) < 2:
                transactions.append(t)
            else:
                self.logger.warning(
                    'rdate(%s) and date(%s) of the transaction %s are far far away, skip it',
                    t.rdate,
                    t.date,
                    t.label
                )
        return transactions


class ProfilePage(MyJsonPage):
    def get_profile(self):
        profile = Person()

        content = self.get_content()

        profile.name = content['prenom'] + ' ' + content['nom']
        profile.address = content['adresse'] + ' ' + content['codePostal'] + ' ' + content['ville']
        profile.country = content['pays']
        profile.birth_date = parse_french_date(content['dateNaissance']).date()

        return profile


class EmailsPage(MyJsonPage):
    def set_email(self, profile):
        content = self.get_content()
        if 'emailPart' in content:
            profile.email = content['emailPart']


class ErrorPage(LoggedPage, HTMLPage):
    def on_load(self):
        if 'gestion-des-erreurs/erreur-pwd' in self.url:
            raise BrowserIncorrectPassword(CleanText('//h3')(self.doc))
        if 'gestion-des-erreurs/opposition' in self.url:
            # need a case to retrieve the error message
            raise BrowserIncorrectPassword('Votre compte a été désactivé')
        if '/pages-gestion-des-erreurs/erreur-technique' in self.url:
            errmsg = CleanText('//h4')(self.doc)
            raise BrowserUnavailable(errmsg)
        if '/pages-gestion-des-erreurs/message-tiers-oppose' in self.url:
            # need a case to retrieve the error message
            raise ActionNeeded("Impossible de se connecter au compte car l'identification en 2 étapes a été activée")


class ErrorCodePage(HTMLPage):
    def on_load(self):
        code = re.search(r'\/\?errorCode=(\d+)', self.url).group(1)
        page = self.browser.open('/particuliers/compte-bancaire/comptes-en-ligne/bredconnect-compte-ligne?errorCode=%s' % code).page
        msg = CleanText('//label[contains(@class, "error")]', default=None)(page.doc)
        # 20100: invalid login/password
        # 139: dispobank user trying to connect to Bred
        if code in ('20100', '139'):
            raise BrowserIncorrectPassword(msg)
        # 20104 & 1000: unknown error during login
        elif code in ('20104', '1000'):
            raise BrowserUnavailable(msg)

        assert False, 'Error %s is not handled yet.' % code
