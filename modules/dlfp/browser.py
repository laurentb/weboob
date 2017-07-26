# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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
import hashlib
import lxml

from requests.exceptions import HTTPError

from weboob.browser import LoginBrowser, need_login, URL
from weboob.browser.exceptions import HTTPNotFound
from weboob.exceptions import BrowserIncorrectPassword, ParseError
from weboob.capabilities.messages import CantSendMessage

from .pages.index import IndexPage, LoginPage
from .pages.news import ContentPage, NewCommentPage, NodePage, CommentPage, NewTagPage, RSSComment
from .pages.board import BoardIndexPage
from .pages.wiki import WikiEditPage
from .tools import id2url, url2id

# Browser


class DLFP(LoginBrowser):
    BASEURL = 'https://linuxfr.org/'

    index = URL(r'/?$', IndexPage)
    login = URL(r'/compte/connexion', LoginPage)
    content = URL(r'/news/.+',
                  r'/wiki/(?!nouveau)[^/]+',
                  r'/suivi/[^\.]+',
                  r'/sondages/[^\.]+',
                  r'/users/[^\./]+/journaux/[^\.]+',
                  r'/forums/[^\./]+/posts/[^\.]+',
                  ContentPage)
    wiki_edit = URL(r'/wiki$',
                    r'/wiki/nouveau',
                    r'/wiki/[^\.]+/modifier',
                    WikiEditPage)
    comment = URL(r'/nodes/(\d+)/comments/(\d+)', CommentPage)
    new_comment = URL(r'/nodes/(\d+)/comments/nouveau', NewCommentPage)
    node = URL(r'/nodes/(\d+)/comments', NodePage)
    new_tag = URL(r'/nodes/(\d+)/tags/nouveau', NewTagPage)
    board_index = URL(r'/board/index.xml', BoardIndexPage)
    rss_comment = URL(r'/nodes/(\d+)/comments.atom', RSSComment)

    last_board_msg_id = None
    _token = None

    def parse_id(self, _id):
        if re.match('^https?://.*linuxfr.org/nodes/\d+/comments/\d+$', _id):
            return _id, None

        url = id2url(_id)
        if url is None:
            if url2id(_id) is not None:
                url = _id
                _id = url2id(url)
            else:
                return None, None

        return url, _id

    @need_login
    def get_wiki_content(self, _id):
        url, _id = self.parse_id('W.%s' % _id)
        if url is None:
            return None

        try:
            self.location('%s/modifier' % url)
        except HTTPNotFound:
            return ''

        assert self.wiki_edit.is_here()

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
        except HTTPNotFound:
            self.location('/wiki/nouveau')
            new = True
        else:
            new = False

        assert self.wiki_edit.is_here()

        return new

    @need_login
    def set_wiki_content(self, name, content, message):
        new = self._go_on_wiki_edit_page(name)
        if new is None:
            return None

        if new:
            title = name.replace('-', ' ')
        else:
            title = None

        self.page.post_content(title, content, message)

    @need_login
    def get_wiki_preview(self, name, content):
        if self._go_on_wiki_edit_page(name) is None:
            return None

        self.page.post_preview(content)
        if self.wiki_edit.is_here():
            return self.page.get_preview_html()
        elif self.content.is_here():
            return self.page.get_article().body

    def get_hash(self, url):
        self.location(url)
        if self.page.doc.xpath('//entry'):
            myhash = hashlib.md5(lxml.etree.tostring(self.page.doc)).hexdigest()
            return myhash
        else:
            return None

    def get_content(self, _id):
        url, _id = self.parse_id(_id)

        if url is None:
            return None

        self.location(url)

        if self.comment.is_here():
            content = self.page.get_comment()
        elif self.content.is_here():
            m = re.match('.*#comment-(\d+)$', url)
            if m:
                content = self.page.get_comment(int(m.group(1)))
            else:
                content = self.page.get_article()
        else:
            raise ParseError('Not on a content or comment page (%r)' % self.page)

        if _id is not None:
            content.id = _id
        return content

    @need_login
    def post_comment(self, thread, reply_id, title, message):
        url = id2url(thread)
        if url is None:
            raise CantSendMessage('%s is not a right ID' % thread)

        self.location(url)
        assert self.content.is_here()
        self.location(self.page.get_post_comment_url())
        assert self.new_comment.is_here()

        form = self.page.get_form(xpath='//form[contains(@action,"comment_new")]')
        if title is not None:
            form['comment[title]'] = title.encode('utf-8')
        form['comment[wiki_body]'] = message.encode('utf-8')
        if int(reply_id) > 0:
            form['comment[parent_id]'] = str(reply_id)
        form['commit'] = 'Poster le commentaire'

        try:
            form.submit()
        except HTTPError as e:
            raise CantSendMessage('Unable to send message to %s.%s: %s' % (thread, reply_id, e))

        if self.node.is_here():
            errors = self.page.get_errors()
            if len(errors) > 0:
                raise CantSendMessage('Unable to send message: %s' % ', '.join(errors))

        return None

    def do_login(self):
        if self.username is None:
            return

        # not usefull for the moment
        #self.location('/', no_login=True)
        data = {'account[login]': self.username,
                'account[password]': self.password,
                'account[remember_me]': 1,
                #'authenticity_token': self.page.get_login_token(),
               }
        self.location('/compte/connexion', data=data)
        if not self.is_logged():
            raise BrowserIncorrectPassword()
        self._token = self.page.doc.xpath('//input[@name="authenticity_token"]')

    def is_logged(self):
        return (self.username is None or (self.page and self.page.logged))

    def close_session(self):
        if self._token:
            self.open('/compte/deconnexion', data={'authenticity_token': self._token[0].attrib['value']})

    def plusse(self, url):
        return self.relevance(url, 'for')

    def moinse(self, url):
        return self.relevance(url, 'against')

    @need_login
    def relevance(self, url, what):
        comment = self.get_content(url)

        if comment is None:
            raise ValueError('The given URL isn\'t a comment.')

        if comment.relevance_token is None:
            return False

        res = self.open('%s%s' % (comment.relevance_url, what),
                        data={'authenticity_token': comment.relevance_token}).content

        return res

    def iter_new_board_messages(self):
        self.location('/board/index.xml')
        assert self.board_index.is_here()

        msgs = self.page.get_messages(self.last_board_msg_id)
        for msg in reversed(msgs):
            self.last_board_msg_id = msg.id
            yield msg

    @need_login
    def board_post(self, msg):
        self.open(self.absurl('/board/'), data={'board[message]': msg},
                  headers={'Referer': self.absurl('/')})

    @need_login
    def add_tag(self, _id, tag):
        url, _id = self.parse_id(_id)
        if url is None:
            return None

        self.location(url)
        assert self.content.is_here()

        self.location(self.page.get_tag_url())
        assert self.new_tag.is_here()

        self.page.tag(tag)
