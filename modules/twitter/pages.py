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

from weboob.tools.json import json
from weboob.browser.pages import HTMLPage, JsonPage, FormNotFound, pagination, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Format, Regexp, Env, DateTime, Filter
from weboob.browser.filters.html import Link, Attr
from weboob.capabilities.messages import Thread, Message
from weboob.capabilities.base import BaseObject


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
            self.has_next = self.doc['has_more_items']

            self.min_position = None
            if 'min_position' in self.doc:
                self.min_position = self.doc['min_position']

            if self.doc['items_html']:
                el = html.parse(StringIO(self.doc['items_html']), parser)
                self.doc = el if el.getroot() is not None else html.Element('brinbrin')
            else:
                self.doc = html.Element('brinbrin')


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        try:
            form = self.get_form(xpath='//form[@action="https://twitter.com/sessions"]')
            form['session[username_or_email]'] = login
            form['session[password]'] = passwd
            form.submit()
            return form['authenticity_token']
        except FormNotFound:
            return CleanText('(//input[@id="authenticity_token"])[1]/@value')(self.doc)

    @property
    def logged(self):
        try:
            self.get_form(xpath='//form[@action="https://twitter.com/sessions"]')
            return False
        except FormNotFound:
            return True

    def get_me(self):
        return Regexp(Link('//a[@data-nav="view_profile"]'), '/(.+)')(self.doc)


class ThreadPage(HTMLPage):

    @method
    class get_thread(ItemElement):
        klass = Thread

        obj_id = Format('%s#%s', Env('user'), Env('_id'))
        obj_title = Format('%s \n\t %s',
                           CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/div/div/a',
                                     replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]),
                           CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/div/p',
                                     replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]))
        obj_date = DateTime(Regexp(CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/div/div[@class="client-and-actions"]/span/span'),
                                   '(\d+:\d+).+- (.+\d{4})',
                                   '\\2 \\1'), translations=DATE_TRANSLATE_FR)

    @method
    class iter_comments(ListElement):
        item_xpath = '//ol[@id="stream-items-id"]/li/ol/div/li/div'

        class item(ItemElement):
            klass = Message

            obj_id = Regexp(Link('./div/div/small/a', default=''), '/.+/status/(.+)', default=None)

            obj_title = Regexp(CleanText('./div[@class="content"]/div/p[has-class("tweet-text")]',
                                         replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]),
                               '(.{50}|.+).+')
            obj_content = CleanText('./div[@class="content"]/div/p[has-class("tweet-text")]',
                                    replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')])
            obj_sender = Regexp(Link('./div/div/small/a', default=''), '/(.+)/status/.+', default=None)
            obj_date = DatetimeFromTimestamp(Attr('./div/div[@class="stream-item-header"]/small/a/span | ./div/div[@class="ProfileTweet-authorDetails"]/span/a/span', 'data-time'))

            def validate(self, obj):
                return obj.id is not None


class SearchPage(HTMLPage):
    def get_trends_token(self):
        json_data = CleanText('//input[@id="init-data"]/@value')(self.doc)
        return json.loads(json_data)['trendsCacheKey']

    def get_min_position(self):
        return CleanText('//div[@class="stream-container "]/@data-min-position')(self.doc)


class TrendsPage(TwitterJsonHTMLPage):

    @method
    class get_trendy_subjects(ListElement):
        item_xpath = '//li[@class="trend-item js-trend-item  "]'

        class item(ItemElement):
            klass = BaseObject

            obj_id = Attr('.', 'data-trend-name')


class TimelineListElement(ListElement):
    item_xpath = '//*[@data-item-type="tweet"]/div[@data-tweet-id]'
    ignore_duplicate = True

    def get_last_id(self):
        _el = self.page.doc.xpath('//*[@data-item-type="tweet"]/div')[-1]
        return CleanText('./@data-tweet-id')(_el)

    class item(ItemElement):
        klass = Thread

        obj_id = Format('%s#%s', CleanText('./@data-screen-name'), CleanText('./@data-tweet-id'))
        obj_title = Format('%s \n\t %s',
                           CleanText('./div/div[@class="stream-item-header"]/a|./div/div[@class="ProfileTweet-authorDetails"]/a',
                                     replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]),
                           CleanText('./div/div/p',
                                     replace=[('@ ', '@'), ('# ', '#'), ('http:// ', 'http://')]))
        obj_date = DatetimeFromTimestamp(Attr('./div/div[@class="stream-item-header"]/small/a/span | ./div/div[@class="ProfileTweet-authorDetails"]/span/a/span', 'data-time'))


class TimelinePage(TwitterJsonHTMLPage):
    @pagination
    @method
    class iter_threads(TimelineListElement):

        def next_page(self):
            if self.page.has_next:
                return u'%s?max_position=%s' % (self.page.url.split('?')[0], self.get_last_id())


class HomeTimelinePage(TwitterJsonHTMLPage, LoggedPage):
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
            params['max_position'] = self.page.min_position
            if 'min_position' in self.env and not params['max_position']:
                params['max_position'] = self.env['min_position']

            if self.page.has_next:
                return u'%s?%s' % (self.page.url.split('?')[0], urllib.urlencode(params))


class LoginErrorPage(HTMLPage):
    pass


class Tweet(JsonPage):
    pass
