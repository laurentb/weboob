# -*- coding: utf-8 -*-

# Copyright(C) 2015 Christophe Lampin
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
from decimal import Decimal

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.profiles import Android
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Account, Transaction

from .pages import LoginPage, CalcPage, ProfilPage, AccountsPage, HistoryPage, I18nPage

__all__ = ['Esalia']


class S2eBrowser(LoginBrowser):

    PROFILE = Android()
    CTCC = ""
    LANG = "FR"

    sessionId = None

    loginp = URL('/$', LoginPage)
    calcp = URL('/s2e_services/restServices/calculetteService/grillemdp\?uuid=(?P<uuid>)', CalcPage)
    profilp = URL('/s2e_services/restServices/authentification/loginS', ProfilPage)
    accountsp = URL('/s2e_services/restServices/situationCompte', AccountsPage)
    historyp = URL('/s2e_services/restServices/listeOperation', HistoryPage)
    i18np = URL('/(?P<lang1>.*)/LANG/(?P<lang2>.*).json', I18nPage)

    def __init__(self, url, username, password, *args, **kwargs):
        super(S2eBrowser, self).__init__(username, password, *args, **kwargs)
        self.BASEURL = "https://" + url

    def do_login(self):
        self.logger.debug('call Browser.do_login')
        self.loginp.stay_or_go()
        self.page.login(self.username, self.password)
        if self.sessionId is None:
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        data = {'clang': self.LANG,
                'ctcc': self.CTCC,
                'login': self.username,
                'session': self.sessionId}

        for k, fond in self.accountsp.open(data=data).get_list().items():
            a = Account()
            a.id = k
            a.type = Account.TYPE_LOAN
            a.balance = Decimal(fond["montantValeurEuro"]).quantize(Decimal('.01'))
            a.label = fond["libelleSupport"]
            a.currency = u"EUR"  # Don't find any possbility to get that from configuration.
            yield a

    @need_login
    def iter_history(self, account):
        # Load i18n for type translation
        self.i18np.open(lang1=self.LANG, lang2=self.LANG).load_i18n()

        # For now detail for each account is not available. History is global for all accounts and very simplist
        data = {'clang': self.LANG,
                'ctcc': self.CTCC,
                'login': self.username,
                'session': self.sessionId}

        for trans in self.historyp.open(data=data).get_transactions():
            t = Transaction()
            t.id = trans["referenceOperationIndividuelle"]
            t.date = datetime.strptime(trans["dateHeureSaisie"], "%d/%m/%Y")
            t.rdate = datetime.strptime(trans["dateHeureSaisie"], "%d/%m/%Y")
            t.type = Transaction.TYPE_DEPOSIT if trans["montantNetEuro"] > 0 else Transaction.TYPE_PAYBACK
            t.raw = trans["typeOperation"]
            t.label = self.i18n["OPERATION_TYPE_" + trans["casDeGestion"]]
            t.amount = Decimal(trans["montantNetEuro"]).quantize(Decimal('.01'))
            yield t


class Esalia(S2eBrowser):
    CTCC = "SG"
    loginp = URL('/Esalia/$', LoginPage)
    i18np = URL('/Esalia/SG/(?P<lang1>.*)/LANG/(?P<lang2>.*).json', I18nPage)


class Capeasi(S2eBrowser):
    CTCC = "AXA"
    loginp = URL('/AXA/$', LoginPage)
    i18np = URL('/AXA/(?P<lang1>.*)/LANG/(?P<lang2>.*).json', I18nPage)


class EREHSBC(S2eBrowser):
    CTCC = "HSBC"
    loginp = URL('/ERE-HSBC/$', LoginPage)
    i18np = URL('/ERE-HSBC/HSBC/(?P<lang1>.*)/LANG/(?P<lang2>.*).json', I18nPage)


class CreditNord(S2eBrowser):
    CTCC = ""   # FIXME : Not Available Yet
    loginp = URL('//$', LoginPage)
    # Hack : Lang.json of BNPERE is only available in app. Get it from Esalia
    i18np = URL('https://m.esalia.com/Esalia/SG/(?P<lang1>.*)/LANG/(?P<lang2>.*).json', I18nPage)


class BNPPERE(S2eBrowser):
    CTCC = "BNP"
    loginp = URL('/$', LoginPage)
    # Hack : Lang.json of BNPERE is only available in app. Get it from Esalia
    i18np = URL('https://m.esalia.com/Esalia/SG/(?P<lang1>.*)/LANG/(?P<lang2>.*).json', I18nPage)
