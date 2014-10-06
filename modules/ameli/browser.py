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

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.capabilities.bill import Detail
from decimal import Decimal
from .pages import LoginPage, HomePage, AccountPage, LastPaymentsPage, PaymentDetailsPage, BillsPage

__all__ = ['AmeliBrowser']


class AmeliBrowser(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'assure.ameli.fr'
    ENCODING = None

    PAGES = {'.*_pageLabel=as_login_page.*': LoginPage,
             '.*_pageLabel=as_accueil_page.*': HomePage,
             '.*_pageLabel=as_etat_civil_page.*': AccountPage,
             '.*_pageLabel=as_revele_mensuel_presta_page.*': BillsPage,
             '.*_pageLabel=as_dernier_paiement_page': LastPaymentsPage,
             '.*_actionOverride=%2Fportlets%2Fpaiements%2Fdetailpaiements&paiements.*': PaymentDetailsPage
             }

    loginp = '/PortailAS/appmanager/PortailAS/assure?_somtc=true&_pageLabel=as_login_page'
    homep = '/PortailAS/appmanager/PortailAS/assure?_nfpb=true&_pageLabel=as_accueil_page'
    accountp = '/PortailAS/appmanager/PortailAS/assure?_nfpb=true&_pageLabel=as_etat_civil_page'
    billsp = '/PortailAS/appmanager/PortailAS/assure?_nfpb=true&_pageLabel=as_revele_mensuel_presta_page'
    lastpaymentsp = '/PortailAS/appmanager/PortailAS/assure?_nfpb=true&_pageLabel=as_dernier_paiement_page'

    is_logging = False

    def home(self):
        self.logger.debug('call Browser.home')
        self.location(self.homep)
        if ((not self.is_logged()) and (not self.is_logging)):
            self.login()

    def is_logged(self):
        self.logger.debug('call Browser.is_logged')
        return self.page.is_logged()

    def login(self):
        self.logger.debug('call Browser.login')
        # Do we really need to login?
        if self.is_logged():
            self.logger.debug('Already logged in')
            return

        if self.is_logging:
            return

        self.is_logging = True

        self.location(self.loginp)
        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

        self.is_logging = False

    def iter_subscription_list(self):
        if not self.is_on_page(AccountPage):
            self.location(self.accountp)
        return self.page.iter_subscription_list()

    def get_subscription(self, id):
        assert isinstance(id, basestring)
        for sub in self.iter_subscription_list():
            if id == sub._id:
                return sub
        return None

    def iter_history(self, sub):
        if not self.is_on_page(LastPaymentsPage):
            self.location(self.lastpaymentsp)
        urls = self.page.iter_last_payments()
        for url in urls:
            self.location(url)
            assert self.is_on_page(PaymentDetailsPage)
            for payment in self.page.iter_payment_details(sub):
                yield payment

    def iter_details(self, sub):
        det = Detail()
        det.id = sub.id
        det.label = sub.label
        det.infos = ''
        det.price = Decimal('0.0')
        yield det

    def iter_bills(self, sub):
        if not sub._id.isdigit():
            return []
        if not self.is_on_page(BillsPage):
            self.location(self.billsp)
            return self.page.iter_bills(sub)

    def get_bill(self, id):
        assert isinstance(id, basestring)
        subs = self.iter_subscription_list()
        for sub in subs:
            for b in self.iter_bills(sub):
                if id == b.id:
                    return b
