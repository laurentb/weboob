# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

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

from mechanize import Browser, response_seek_wrapper, BrowserStateError
import urllib2
import html5lib
from html5lib import treebuilders
import re
import time
from logging import warning, error
from copy import copy

from dlfp.pages.login import IndexPage, LoginPage
from dlfp.exceptions import DLFPIncorrectPassword, DLFPUnavailable, DLFPRetry
from dlfp.firefox_cookies import FirefoxCookieJar

class NoHistory:
    def __init__(self): pass
    def add(self, request, response): pass
    def back(self, n, _response): pass
    def clear(self): pass
    def close(self): pass

class DLFP(Browser):

    pages = {'https://linuxfr.org/': IndexPage,
             'https://linuxfr.org/pub/': IndexPage,
             'https://linuxfr.org/my/': IndexPage,
             'https://linuxfr.org/login.html': LoginPage,
            }

    def __init__(self, username, password=None, firefox_cookies=None):
        Browser.__init__(self, history=NoHistory())
        self.addheaders = [
                ['User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.4) Gecko/2008111318 Ubuntu/8.10 (intrepid) Firefox/3.0.3']
            ]

        # Share cookies with firefox
        if firefox_cookies:
            self.__cookie = FirefoxCookieJar(firefox_cookies)
            self.__cookie.load()
            self.set_cookiejar(self.__cookie)
        else:
            self.__cookie = None

        self.__parser = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))
        self.__page = None
        self.__last_update = 0.0
        self.username = username
        self.password = password
        if self.password:
            try:
                self.home()
            except DLFPUnavailable:
                pass

    def page(self):
        return self.__page

    def home(self):
        return self.location('https://linuxfr.org')

    def pageaccess(func):
        def inner(self, *args, **kwargs):
            if not self.__page or not self.__page.isLogged() and self.password:
                self.home()

            return func(self, *args, **kwargs)
        return inner

    @pageaccess
    def keepalive(self):
        self.home()

    def login(self):
        self.location('/login.html', 'login=%s&passwd=%s&isauto=1' % (self.username, self.password))

    def openurl(self, *args, **kwargs):
        try:
            return Browser.open(self, *args, **kwargs)
        except (response_seek_wrapper, urllib2.HTTPError, urllib2.URLError), e:
            error(e)
            raise DLFPUnavailable()
        except BrowserStateError:
            self.home()
            return Browser.open(self, *args, **kwargs)

    def submit(self, *args, **kwargs):
        try:
            self.__changeLocation(Browser.submit(self, *args, **kwargs))
        except (response_seek_wrapper, urllib2.HTTPError, urllib2.URLError), e:
            error(e)
            self.__page = None
            raise DLFPUnavailable()
        except (BrowserStateError,DLFPRetry):
            self.home()
            raise DLFPUnavailable()

    def isOnPage(self, pageCls):
        return isinstance(self.__page, pageCls)

    def follow_link(self, *args, **kwargs):
        try:
            self.__changeLocation(Browser.follow_link(self, *args, **kwargs))
        except (response_seek_wrapper, urllib2.HTTPError, urllib2.URLError), e:
            error(e)
            self.__page = None
            raise DLFPUnavailable()
        except (BrowserStateError,DLFPRetry):
            self.home()
            raise DLFPUnavailable()

    def location(self, *args, **kwargs):
        keep_args = copy(args)
        keep_kwargs = kwargs.copy()

        try:
            self.__changeLocation(Browser.open(self, *args, **kwargs))
        except DLFPRetry:
            if not self.__page or not args or self.__page.url != args[0]:
                self.location(keep_args, keep_kwargs)
        except (response_seek_wrapper, urllib2.HTTPError, urllib2.URLError), e:
            error(e)
            self.__page = None
            raise DLFPUnavailable()
        except BrowserStateError:
            self.home()
            self.location(*keep_args, **keep_kwargs)

    def __changeLocation(self, result):
        # Find page from url
        pageCls = None
        for key, value in self.pages.items():
            regexp = re.compile('^%s$' % key)
            m = regexp.match(result.geturl())
            if m:
                pageCls = value
                break

        # Not found
        if not pageCls:
            self.__page = None
            r = result.read()
            if isinstance(r, unicode):
                r = r.encode('iso-8859-15', 'replace')
            print r
            warning('Ho my fucking god, there isn\'t any page named %s' % result.geturl())
            return

        print '[%s] Gone on %s' % (self.username, result.geturl())
        self.__last_update = time.time()

        document = self.__parser.parse(result, encoding='iso-8859-1')
        self.__page = pageCls(self, document, result.geturl())
        self.__page.loaded()

        # Special pages
        if isinstance(self.__page, LoginPage):
            if self.__page.hasError():
                raise DLFPIncorrectPassword()
            raise DLFPRetry()
        if not self.__page.isLogged() and self.password:
            print '!! Relogin !!'
            self.login()
            return

        if self.__cookie:
            self.__cookie.save()

