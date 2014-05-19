# -*- coding: utf-8 -*-

# Copyright(C) 2012 Johann Broudin
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

from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.capabilities.bank import Account, Transaction
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.base import NotAvailable
from weboob.tools.exceptions import BrowserIncorrectPassword, ParseError
from weboob.tools.browser2 import BaseBrowser

from re import match, compile, sub
from decimal import Decimal
from lxml import etree
from datetime import date
from StringIO import StringIO



__all__ = ['CmbBackend']


class CmbBackend(BaseBackend, ICapBank):
    NAME = 'cmb'
    MAINTAINER = u'Johann Broudin'
    EMAIL = 'Johann.Broudin@6-8.fr'
    VERSION = '0.j'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Crédit Mutuel de Bretagne'
    CONFIG = BackendConfig(
            ValueBackendPassword('login', label='Identifiant', masked=False),
            ValueBackendPassword('password', label='Mot de passe', masked=True))
    LABEL_PATTERNS = [
            (   # card
                compile('^CARTE (?P<text>.*)'),
                Transaction.TYPE_CARD,
                '%(text)s'
            ),
            (   # order
                compile('^PRLV (?P<text>.*)'),
                Transaction.TYPE_ORDER,
                '%(text)s'
            ),
            (   # withdrawal
                compile('^RET DAB (?P<text>.*)'),
                Transaction.TYPE_WITHDRAWAL,
                '%(text)s'
            ),
            (   # loan payment
                compile('^ECH (?P<text>.*)'),
                Transaction.TYPE_LOAN_PAYMENT,
                '%(text)s'
            ),
            (   # transfer
                compile('^VIR (?P<text>.*)'),
                Transaction.TYPE_TRANSFER,
                '%(text)s'
            ),
            (   # payback
                compile('^ANN (?P<text>.*)'),
                Transaction.TYPE_PAYBACK,
                '%(text)s'
            ),
            (   # bank
                compile('^F (?P<text>.*)'),
                Transaction.TYPE_BANK,
                '%(text)s'
            )
            ]

    BROWSER = BaseBrowser
    islogged = False

    def login(self):
        data = {
            'codeEspace': 'NO',
            'codeEFS': '01',
            'codeSi': '001',
            'noPersonne': self.config['login'].get(),
            'motDePasse': self.config['password'].get()
            }

        response = self.browser.open("https://www.cmb.fr/domiweb/servlet/Identification", allow_redirects=False, data=data)

        if response.status_code == 302:
          self.islogged=True
          return True
        else:
            raise BrowserIncorrectPassword()
        return False

    def iter_accounts(self):
        if not self.islogged:
            self.login()

        data = self.browser.open("https://www.cmb.fr/domiweb/prive/particulier/releve/0-releve.act").content
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(data), parser)

        table = tree.xpath('/html/body/table')
        if len(table) == 0:
            title = tree.xpath('/html/head/title')[0].text
            if title == u"Utilisateur non identifié":
                self.login()
                data = self.browser.open("https://www.cmb.fr/domiweb/prive/particulier/releve/0-releve.act").content

                parser = etree.HTMLParser()
                tree = etree.parse(StringIO(data), parser)
                table = tree.xpath('/html/body/table')
                if len(table) == 0:
                    raise ParseError()
            else:
                raise ParseError()

        for tr in tree.xpath('/html/body//table[contains(@class, "Tb")]/tr'):
            if tr.get('class', None) not in ('LnTit', 'LnTot', 'LnMnTiers', None):
                account = Account()
                td = tr.xpath('td')

                a = td[1].xpath('a')
                account.label = unicode(a[0].text).strip()
                href = a[0].get('href')
                m = match(r"javascript:releve\((.*),'(.*)','(.*)'\)",
                             href)
                if not m:
                    continue
                account.id = unicode(m.group(1) + m.group(2) + m.group(3))
                account._cmbvaleur = m.group(1)
                account._cmbvaleur2 = m.group(2)
                account._cmbtype = m.group(3)

                balance = u''.join([txt.strip() for txt in td[2].itertext()])
                balance = balance.replace(',', '.').replace(u"\xa0", '')
                account.balance = Decimal(balance)

                span = td[4].xpath('a/span')
                if len(span):
                    coming = span[0].text.replace(' ', '').replace(',', '.')
                    coming = coming.replace(u"\xa0", '')
                    account.coming = Decimal(coming)
                else:
                    account.coming = NotAvailable

                yield account

    def get_account(self, _id):
        for account in self.iter_accounts():
            if account.id == _id:
                return account

        raise AccountNotFound()

    def iter_history(self, account):
        if not self.islogged:
            self.login()

        page = "https://www.cmb.fr/domiweb/prive/particulier/releve/"
        if account._cmbtype == 'D':
            page += "10-releve.act"
        else:
            page += "2-releve.act"
        page +="?noPageReleve=1&indiceCompte="
        page += account._cmbvaleur
        page += "&typeCompte="
        page += account._cmbvaleur2
        page += "&deviseOrigineEcran=EUR"

        data = self.browser.open(page).content
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(data), parser)

        tables = tree.xpath('/html/body/table')
        if len(tables) == 0:
            title = tree.xpath('/html/head/title')[0].text
            if title == u"Utilisateur non identifié":
                self.login()
                data = self.browser.open(page).content

                parser = etree.HTMLParser()
                tree = etree.parse(StringIO(data), parser)
                tables = tree.xpath('/html/body/table')
                if len(tables) == 0:
                    raise ParseError()
            else:
                raise ParseError()

        i = 0

        for table in tables:
            if table.get('id') != "tableMouvements":
                continue
            for tr in table.getiterator('tr'):
                if (tr.get('class') != 'LnTit' and
                        tr.get('class') != 'LnTot'):
                    operation = Transaction(i)
                    td = tr.xpath('td')

                    div = td[1].xpath('div')
                    d = div[0].text.split('/')
                    operation.date = date(*reversed([int(x) for x in d]))

                    div = td[2].xpath('div')
                    label = div[0].xpath('a')[0].text.replace('\n', '')
                    operation.raw = unicode(' '.join(label.split()))
                    for pattern, _type, _label in self.LABEL_PATTERNS:
                        mm = pattern.match(operation.raw)
                        if mm:
                            operation.type = _type
                            operation.label = sub('[ ]+', ' ',
                                    _label % mm.groupdict()).strip()
                            break

                    amount = td[3].text
                    if amount.count(',') != 1:
                        amount = td[4].text
                        amount = amount.replace(',', '.').replace(u'\xa0', '')
                        operation.amount = Decimal(amount)
                    else:
                        amount = amount.replace(',', '.').replace(u'\xa0', '')
                        operation.amount = - Decimal(amount)

                    i += 1
                    yield operation
