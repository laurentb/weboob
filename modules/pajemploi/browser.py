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
from weboob.capabilities.bill import Subscription

from .pages import (
    LoginPage,
    HomePage,
    EmployeesPage,
    PayslipDownloadPage,
    TaxCertificatesPage,
    DeclarationSetupPage,
    DeclarationListPage,
    DeclarationDetailPage,
    MonthlyReportDownloadPage,
    RegistrationRecordDownloadPage,
    CotisationsDownloadPage,
    AjaxDetailSocialInfoPage,
)


class PajemploiBrowser(LoginBrowser):
    BASEURL = "https://www.pajemploi.urssaf.fr"

    logout                       = URL(r"/pajeweb/j_spring_security_logout$",
                                       r"/pajeweb/quit.htm$")

    login                        = URL(r"/info/accueil.html$",
                                       r"/portail/accueil.html$",
                                       r"/pajewebinfo/cms/sites/pajewebinfo/accueil.html$",
                                       r"/pajeweb/connect.htm$",
                                       r"/pajeweb/home.jsp$", LoginPage)

    homepage                     = URL(r"/info/accueil.html$",
                                       r"/portail/accueil.html$",
                                       r"/pajewebinfo/cms/sites/pajewebinfo/accueil.html$",
                                       r"/pajeweb/connect.htm$",
                                       r"/pajeweb/home.jsp$", HomePage)

    employees                    = URL(r"/pajeweb/listesala/gerersala.htm$", EmployeesPage)

    tax_certificates             = URL(r"/pajeweb/atfirecap.htm$", TaxCertificatesPage)

    declaration_setup            = URL(r"/pajeweb/listeVSssl.jsp$", DeclarationSetupPage)
    declaration_list             = URL(r"/pajeweb/ajaxlistevs.jsp$", DeclarationListPage)
    declaration_detail           = URL(r"/pajeweb/recapitulatifPrestationFiltre.htm$", DeclarationDetailPage)
    payslip_download             = URL(r"/pajeweb/paje_bulletinsalaire.pdf\?ref=(?P<refdoc>.*)", PayslipDownloadPage)
    monthly_report_download      = URL(r"/pajeweb/decla/saisie/afficherReleveMensuel.htm$", MonthlyReportDownloadPage)
    registration_record_download = URL(r"/pajeweb/afficherCertificat.htm$", RegistrationRecordDownloadPage)
    cotisations_download         = URL(r"/pajeweb/paje_decomptecotiempl.pdf?ref=(?P<refdoc>.*)", CotisationsDownloadPage)
    ajax_detail_social_info      = URL(r'/pajeweb/ajaxdetailvs.jsp$', AjaxDetailSocialInfoPage)

    def do_login(self):
        self.session.cookies.clear()
        self.login.go()
        self.page.login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

    def do_logout(self):
        self.logout.go()
        self.session.cookies.clear()

    @need_login
    def iter_subscription(self):
        self.employees.go()

        s = Subscription()
        s.label = "Attestations fiscales"
        s.id = "taxcertificates"
        s._type = s.id
        yield s

        for sub in self.page.iter_subscriptions(subscriber=None):
            yield sub

        return []

    @need_login
    def iter_documents(self, subscription):
        if subscription._type == "employee":

            self.declaration_setup.go()
            data = self.page.get_data(subscription)
            self.declaration_list.go(data=data)

            for proto_doc in self.page.iter_documents(subscription=subscription.id):
                data = {"refdoc": proto_doc._refdoc, "norng": proto_doc._norng}
                self.declaration_detail.go(data=data)
                for doc in self.page.iter_documents(proto_doc):
                    doc._previous_data = data
                    doc._previous_page = self.declaration_detail
                    yield doc

        elif subscription._type == "taxcertificates":

            self.tax_certificates.go()
            for doc in self.page.iter_documents(subscription=subscription.id):
                yield doc

        return []

    def download_document(self, document):
        if (
            hasattr(document, "_need_refresh_previous_page")
            and document._need_refresh_previous_page
        ):
            document._previous_page.go(data=document._previous_data)
        return self.open(document.url).content
