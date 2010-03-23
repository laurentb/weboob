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

import mechanize
import urllib2
import html5lib
import ClientForm
from html5lib import treebuilders
import re
import time
from logging import warning, error
from copy import copy

try:
    from weboob.tools.firefox_cookies import FirefoxCookieJar
    HAVE_COOKIES = True
except ImportError, e:
    warning("Unable to store cookies: %s" % e)
    HAVE_COOKIES = False

class BrowserIncorrectPassword(Exception):
    pass

class BrowserUnavailable(Exception):
    pass

class BrowserRetry(Exception):
    pass

class NoHistory:
    def __init__(self): pass
    def add(self, request, response): pass
    def back(self, n, _response): pass
    def clear(self): pass
    def close(self): pass

class BasePage:
    def __init__(self, browser, document, url=''):
        self.browser = browser
        self.document = document
        self.url = url

    def loaded(self):
        pass

class StandardParser(html5lib.HTMLParser):
    def __init__(self):
        html5lib.HTMLParser.__init__(self, tree=treebuilders.getTreeBuilder("dom"))

    def parse(self, data):
        return html5lib.HTMLParser.parse(data, encoding='iso-8859-1')

class Browser(mechanize.Browser):

    # ------ Class attributes --------------------------------------

    DOMAIN = None
    PROTOCOL = 'http'
    PAGES = {}
    USER_AGENT = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.4) Gecko/2008111318 Ubuntu/8.10 (intrepid) Firefox/3.0.3'

    # ------ Abstract methods --------------------------------------

    # Go to home
    def home(self):
        raise NotImplementedError()

    # Login to the website
    def login(self):
        raise NotImplementedError()

    # Return True if we are logged on website
    def is_logged(self):
        raise NotImplementedError()

    # ------ Browser methods ---------------------------------------

    def __init__(self, username, password=None, firefox_cookies=None, parser=StandardParser):
        mechanize.Browser.__init__(self, history=NoHistory())
        self.addheaders = [
                ['User-agent', self.USER_AGENT]
            ]

        # Share cookies with firefox
        if firefox_cookies and HAVE_COOKIES:
            self.__cookie = FirefoxCookieJar(self.DOMAIN, firefox_cookies)
            self.__cookie.load()
            self.set_cookiejar(self.__cookie)
        else:
            self.__cookie = None

        self.__parser = parser()
        self.page = None
        self.last_update = 0.0
        self.username = username
        self.password = password
        if self.password:
            try:
                self.home()
            except BrowserUnavailable:
                pass

    def set_parser(self, parser):
        self.__parser = parser

    def pageaccess(func):
        def inner(self, *args, **kwargs):
            if not self.page or not self.page.is_logged() and self.password:
                self.home()

            return func(self, *args, **kwargs)
        return inner

    @pageaccess
    def keepalive(self):
        self.home()

    def change_location(func):
        def inner(self, *args, **kwargs):
            if args and args[0][0] == '/' and (not self.request or self.request.host != self.DOMAIN):
                args = ('%s://%s%s' % (self.PROTOCOL, self.DOMAIN, args[0]),) + args[1:]
                print args

            return func(self, *args, **kwargs)
        return inner

    @change_location
    def openurl(self, *args, **kwargs):
        try:
            return mechanize.Browser.open(self, *args, **kwargs)
        except (mechanize.response_seek_wrapper, urllib2.HTTPError, urllib2.URLError), e:
            error(e)
            raise BrowserUnavailable()
        except mechanize.BrowserStateError:
            self.home()
            return mechanize.Browser.open(self, *args, **kwargs)

    def submit(self, *args, **kwargs):
        try:
            self.__change_location(mechanize.Browser.submit(self, *args, **kwargs))
        except (mechanize.response_seek_wrapper, urllib2.HTTPError, urllib2.URLError), e:
            error(e)
            self.page = None
            raise BrowserUnavailable()
        except (mechanize.BrowserStateError,BrowserRetry):
            self.home()
            raise BrowserUnavailable()

    def is_on_page(self, pageCls):
        return isinstance(self.page, pageCls)

    def follow_link(self, *args, **kwargs):
        try:
            self.__change_location(mechanize.Browser.follow_link(self, *args, **kwargs))
        except (mechanize.response_seek_wrapper, urllib2.HTTPError, urllib2.URLError), e:
            error(e)
            self.page = None
            raise BrowserUnavailable()
        except (mechanize.BrowserStateError,BrowserRetry):
            self.home()
            raise BrowserUnavailable()

    @change_location
    def location(self, *args, **kwargs):
        keep_args = copy(args)
        keep_kwargs = kwargs.copy()

        try:
            self.__change_location(mechanize.Browser.open(self, *args, **kwargs))
        except BrowserRetry:
            if not self.page or not args or self.page.url != args[0]:
                self.location(keep_args, keep_kwargs)
        except (mechanize.response_seek_wrapper, urllib2.HTTPError, urllib2.URLError), e:
            error(e)
            self.page = None
            raise BrowserUnavailable()
        except mechanize.BrowserStateError:
            self.home()
            self.location(*keep_args, **keep_kwargs)

    def __change_location(self, result):
        # Find page from url
        pageCls = None
        for key, value in self.PAGES.items():
            regexp = re.compile('^%s$' % key)
            m = regexp.match(result.geturl())
            if m:
                pageCls = value
                break

        # Not found
        if not pageCls:
            self.page = None
            r = result.read()
            if isinstance(r, unicode):
                r = r.encode('iso-8859-15', 'replace')
            print r
            warning('Ho my fucking god, there isn\'t any page named %s' % result.geturl())
            return

        print '[%s] Gone on %s' % (self.username, result.geturl())
        self.last_update = time.time()

        document = self.__parser.parse(result)
        self.page = pageCls(self, document, result.geturl())
        self.page.loaded()

        if not self.is_logged() and self.password:
            print '!! Relogin !!'
            self.login()
            return

        if self.__cookie:
            self.__cookie.save()

    def str(self, s):
        if isinstance(s, unicode):
            s = s.encode('iso-8859-15', 'replace')
        return s

    def set_field(self, args, label, field=None, value=None, is_list=False):
        try:
            if not field:
                field = label
            if args.get(label, None) is not None:
                if not value:
                    if is_list:
                        if isinstance(is_list, (list, tuple)):
                            try:
                                value = [self.str(is_list.index(args[label]))]
                            except ValueError, e:
                                if args[label]:
                                    print '[%s] %s: %s' % (label, args[label], e)
                                return
                        else:
                            value = [self.str(args[label])]
                    else:
                        value = self.str(args[label])
                self[field] = value
        except ClientForm.ControlNotFoundError:
            return

