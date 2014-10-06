# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Jeremy Monnet
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

from datetime import date
from weboob.capabilities.library import Book
from weboob.deprecated.browser import Page, BrowserUnavailable
from weboob.deprecated.mech import ClientForm


class SkipPage(Page):
    pass


class HomePage(Page):
    pass


def txt2date(s):
    return date(*reversed([int(x) for x in s.split(' ')[-1].split('/')]))


class RentedPage(Page):
    # TODO, table limited to 20 items, need to use pagination
    def get_list(self):
        for book in self.iter_books('//tr[contains(@id, "ctl00_ContentPlaceHolder1_ctl00_ctl07_COMPTE_PRET_1_1_GrillePrets_ctl00__")]', 1):
            book.late = False
            yield book

        for book in self.iter_books('//tr[contains(@id, "ctl00_ContentPlaceHolder1_ctl00_ctl08_COMPTE_RETARD_0_1_GrilleRetards_ctl00__")]', 0):
            book.late = True
            yield book

    def iter_books(self, el, start):
        for tr in self.document.getroot().xpath(el):
            book = Book(tr[start].text)
            book.name = tr[start+3].text
            book.author = tr[start+4].text
            book.date = txt2date(tr[start+5].text)
            yield book


class HistoryPage(Page):
    pass


class BookedPage(Page):
    # TODO, table limited to 20 items, need to use pagination
    def get_list(self):
        for tr in self.document.getroot().xpath('//tr[contains(@id, "ctl00_ContentPlaceHolder1_ctl00_ctl09_COMPTE_INFOS_0_GrilleInfos_ctl00__0")]'):
            username=tr[1].text+"_"+tr[0].text

        for i, tr in enumerate(self.document.getroot().xpath('//tr[contains(@id, "ctl00_ContentPlaceHolder1_ctl00_ctl10_COMPTE_RESA_1_1_GrilleResas_ctl00__")]')):
            book = Book('%s%d' % (username, i))
            # if all the books booked are available, there are only 7 columns.
            # if (at least ?) one book is still not available, yous can cancel, and the first column does contain the checkbox. So 8 columns.
            if (len(tr) == 7):
                start = 2
            if (len(tr) == 8):
                start = 3
            book.name = tr[start].text
            book.author = tr[start+1].text
            book.date = txt2date(tr[start+3].text)
            book.late = False
            yield book


class LoginPage(Page):
    def login(self, login, passwd):
        self.browser.select_form(predicate=lambda x: x.attrs.get('id','')=='aspnetForm')
        self.browser.form.set_all_readonly(False)
        self.browser['ctl00$ContentPlaceHolder1$ctl00$ctl04$ctl00$TextSaisie'] = login
        self.browser['ctl00$ContentPlaceHolder1$ctl00$ctl04$ctl00$TextPass'] = passwd
        self.browser['ctl00_ScriptManager1_TSM']="%3B%3BSystem.Web.Extensions%2C%20Version%3D1.0.61025.0%2C%20Culture%3Dneutral%2C%20PublicKeyToken%3D31bf3856ad364e35%3Afr-FR%3A1f0f78f9-0731-4ae9-b308-56936732ccb8%3Aea597d4b%3Ab25378d2%3BTelerik.Web.UI%2C%20Version%3D2009.3.1314.20%2C%20Culture%3Dneutral%2C%20PublicKeyToken%3D121fae78165ba3d4%3Afr-FR%3Aec1048f9-7413-49ac-913a-b3b534cde186%3A16e4e7cd%3Aed16cbdc%3Af7645509%3A24ee1bba%3A19620875%3A874f8ea2%3A33108d14%3Abd8f85e4"
        self.browser.controls.append(ClientForm.TextControl('text', 'RadAJAXControlID', {'value': ''}))
        self.browser['RadAJAXControlID']="ctl00_ContentPlaceHolder1_ctl00_ctl04_ctl00_RadAjaxPanelConnexion"
        self.browser.controls.append(ClientForm.TextControl('text', 'ctl00$ScriptManager1', {'value': ''}))
        self.browser['ctl00$ScriptManager1']="ctl00$ContentPlaceHolder1$ctl00$ctl04$ctl00$ctl00$ContentPlaceHolder1$ctl00$ctl04$ctl00$RadAjaxPanelConnexionPanel|"
        self.browser.controls.append(ClientForm.TextControl('text', '__EVENTTARGET', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', '__EVENTARGUMENT', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', 'ctl00$ContentPlaceHolder1$ctl00$ctl04$ctl00$btnImgConnexion.x', {'value': ''}))
        self.browser['ctl00$ContentPlaceHolder1$ctl00$ctl04$ctl00$btnImgConnexion.x']="76"
        self.browser.controls.append(ClientForm.TextControl('text', 'ctl00$ContentPlaceHolder1$ctl00$ctl04$ctl00$btnImgConnexion.y', {'value': ''}))
        self.browser['ctl00$ContentPlaceHolder1$ctl00$ctl04$ctl00$btnImgConnexion.y']="10"

        try:
            self.browser.submit()
        except BrowserUnavailable:
            # Login is not valid
            return False
        return True

    def is_error(self):
        for text in self.document.find('body').itertext():
            text=text.strip()
            # Login seems valid, but password does not
            needle='Echec lors de l\'authentification'
            if text.startswith(needle.decode('utf-8')):
                return True
        return False
