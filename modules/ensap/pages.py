# -*- coding: utf-8 -*-

# Copyright(C) 2017      Juliette Fourcot
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

from __future__ import unicode_literals


from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Subscription, Document
from weboob.browser.filters.standard import Date, CleanText, Format, Regexp


class LoginPage(HTMLPage):
    pass


class LoginValidityPage(JsonPage):
    def check_logged(self):
        if self.get("code") == 60:
            return True
        return False


class HomePage(JsonPage):
    def iter_subscription(self):
        obj = Subscription()
        obj.subscriber = self.get("donnee.identification.identite")
        obj.label = "Account of %s" % obj.subscriber
        obj.id = CleanText(replace=[(' ', '.')]).filter(obj.subscriber)
        return [obj]


class DocumentsPage(JsonPage):
    @method
    class iter_documents(DictElement):
        item_xpath = 'donnee/listeDocument'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Document
            obj_date = Date(Dict('date'))
            obj_format = "pdf"
            obj_label = Format("%s : %s", Dict('libelle1'), Dict('libelle3'))
            obj_type = CleanText(Dict('libelleIcone'),
                                 replace=[('Icône ', '')])
            obj_id = Regexp(Dict('libelle2'), r"(\S+)\.", nth=0)
            obj_url = Format("/prive/telechargerdocument/v1?documentUuid=%s",
                             Dict('documentUuid'))


class LoginControlPage(JsonPage):
    def get_xsrf(self):
        return self.get("xcrf")
