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
import urllib
from urlparse import urlsplit

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.capabilities.messages import CantSendMessage

from .pages.index import LoginPage
from .pages.forum import ForumPage, TopicPage, PostingPage
from .tools import id2url, url2id


__all__ = ['PhpBB']


# Browser
class PhpBB(Browser):
    PAGES = {'https?://.*/index.php':                 ForumPage,
             'https?://.*/':                          ForumPage,
             'https?://.*/viewforum.php\?f=(\d+)':    ForumPage,
             'https?://.*/search.php\?.*':            ForumPage,
             'https?://.*/viewtopic.php\?.*':         TopicPage,
             'https?://.*/posting.php\?.*':           PostingPage,
             'https?://.*/ucp.php\?mode=login.*':     LoginPage,
            }

    last_board_msg_id = None

    def __init__(self, url, *args, **kwargs):
        self.url = url
        v = urlsplit(url)
        self.PROTOCOL = v.scheme
        self.DOMAIN = v.netloc
        self.BASEPATH = v.path[:v.path.rfind('/')]
        Browser.__init__(self, *args, **kwargs)

    def absurl(self, rel):
        return Browser.absurl(self, '%s/%s' % (self.BASEPATH, rel))

    def home(self):
        self.location(self.url)

    def is_logged(self):
        return not self.page or self.page.is_logged()

    def login(self):
        data = {'login': 'Connexion',
                'username': self.username,
                'password': self.password,
               }
        self.location('%s/ucp.php?mode=login' % self.BASEPATH, urllib.urlencode(data), no_login=True)

        assert self.is_on_page(LoginPage)

        if not self.page.is_logged():
            raise BrowserIncorrectPassword(self.page.get_error_message())

    def get_root_feed_url(self):
        self.home()
        return self.page.get_feed_url()

    def iter_links(self, url):
        if url:
            self.location(url)
        else:
            self.home()

        assert self.is_on_page(ForumPage)
        return self.page.iter_links()

    def iter_posts(self, id, stop_id=None):
        if id.startswith('http'):
            self.location(id)
        else:
            self.location('%s/%s' % (self.BASEPATH, id2url(id)))
        assert self.is_on_page(TopicPage)

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

    def riter_posts(self, id, stop_id=None):
        if id.startswith('http'):
            self.location(id)
        else:
            self.location('%s/%s' % (self.BASEPATH, id2url(id)))
        assert self.is_on_page(TopicPage)

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

    def get_post(self, id):
        if id.startswith('http'):
            self.location(id)
            id = url2id(id)
        else:
            self.location('%s/%s' % (self.BASEPATH, id2url(id)))
        assert self.is_on_page(TopicPage)

        post = self.page.get_post(int(id.split('.')[-1]))
        if not post:
            return None

        if post.parent == 0 and self.page.cur_page > 1:
            self.location(self.page.prev_page_url())
            post.parent = self.page.get_last_post_id()

        return post

    def get_forums(self):
        self.home()
        return dict(self.page.iter_all_forums())

    def post_answer(self, forum_id, topic_id, title, content):
        if topic_id == 0:
            if not forum_id:
                forums = self.get_forums()
                forums_prompt = 'Forums list:\n%s' % ('\n'.join(['\t- %s' % f for f in forums.itervalues()]))
                m = re.match('\[(.*)\] (.*)', title or '')
                if not m:
                    raise CantSendMessage('Please enter a title formatted like that:\n\t"[FORUM] SUBJECT"\n\n%s' % forums_prompt)

                forum_id = None
                for k,v in forums.iteritems():
                    if v.lower() == m.group(1).lower():
                        forum_id = k
                        break

            if not forum_id:
                raise CantSendMessage('Forum "%s" not found.\n\n%s' % (m.group(1), forums_prompt))

            self.location('%s/posting.php?mode=post&f=%d' % (self.BASEPATH, forum_id))

            assert self.is_on_page(PostingPage)
            self.page.post(title, content)

            assert self.is_on_page(PostingPage)
            error = self.page.get_error_message()
            if error:
                raise CantSendMessage(u'Unable to send message: %s' % error)
        else:
            self.location('%s/%s' % (self.BASEPATH, id2url(topic_id)))
            assert self.is_on_page(TopicPage)

            self.page.go_reply()
            assert self.is_on_page(PostingPage)

            # Don't send title because it isn't needed in real use case
            # and with monboob title is something like:
            #   Re: [Forum Name] Re: Topic Name
            if title is not None and title.startswith('Re:'):
                title = None
            self.page.post(title, content)

            assert self.is_on_page(PostingPage)
            error = self.page.get_error_message()
            if error:
                raise CantSendMessage(u'Unable to send message: %s' % error)
