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


from weboob.capabilities.bill import DocumentTypes, Subscription, Document
from weboob.browser.pages import JsonPage, HTMLPage, LoggedPage, RawPage
from weboob.browser.elements import (
    method,
    DictElement,
    ItemElement,
)
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    CleanText,
    Regexp,
    Env,
    Date,
    Format,
    Field,
    BrowserURL,
)


class CesuPage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath('//*[@id="deconnexion_link"]'))


class LoginPage(CesuPage):
    def is_here(self):
        return not bool(self.doc.xpath('//*[@id="deconnexion_link"]'))

    def login(self, username, password):
        form = self.get_form(xpath='//form[has-class("loginForm")]')
        form["username"] = username
        form["password"] = password
        form.submit()


class HomePage(LoggedPage, JsonPage):
    def is_ok(self):
        return self.doc["result"] == "ok"


class CesuApiPage(LoggedPage, JsonPage):
    def get_liste_messages(self):
        return self.doc["listeMessages"]

    def has_message(self):
        return self.doc["hasMessage"]

    def has_msg_avert(self):
        return self.doc["hasMsgAvert"]

    def has_msg_err_fonc(self):
        return self.doc["hasMsgErrFonc"]

    def has_msg_err_tech(self):
        return self.doc["hasMsgErrTech"]

    def has_msg_info(self):
        return self.doc["hasMsgInfo"]

    def get_object(self):
        return self.doc.get("objet", {})

    def get_objects(self):
        return self.doc.get("listeObjets", [])


class StatusPage(CesuApiPage):
    pass


class EmployerPage(CesuApiPage):
    pass


class EmployeesPage(CesuApiPage):
    @method
    class iter_subscriptions(DictElement):
        item_xpath = "listeObjets"

        class item(ItemElement):
            klass = Subscription

            obj_id = CleanText(Dict("noIntSala"))
            obj_label = Format(
                "%s %s",
                CleanText(Dict("prenom")),
                CleanText(Dict("nom")),
            )
            # obj_subscriber = Env("subscriber")
            obj__type = "employee"


class RegistrationPage(CesuApiPage):
    @method
    class iter_documents(DictElement):
        item_xpath = "listeObjets"

        class item(ItemElement):
            klass = Document

            obj_id = Format("%s_%s", Env("subscription"), Dict("referenceDocumentaire"))
            obj_format = "pdf"
            obj_date = Date(Dict("dtFin"))
            obj_label = Format(
                "Bulletin de salaire %s %s %s",
                Dict("salarieDTO/prenom"),
                Dict("salarieDTO/nom"),
                Dict("periode"),
            )
            obj_type = DocumentTypes.OTHER
            obj_url = BrowserURL(
                "payslip_download",
                employer=Env("employer"),
                ref_doc=Dict("referenceDocumentaire"),
            )


class RegistrationDashboardPage(CesuApiPage):
    pass


class DirectDebitSummaryPage(CesuApiPage):
    pass


class EmployeesDashboardPage(CesuApiPage):
    pass


class CurrentFiscalAdvantagePage(CesuApiPage):
    pass


class LastDayMonthPage(CesuApiPage):
    pass


class DirectDebitsHeaderPage(CesuApiPage):
    @method
    class iter_documents(DictElement):
        item_xpath = "listeObjets"

        class item(ItemElement):
            klass = Document

            obj_id = Format("%s_%s", Env("subscription"), Dict("reference"))
            obj_format = "pdf"
            obj_date = Date(Dict("datePrelevement"))
            obj__period = Regexp(
                Dict("datePrelevement"), r"(\d{4})-(\d{2})-(\d{2})", "\\1\\2"
            )
            obj_label = Format("Prélèvement du %s", Field("date"))
            obj_type = DocumentTypes.OTHER
            obj_url = BrowserURL(
                "direct_debit_download",
                employer=Env("employer"),
                reference=Dict("reference"),
                period=Field("_period"),
                type=Dict("typeOrigine"),
            )


class DirectDebitsDetailPage(CesuApiPage):
    pass


class DirectDebitDownloadPage(RawPage):
    pass


class TaxCertificatesPage(CesuApiPage):
    @method
    class iter_documents(DictElement):
        item_xpath = "listeObjets"

        class item(ItemElement):
            klass = Document

            obj_id = Format("%s_%s", Env("subscription"), Dict("periode"))
            obj_format = "pdf"
            obj_date = Date(Format("%s-12-31", Dict("periode")))
            obj_label = Format("Attestation fiscale %s", Dict("periode"))
            obj_type = DocumentTypes.OTHER
            obj_url = BrowserURL(
                "tax_certificate_download",
                employer=Env("employer"),
                year=Dict("periode"),
            )


class TaxCertificateDownloadPage(RawPage):
    pass


class PayslipDownloadPage(RawPage):
    pass
