# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from datetime import datetime
from weboob.tools.date import DATE_TRANSLATE_FR
from io import StringIO
import lxml.html as html
import urllib

from weboob.tools.browser2.page import HTMLPage, JsonPage, method, ListElement, ItemElement, FormNotFound, pagination
from weboob.tools.browser2.filters import CleanText, Format, Link, Regexp, Env, DateTime, Attr, Filter
from weboob.capabilities.messages import Thread, Message
from weboob.capabilities.base import CapBaseObject
__all__ = ['LoginPage', 'LoginErrorPage', 'ThreadPage', 'TwitterBasePage', 'Tweet', 'TrendsPage', 'TimelinePage', 'HomeTimelinePage', 'SearchTimeLinePage']


class DatetimeFromTimestamp(Filter):
    def filter(self, el):
        return datetime.fromtimestamp(float(el))


class TwitterJsonHTMLPage(JsonPage):

    ENCODING = None
    has_next = None
    scroll_cursor = None

    def __init__(self, browser, response, *args, **kwargs):
        super(TwitterJsonHTMLPage, self).__init__(browser, response, *args, **kwargs)
        self.encoding = self.ENCODING or response.encoding
        parser = html.HTMLParser(encoding=self.encoding)
        if 'module_html' in self.doc:
            self.doc = html.parse(StringIO(self.doc['module_html']), parser)
        else:
            if 'scroll_cursor' in self.doc:
                self.scroll_cursor = self.doc['scroll_cursor']

            self.has_next = self.doc['has_more_items']
            self.doc = html.parse(StringIO(self.doc['items_html']), parser)


class TwitterBasePage(HTMLPage):
    @method
    class iter_threads(ListElement):
        item_xpath = '//*[@data-item-type="tweet"]/div'

        class item(ItemElement):
            klass = Thread

            obj_id = Regexp(Link('./div/div/a[@class="details with-icn js-details"]|./div/div/span/a[@class="ProfileTweet-timestamp js-permalink js-nav js-tooltip"]'), '/(.+)/status/(.+)', '\\1#\\2')
            obj_title = Format('%s \n\t %s',
                               CleanText('./div/div[@class="stream-item-header"]/a|./div/div[@class="ProfileTweet-authorDetails"]/a',
                                         replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]),
                               CleanText('./div/p',
                                         replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]))
            obj_date = DatetimeFromTimestamp(Attr('./div/div[@class="stream-item-header"]/small/a/span|./div/div/span/a[@class="ProfileTweet-timestamp js-permalink js-nav js-tooltip"]/span', 'data-time'))


class LoginPage(TwitterBasePage):
    def login(self, login, passwd):
        form = self.get_form(xpath='//form[@action="https://twitter.com/sessions"]')
        form['session[username_or_email]'] = login
        form['session[password]'] = passwd
        form.submit()
        return form['authenticity_token']

    @property
    def logged(self):
        try:
            self.get_form(xpath='//form[@action="https://twitter.com/sessions"]')
            return False
        except FormNotFound:
            return True

    def get_me(self):
        return Regexp(Link('//a[@data-nav="profile"]'), '/(.+)')(self.doc)


class ThreadPage(HTMLPage):

    @method
    class get_thread(ItemElement):
        klass = Thread

        obj_id = Format('%s#%s', Env('user'), Env('_id'))
        obj_title = Format('%s \n\t %s',
                           CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/div/div/a',
                                     replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]),
                           CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/p',
                                     replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]))

        obj_date = DateTime(Regexp(CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/div/div/div[@class="client-and-actions"]/span'),
                                   '(\d+:\d+).+- (.+\d{4})',
                                   '\\2 \\1'), translations=DATE_TRANSLATE_FR)

    @method
    class iter_comments(ListElement):
        item_xpath = '//ol[@id="stream-items-id"]/li/div'

        class item(ItemElement):
            klass = Message

            obj_id = Regexp(Link('./div/div/a[@class="details with-icn js-details"]'), '/.+/status/(.+)')
            obj_title = Regexp(CleanText('./div/p', replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]),
                               '(.{50}|.+).+')
            obj_content = CleanText('./div/p', replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')])
            obj_sender = Regexp(Link('./div/div/a[@class="details with-icn js-details"]'), '/(.+)/status/.+')
            obj_date = DatetimeFromTimestamp(Attr('./div/div[@class="stream-item-header"]/small/a/span', 'data-time'))


class TrendsPage(TwitterJsonHTMLPage):

    @method
    class get_trendy_subjects(ListElement):
        item_xpath = '//li[@class="trend-item js-trend-item  "]'

        class item(ItemElement):
            klass = CapBaseObject

            obj_id = Attr('.', 'data-trend-name')


class TimelineListElement(ListElement):
    item_xpath = '//*[@data-item-type="tweet"]/div'

    def get_last_id(self):
        _el = self.page.doc.xpath('//*[@data-item-type="tweet"]/div')[-1]
        return Regexp(Link('./div/div/a[@class="details with-icn js-details"]|./div/div/span/a[@class="ProfileTweet-timestamp js-permalink js-nav js-tooltip"]'), '/.+/status/(.+)')(_el)

    class item(ItemElement):
        klass = Thread

        obj_id = Regexp(Link('./div/div/a[@class="details with-icn js-details"]|./div/div/span/a[@class="ProfileTweet-timestamp js-permalink js-nav js-tooltip"]'), '/(.+)/status/(.+)', '\\1#\\2')
        obj_title = Format('%s \n\t %s',
                           CleanText('./div/div[@class="stream-item-header"]/a|./div/div[@class="ProfileTweet-authorDetails"]/a',
                                     replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]),
                           CleanText('./div/p',
                                     replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]))
        obj_date = DatetimeFromTimestamp(Attr('./div/div[@class="stream-item-header"]/small/a/span|./div/div/span/a[@class="ProfileTweet-timestamp js-permalink js-nav js-tooltip"]/span', 'data-time'))


class TimelinePage(TwitterJsonHTMLPage):
    @pagination
    @method
    class iter_threads(TimelineListElement):

        def next_page(self):
            if self.page.has_next:
                return u'%s?max_position=%s' % (self.page.url.split('?')[0], self.get_last_id())


class HomeTimelinePage(TwitterJsonHTMLPage):
    @pagination
    @method
    class iter_threads(TimelineListElement):

        def next_page(self):
            if self.page.has_next:
                return u'%s?max_id=%s' % (self.page.url.split('?')[0], self.get_last_id())


class SearchTimelinePage(TwitterJsonHTMLPage):
    @pagination
    @method
    class iter_threads(TimelineListElement):

        def next_page(self):
            params = self.env['params']
            params['scroll_cursor'] = self.page.scroll_cursor
            if self.page.has_next:
                return u'%s?%s' % (self.page.url.split('?')[0], urllib.urlencode(params))


class LoginErrorPage(HTMLPage):
    pass


class Tweet(JsonPage):
    pass
