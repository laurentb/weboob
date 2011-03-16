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
        self.username = None
        self.date = None
        self.body = u''
        self.signature = u''
        self.score = 0
        self.url = u''
        self.comments = []

        self.id = div.attrib['id'].split('-')[1]
        self.url = '%s#%s' % (article.url, div.attrib['id'])
        self.title = unicode(select(div.find('h2'), 'a.title', 1).text)
        try:
            a = select(div.find('p'), 'a[rel=author]', 1)
        except SelectElementException:
            self.author = 'Anonyme'
            self.username = None
        else:
            self.author = unicode(a.text)
            self.username = unicode(a.attrib['href'].split('/')[2])
        self.date = datetime.strptime(select(div.find('p'), 'time', 1).attrib['datetime'].split('+')[0],
                                      '%Y-%m-%dT%H:%M:%S')
        self.date = local2utc(self.date)

        content = div.find('div')
        try:
            signature = select(content, 'p.signature', 1)
        except SelectElementException:
            # No signature.
            pass
        else:
            content.remove(signature)
            self.signature = self.browser.parser.tostring(signature)
        self.body = self.browser.parser.tostring(content)

        self.score = int(select(div.find('p'), 'span.score', 1).text)
        forms = select(div.find('footer'), 'form.button_to')
        if len(forms) == 0:
            self.relevance_url = None
            self.relevance_token = None
        else:
            self.relevance_url = forms[0].attrib['action'].rstrip('for').rstrip('against')
            self.relevance_token = select(forms[0], 'input[name=authenticity_token]', 1).attrib['value']

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
        self.title = None
        self.author = None
        self.body = None
        self.date = None
        self.comments = []

        if tree is None:
            return

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

    def append_comment(self, comment):
        self.comments.append(comment)

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c

    def parse_part2(self, div):
        self.part2 = self.browser.parser.tostring(div)

class CommentPage(DLFPPage):
    def get_comment(self):
        article = Article(self.browser, self.url, None)
        return Comment(article, select(self.document.getroot(), 'li.comment', 1), 0)

class ContentPage(DLFPPage):
    def on_loaded(self):
        self.article = None

    def get_comment(self, id):
        article = Article(self.browser, self.url, None)
        try:
            li = select(self.document.getroot(), 'li#comment-%s' % id, 1)
        except SelectElementException:
            return None
        else:
            return Comment(article, li, 0)

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

    def get_tag_url(self):
        return select(self.document.getroot(), 'div.tag_in_place', 1).find('a').attrib['href']

class NewCommentPage(DLFPPage):
    pass

class NewTagPage(DLFPPage):
    def _is_tag_form(self, form):
        return form.action.endswith('/tags')

    def tag(self, tag):
        self.browser.select_form(predicate=self._is_tag_form)
        self.browser['tags'] = tag
        self.browser.submit()

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
