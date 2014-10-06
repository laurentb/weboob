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


from datetime import datetime

from weboob.deprecated.browser import BrokenPageError
from weboob.tools.date import local2utc
from ..tools import url2id

from .index import DLFPPage


class RSSComment(DLFPPage):
    def on_loaded(self):
        pass


class Content(object):
    TAGGABLE = False

    def __init__(self, browser):
        self.browser = browser
        self.url = u''
        self.id = u''
        self.title = u''
        self.author = u''
        self.username = u''
        self.body = u''
        self.date = None
        self.score = 0
        self.comments = []
        self.relevance_url = None
        self.relevance_token = None

    def is_taggable(self):
        return False


class Comment(Content):
    def __init__(self, article, div, reply_id):
        Content.__init__(self, article.browser)
        self.reply_id = reply_id
        self.signature = u''
        self.preurl = article.url
        self.div = div
        self.id = div.attrib['id'].split('-')[1]
        subs = div.find('ul')
        if subs is not None:
            for sub in subs.findall('li'):
                comment = Comment(article, sub, self.id)
                self.comments.append(comment)

    def parse(self):
        self.url = '%s#%s' % (self.preurl, self.div.attrib['id'])
        self.title = unicode(self.browser.parser.select(self.div.find('h2'), 'a.title', 1).text)
        try:
            a = self.browser.parser.select(self.div.find('p'), 'a[rel=author]', 1)
        except BrokenPageError:
            self.author = 'Anonyme'
            self.username = None
        else:
            self.author = unicode(a.text)
            self.username = unicode(a.attrib['href'].split('/')[2])
        self.date = datetime.strptime(self.browser.parser.select(self.div.find('p'), 'time', 1).attrib['datetime'].split('+')[0],
                                      '%Y-%m-%dT%H:%M:%S')
        self.date = local2utc(self.date)

        content = self.div.find('div')
        try:
            signature = self.browser.parser.select(content, 'p.signature', 1)
        except BrokenPageError:
            # No signature.
            pass
        else:
            content.remove(signature)
            self.signature = self.browser.parser.tostring(signature)
        self.body = self.browser.parser.tostring(content)

        self.score = int(self.browser.parser.select(self.div.find('p'), 'span.score', 1).text)
        forms = self.browser.parser.select(self.div.find('footer'), 'form.button_to')
        if len(forms) > 0:
            self.relevance_url = forms[0].attrib['action'].rstrip('for').rstrip('against')
            self.relevance_token = self.browser.parser.select(forms[0], 'input[name=authenticity_token]', 1).attrib['value']

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c

    def __repr__(self):
        return u"<Comment id=%r author=%r title=%r>" % (self.id, self.author, self.title)


class Article(Content):
    TAGGABLE = True

    def __init__(self, browser, url, tree):
        Content.__init__(self, browser)
        self.url = url
        self.id = url2id(self.url)

        if tree is None:
            return

        header = tree.find('header')
        self.title = u' — '.join([a.text for a in header.find('h1').xpath('.//a')])
        try:
            a = self.browser.parser.select(header, 'a[rel=author]', 1)
        except BrokenPageError:
            self.author = 'Anonyme'
            self.username = None
        else:
            self.author = unicode(a.text)
            self.username = unicode(a.attrib['href'].split('/')[2])
        self.body = self.browser.parser.tostring(self.browser.parser.select(tree, 'div.content', 1))
        try:
            self.date = datetime.strptime(self.browser.parser.select(header, 'time', 1).attrib['datetime'].split('+')[0],
                                          '%Y-%m-%dT%H:%M:%S')
            self.date = local2utc(self.date)
        except BrokenPageError:
            pass
        for form in self.browser.parser.select(tree.find('footer'), 'form.button_to'):
            if form.attrib['action'].endswith('/for'):
                self.relevance_url = form.attrib['action'].rstrip('for').rstrip('against')
                self.relevance_token = self.browser.parser.select(form, 'input[name=authenticity_token]', 1).attrib['value']

        self.score = int(self.browser.parser.select(tree, 'div.figures figure.score', 1).text)

    def append_comment(self, comment):
        self.comments.append(comment)

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c


class CommentPage(DLFPPage):
    def get_comment(self):
        article = Article(self.browser, self.url, None)
        return Comment(article, self.parser.select(self.document.getroot(), 'li.comment', 1), 0)


class ContentPage(DLFPPage):
    def on_loaded(self):
        self.article = None

    def is_taggable(self):
        return True

    def get_comment(self, id):
        article = Article(self.browser, self.url, None)
        try:
            li = self.parser.select(self.document.getroot(), 'li#comment-%s' % id, 1)
        except BrokenPageError:
            return None
        else:
            return Comment(article, li, 0)

    def get_article(self):
        if not self.article:
            self.article = Article(self.browser,
                                   self.url,
                                   self.parser.select(self.document.getroot(), 'main#contents article', 1))

            try:
                threads = self.parser.select(self.document.getroot(), 'ul.threads', 1)
            except BrokenPageError:
                pass # no comments
            else:
                for comment in threads.findall('li'):
                    self.article.append_comment(Comment(self.article, comment, 0))

        return self.article

    def get_post_comment_url(self):
        return self.parser.select(self.document.getroot(), 'p#send-comment', 1).find('a').attrib['href']

    def get_tag_url(self):
        return self.parser.select(self.document.getroot(), 'div.tag_in_place', 1).find('a').attrib['href']


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
            div = self.parser.select(self.document.getroot(), 'div.errors', 1)
        except BrokenPageError:
            return []

        l = []
        for li in div.find('ul').findall('li'):
            l.append(li.text)
        return l
