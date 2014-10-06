# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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


#from logging import error

from weboob.deprecated.browser import Page, BrowserUnavailable


class LoginPage(Page):
    def login(self, login, passwd):
        msgb = self.document.xpath(".//*[@id='message_client']/text()")
        msga = ''.join(msgb)
        msg = msga.strip("\n")

        if "maintenance" in msg:
            raise BrowserUnavailable(msg)

        self.browser.select_form(nr=3)
        self.browser['login'] = login.encode('utf-8')
        self.browser['passwd'] = passwd.encode('utf-8')
        self.browser.submit(nologin=True)


# vim:ts=4:sw=4
