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


from datetime import datetime

from weboob.tools.parsers.lxmlparser import select, SelectElementException
from weboob.tools.misc import local2utc
from weboob.backends.dlfp.tools import url2id

from .index import DLFPPage

class Comment(object):
    def __init__(self, article, div, reply_id):
        self.browser = article.browser
        self.id = ''
        self.reply_id = reply_id
        self.title = u''
        self.author = u''
        self.date = None
        self.body = u''
        self.score = 0
        self.url = u''
        self.comments = []

        self.id = div.attrib['id'].split('-')[1]
        self.url = '%s#%s' % (article.url, div.attrib['id'])
        self.title = unicode(select(div.find('h2'), 'a.title', 1).text)
        try:
            self.author = unicode(select(div.find('p'), 'a[rel=author]', 1).text)
        except SelectElementException:
            self.author = 'Anonyme'
        self.date = datetime.strptime(select(div.find('p'), 'time', 1).attrib['datetime'].split('+')[0],
                                      '%Y-%m-%dT%H:%M:%S')
        self.date = local2utc(self.date)
        self.body = self.browser.parser.tostring(div.find('div'))
        self.score = int(select(div.find('p'), 'span.score', 1).text)

        subs = div.find('ul')
        if subs is not None:
            for sub in subs.findall('li'):
                comment = Comment(article, sub, self.id)
                self.comments.append(comment)

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c

    def __repr__(self):
        return u"<Comment id=%r author=%r title=%r>" % (self.id, self.author, self.title)

class Article(object):
    def __init__(self, browser, url, tree):
        self.browser = browser
        self.url = url
        self.id = url2id(self.url)

        header = tree.find('header')
        self.title = u' — '.join([a.text for a in header.find('h1').findall('a')])
        try:
            self.author = select(header, 'a[rel=author]', 1).text
        except SelectElementException:
            self.author = 'Anonyme'
        self.body = self.browser.parser.tostring(select(tree, 'div.content', 1))
        self.date = datetime.strptime(select(header, 'time', 1).attrib['datetime'].split('+')[0],
                                      '%Y-%m-%dT%H:%M:%S')
        self.date = local2utc(self.date)

        self.comments = []

    def append_comment(self, comment):
        self.comments.append(comment)

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c

    def parse_part2(self, div):
        self.part2 = self.browser.parser.tostring(div)

class ContentPage(DLFPPage):
    def on_loaded(self):
        self.article = None

    def get_article(self):
        if not self.article:
            self.article = Article(self.browser,
                                   self.url,
                                   select(self.document.getroot(), 'article', 1))

            try:
                threads = select(self.document.getroot(), 'ul.threads', 1)
            except SelectElementException:
                pass # no comments
            else:
                for comment in threads.findall('li'):
                    self.article.append_comment(Comment(self.article, comment, 0))

        return self.article

    def get_post_comment_url(self):
        return select(self.document.getroot(), 'p#send-comment', 1).find('a').attrib['href']

class NewCommentPage(DLFPPage):
    pass

class NodePage(DLFPPage):
    def get_errors(self):
        try:
            div = select(self.document.getroot(), 'div.errors', 1)
        except SelectElementException:
            return []

        l = []
        for li in div.find('ul').findall('li'):
            l.append(li.text)
        return l
