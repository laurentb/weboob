# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime

from weboob.capabilities.messages import Message
from weboob.capabilities.collection import Collection
from weboob.browser.pages import JsonPage, LoggedPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.standard import CleanText, Format
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import CleanHTML


class ContentsPage(LoggedPage, JsonPage):

    @method
    class get_articles(DictElement):
        item_xpath = 'items'

        class item(ItemElement):
            klass = Message

            obj_id = Format(u'%s#%s', CleanText(Dict('origin/streamId')), CleanText(Dict('id')))
            obj_sender = CleanText(Dict('author', default=u''))
            obj_title = Format(u'%s - %s', CleanText(Dict('origin/title', default=u'')),
                               CleanText(Dict('title', default=u'')))

            def obj_date(self):
                return datetime.fromtimestamp(Dict('published')(self.el) / 1e3)

            def obj_content(self):
                if 'content' in self.el.keys():
                    return Format(u'%s%s\r\n',
                                  CleanHTML(Dict('content/content')), CleanText(Dict('origin/htmlUrl')))(self.el)
                elif 'summary' in self.el.keys():
                    return Format(u'%s%s\r\n',
                                  CleanHTML(Dict('summary/content')), CleanText(Dict('origin/htmlUrl')))(self.el)
                else:
                    return ''


class TokenPage(JsonPage):
    def get_token(self):
        return self.doc['access_token'], self.doc['id']


class EssentialsPage(JsonPage):
    def get_categories(self):
        for category in self.doc:
            name = u'%s' % category.get('label')
            yield Collection([name], name)

    def get_feeds(self, label):
        for category in self.doc:
            if category.get('label') == label:
                feeds = category.get('subscriptions')
                for feed in feeds:
                    yield Collection([label, feed.get('title')])

    def get_feed_url(self, _category, _feed):
        for category in self.doc:
            if category.get('label') == _category:
                feeds = category.get('subscriptions')
                for feed in feeds:
                    if feed.get('title') == _feed:
                        return feed.get('id')


class PreferencesPage(LoggedPage, JsonPage):
    def get_categories(self):
        for category, value in self.doc.items():
            if value in [u"shown", u"hidden"]:
                yield Collection([u'%s' % category], u'%s' % category.replace('global.', ''))


class MarkerPage(LoggedPage):
    pass
