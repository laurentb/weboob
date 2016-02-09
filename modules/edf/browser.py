# -*- coding: utf-8 -*-

# Copyright(C) 2013      Christophe Gouiran
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
from .pages import LoginPage, FirstRedirectionPage, SecondRedirectionPage, OtherPage, AccountPage, BillsPage, LastPaymentsPage, LastPaymentsPage2

__all__ = ['EdfBrowser']


class EdfBrowser(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'monagencepart.edf.fr'
    ENCODING = None
    #DEBUG_HTTP = True
    #DEBUG_MECHANIZE = True

    PAGES = {'.*page_authentification': LoginPage,
             '.*serviceRedirectionAel.*': FirstRedirectionPage,
             '.*Routage\?service=.*': SecondRedirectionPage,
             '.*routage/Routage.*': SecondRedirectionPage,
             '.*page_synthese_client': AccountPage,
             '.*autres-pages-.*': OtherPage,
             '.*page_mes_factures.*': BillsPage,
             '.*portlet_mon_paiement_1.*': LastPaymentsPage,
             '.*portlet_echeancier_2.*': LastPaymentsPage2
             }

    loginp = '/ASPFront/appmanager/ASPFront/front?_nfpb=true&_pageLabel=page_authentification'
    accountp = '/ASPFront/appmanager/ASPFront/front?_nfls=false&_nfpb=true&_pageLabel=private/page_synthese_client'
    billsp = '/ASPFront/appmanager/ASPFront/front?_nfls=false&_nfpb=true&_pageLabel=private/page_mes_factures&portletInstance2=portlet_suivi_consommation_2'
    lastpaymentsp = '/ASPFront/appmanager/ASPFront/front?_nfls=false&_nfpb=true&_pageLabel=private/page_mon_paiement&portletInstance=portlet_mon_paiement_1'

    is_logging = False

    def home(self):
        if not self.is_logged():
            self.login()

    def is_logged(self):
        logged = self.page and self.page.is_logged() or self.is_logging
        self.logger.debug('logged: %s' % (logged))
        return logged

    def login(self):
        # Do we really need to login?
        if self.is_logged():
            self.logger.debug('Already logged in')
            return

        self.is_logging = True

        self.location(self.loginp)
        self.page.login(self.username, self.password)

        self.is_logging = False

        if not self.is_logged():
            raise BrowserIncorrectPassword()

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
        if not sub._id.isdigit():
            return []
        if not self.is_on_page(LastPaymentsPage):
            self.location(self.lastpaymentsp)
        return self.page.iter_payments(sub)

    def iter_details(self, sub):
        det = Detail()
        det.id = sub.id
        det.label = sub.label
        det.infos = ''
        det.price = Decimal('0.0')
        yield det

    def iter_documents(self, sub):
        if not sub._id.isdigit():
            return []
        if not self.is_on_page(BillsPage):
            self.location(self.billsp)
            return self.page.iter_documents(sub)

    def get_document(self, id):
        assert isinstance(id, basestring)
        subs = self.iter_subscription_list()
        for sub in subs:
            for b in self.iter_documents(sub):
                if id == b.id:
                    return b
