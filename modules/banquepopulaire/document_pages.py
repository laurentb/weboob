# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

import base64

from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.standard import Date, Env, Format
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Subscription, Document, DocumentTypes

from weboob.browser.pages import LoggedPage, JsonPage


class BasicTokenPage(LoggedPage, JsonPage):
    def get_basic_token(self):
        token = ('BP_MDE.RIA_PROD_1.0:%s' % self.doc['appContext']['clientSecret']).encode('utf-8')
        return base64.b64encode(token).decode('utf-8')


class SubscriberPage(LoggedPage, JsonPage):
    def get_subscriber(self):
        return self.doc['nomRaisonSociale']

    def get_status_dematerialized(self):
        return self.doc['roleUtilisateurCoffreNumerique']['code']

class SubscriptionsPage(LoggedPage, JsonPage):
    @method
    class get_subscriptions(DictElement):
        item_xpath = '_embedded/content'
        class item(ItemElement):
            klass = Subscription

            obj_id = Dict('idContrat/identifiant')
            obj_subscriber = Env('subscriber')
            obj_label = Dict('intituleContrat')
            obj__bank_code = Dict('idContrat/codeBanque')


class DocumentsPage(LoggedPage, JsonPage):
    @method
    class iter_documents(DictElement):
        item_xpath = '_embedded/content'

        def condition(self):
            return '_embedded' in self.page.doc

        class item(ItemElement):
            klass = Document

            obj_id = Format('%s_%s', Env('subid'), Dict('identifiantDocument/identifiant'))
            obj_date = Date(Dict('dateCreation'))
            obj_label = Dict('libelle')
            obj_format = 'pdf'
            obj_type = DocumentTypes.STATEMENT
            obj_url = Dict('_links/document/href')
