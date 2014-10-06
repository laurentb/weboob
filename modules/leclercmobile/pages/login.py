# -*- coding: utf-8 -*-

# Copyright(C) 2012  Florent Fourcot
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

import StringIO
from weboob.deprecated.browser import Page
from weboob.deprecated.mech import ClientForm


class LoginPage(Page):
    def on_loaded(self):
        pass

    def login(self, login, password):
        form = list(self.browser.forms())[0]
        self.browser.select_form("aspnetForm")
        self.browser.set_all_readonly(False)
        self.browser.controls.append(ClientForm.TextControl('text', '__ASYNCPOST', {'value': "true"}))
        self.browser['__EVENTTARGET'] = "ctl00$cMain$lnkValider"
        self.browser['ctl00$cMain$ascSaisieMsIsdn$txtMsIsdn'] = login.encode('iso-8859-1')
        self.browser['ctl00$cMain$txtMdp'] = password.encode('iso-8859-1')
        self.browser.submit(nologin=True)
        return form

    def iswait(self):
        spanwait = self.document.xpath('//span[@id="ctl00_ascAttente_timerAttente"]')
        return len(spanwait) > 0

    def iserror(self):
        error = self.document.xpath('//span[@id="ctl00_cMain_ascLibErreur_lblErreur"]')
        return len(error) > 0

    def getredirect(self):
        string = StringIO.StringIO()
        self.document.write(string)
        try:
            redirect = string.getvalue().split('pageRedirect')[1].split('|')[2]
        except:
            redirect = ''
        return redirect

    def next(self, login, form):
        self.browser.form = form
        string = StringIO.StringIO()
        self.document.write(string)
        controlvalue = string.getvalue().split('__EVENTVALIDATION')[1].split('|')[1]
        state = string.getvalue().split('__VIEWSTATE')[1].split('|')[1]
        self.browser.controls.append(ClientForm.TextControl('text', 'ctl00$objScriptManager', {'value': "ctl00$ascAttente$panelAttente|ctl00$ascAttente$timerAttente"}))
        self.browser['__VIEWSTATE'] = state
        self.browser['__EVENTTARGET'] = "ctl00$ascAttente$timerAttente"
        self.browser['__EVENTVALIDATION'] = controlvalue
        self.browser['ctl00$cMain$ascSaisieMsIsdn$txtMsIsdn'] = login.encode('iso-8859-1')
        self.browser['ctl00$cMain$txtMdp'] = ""
        self.browser.submit(nologin=True)
