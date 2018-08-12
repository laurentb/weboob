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

from weboob.browser import URL, LoginBrowser, need_login
from weboob.capabilities.messages import CantSendMessage
from weboob.exceptions import BrowserIncorrectPassword

from .pages.forum import ForumPage, PostingPage, TopicPage
from .pages.index import LoginPage
from .tools import id2url, url2id

__all__ = ['PhpBB']


# Browser
class PhpBB(LoginBrowser):
    forum = URL(r'.*index.php',
                r'/$',
                r'.*viewforum.php\?f=(\d+)',
                r'.*search.php\?.*',
                ForumPage)
    topic = URL(r'.*viewtopic.php\?.*', TopicPage)
    posting = URL(r'.*posting.php\?.*', PostingPage)
    login = URL(r'.*ucp.php\?mode=login.*', LoginPage)

    last_board_msg_id = None

    def __init__(self, url, *args, **kwargs):
        self.BASEURL = url
        super(PhpBB, self).__init__(*args, **kwargs)

    def home(self):
        self.location(self.BASEURL)

    def do_login(self):
        data = {'login': 'Connexion',
                'username': self.username,
                'password': self.password,
                }
        self.location('ucp.php?mode=login', data=data)

        if not self.page.logged:
            raise BrowserIncorrectPassword(self.page.get_error_message())

    @need_login
    def get_root_feed_url(self):
        self.home()
        return self.page.get_feed_url()

    @need_login
    def iter_links(self, url):
        if url:
            self.location(url)
        else:
            self.home()

        assert self.forum.is_here()
        return self.page.iter_links()

    @need_login
    def iter_posts(self, id, stop_id=None):
        if id.startswith('http'):
            self.location(id)
        else:
            self.location('%s/%s' % (self.BASEURL, id2url(id)))
        assert self.topic.is_here()

        parent = 0
        while True:
            for post in self.page.iter_posts():
                if stop_id and post.id >= stop_id:
                    return

                post.parent = parent
                yield post
                parent = post.id

            if self.page.cur_page == self.page.tot_pages:
                return
            self.location(self.page.next_page_url())

    @need_login
    def riter_posts(self, id, stop_id=None):
        if id.startswith('http'):
            self.location(id)
        else:
            self.location('%s/%s' % (self.BASEURL, id2url(id)))
        assert self.topic.is_here()

        child = None
        while True:
            for post in self.page.riter_posts():
                if child:
                    child.parent = post.id
                    yield child
                if post.id <= stop_id:
                    return
                child = post

            if self.page.cur_page == 1:
                if child:
                    yield child
                return
            self.location(self.page.prev_page_url())

    @need_login
    def get_post(self, id):
        if id.startswith('http'):
            self.location(id)
            id = url2id(id)
        else:
            self.location('%s/%s' % (self.BASEURL, id2url(id)))
        assert self.topic.is_here()

        post = self.page.get_post(int(id.split('.')[-1]))
        if not post:
            return None

        if post.parent == 0 and self.page.cur_page > 1:
            self.location(self.page.prev_page_url())
            post.parent = self.page.get_last_post_id()

        return post

    @need_login
    def get_forums(self):
        self.home()
        return dict(self.page.iter_all_forums())

    @need_login
    def post_answer(self, forum_id, topic_id, title, content):
        if topic_id == 0:
            if not forum_id:
                forums = self.get_forums()
                forums_prompt = 'Forums list:\n%s' % ('\n'.join(['\t- %s' % f for f in forums.itervalues()]))
                m = re.match('\[(.*)\] (.*)', title or '')
                if not m:
                    raise CantSendMessage('Please enter a title formatted like that:\n\t"[FORUM] SUBJECT"\n\n%s' % forums_prompt)

                forum_id = None
                for k, v in forums.items():
                    if v.lower() == m.group(1).lower():
                        forum_id = k
                        break

            if not forum_id:
                raise CantSendMessage('Forum "%s" not found.\n\n%s' % (m.group(1), forums_prompt))

            self.location('%s/posting.php?mode=post&f=%d' % (self.BASEURL, forum_id))

            assert self.posting.is_here()
            self.page.post(title, content)

            assert self.posting.is_here()
            error = self.page.get_error_message()
            if error:
                raise CantSendMessage(u'Unable to send message: %s' % error)
        else:
            self.location('%s/%s' % (self.BASEURL, id2url('%s.%s' % (forum_id, topic_id))))
            assert self.topic.is_here()

            self.page.go_reply()
            assert self.posting.is_here()

            # Don't send title because it isn't needed in real use case
            # and with monboob title is something like:
            #   Re: [Forum Name] Re: Topic Name
            if title is not None and title.startswith('Re:'):
                title = None
            self.page.post(title, content)

            assert self.posting.is_here() or self.topic.is_here()
            error = self.page.get_error_message()
            if error:
                raise CantSendMessage(u'Unable to send message: %s' % error)
