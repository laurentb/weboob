# -*- coding: utf-8 -*-

# Copyright(C) 2015 Christophe Lampiné
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

import random

from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage


class LoginPage(HTMLPage):
    def generate_uuid(self):
        chars = list('0123456789abcdef')
        uuid = [None]*36
        rnd = random.random
        for i in (8, 13, 18, 23):
            uuid[i] = '-'
        uuid[14] = '4'  # version 4

        for i in range(36):
            if uuid[i] is None:
                r = 0 | int(rnd()*16)
                idx = (((r & 0x3) | 0x8) if (i == 19) else (r & 0xf))
                uuid[i] = chars[idx]
            i += 1

        return ''.join(uuid)

    def login(self, login, password):
        uuid = self.generate_uuid()
        data = self.browser.calcp.open(uuid=uuid).get_data(login, password)
        self.browser.profilp.open(data=data).store_sessionId()


class CalcPage(JsonPage):
    def get_data(self, login, password):
        convert_data = {}
        for num_data in self.doc['grilleMdp']:
            convert_data[num_data["nom"]] = num_data["valeur"]

        encrypt_pass = ""
        for char in password:
            encrypt_pass += (convert_data[int(char)] + ":")

        data = {'clang': self.browser.LANG,
                'conversationId': self.doc["conversationId"],
                'ctcc': self.browser.CTCC,
                'login': login,
                'password': encrypt_pass}

        return data


class ProfilPage(JsonPage):
    def store_sessionId(self):
        self.browser.sessionId = self.doc['session']


class AccountsPage(LoggedPage, JsonPage):
    def get_list(self):
        accounts = {}
        for entreprise in self.doc["listeEntreprise"]:
            for dispositif in entreprise["listeDispositf"]:  # Ceci n'est pas une erreur de frappe ;)
                for fonds in dispositif["listeFonds"]:
                    if fonds["montantValeurEuro"] == 0:
                        continue
                    fonds["codeLong"] = entreprise["codeEntreprise"] + dispositif["codeDispositif"] + fonds["codeSupport"]
                    if fonds["codeLong"] in accounts:
                        accounts[fonds["codeLong"]]["montantValeurEuro"] += fonds["montantValeurEuro"]
                    else:
                        accounts[fonds["codeLong"]] = fonds
        return accounts


class HistoryPage(LoggedPage, JsonPage):
    def get_transactions(self):
        for operation in self.doc["listeOperations"]:
            yield operation


class I18nPage(JsonPage):
    def load_i18n(self):
        self.browser.i18n = self.doc["i18n"]
