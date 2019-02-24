# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

from collections import OrderedDict

from weboob.browser.elements import method, ListElement, ItemElement, SkipItem
from weboob.browser.filters.standard import CleanText, Regexp, Field, DateTime
from weboob.browser.filters.html import AbsoluteLink, Link, Attr, CleanHTML
from weboob.browser.pages import HTMLPage, RawPage, pagination
from weboob.capabilities.image import BaseImage, Thumbnail
from weboob.capabilities.messages import Thread, Message
from weboob.tools.compat import urljoin


class list_entry(ItemElement):
    obj_title = CleanText('.//a[has-class("title")]')
    obj_date = DateTime(Attr('.//time[@class="live-timestamp"]', 'datetime'))
    obj__page = AbsoluteLink('.//a[has-class("comments")]')
    obj_id = Regexp(Field('_page'), '/comments/([^/]+)/')


class ListPage(HTMLPage):
    @pagination
    @method
    class iter_images(ListElement):
        item_xpath = '//div[has-class("entry")]'

        class item(list_entry):
            klass = BaseImage

            obj_author = CleanText('.//a[has-class("author")]')

            def obj_thumbnail(self):
                path = Attr('..//a[has-class("thumbnail")]/img', 'src', default=None)(self)
                if path is None:
                    raise SkipItem('not an image thread')
                return Thumbnail(urljoin(self.page.url, path))

            def obj_url(self):
                self.obj_thumbnail()

                url = urljoin(self.page.url, Link('..//a[has-class("thumbnail")]')(self))
                if url != Field('_page')(self):
                    return url
                # TODO lazy load with fillobj?
                return self.page.browser.open(url).page.get_image_url()

        next_page = Link('//a[contains(@rel,"next")]', default=None)

    @pagination
    @method
    class iter_threads(ListElement):
        item_xpath = '//div[has-class("entry")]'

        class item(list_entry):
            klass = Thread

            obj_url = Field('_page')

        next_page = Link('//a[contains(@rel,"next")]', default=None)


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_images(ListElement):
        item_xpath = '//div[has-class("search-result")]'

        class item(ItemElement):
            klass = BaseImage

            obj__page = AbsoluteLink('.//a[has-class("search-comments")]')
            obj_id = Regexp(Field('_page'), '/comments/([^/]+)/')
            obj_date = DateTime(Attr('.//time', 'datetime'))
            obj_title = CleanText('.//a[has-class("search-title")]')
            obj_author = CleanText('.//a[has-class("author")]')

            def obj_thumbnail(self):
                path = Attr('./a[has-class("thumbnail")]/img', 'src', default=None)(self)
                if path is None:
                    raise SkipItem('not an image thread')
                return Thumbnail(urljoin(self.page.url, path))

            def obj_url(self):
                self.obj_thumbnail()

                url = urljoin(self.page.url, Link('./a[has-class("thumbnail")]')(self))
                if url != Field('_page')(self):
                    return url
                # TODO lazy load with fillobj?
                return self.page.browser.open(url).page.get_image_url()


class EntryPage(HTMLPage):
    @method
    class get_image(ItemElement):
        klass = BaseImage

        obj_title = CleanText('//div[@id="siteTable"]//a[has-class("title")]')
        obj_date = DateTime(Attr('//div[@id="siteTable"]//time', 'datetime'))
        obj_author = CleanText('//div[@id="siteTable"]//a[has-class("author")]')

        def obj_thumbnail(self):
            path = Attr('//div[@id="siteTable"]//a[has-class("thumbnail")]/img', 'src', default=None)(self)
            if path is None:
                raise SkipItem('not an image thread')
            return Thumbnail(urljoin(self.page.url, path))

        def obj_url(self):
            return self.page.get_image_url()

        def obj__page(self):
            return self.page.url

    def get_image_url(self):
        if self.doc.xpath('//video[@class="preview"]'):
            raise SkipItem('Videos are not implemented')
        return urljoin(self.url, Link('//a[img[@class="preview"]]')(self.doc))

    def get_thread(self, id):
        thr = Thread(id=id)
        self.fill_thread(thr)
        thr.date = thr.root.date
        thr.title = thr.root.title
        thr.url = thr.root.url
        return thr

    def fill_thread(self, thread):
        thread.root = None
        msgs = OrderedDict()

        title = CleanText('//a[has-class("title")]')(self.doc)

        for m in self.iter_messages():
            m.thread = thread
            if not m.url:
                assert not thread.root, 'there cannot be 2 roots'
                thread.root = m
                m.id = thread.id
                m.parent = None
                m.url = self.url
            else:
                assert m.id not in msgs
                msgs[m.id] = m
                m.id = '%s.%s' % (thread.id, m.id)

        for m in msgs.values():
            if m is thread.root:
                continue

            if m._parent_part:
                m.parent = msgs[m._parent_part]
            else:
                m.parent = thread.root
            m.parent.children.append(m)
            m.title = 'Re: %s' % title

        thread.root.title = title

    @method
    class iter_messages(ListElement):
        item_xpath = '//div[has-class("entry")]'

        class item(ItemElement):
            klass = Message

            # TODO deleted messages, collapsed messages, pagination

            def condition(self):
                if len(self.el.xpath('./span[@class="morecomments"]')):
                    return False
                if len(self.el.xpath('.//div[has-class("usertext")][has-class("grayed")]')):
                    return False
                if len(self.el.xpath('./ancestor::div[@id="siteTable_deleted"]')):
                    return False
                return True

            obj_content = CleanHTML('.//div[has-class("usertext-body")]')
            obj_sender = CleanText('.//a[has-class("author")]')
            obj_date = DateTime(Attr('.//time[@class="live-timestamp"]', 'datetime'))
            obj_url = AbsoluteLink('.//a[@data-event-action="permalink"]', default='')
            obj_id = Regexp(Field('url'), '/(\w+)/$', default=None)
            obj__parent_part = Regexp(Link('.//a[@data-event-action="parent"]', default=''), r'#(\w+)', default=None)

            def obj_children(self):
                return []


class CatchHTTP(RawPage):
    pass
