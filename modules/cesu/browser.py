# -*- coding: utf-8 -*-

# Copyright(C) 2020      Ludovic LANGE
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from datetime import datetime
from dateutil.relativedelta import relativedelta
from weboob.capabilities.bill import Subscription
import calendar

from .pages import (
    LoginPage,
    HomePage,
    StatusPage,
    EmployerPage,
    EmployeesPage,
    RegistrationPage,
    RegistrationDashboardPage,
    DirectDebitSummaryPage,
    EmployeesDashboardPage,
    CurrentFiscalAdvantagePage,
    LastDayMonthPage,
    DirectDebitsHeaderPage,
    DirectDebitsDetailPage,
    PayslipDownloadPage,
    DirectDebitDownloadPage,
    TaxCertificateDownloadPage,
    TaxCertificatesPage,
)


class CesuBrowser(LoginBrowser):
    BASEURL = 'https://www.cesu.urssaf.fr'

    logout                   = URL(r'/cesuwebdec/deconnexion$')

    login                    = URL(r'/info/accueil.html$', LoginPage)

    homepage                 = URL(r'/info/accueil\.login\.do$', HomePage)

    status                   = URL(r'/cesuwebdec/status', StatusPage)
    employer                 = URL(r'/cesuwebdec/employeursIdentite/(?P<employer>.*)', EmployerPage)
    employees                = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/salaries', EmployeesPage)
    registrations            = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/declarationsby\?.*', RegistrationPage)
    registrations_dashboard  = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/declarationsTdBby\?.*', RegistrationDashboardPage)
    direct_debits_summary    = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/recapprelevements', DirectDebitSummaryPage)
    employees_dashboard      = URL(r'/cesuwebdec/salariesTdb?pseudoSiret=(?P<employer>.*)&maxResult=8', EmployeesDashboardPage)
    current_fiscal_advantage = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/avantagefiscalencours', CurrentFiscalAdvantagePage)
    last_day_month           = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/dernierJourOuvreMois', LastDayMonthPage)
    direct_debits_header     = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/entetePrelevements\?.*', DirectDebitsHeaderPage)
    direct_debits_detail     = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/detailPrelevements\?periode=202001&type=IPVT&reference=0634675&idPrelevement=0', DirectDebitsDetailPage)
    tax_certificates         = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/attestationsfiscales', TaxCertificatesPage)
    payslip_download         = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/editions/bulletinSalairePE\?refDoc=(?P<ref_doc>.*)', PayslipDownloadPage)
    direct_debit_download    = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/editions/avisPrelevement\?reference=(?P<reference>.*)&periode=(?P<period>.*)&type=(?P<type>.*)', DirectDebitDownloadPage)
    tax_certificate_download = URL(r'/cesuwebdec/employeurs/(?P<employer>.*)/editions/attestation_fiscale_annee\?periode=(?P<year>.*)', TaxCertificateDownloadPage)

    employer = None
    compteur = 0

    def do_login(self):
        self.session.cookies.clear()
        self.login.go()
        self.session.headers.update(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        self.page.login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

        self.status.go()
        self.employer = self.page.get_object().get("numero")

    def do_logout(self):
        self.logout.go()
        self.session.cookies.clear()

    @need_login
    def iter_subscription(self):
        self.employees.go(employer=self.employer)

        for sub in self.page.iter_subscriptions(subscriber=None):
            yield sub

        s = Subscription()
        s.label = "Prélèvements"
        s.id = "prelevements"
        s._type = s.id
        yield s

        s = Subscription()
        s.label = "Attestations fiscales"
        s.id = "taxcertificates"
        s._type = s.id
        yield s

    def _search_registrations(
        self, subscription, begin_date, end_date, num_start, step
    ):
        self.registrations.go(
            employer=self.employer,
            params={
                "numInterneSalarie": subscription.id,
                "dtDebutRecherche": begin_date.strftime("%Y%m%d"),
                "dtFinRecherche": end_date.strftime("%Y%m%d"),
                "numStart": num_start,
                "nbAffiche": step,
                "numeroOrdre": self.compteur,
            },
        )
        self.compteur += 1

    def _search_direct_debits(self, begin_date, end_date):
        self.direct_debits_header.go(
            employer=self.employer,
            params={
                "dtDebut": begin_date.strftime("%Y%m%d"),
                "dtFin": end_date.strftime("%Y%m%d"),
                "numeroOrdre": self.compteur,
                "nature": "",
            },
        )
        self.compteur += 1

    @need_login
    def iter_documents(self, subscription):
        self.compteur = 0
        if subscription._type == "employee":

            end_date = datetime.today()
            # 5 years maximum
            begin_date = end_date - relativedelta(years=+5)

            has_results = True
            num_start = 0
            step = 24

            while has_results:
                self._search_registrations(
                    subscription, begin_date, end_date, num_start, step
                )

                num_start += step

                has_results = len(self.page.get_objects()) > 0
                # # No more documents
                # if self.page.has_error_msg():
                #     break

                for doc in self.page.iter_documents(
                    subscription=subscription.id, employer=self.employer
                ):
                    yield doc

        elif subscription._type == "prelevements":

            # Start end of month
            end_date = datetime.today()
            end_date += relativedelta(
                day=calendar.monthrange(end_date.year, end_date.month)[1],
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            # 1 year maximum ; beginning of month
            begin_date = end_date - relativedelta(years=+1, day=1)

            self._search_direct_debits(begin_date, end_date)

            has_results = len(self.page.get_objects()) > 0

            for doc in self.page.iter_documents(
                subscription=subscription.id, employer=self.employer
            ):
                yield doc

        elif subscription._type == "taxcertificates":

            self.tax_certificates.go(employer=self.employer)
            for doc in self.page.iter_documents(
                subscription=subscription.id, employer=self.employer
            ):
                yield doc
