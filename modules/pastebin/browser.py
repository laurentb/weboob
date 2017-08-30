# -*- coding: utf-8 -*-

# Copyright(C) 2011-2014 Laurent Bachelier
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


import re

from weboob.capabilities.paste import BasePaste, PasteNotFound
from weboob.browser import LoginBrowser, need_login, URL
from weboob.browser.pages import HTMLPage, RawPage
from weboob.browser.elements import ItemElement, method
from weboob.browser.filters.standard import Base, CleanText, DateTime, Env, Filter, FilterError, RawText
from weboob.browser.filters.html import Attr
from weboob.exceptions import BrowserHTTPNotFound, BrowserIncorrectPassword, BrowserUnavailable


class PastebinPaste(BasePaste):
    # TODO perhaps move this logic elsewhere, remove this and id2url from capability
    # (page_url is required by pastoob)
    @classmethod
    def id2url(cls, _id):
        return '%s%s' % (PastebinBrowser.BASEURL, _id)


class BasePastebinPage(HTMLPage):
    @property
    def logged(self):
        for link in self.doc.xpath('//div[@id="header_bottom"]/ul[@class="top_menu"]//ul/li/a'):
            if link.text == 'logout':
                return True
            if link.text == 'login':
                return False
            raise BrowserUnavailable('Unable to determine login state')


class LoginPage(BasePastebinPage):
    def login(self, username, password):
        form = self.get_form('myform')
        form['user_name'] = username
        form['user_password'] = password
        form.submit()


class CleanVisibility(Filter):
    def filter(self, txt):
        if txt.startswith('Public'):
            return True
        if txt.startswith('Unlisted') or txt.startswith('Private'):
            return False
        return self.default_or_raise(FilterError('Unable to get the paste visibility'))


class PastePage(BasePastebinPage):
    @method
    class fill_paste(ItemElement):
        klass = PastebinPaste

        def parse(self, el):
            self.env['header'] = el.find('//div[@id="content_left"]//div[@class="paste_box_info"]')

        obj_id = Env('id')
        obj_title = Base(Env('header'), CleanText('.//div[@class="paste_box_line1"]//h1'))
        obj_contents = RawText('//textarea[@id="paste_code"]')
        obj_public = Base(
            Env('header'),
            CleanVisibility(Attr('.//div[@class="paste_box_line1"]//img', 'title')))
        obj__date = Base(
            Env('header'),
            DateTime(Attr('.//div[@class="paste_box_line2"]/span[1]', 'title')))


class PostPage(BasePastebinPage):
    def post(self, paste, expiration=None):
        form = self.get_form(name='myform')
        form['paste_code'] = paste.contents
        form['paste_name'] = paste.title
        if paste.public is True:
            form['paste_private'] = '0'
        elif paste.public is False:
            form['paste_private'] = '1'
        if expiration:
            form['paste_expire_date'] = expiration
        form.submit()


class WarningPage(BasePastebinPage):
    def __init__(self, *args, **kwargs):
        raise LimitExceeded()


class UserPage(BasePastebinPage):
    pass


class BadAPIRequest(BrowserUnavailable):
    pass


class LimitExceeded(BrowserUnavailable):
    pass


class PastebinBrowser(LoginBrowser):
    BASEURL = 'https://pastebin.com/'

    warning = URL('warning\.php\?p=(?P<id>\d+)', WarningPage)
    api = URL('api/api_post\.php', RawPage)
    apilogin = URL('api/api_login\.php', RawPage)
    login = URL('login', LoginPage)
    userprofile = URL('u/(?P<username>.+)', UserPage)
    postpage = URL('$', PostPage)
    paste = URL('(?P<id>\w+)', PastePage)
    raw = URL('raw\.php\?i=(?P<id>\w+)', RawPage)

    def __init__(self, api_key, *args, **kwargs):
        super(PastebinBrowser, self).__init__(*args, **kwargs)
        self.api_key = api_key
        self.user_key = None

        # being connected is optionnal at the module level, so require
        # login only if an username is configured
        if self.username:
            self.post = need_login(self.post_paste)

    def fill_paste(self, paste):
        """
        Get as much as information possible from the paste page
        """
        try:
            return self.paste.stay_or_go(id=paste.id).fill_paste(paste)
        except BrowserHTTPNotFound:
            raise PasteNotFound()

    @paste.id2url
    def get_paste(self, url):
        m = self.paste.match(url)
        if m:
            return PastebinPaste(m.groupdict()['id'])

    def get_contents(self, _id):
        """
        Get the contents from the raw URL
        This is the fastest and safest method if you only want the content.
        Returns unicode.
        """
        try:
            return self.raw.open(id=_id).response.text
        except BrowserHTTPNotFound:
            raise PasteNotFound()

    def post_paste(self, paste, expiration=None):
        self.postpage.stay_or_go().post(paste, expiration=expiration)
        # We cannot call fill_paste because we often have a captcha
        # anti-spam page, and do not detect it.
        paste.id = self.page.params['id']

    def api_post_paste(self, paste, expiration=None):
        data = {'api_dev_key': self.api_key,
                'api_option': 'paste',
                'api_paste_code': paste.contents}
        if self.password:
            data['api_user_key'] = self.api_login()
        if paste.public is True:
            data['api_paste_private'] = '0'
        elif paste.public is False:
            data['api_paste_private'] = '1'
        if paste.title:
            data['api_paste_name'] = paste.title
        if expiration:
            data['api_paste_expire_date'] = expiration
        res = self.open(self.api.build(), data=data, data_encoding='utf-8').text
        self._validate_api_response(res)
        paste.id = self.paste.match(res).groupdict()['id']

    def api_login(self):
        # "The api_user_key does not expire."
        # TODO store it on disk
        if self.user_key:
            return self.user_key

        data = {'api_dev_key': self.api_key,
                'api_user_name': self.username,
                'api_user_password': self.password}
        res = self.open(self.apilogin.build(), data=data, data_encoding='utf-8').text
        try:
            self._validate_api_response(res)
        except BadAPIRequest as e:
            if str(e) == 'invalid login':
                raise BrowserIncorrectPassword()
            else:
                raise e
        self.user_key = res
        return res

    # TODO make it into a Page?
    def _validate_api_response(self, res):
        matches = re.match('Bad API request, (?P<error>.+)', res)
        if matches:
            raise BadAPIRequest(matches.groupdict().get('error'))

    def do_login(self):
        self.login.stay_or_go().login()
        self.page.login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()
