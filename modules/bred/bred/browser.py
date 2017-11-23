# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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

import json
import re
import time
from datetime import date
from decimal import Decimal

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction, sorted_transactions
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, ActionNeeded, ParseError
from weboob.browser import DomainBrowser

__all__ = ['BredBrowser']


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^.*Virement (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(u'PRELEV SEPA (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile(u'.*Prélèvement.*'),        FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^(REGL|Rgt)(?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>.*) Carte \d+\s+ LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile(u'^Débit mensuel.*'), FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile(u"^Retrait d'espèces à un DAB (?P<text>.*) CARTE [X\d]+ LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})"),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^Paiement de chèque (?P<text>.*)'),  FrenchTransaction.TYPE_CHECK),
                (re.compile(u'^(Cotisation|Intérêts) (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile(u'^(Remise Chèque|Remise de chèque)\s*(?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^Versement (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class BredBrowser(DomainBrowser):
    BASEURL = 'https://www.bred.fr'

    def __init__(self, accnum, login, password, *args, **kwargs):
        super(BredBrowser, self).__init__(*args, **kwargs)
        self.login = login
        # Bred only use first 8 char (even if the password is set to be bigger)
        # The js login form remove after 8th char. No comment.
        self.password = password[:8]
        self.accnum = accnum
        self.universes = None
        self.current_univers = None

    def do_post_auth(self):
        if 'hsess' not in self.session.cookies:
            self.location('/')  # set session token
            assert 'hsess' in self.session.cookies, "Session token not correctly set"

        # hard-coded authentication payload
        data = dict(identifiant=self.login, password=self.password)
        cookies = {k: v for k, v in self.session.cookies.items() if k in ('hsess', )}
        return self.open('https://www.bred.fr/transactionnel/Authentication', data=data, cookies=cookies)

    def do_login(self):
        r = self.do_post_auth()
        if 'gestion-des-erreurs/erreur-pwd' in r.url:
            raise BrowserIncorrectPassword('Bad login/password.')
        if 'gestion-des-erreurs/opposition' in r.url:
            raise BrowserIncorrectPassword('Your account is disabled')
        if '/pages-gestion-des-erreurs/erreur-technique' in r.url:
            errmsg = re.search(r'<h4>(.*)</h4>', r.text).group(1)
            raise BrowserUnavailable(errmsg)
        if '/pages-gestion-des-erreurs/message-tiers-oppose' in r.url:
            raise ActionNeeded('Cannot connect to account because 2-factor authentication is enabled')

    ACCOUNT_TYPES = {'000': Account.TYPE_CHECKING,
                     '999': Account.TYPE_MARKET,
                     '011': Account.TYPE_CARD,
                     '023': Account.TYPE_SAVINGS,
                     '078': Account.TYPE_SAVINGS,
                     '080': Account.TYPE_SAVINGS,
                     '027': Account.TYPE_SAVINGS,
                     '037': Account.TYPE_SAVINGS,
                     '730': Account.TYPE_DEPOSIT,
                    }

    def get_universes(self):
        """Get universes (particulier, pro, etc)"""

        self.do_login()
        self.get_and_update_bred_token()
        universe_data = self.open(
            '/transactionnel/services/applications/menu/getMenuUnivers',
            headers={'Accept': 'application/json'}
        ).json().get('content', {})

        universes = {}
        universes[universe_data['universKey']] = universe_data['title']
        for universe in universe_data.get('menus', {}):
            universes[universe['universKey']] = universe['title']

        return universes

    def get_and_update_bred_token(self):
        timestamp = int(time.time() * 1000)
        x_token_bred = self.location('/transactionnel/services/rest/User/nonce?random={}'.format(timestamp)).json()['content']
        self.session.headers.update({'X-Token-Bred': x_token_bred, })  # update headers for session
        return {'X-Token-Bred': x_token_bred, }

    def move_to_univers(self, univers):
        if univers == self.current_univers:
            return
        self.open('/transactionnel/services/applications/listes/{key}/default'.format(key=univers))
        self.get_and_update_bred_token()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.open(
            '/transactionnel/services/rest/User/switch',
            data=json.dumps({'all': 'false', 'univers': univers}),
            headers=headers,
        )
        self.current_univers = univers

    def get_accounts_list(self):
        accounts = []
        for universe_key in self.get_universes():
            self.move_to_univers(universe_key)
            accounts.extend(self.get_list())
            accounts.extend(self.get_loans_list())

        return sorted(accounts, key=lambda x: x._univers)

    def get_loans_list(self):
        call_response = self.location('/transactionnel/services/applications/prets/liste').json().get('content', [])

        for content in call_response:
            a = Account()
            a.id = "%s.%s" % (content['comptePrets'].strip(), content['numeroDossier'].strip())
            a.type = Account.TYPE_LOAN
            a.label = ' '.join([content['intitule'].strip(), content['libellePrets'].strip()])
            a.balance = -Decimal(str(content['montantCapitalDu']['valeur']))
            a.currency = content['montantCapitalDu']['monnaie']['code'].strip()
            a._univers = self.current_univers
            yield a

    def get_list(self):
        call_response = self.location(
            '/transactionnel/services/rest/Account/accounts'
        ).json().get('content', [])
        seen = set()

        for content in call_response:
            if self.accnum != '00000000000' and content['numero'] != self.accnum:
                continue
            for poste in content['postes']:
                a = Account()
                a._number = content['numeroLong']
                a._nature = poste['codeNature']
                a._codeSousPoste = poste['codeSousPoste'] if 'codeSousPoste' in poste else None
                a._consultable = poste['consultable']
                a._univers = self.current_univers
                a.id = '%s.%s' % (a._number, a._nature)

                if a.id in seen:
                    # some accounts like "compte à terme fidélis" have the same _number and _nature
                    # but in fact are kind of closed, so worthless...
                    self.logger.warning('ignored account id %r (%r) because it is already used', a.id, poste.get('numeroDossier'))
                    continue

                seen.add(a.id)

                a.type = self.ACCOUNT_TYPES.get(poste['codeNature'], Account.TYPE_UNKNOWN)
                if a.type == Account.TYPE_CHECKING:
                    iban_response = self.location(
                        '/transactionnel/services/rest/Account/account/%s/iban' % a._number
                    ).json().get('content', {})
                    a.iban = iban_response.get('iban', NotAvailable)
                else:
                    a.iban = NotAvailable

                if 'numeroDossier' in poste and poste['numeroDossier']:
                    a._file_number = poste['numeroDossier']
                    a.id += '.%s' % a._file_number

                if poste['postePortefeuille']:
                    a.label = u'Portefeuille Titres'
                    a.balance = Decimal(str(poste['montantTitres']['valeur']))
                    a.currency = poste['montantTitres']['monnaie']['code'].strip()
                    if not a.balance and not a.currency and 'dateTitres' not in poste:
                        continue
                    yield a

                if 'libelle' not in poste:
                    continue

                a.label = ' '.join([content['intitule'].strip(), poste['libelle'].strip()])
                a.balance = Decimal(str(poste['solde']['valeur']))
                a.currency = poste['solde']['monnaie']['code'].strip()
                # Some accounts may have balance currency
                if 'Solde en devises' in a.label and a.currency != u'EUR':
                    a.id += str(poste['monnaie']['codeSwift'])
                yield a

    def _make_api_call(self, account, start_date, end_date, offset, max_length=50):
        HEADERS = {
            'Accept': "application/json",
            'Content-Type': 'application/json',
        }
        HEADERS.update(self.get_and_update_bred_token())
        call_payload = {
            "account": account._number,
            "poste": account._nature,
            "sousPoste": account._codeSousPoste or '00',
            "devise": account.currency,
            "fromDate": start_date.strftime('%Y-%m-%d'),
            "toDate": end_date.strftime('%Y-%m-%d'),
            "from": offset,
            "size": max_length,  # max length of transactions
            "search": "",
            "categorie": "",
        }
        result = self.open('/transactionnel/services/applications/operations/getSearch/', data=json.dumps(call_payload), headers=HEADERS, ).json()

        if int(result['erreur']['code']) != 0:
            raise BrowserUnavailable("API sent back an error code")

        transaction_list = result['content']['operations']
        return transaction_list

    def get_history(self, account, coming=False):
        if account.type is Account.TYPE_LOAN or not account._consultable:
            raise NotImplementedError()

        if account._univers != self.current_univers:
            self.move_to_univers(account._univers)

        today = date.today()
        seen = set()
        offset = 0
        next_page = True
        while next_page:
            operation_list = self._make_api_call(
                account=account,
                start_date=date(day=1, month=1, year=2000), end_date=date.today(),
                offset=offset, max_length=50,
            )
            transactions = []
            for op in reversed(operation_list):
                t = Transaction()
                t.id = op['id']
                if op['id'] in seen:
                    raise ParseError('There are several transactions with the same ID, probably an infinite loop')

                seen.add(t.id)
                d = date.fromtimestamp(op.get('dateDebit', op.get('dateOperation'))/1000)
                op['details'] = [re.sub('\s+', ' ', i).replace('\x00', '') for i in op['details'] if i]  # sometimes they put "null" elements...
                label = re.sub('\s+', ' ', op['libelle']).replace('\x00', '')
                raw = ' '.join([label] + op['details'])
                vdate = date.fromtimestamp(op.get('dateValeur', op.get('dateDebit', op.get('dateOperation')))/1000)
                t.parse(d, raw, vdate=vdate)
                t.amount = Decimal(str(op['montant']))
                t.rdate = date.fromtimestamp(op.get('dateOperation', op.get('dateDebit'))/1000)
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

                transactions.append(t)

            # Transactions are unsorted
            for t in sorted_transactions(transactions):
                if coming == t._coming:
                    yield t
                elif coming and not t._coming:
                    # coming transactions are at the top of history
                    self.logger.debug('stopping coming after %s', t)
                    return

            next_page = bool(transactions)
            offset += 50

            assert offset < 30000, 'the site may be doing an infinite loop'
