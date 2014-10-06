# -*- coding: utf-8 -*-

# Copyright(C) 2013      Christophe Lampin
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
from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.capabilities.bill import Detail
from decimal import Decimal
from .pages import LoginPage, HomePage, AccountPage, HistoryPage, BillsPage

__all__ = ['AmeliProBrowser']


class AmeliProBrowser(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'espacepro.ameli.fr'
    ENCODING = None

    PAGES = {'.*_pageLabel=vp_login_page.*':  LoginPage,
             '.*_pageLabel=vp_accueil.*': HomePage,
             '.*_pageLabel=vp_coordonnees_infos_perso_page.*': AccountPage,
             '.*_pageLabel=vp_recherche_par_date_paiements_page.*': HistoryPage,
             '.*_pageLabel=vp_releves_mensuels_page.*': BillsPage,
             }

    loginp = '/PortailPS/appmanager/portailps/professionnelsante?_nfpb=true&_pageLabel=vp_login_page'
    homep = '/PortailPS/appmanager/portailps/professionnelsante?_nfpb=true&_pageLabel=vp_accueil_book'
    accountp = '/PortailPS/appmanager/portailps/professionnelsante?_nfpb=true&_pageLabel=vp_coordonnees_infos_perso_page'
    billsp = '/PortailPS/appmanager/portailps/professionnelsante?_nfpb=true&_pageLabel=vp_releves_mensuels_page'
    searchp = '/PortailPS/appmanager/portailps/professionnelsante?_nfpb=true&_pageLabel=vp_recherche_par_date_paiements_page'
    historyp = '/PortailPS/appmanager/portailps/professionnelsante?_nfpb=true&_windowLabel=vp_recherche_paiement_tiers_payant_portlet_1&vp_recherche_paiement_tiers_payant_portlet_1_actionOverride=%2Fportlets%2Fpaiements%2Frecherche&_pageLabel=vp_recherche_par_date_paiements_page'

    def home(self):
        self.location(self.homep)

    def is_logged(self):
        if self.is_on_page(LoginPage):
            return False
        return True

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        if not self.is_on_page(LoginPage):
            self.location(self.loginp)
        self.page.login(self.username, self.password)
        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def get_subscription_list(self):
        if not self.is_on_page(AccountPage):
            self.location(self.accountp)
        return self.page.get_subscription_list()

    def get_subscription(self, id):
        assert isinstance(id, basestring)
        return self.get_subscription_list()

    def iter_history(self, subscription):
        if not self.is_on_page(HistoryPage):
            self.location(self.searchp)

        date_deb = self.page.document.xpath('//input[@name="vp_recherche_paiement_tiers_payant_portlet_1dateDebutRecherche"]')[0].value
        date_fin = self.page.document.xpath('//input[@name="vp_recherche_paiement_tiers_payant_portlet_1dateFinRecherche"]')[0].value

        data = {'vp_recherche_paiement_tiers_payant_portlet_1dateDebutRecherche': date_deb,
                'vp_recherche_paiement_tiers_payant_portlet_1dateFinRecherche': date_fin,
                'vp_recherche_paiement_tiers_payant_portlet_1codeOrganisme': 'null',
                'vp_recherche_paiement_tiers_payant_portlet_1actionEvt': 'rechercheParDate',
                'vp_recherche_paiement_tiers_payant_portlet_1codeRegime': '01',
               }

        self.location(self.historyp, urllib.urlencode(data))
        return self.page.iter_history()

    def get_details(self, sub):
        det = Detail()
        det.id = sub.id
        det.label = sub.label
        det.infos = ''
        det.price = Decimal('0.0')
        return det

    def iter_bills(self):
        if not self.is_on_page(BillsPage):
            self.location(self.billsp)
        return self.page.iter_bills()

    def get_bill(self, id):
        assert isinstance(id, basestring)
        for b in self.iter_bills():
            if id == b.id:
                return b
        return None
