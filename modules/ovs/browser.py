# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.tools.parsers.iparser import IParser
import BeautifulSoup

from .pages import PagePrivateThreadsList, PagePrivateThread, PageLogin, PageIndex, DummyPage, PageUserProfile


__all__ = ['OvsBrowser']


class SoupParser(IParser):
    def parse(self, data, encoding=None):
        return BeautifulSoup.BeautifulSoup(data.read().decode(encoding or 'utf-8'), convertEntities=BeautifulSoup.BeautifulStoneSoup.ALL_ENTITIES)


class OvsBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'paris.onvasortir.com'
    ENCODING = 'cp1252'

    def __init__(self, city, username, password, *a, **kw):
        self.DOMAIN = '%s.onvasortir.com' % city
        self.PAGES = {
            '%s://%s/' % (self.PROTOCOL, self.DOMAIN): PageIndex,

            r'%s://%s/message_read.php\?Id=.+' % (self.PROTOCOL, self.DOMAIN): PagePrivateThread,

            '%s://%s/vue_messages_recus.php' % (self.PROTOCOL, self.DOMAIN): PagePrivateThreadsList,
            '%s://%s/vue_messages_envoyes.php' % (self.PROTOCOL, self.DOMAIN): PagePrivateThreadsList,

            '%s://%s/page_action_connect.php' % (self.PROTOCOL, self.DOMAIN): PageLogin,

            r'%s://%s/\?Langue=EN' % (self.PROTOCOL, self.DOMAIN): DummyPage,
            '%s://%s/page_action_boost.php' % (self.PROTOCOL, self.DOMAIN): DummyPage,
            '%s://%s/vue_profil_all.php.php' % (self.PROTOCOL, self.DOMAIN): DummyPage,
            r'%s://%s/message_msg_envoi_ok.php\?.*' % (self.PROTOCOL, self.DOMAIN): DummyPage,
            '%s://%s/message_action_envoi.php' % (self.PROTOCOL, self.DOMAIN): DummyPage,

            r'%s://%s/profil_read.php\?.+' % (self.PROTOCOL, self.DOMAIN): PageUserProfile,
        }

        kw['parser'] = SoupParser()
        BaseBrowser.__init__(self, username, password, *a, **kw)

    def iter_threads_list(self):
        self.location('/vue_messages_recus.php')
        assert self.is_on_page(PagePrivateThreadsList)
        for thread in self.page.iter_threads_list():
            yield thread

        self.location('/vue_messages_envoyes.php')
        assert self.is_on_page(PagePrivateThreadsList)
        for thread in self.page.iter_threads_list():
            yield thread

    def get_thread(self, _id):
        self.location('/message_read.php?Id=%s&AffMsg=all' % _id)
        assert self.is_on_page(PagePrivateThread)
        return self.page.get_thread(_id)

    def login(self):
        assert not self.is_logged()

        self.page.login(self.username, self.password)
        if not self.is_logged():
            raise BrowserIncorrectPassword()
        self.location('/?Langue=EN')
        self.location('/page_action_boost.php')
        self.location('/')

    def is_logged(self):
        return (self.is_on_page(DummyPage) or self.page.is_logged())

    def post_to_thread(self, thread_id, subject, body):
        self.location('/message_read.php?Id=%s' % thread_id.encode(self.ENCODING)) # FIXME
        assert self.is_on_page(PagePrivateThread)
        self.page.post_to_thread(thread_id, subject, body)

    def create_thread(self, recipient, subject, body):
        self.location('/profil_read.php?%s' % recipient.encode(self.ENCODING)) # FIXME
        assert self.is_on_page(PageUserProfile)
        self.page.create_thread(recipient, subject, body)
