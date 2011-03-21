# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import urllib
import re

from weboob.tools.browser import BaseBrowser, BrowserHTTPNotFound, BrowserHTTPError, BrowserIncorrectPassword
from weboob.capabilities.messages import CantSendMessage

from .pages.index import IndexPage, LoginPage
from .pages.news import ContentPage, NewCommentPage, NodePage, CommentPage, NewTagPage
from .pages.board import BoardIndexPage
from .pages.wiki import WikiEditPage
from .tools import id2url, url2id

# Browser
class DLFP(BaseBrowser):
    DOMAIN = 'linuxfr.org'
    PROTOCOL = 'https'
    PAGES = {'https://linuxfr.org/?': IndexPage,
             'https://linuxfr.org/login.html': LoginPage,
             'https://linuxfr.org/news/[^\.]+': ContentPage,
             'https://linuxfr.org/wiki/(?!nouveau)[^/]+': ContentPage,
             'https://linuxfr.org/wiki': WikiEditPage,
             'https://linuxfr.org/wiki/nouveau': WikiEditPage,
             'https://linuxfr.org/wiki/[^\.]+/modifier': WikiEditPage,
             'https://linuxfr.org/suivi/[^\.]+': ContentPage,
             'https://linuxfr.org/users/[\w\-_]+/journaux/[^\.]+': ContentPage,
             'https://linuxfr.org/forums/[\w\-_]+/posts/[^\.]+': ContentPage,
             'https://linuxfr.org/nodes/(\d+)/comments/(\d+)': CommentPage,
             'https://linuxfr.org/nodes/(\d+)/comments/nouveau': NewCommentPage,
             'https://linuxfr.org/nodes/(\d+)/comments': NodePage,
             'https://linuxfr.org/nodes/(\d+)/tags/nouveau': NewTagPage,
             'https://linuxfr.org/board/index.xml': BoardIndexPage,
            }

    last_board_msg_id = None

    def home(self):
        return self.location('https://linuxfr.org')

    def parse_id(self, _id):
        if re.match('^https?://linuxfr.org/nodes/\d+/comments/\d+$', _id):
            return _id, None

        url = id2url(_id)
        if url is None:
            if url2id(_id) is not None:
                url = _id
                _id = url2id(url)
            else:
                return None, None

        return url, _id

    def get_wiki_content(self, _id):
        url, _id = self.parse_id('W.%s' % _id)
        if url is None:
            return None

        try:
            self.location('%s/modifier' % url)
        except BrowserHTTPNotFound:
            return ''

        assert self.is_on_page(WikiEditPage)

        return self.page.get_body()

    def _go_on_wiki_edit_page(self, name):
        """
        Go on the wiki page named 'name'.

        Return True if this is a new page, or False if
        the page already exist.
        Return None if it isn't a right wiki page name.
        """
        url, _id = self.parse_id('W.%s' % name)
        if url is None:
            return None

        try:
            self.location('%s/modifier' % url)
        except BrowserHTTPNotFound:
            self.location('/wiki/nouveau')
            new = True
        else:
            new = False

        assert self.is_on_page(WikiEditPage)

        return new

    def set_wiki_content(self, name, content, message):
        new = self._go_on_wiki_edit_page(name)
        if new is None:
            return None

        if new:
            title = name.replace('-', ' ')
        else:
            title = None

        self.page.post_content(title, content, message)

    def get_wiki_preview(self, name, content):
        if self._go_on_wiki_edit_page(name) is None:
            return None

        self.page.post_preview(content)
        if self.is_on_page(WikiEditPage):
            return self.page.get_preview_html()
        elif self.is_on_page(ContentPage):
            return self.page.get_article().body

    def get_content(self, _id):
        url, _id = self.parse_id(_id)

        if url is None:
            return None

        self.location(url)
        self.page.url = self.absurl(url)

        if self.is_on_page(CommentPage):
            content = self.page.get_comment()
        elif self.is_on_page(ContentPage):
            m = re.match('.*#comment-(\d+)$', url)
            if m:
                content = self.page.get_comment(int(m.group(1)))
            else:
                content = self.page.get_article()

        if _id is not None:
            content.id = _id
        return content

    def _is_comment_submit_form(self, form):
        return 'comment_new' in form.action

    def post_comment(self, thread, reply_id, title, message):
        url = id2url(thread)
        if url is None:
            raise CantSendMessage('%s is not a right ID' % thread)

        self.location(url)
        assert self.is_on_page(ContentPage)
        self.location(self.page.get_post_comment_url())
        assert self.is_on_page(NewCommentPage)

        self.select_form(predicate=self._is_comment_submit_form)
        self.set_all_readonly(False)
        if title is not None:
            self['comment[title]'] = title.encode('utf-8')
        self['comment[wiki_body]'] = message.encode('utf-8')
        if int(reply_id) > 0:
            self['comment[parent_id]'] = str(reply_id)
        self['commit'] = 'Poster le commentaire'

        try:
            self.submit()
        except BrowserHTTPError, e:
            raise CantSendMessage('Unable to send message to %s.%s: %s' % (thread, reply_id, e))

        if self.is_on_page(NodePage):
            errors = self.page.get_errors()
            if len(errors) > 0:
                raise CantSendMessage('Unable to send message: %s' % ', '.join(errors))

        return None

    def login(self):
        data = {'account[login]': self.username,
                'account[password]': self.password,
                'account[remember_me]': 1}
        self.location('/compte/connexion', urllib.urlencode(data), no_login=True)
        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def is_logged(self):
        return (self.page and self.page.is_logged())

    def close_session(self):
        self.openurl('/compte/deconnexion')

    def plusse(self, url):
        return self.relevance(url, 'for')

    def moinse(self, url):
        return self.relevance(url, 'against')

    def relevance(self, url, what):
        comment = self.get_content(url)

        if comment is None:
            raise ValueError('The given URL isn\'t a comment.')

        if comment.relevance_token is None:
            return False

        res = self.readurl('%s%s' % (comment.relevance_url, what),
                           urllib.urlencode({'authenticity_token': comment.relevance_token}))

        return res

    def iter_new_board_messages(self):
        self.location('/board/index.xml')
        assert self.is_on_page(BoardIndexPage)

        msgs = self.page.get_messages(self.last_board_msg_id)
        for msg in reversed(msgs):
            self.last_board_msg_id = msg.id
            yield msg

    def board_post(self, msg):
        request = self.request_class(self.absurl('/board/'),
                                     urllib.urlencode({'board[message]': msg}),
                                     {'Referer': self.absurl('/')})
        self.readurl(request)

    def add_tag(self, _id, tag):
        url, _id = self.parse_id(_id)
        if url is None:
            return None

        self.location(url)
        assert self.is_on_page(ContentPage)

        self.location(self.page.get_tag_url())
        assert self.is_on_page(NewTagPage)

        self.page.tag(tag)
