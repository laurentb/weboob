# -*- coding: utf-8 -*-

"""
Copyright(C) 2008-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

import time
from logging import warning

from weboob.tools.browser import Browser
from weboob.backends.aum.exceptions import AdopteWait

from weboob.backends.aum.pages.home import HomePage
from weboob.backends.aum.pages.contact_list import ContactListPage
from weboob.backends.aum.pages.contact_thread import ContactThreadPage
from weboob.backends.aum.pages.baskets import BasketsPage
from weboob.backends.aum.pages.profile import ProfilePage
from weboob.backends.aum.pages.search import SearchPage
from weboob.backends.aum.pages.login import LoginPage, RedirectPage, BanPage, ErrPage, RegisterPage, RegisterWaitPage, RegisterConfirmPage
from weboob.backends.aum.pages.edit import EditPhotoPage, EditPhotoCbPage, EditAnnouncePage, EditDescriptionPage, EditSexPage, EditPersonalityPage
from weboob.backends.aum.pages.wait import WaitPage

class AdopteUnMec(Browser):
    DOMAIN = 'www.adopteunmec.com'
    PROTOCOL = 'http'
    PAGES = {'http://www.adopteunmec.com/': LoginPage,
             'http://www.adopteunmec.com/index.html': LoginPage,
             'http://www.adopteunmec.com/index.php': LoginPage,
             'http://www.adopteunmec.com/loginErr.php.*': ErrPage,
             'http://www.adopteunmec.com/bans.php\?who=auto': BanPage,
             'http://www.adopteunmec.com/redirect.php\?action=login': RedirectPage,
             'http://www.adopteunmec.com/wait.php': WaitPage,
             'http://www.adopteunmec.com/register2.php': RegisterPage,
             'http://www.adopteunmec.com/register3.php.*': RegisterWaitPage,
             'http://www.adopteunmec.com/register4.php.*': RegisterConfirmPage,
             'http://www.adopteunmec.com/home.php': HomePage,
             'http://www.adopteunmec.com/mails.php': ContactListPage,
             'http://www.adopteunmec.com/mails.php\?type=1': BasketsPage,
             'http://www.adopteunmec.com/thread.php\?id=([0-9]+)': ContactThreadPage,
             'http://www.adopteunmec.com/edit.php\?type=1': EditPhotoPage,
             'http://s\d+.adopteunmec.com/upload2.php\?.*': EditPhotoCbPage,
             'http://www.adopteunmec.com/edit.php\?type=2': EditAnnouncePage,
             'http://www.adopteunmec.com/edit.php\?type=3': EditDescriptionPage,
             'http://www.adopteunmec.com/edit.php\?type=4': EditSexPage,
             'http://www.adopteunmec.com/edit.php\?type=5': EditPersonalityPage,
             'http://www.adopteunmec.com/search.php.*': SearchPage,
             'http://www.adopteunmec.com/rencontres-femmes/(.*)/([0-9]+)': ProfilePage,
             'http://www.adopteunmec.com/catalogue-hommes/(.*)/([0-9]+)': ProfilePage,
             'http://www.adopteunmec.com/view2.php': ProfilePage, # my own profile
             'http://www.adopteunmec.com/(\w+)': ProfilePage, # a custom profile url
            }

    def login(self):
        if not self.isOnPage(LoginPage):
            self.home()
        self.page.login(self.username, self.password)

    def isLogged(self):
        return not self.isOnPage(LoginPage)

    def home(self):
        return self.location('http://www.adopteunmec.com/home.php')

    def pageaccess(func):
        def inner(self, *args, **kwargs):
            if self.isOnPage(WaitPage):
                if not self.page.check():
                    raise AdopteWait()
                self.home()
            if not self.page or self.isOnPage(LoginPage) and self.password:
                self.home()

            return func(self, *args, **kwargs)
        return inner

    def register(self, nickname, password, sex, birthday_d, birthday_m, birthday_y, zipcode, country, godfather=''):
        if not self.isOnPage(RegisterPage):
            self.location('http://www.adopteunmec.com/register2.php')

        return self.page.register(nickname, password, sex, birthday_d, birthday_m, birthday_y, zipcode, country, godfather)

    @pageaccess
    def addPhoto(self, name, f):
        if not self.isOnPage(EditPhotoPage):
            self.location('/edit.php?type=1')
        return self.page.addPhoto(name, f)

    @pageaccess
    def setNickname(self, nickname):
        if not self.isOnPage(EditAnnouncePage):
            self.location('/edit.php?type=2')
        return self.page.setNickname(nickname)

    @pageaccess
    def setAnnounce(self, title=None, description=None, lookingfor=None):
        if not self.isOnPage(EditAnnouncePage):
            self.location('/edit.php?type=2')
        return self.page.setAnnounce(title, description, lookingfor)

    @pageaccess
    def score(self):
        if time.time() - self.__last_update > 60:
            self.home()
        return self.page.score()

    @pageaccess
    def getMyName(self):
        if time.time() - self.__last_update > 60:
            self.home()
        return self.page.getMyName()

    @pageaccess
    def getMyID(self):
        if not self.isOnPage(HomePage):
            self.home()
        return self.page.getMyID()

    @pageaccess
    def nbNewMails(self):
        if time.time() - self.__last_update > 60:
            self.home()
        return self.page.nbNewMails()

    @pageaccess
    def nbNewBaskets(self):
        if time.time() - self.__last_update > 60:
            self.home()
        return self.page.nbNewBaskets()

    @pageaccess
    def nbNewVisites(self):
        if time.time() - self.__last_update > 60:
            self.home()
        return self.page.nbNewVisites()

    @pageaccess
    def nbAvailableCharms(self):
        self.home()
        return self.page.nbAvailableCharms()

    @pageaccess
    def getBaskets(self):
        self.location('/mails.php?type=1')
        return self.page.getProfilesIDsList()

    @pageaccess
    def getContactList(self):
        if not self.isOnPage(ContactListPage):
            self.location('/mails.php')

        return self.page.getContactList()

    @pageaccess
    def getThreadMails(self, id):
        self.page.openThreadPage(id)
        return self.page.getMails()

    @pageaccess
    def postMail(self, id, content):
        self.page.openThreadPage(id)
        self.page.post(content)

    @pageaccess
    def sendCharm(self, id):
        result = self.openurl('http://www.adopteunmec.com/fajax_addBasket.php?id=%s' % id).read()
        warning('Charm: %s' % result)
        return result.find('noMoreFlashes') < 0

    @pageaccess
    def addBasket(self, id):
        result = self.openurl('http://www.adopteunmec.com/fajax_addBasket.php?id=%s' % id).read()
        warning('Basket: %s' % result)
        # TODO check if it works (but it should)
        return True

    @pageaccess
    def rate(self, id, what, rating):
        print 'rate "%s"' % id, what, rating
        result = self.openurl('http://www.adopteunmec.com/fajax_vote.php', 'member=%s&what=%s&rating=%s' % (id, what, rating)).read()
        print result
        return True

    @pageaccess
    def searchProfiles(self, **kwargs):
        self.location('/search.php?display=1')
        self.page.search(**kwargs)
        return self.page.getProfilesIDs()

    @pageaccess
    def getProfile(self, link):
        if isinstance(link, (str,unicode)) and link.startswith('/'):
            link = link[1:]
        self.location('/%s' % link)
        return self.page

    @pageaccess
    def isSlutOnline(self, id):
        result = self.openurl('http://www.adopteunmec.com/%s' % id).read()
        r = result.find('<td align="right" style="font-size:12px;font-weight:bold">en ligne</td>') >= 0
        print 'isSlutOnline(%s) = %s' % (id, r)
        return r
