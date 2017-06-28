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


from time import sleep

from weboob.deprecated.browser import BrokenPageError
from weboob.browser.filters.standard import CleanText
from weboob.tools.compat import urlsplit, parse_qs

from .index import PhpBBPage
from ..tools import parse_date


class Link(object):
    (FORUM,
     TOPIC) = xrange(2)

    def __init__(self, type, url):
        self.type = type
        self.url = url
        self.title = u''
        self.date = None


class ForumPage(PhpBBPage):
    def iter_links(self):
        for li in self.doc.xpath('//ul[has-class("forums")]//li[has-class("row")]'):
            title = li.xpath('.//a[has-class("forumtitle")]')[0]
            link = Link(Link.FORUM, title.attrib['href'])
            link.title = title.text.strip()
            yield link

        for li in self.doc.xpath('//ul[has-class("topics")]//li[has-class("row")]'):
            title = li.xpath('.//a[has-class("topictitle")]')[0]
            link = Link(Link.TOPIC, title.attrib['href'])
            link.title = title.text.strip()
            for a in li.find('dl').find('dt').findall('a'):
                for text in (a.text, a.tail):
                    if text is None:
                        continue
                    try:
                        link.date = parse_date(text.strip(u'» \r\n'))
                    except ValueError:
                        continue
                    else:
                        break
            yield link

    def iter_all_forums(self):
        for option in self.doc.xpath('//select[@id="f"]//option'):
            value = int(option.attrib['value'])
            if value < 0 or not option.text:
                continue

            yield value, option.text.strip(u'» \xa0\n\r')


class Post(object):
    def __init__(self, forum_id, topic_id, id):
        self.id = int(id)
        self.forum_id = forum_id
        self.topic_id = topic_id
        self.title = u''
        self.author = u''
        self.date = None
        self.content = u''
        self.signature = u''
        self.parent = 0


class TopicPage(PhpBBPage):
    def on_load(self):
        div = self.doc.xpath('//div[has-class("pagination")]')[0]
        strongs = div.xpath('.//strong')
        self.cur_page = int(strongs[0].text.strip())
        self.tot_pages = int(strongs[1].text.strip())

        try:
            url = self.doc.xpath('//h2/a')[-1].attrib['href']
        except BrokenPageError:
            url = self.url
        v = urlsplit(url)
        args = parse_qs(v.query)
        self.topic_id = int(args['t'][0])
        self.forum_id = int(args['f'][0]) if 'f' in args else 0

        self.forum_title = u''
        nav = self.doc.xpath('//li[has-class("icon-home")]')
        if len(nav) > 0:
            text = nav[0].xpath('.//a')[-1].text.strip()
            if len(text) >= 20:
                text = text[:20] + u'…'
            self.forum_title = '[%s] ' % text

    def go_reply(self):
        for url in self.doc.xpath('//a[contains(@href,"posting.php")]/@href'):
            return self.browser.location(url)

    def next_page_url(self):
        try:
            return self.doc.xpath('//a[has-class("right-box")]')[0].attrib['href']
        except BrokenPageError:
            a_list = self.doc.xpath('//div[has-class("pagination")]')[0].findall('a')
            if self.cur_page == self.tot_pages:
                return '#'
            return a_list[-1].attrib['href']

    def prev_page_url(self):
        try:
            return self.doc.xpath('//a[has-class("left-box")]')[0].attrib['href']
        except BrokenPageError:
            a_list = self.doc.xpath('//div[has-class("pagination")]')[0].findall('a')
            if self.cur_page == self.tot_pages:
                a = a_list[-1]
            else:
                a = a_list[-2]
            return a.attrib['href']

    def iter_posts(self):
        for div in self.doc.xpath('//div[has-class("post")]'):
            yield self._get_post(div)

    def riter_posts(self):
        for div in reversed(self.doc.xpath('//div[has-class("post")]')):
            yield self._get_post(div)

    def get_post(self, id):
        parent = 0
        for div in self.doc.xpath('//div[has-class("post")]'):
            if div.attrib['id'] == 'p%d' % id:
                post = self._get_post(div)
                post.parent = parent
                return post
            else:
                parent = int(div.attrib['id'][1:])

    def _get_post(self, div):
        body = div.xpath('.//div[has-class("postbody")]')[0]
        profile = div.xpath('.//dl[has-class("postprofile")]')[0]

        id = div.attrib['id'][1:]
        post = Post(self.forum_id, self.topic_id, id)

        title_tags = body.xpath('.//h3/a')
        if len(title_tags) == 0:
            title_tags = self.doc.xpath('//h2/a')
        if len(title_tags) == 0:
            title = u''
            self.logger.warning('Unable to parse title')
        else:
            title = title_tags[-1].text.strip()

        post.title = self.forum_title + title
        for a in profile.xpath('.//dt//a'):
            if a.text:
                post.author = a.text.strip()

        p_tags = body.xpath('.//p[has-class("author")]')
        if len(p_tags) == 0:
            p_tags = body.find('p')
        if len(p_tags) == 0:
            post.date = None
            self.logger.warning('Unable to parse datetime')
        else:
            p = p_tags[0]
            text = p.find('strong') is not None and p.find('strong').tail
            if not text:
                text = ''.join(t.strip() for t in p.xpath('./text()')).strip()

            text = text.strip(u'» \n\r')
            try:
                post.date = parse_date(text)
            except ValueError:
                self.logger.warning(u'Unable to parse datetime "%s"' % text)

        post.content = CleanText().filter(body.xpath('.//div[has-class("content")]')[0])

        signature = body.xpath('.//div[has-class("signature")]')
        if len(signature) > 0:
            post.signature = CleanText().filter(signature[0])
        return post

    def get_last_post_id(self):
        id = 0
        for div in self.doc.xpath('//div[has-class("post")]'):
            id = int(div.attrib['id'][1:])
        return id


class PostingPage(PhpBBPage):
    def post(self, title, content):
        form = self.get_form(id='postform')

        if title:
            form['subject'] = title.encode('utf-8')
        form['message'] = content.encode('utf-8')

        # This code on phpbb:
        #   if ($cancel || ($current_time - $lastclick < 2 && $submit))
        #   {
        #       /* ... */
        #       redirect($redirect);
        #   }
        # To prevent that shit because weboob is too fast, we simulate
        # a value of lastclick 10 seconds before.
        form['lastclick'] = str(int(form['lastclick']) - 10)
        form.setdefault('post', 'Submit')
        form.pop('save', '')
        form.pop('preview', '')

        # Likewise for create_time, with this check:
        #   $diff = time() - $creation_time;
        #   // If creation_time and the time() now is zero we can assume it was not a human doing this (the check for if ($diff)...
        #   if ($diff && ($diff <= $timespan || $timespan === -1))
        # But as the form_token depends on the create_time value, I can't
        # change it. But I can wait a second before posting...
        sleep(1)

        form.submit(name='post')
