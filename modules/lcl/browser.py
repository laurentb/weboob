# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Romain Bignon, Pierre Mazière
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


import urllib
from urlparse import urlsplit, parse_qsl

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.bank import Account

from .pages import LoginPage, AccountsPage, AccountHistoryPage, \
                   CBListPage, CBHistoryPage, ContractsPage, BoursePage, \
                   AVPage, AVDetailPage, DiscPage, NoPermissionPage, RibPage, \
                   HomePage


__all__ = ['LCLBrowser','LCLProBrowser']


# Browser
class LCLBrowser(LoginBrowser):
    BASEURL = 'https://particuliers.secure.lcl.fr'

    login = URL('/outil/UAUT/Authentication/authenticate',
                '/outil/UAUT\?from=.*',
                '/outil/UWER/Accueil/majicER',
                '/outil/UWER/Enregistrement/forwardAcc',
                LoginPage)
    contracts = URL('/outil/UAUT/Contrat/choixContrat.*',
                    '/outil/UAUT/Contract/getContract.*',
                    '/outil/UAUT/Contract/selectContracts.*',
                    '/outil/UAUT/Accueil/preRoutageLogin',
                    '.*outil/UAUT/Contract/routing',
                    ContractsPage)
    home = URL('/outil/UWHO/Accueil/', HomePage)
    accounts = URL('/outil/UWSP/Synthese', AccountsPage)
    history = URL('/outil/UWLM/ListeMouvements.*/accesListeMouvements.*',
                  '/outil/UWLM/DetailMouvement.*/accesDetailMouvement.*',
                  '/outil/UWLM/Rebond',
                  AccountHistoryPage)
    rib = URL('/outil/UWRI/Accueil/detailRib',
              '/outil/UWRI/Accueil/listeRib', RibPage)
    cb_list = URL('/outil/UWCB/UWCBEncours.*/listeCBCompte.*', CBListPage)
    cb_history = URL('/outil/UWCB/UWCBEncours.*/listeOperations.*', CBHistoryPage)
    skip = URL('/outil/UAUT/Contrat/selectionnerContrat.*',
               '/index.html')
    no_perm = URL('/outil/UAUT/SansDroit/affichePageSansDroit.*', NoPermissionPage)

    bourse = URL('https://bourse.secure.lcl.fr/netfinca-titres/servlet/com.netfinca.frontcr.synthesis.HomeSynthesis',
                 'https://bourse.secure.lcl.fr/netfinca-titres/servlet/com.netfinca.frontcr.account.*',
                 '/outil/UWBO.*', BoursePage)
    disc = URL('https://bourse.secure.lcl.fr/netfinca-titres/servlet/com.netfinca.frontcr.login.ContextTransferDisconnect',
               '/outil/UAUT/RetourPartenaire/retourCar', DiscPage)

    assurancevie = URL('/outil/UWVI/AssuranceVie/accesSynthese', AVPage)
    avdetail = URL('https://ASSURANCE-VIE-et-prevoyance.secure.lcl.fr.*',
                   'https://assurance-vie-et-prevoyance.secure.lcl.fr.*',
                   '/outil/UWVI/Routage', AVDetailPage)

    TIMEOUT = 30.0

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        # we force the browser to go to login page so it's work even
        # if the session expire
        self.login.go()

        if not self.page.login(self.username, self.password) or \
           (self.login.is_here() and self.page.is_error()) :
            raise BrowserIncorrectPassword("invalid login/password.\nIf you did not change anything, be sure to check for password renewal request\non the original web site.\nAutomatic renewal will be implemented later.")

        self.accounts.stay_or_go()

    @need_login
    def connexion_bourse(self):
        self.location('/outil/UWBO/AccesBourse/temporisationCar?codeTicker=TICKERBOURSECLI')
        if self.no_perm.is_here():
            return False
        self.location(self.page.get_next())
        self.bourse.stay_or_go()
        return True

    def deconnexion_bourse(self):
        self.disc.stay_or_go()
        self.page.come_back()
        self.page.come_back()

    @need_login
    def get_accounts_list(self):
        self.assurancevie.stay_or_go()
        if self.no_perm.is_here():
            self.logger.warning('Life insurances are unavailable.')
        else:
            for a in self.page.get_list():
                yield a
        self.accounts.stay_or_go()
        accounts = list()
        for acc in self.page.get_list():
            self.location('/outil/UWRI/Accueil/')
            self.rib.go(data={'compte': '%s/%s/%s' % (acc.id[0:5],acc.id[5:11],acc.id[11:])})
            if self.rib.is_here():
                acc.iban = self.page.get_iban()
            accounts.append(acc)

        if self.connexion_bourse():
            acc = list(self.page.populate(accounts))
            self.deconnexion_bourse()
            # Disconnecting from bourse portal before returning account list
            # to be sure that we are on the banque portal
            for a in acc:
                yield a
        else:
            for a in accounts:
                yield a

    @need_login
    def get_history(self, account):
        if not account._link_id:
            return
        self.location(account._link_id)
        for tr in self.page.get_operations():
            yield tr

        for tr in self.get_cb_operations(account, 1):
            yield tr

    @need_login
    def get_cb_operations(self, account, month=0):
        """
        Get CB operations.

        * month=0 : current operations (non debited)
        * month=1 : previous month operations (debited)
        """
        for link in account._coming_links:
            v = urlsplit(self.absurl(link))
            args = dict(parse_qsl(v.query))
            args['MOIS'] = month

            self.location('%s?%s' % (v.path, urllib.urlencode(args)))

            for tr in self.page.get_operations():
                yield tr

            for card_link in self.page.get_cards():
                self.location(card_link)
                for tr in self.page.get_operations():
                    yield tr

    def disc_from_AV_investment_detail(self):
        self.page.come_back()
        self.page.sub()
        self.page.come_back()

    @need_login
    def get_investment(self, account):
        if account.type == Account.TYPE_LIFE_INSURANCE and account._form:
            self.assurancevie.stay_or_go()
            account._form.submit()
            self.page.sub()
            self.page.sub()
            for inv in self.page.iter_investment():
                yield inv
            self.disc_from_AV_investment_detail()
        elif account._market_link:
            self.connexion_bourse()
            self.location(account._market_link)
            for inv in self.page.iter_investment():
                yield inv
            self.deconnexion_bourse()


class LCLProBrowser(LCLBrowser):
    BASEURL = 'https://professionnels.secure.lcl.fr'

    #We need to add this on the login form
    IDENTIFIANT_ROUTING = 'CLA'

    def __init__(self, *args, **kwargs):
        super(LCLProBrowser, self).__init__(*args, **kwargs)
        self.session.cookies.set("lclgen","professionnels")
