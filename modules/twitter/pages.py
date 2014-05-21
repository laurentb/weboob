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

from weboob.tools.browser2.page import HTMLPage, JsonPage, method, ListElement, ItemElement, FormNotFound
from weboob.tools.browser2.filters import CleanText, Format, Link, Regexp, Env, DateTime, Attr, Filter
from weboob.capabilities.messages import Thread, Message

__all__ = ['LoginPage', 'LoginErrorPage', 'ThreadPage', 'HomePage', 'Tweet']


class DatetimeFromTimestamp(Filter):
    def filter(self, el):
        return datetime.fromtimestamp(float(el))


class LoginPage(HTMLPage):
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

    @method
    class iter_threads(ListElement):
        item_xpath = '//li[@data-item-type="tweet"]/div'

        class item(ItemElement):
            klass = Thread

            obj_id = Regexp(Link('./div/div/a[@class="details with-icn js-details"]'), '/(.+)/status/(.+)', '\\1#\\2')
            obj_title = Format('%s \n\t %s',
                               CleanText('./div/div[@class="stream-item-header"]/a'),
                               CleanText('./div/p'))
            obj_date = DatetimeFromTimestamp(Attr('./div/div[@class="stream-item-header"]/small/a/span', 'data-time'), DATE_TRANSLATE_FR)


class ThreadPage(HTMLPage):

    @method
    class get_thread(ItemElement):
        klass = Thread

        def parse(self, el):
            pass

        obj_id = Format('%s#%s', Env('user'), Env('_id'))
        obj_title = Format('%s \n\t %s',
                           CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/div/div/a'),
                           CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/p'))

        obj_date = DateTime(Regexp(CleanText('//div[@class="permalink-inner permalink-tweet-container"]/div/div/div/div[@class="client-and-actions"]/span'),
                                   '(\d+:\d+).+- (.+\d{4})',
                                   '\\2 \\1'))

    @method
    class iter_comments(ListElement):
        item_xpath = '//ol[@id="stream-items-id"]/li/div'

        class item(ItemElement):
            klass = Message

            def parse(self, el):
                pass

            obj_id = Regexp(Link('./div/div/a[@class="details with-icn js-details"]'), '/.+/status/(.+)')
            obj_title = Regexp(CleanText('./div/p'), '(.{50}|.+).+')
            obj_content = CleanText('./div/p')
            obj_sender = Regexp(Link('./div/div/a[@class="details with-icn js-details"]'), '/(.+)/status/.+')
            obj_date = DatetimeFromTimestamp(Attr('./div/div[@class="stream-item-header"]/small/a/span', 'data-time'))


class LoginErrorPage(HTMLPage):
    pass


class Tweet(JsonPage):
    pass


class HomePage(HTMLPage):
    pass
