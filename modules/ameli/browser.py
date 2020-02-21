# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
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

from datetime import date
from time import time
from dateutil.relativedelta import relativedelta

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import ActionNeeded

from .pages import ErrorPage, LoginPage, RedirectPage, CguPage, SubscriptionPage, DocumentsPage


class AmeliBrowser(LoginBrowser):
    BASEURL = 'https://assure.ameli.fr'

    error_page = URL(r'/vu/INDISPO_COMPTE_ASSURES.html', ErrorPage)
    login_page = URL(r'/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&connexioncompte_2actionEvt=afficher.*', LoginPage)
    redirect_page = URL(r'/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&.*validationconnexioncompte.*', RedirectPage)
    cgu_page = URL(r'/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&_pageLabel=as_conditions_generales_page.*', CguPage)
    subscription_page = URL(r'/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&_pageLabel=as_info_perso_page.*', SubscriptionPage)
    documents_page = URL(r'/PortailAS/paiements.do', DocumentsPage)

    def do_login(self):
        self.login_page.go()
        self.page.login(self.username, self.password)

        if self.cgu_page.is_here():
            raise ActionNeeded(self.page.get_cgu_message())

    @need_login
    def iter_subscription(self):
        self.subscription_page.go()
        yield self.page.get_subscription()

    @need_login
    def iter_documents(self, subscription):
        end_date = date.today()

        start_date = end_date - relativedelta(years=1)
        # FUN FACT, website tell us documents are available for 6 months
        # let's suppose today is 28/05/19, website frontend limit DateDebut to 28/11/18 but we can get a little bit more
        # by setting a previous date and get documents that are no longer available for simple user

        params = {
            'Beneficiaire': 'tout_selectionner',
            'DateDebut': start_date.strftime('%d/%m/%Y'),
            'DateFin': end_date.strftime('%d/%m/%Y'),
            'actionEvt': 'afficherPaiementsComplementaires',
            'afficherIJ': 'false',
            'afficherInva': 'false',
            'afficherPT': 'false',
            'afficherRS': 'false',
            'afficherReleves': 'false',
            'afficherRentes': 'false',
            'idNoCache': int(time()*1000)
        }

        # the second request is stateful
        # first value of actionEvt is afficherPaiementsComplementaires to get all payments from last 6 months
        # (start_date 6 months in the past is needed but not enough)
        self.documents_page.go(params=params)

        # then we set Rechercher to actionEvt to filter for this subscription, within last 6 months
        # without first request we would have filter for this subscription but within last 2 months
        params['actionEvt'] = 'Rechercher'
        params['Beneficiaire'] = 'tout_selectionner'
        self.documents_page.go(params=params)
        return self.page.iter_documents(subid=subscription.id)
