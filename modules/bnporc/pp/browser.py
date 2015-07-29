# -*- coding: utf-8 -*-

# Copyright(C) 2009-2013  Romain Bignon
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


import time

from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import AccountNotFound
from weboob.tools.json import json
from weboob.exceptions import BrowserPasswordExpired

from .pages import LoginPage, AccountsPage, AccountsIBANPage, HistoryPage, TransferInitPage, ConnectionThresholdPage


__all__ = ['BNPParibasBrowser']


class CompatMixin(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass


def JSON(data):
    return ('json', data)


def isJSON(obj):
    return type(obj) is tuple and obj and obj[0] == 'json'


class JsonBrowserMixin(object):
    def open(self, *args, **kwargs):
        if isJSON(kwargs.get('data')):
            kwargs['data'] = json.dumps(kwargs['data'][1])
            if not 'headers' in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']['Content-Type'] = 'application/json'

        return super(JsonBrowserMixin, self).open(*args, **kwargs)


class BNPParibasBrowser(CompatMixin, JsonBrowserMixin, LoginBrowser):
    BASEURL_TEMPLATE = r'https://%s.bnpparibas/'
    BASEURL = BASEURL_TEMPLATE % 'mabanque'
    TIMEOUT = 30.0

    login = URL(r'identification-wspl-pres/identification\?acceptRedirection=true&timestamp=(?P<timestamp>\d+)',
                'SEEA-pa01/devServer/seeaserver',
                'https://mabanqueprivee.bnpparibas.net/fr/espace-prive/comptes-et-contrats\?u=%2FSEEA-pa01%2FdevServer%2Fseeaserver',
                LoginPage)
    con_threshold = URL(r'/fr/connexion/100-connexions', ConnectionThresholdPage)
    accounts = URL('udc-wspl/rest/getlstcpt', AccountsPage)
    ibans = URL('rib-wspl/rpc/comptes', AccountsIBANPage)
    history = URL('rop-wspl/rest/releveOp', HistoryPage)
    transfer_init = URL('virement-wspl/rest/initialisationVirement', TransferInitPage)

    class ProAccount(Exception):
        pass

    def __init__(self, *args, **kwargs):
        super(BNPParibasBrowser, self).__init__(*args, **kwargs)
        self.do_login()

    def switch(self, subdomain):
        self.BASEURL = self.BASEURL_TEMPLATE % subdomain

    def do_login(self):
        self.switch('mabanque')
        timestamp = lambda: int(time.time() * 1e3)
        self.login.go(timestamp=timestamp())
        if self.login.is_here():
            self.page.login(self.username, self.password)
        if self.con_threshold.is_here():
            raise BrowserPasswordExpired(u'Vous avez atteint le seuil de 100 connexions avec le même code secret. Par mesure de sécurité, veuillez le changer.')

    @need_login
    def get_accounts_list(self):
        ibans = self.ibans.go().get_ibans_dict()
        ibans.update(self.transfer_init.go(data=JSON({'restitutionVF': 1, 'type': 'TOUS'})).get_ibans_dict())

        self.accounts.go().iter_accounts(ibans)
        return self.page.iter_accounts(ibans)

    @need_login
    def get_account(self, _id):
        return find_object(self.get_accounts_list(), id=_id, error=AccountNotFound)

    @need_login
    def iter_history(self, account, coming=False):
        self.page = self.history.go(data=JSON({
            "ibanCrypte": account.id,
            "pastOrPending": 1,
            "triAV": 0,
            "startDate": None,
            "endDate": None
        }))
        return self.page.iter_coming() if coming else self.page.iter_history()

    @need_login
    def iter_coming_operations(self, account):
        return self.iter_history(account, coming=True)

    @need_login
    def iter_investment(self, account):
        raise NotImplementedError()

    @need_login
    def get_transfer_accounts(self):
        raise NotImplementedError()

    @need_login
    def transfer(self, account, to, amount, reason):
        raise NotImplementedError()

    @need_login
    def iter_threads(self):
        raise NotImplementedError()

    @need_login
    def get_thread(self, thread):
        raise NotImplementedError()
