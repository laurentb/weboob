# -*- coding: utf-8 -*-

# Copyright(C) 2013-2015      Christophe Lampin
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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bill import Detail
from decimal import Decimal
from .pages import LoginPage, HomePage, AccountPage, LastPaymentsPage, PaymentDetailsPage, BillsPage

__all__ = ['AmeliBrowser']


class AmeliBrowser(LoginBrowser):
    BASEURL = 'https://assure.ameli.fr'

    loginp = URL('/PortailAS/appmanager/PortailAS/assure\?.*_pageLabel=as_login_page', LoginPage)
    homep = URL('/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&_pageLabel=as_accueil_page', HomePage)
    accountp = URL('/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&_pageLabel=as_info_perso_page', AccountPage)
    billsp = URL('/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&_pageLabel=as_revele_mensuel_presta_page', BillsPage)
    paymentdetailsp = URL('/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&_pageLabel=as_dernier_paiement_page&paiements_1_actionOverride=%2Fportlets%2Fpaiements%2Fdetailpaiements&paiements_1idPaiement=.*', PaymentDetailsPage)
    lastpaymentsp = URL('/PortailAS/appmanager/PortailAS/assure\?_nfpb=true&_pageLabel=as_dernier_paiement_page$', LastPaymentsPage)

    logged = False

    def do_login(self):
        self.logger.debug('call Browser.do_login')
        if self.logged:
            return True

        self.loginp.stay_or_go()
        if self.homep.is_here():
            self.logged = True
            return True

        self.page.login(self.username, self.password)

        self.homep.stay_or_go() # Redirection not interpreted by browser. Mannually redirect on homep

        if not self.homep.is_here():
            raise BrowserIncorrectPassword()

        self.logged = True

    @need_login
    def iter_subscription_list(self):
        self.logger.debug('call Browser.iter_subscription_list')
        self.accountp.stay_or_go()
        return self.page.iter_subscription_list()

    @need_login
    def get_subscription(self, id):
        self.logger.debug('call Browser.get_subscription')
        assert isinstance(id, basestring)
        for sub in self.iter_subscription_list():
            if id == sub._id:
                return sub
        return None

    @need_login
    def iter_history(self, sub):
        self.logger.debug('call Browser.iter_history')
        self.lastpaymentsp.stay_or_go()
        urls = self.page.iter_last_payments()
        for url in urls:
            self.location(url)
            assert self.paymentdetailsp.is_here()
            for payment in self.page.iter_payment_details(sub):
                yield payment

    @need_login
    def iter_details(self, sub):
        self.logger.debug('call Browser.iter_details')
        det = Detail()
        det.id = sub.id
        det.label = sub.label
        det.infos = ''
        det.price = Decimal('0.0')
        yield det

    @need_login
    def iter_bills(self, sub):
        self.logger.debug('call Browser.iter_bills')
        if not sub._id.isdigit():
            return []
        self.billsp.stay_or_go()
        return self.page.iter_bills(sub)

    @need_login
    def get_bill(self, id):
        self.logger.debug('call Browser.get_bill')
        assert isinstance(id, basestring)
        subs = self.iter_subscription_list()
        for sub in subs:
            for b in self.iter_bills(sub):
                if id == b.id:
                    return b
        return False
